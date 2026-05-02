"""
Main entry point for PostureGuard.
Integrates Camera, Analyser, AlertManager, SessionTimer, and the Rumps menu bar app.
"""

import rumps
import threading
import logging
import os
from config import load_config, save_config, CONFIG_FILE
from camera import CameraModule
from posture_analyser import PostureAnalyser
from alert_manager import AlertManager
from session_timer import SessionTimer
from ui.calibration_ui import CalibrationUI
from ui.overlay import PostureWarningOverlay

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PostureGuard")

def _run_calibration_worker():
    """Standalone worker function for multiprocessing.
    Must be defined at top-level to be picklable.
    """
    try:
        from ui.calibration_ui import CalibrationUI
        from camera import CameraModule
        from posture_analyser import PostureAnalyser
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("CalibrationWorker")

        cam = CameraModule(callback=lambda x: None)
        cam.start()
        analyser = PostureAnalyser()

        cal_ui = CalibrationUI(cam, analyser)
        cal_ui.run()
    except Exception as e:
        print(f"Calibration process error: {e}")
    finally:
        try:
            cam.stop()
        except:
            pass

class PostureGuardApp(rumps.App):
    def __init__(self):
        super().__init__("PostureGuard")

        # Load configuration
        self.config = load_config()

        # Core components
        self.analyser = PostureAnalyser()
        self.alert_manager = AlertManager(overlay_class=PostureWarningOverlay)

        # Session Timer setup
        self.session_timer = SessionTimer(
            on_break_complete=self.on_break_complete,
            on_break_trigger=self.trigger_walk_ui,
            lock_callback=self.alert_manager.lock_screen
        )

        # Camera setup
        self.camera = CameraModule(
            callback=self.process_frame,
            interval=self.config['timers']['camera_check_interval_seconds']
        )

        # Debug window buffer
        self.debug_frame_buffer = None

        # Menu setup
        self.menu = [
            rumps.MenuItem("Status: Initializing...", callback=None),
            rumps.MenuItem("Session: 00:00", callback=None),
            None,
            rumps.MenuItem("Pause Monitoring", callback=self.toggle_monitoring),
            rumps.MenuItem("Re-Calibrate", callback=self.run_calibration),
            rumps.MenuItem(f"Debug View ({'ON' if self.config['ui'].get('show_debug_overlay', False) else 'OFF'})", callback=self.toggle_debug_view),
            None,
            rumps.MenuItem("Quit PostureGuard", callback=self.quit_app),
        ]

        # Set initial title instead of icon, as rumps.App.icon expects a file path
        self.title = "⏸"

    def on_break_complete(self):
        """Callback for when the walk break is finished."""
        logger.info("Walk break completed. Resuming monitoring.")
        self.session_timer.notify_break_finished()
        self.resume_monitoring()

    def trigger_walk_ui(self):
        """Launched by session_timer to show the walk break window."""
        from ui.walk_reminder import WalkReminderWindow
        logger.info("Launching walk reminder UI.")
        threading.Thread(
            target=lambda: WalkReminderWindow(on_resume_callback=self.on_break_complete).show(),
            daemon=True
        ).start()

    def process_frame(self, frame):
        """Callback invoked by CameraModule every 2 seconds."""
        try:
            result = self.analyser.analyze_frame(
                frame,
                self.config['calibration'],
                self.config['thresholds']
            )

            # Update alert manager (handles timers and locking)
            self.alert_manager.update(result)

            # Debug Overlay Logic
            if self.config['ui'].get('show_debug_overlay', False):
                self.show_debug_window(frame, result)

            # Update UI components (must be done on main thread for rumps)
            self.update_ui_status(result)

        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    def show_debug_window(self, frame, result):
        """Prepares the debug frame and stores it in the buffer."""
        import cv2
        import mediapipe as mp

        try:
            # Create a copy to avoid modifying the original frame
            debug_frame = frame.copy()

            # Draw landmarks
            mp_drawing = mp.solutions.drawing_utils
            mp_pose = mp.solutions.pose

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.analyser.pose.process(image_rgb)

            if res.pose_landmarks:
                mp_drawing.draw_landmarks(
                    debug_frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # Draw status and checks
            y0, x0 = 30, 10
            font = cv2.FONT_HERSHEY_SIMPLEX

            # Overall Status
            color = (0, 255, 0) if result.status == "GOOD" else (0, 0, 255) if result.status == "BAD" else (255, 255, 255)
            cv2.putText(debug_frame, f"STATUS: {result.status}", (x0, y0), font, 1, color, 2, cv2.LINE_AA)

            # Individual Checks
            y_offset = 70
            for check, passed in result.checks.items():
                check_color = (0, 255, 0) if not passed else (0, 0, 255) # SRD: bad if True, so passed if False
                text = f"{check}: {'PASS' if not passed else 'FAIL'}"
                cv2.putText(debug_frame, text, (x0, y_offset), font, 0.6, check_color, 1, cv2.LINE_AA)
                y_offset += 30

            # Store in buffer instead of calling cv2.imshow directly
            self.debug_frame_buffer = debug_frame
        except Exception as e:
            logger.error(f"Debug frame preparation error: {e}")

    def update_ui_status(self, result):
        """Updates the menu bar icon and text based on posture result."""
        if self.alert_manager.is_paused:
            self.title = "⏸"
        elif result.status == "BAD":
            if self.alert_manager.bad_posture_start_time is not None:
                self.title = "⚠️"
            else:
                self.title = "✅"
        elif result.status == "GOOD":
            self.title = "✅"
        else: # UNKNOWN
            self.title = "⚪"

        status_text = f"Status: {result.status}"
        seconds = self.session_timer.cumulative_seconds
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        session_text = f"Session: {hours:02d}:{mins:02d}:{secs:02d}"

        # Robust update: match items by content and update them
        for item in self.menu:
            if not item or not hasattr(item, 'title'):
                continue

            current_title = item.title
            if isinstance(current_title, str):
                if current_title.startswith("Status:"):
                    item.title = status_text
                elif current_title.startswith("Session:"):
                    item.title = session_text

    def toggle_monitoring(self, _):
        """Toggles the monitoring state between paused and active."""
        if self.alert_manager.is_paused:
            self.resume_monitoring()
        else:
            self.pause_monitoring()

    def pause_monitoring(self):
        self.alert_manager.pause()
        self.session_timer.pause()
        for item in self.menu:
            if item and hasattr(item, 'title') and isinstance(item.title, str):
                if item.title == "Pause Monitoring":
                    item.title = "Resume Monitoring"
        self.title = "⏸"
        logger.info("Monitoring paused.")

    def resume_monitoring(self):
        self.alert_manager.resume()
        self.session_timer.resume()
        for item in self.menu:
            if item and hasattr(item, 'title') and isinstance(item.title, str):
                if item.title == "Resume Monitoring":
                    item.title = "Pause Monitoring"
        logger.info("Monitoring resumed.")

    def toggle_debug_view(self, _):
        """Toggles the debug overlay setting in config and updates UI."""
        current = self.config['ui'].get('show_debug_overlay', False)
        self.config['ui']['show_debug_overlay'] = not current
        save_config(self.config)

        # Find the Debug View menu item and update its label
        for item in self.menu:
            if item and hasattr(item, 'title'):
                current_title = item.title
                if isinstance(current_title, str) and "Debug View" in current_title:
                    status = "ON" if self.config['ui']['show_debug_overlay'] else "OFF"
                    item.title = f"Debug View ({status})"

        logger.info(f"Debug view toggled to: {self.config['ui']['show_debug_overlay']}")

    def quit_app(self, _):
        """Cleanly stops all background threads and exits."""
        logger.info("Quitting PostureGuard...")

        # Close OpenCV windows if they exist
        import cv2
        cv2.destroyAllWindows()

        self.camera.stop()
        self.session_timer.stop()
        rumps.app.quit(self)

    def run_calibration(self, _=None):
        """Opens the calibration wizard."""
        logger.info("User requested re-calibration.")

        self.pause_monitoring()

        # We use multiprocessing to avoid macOS Tkinter threading crashes.
        # The worker must be a top-level function to be picklable.
        import multiprocessing
        p = multiprocessing.Process(target=_run_calibration_worker)
        p.start()

        # Start a timer to monitor the process and resume monitoring when it ends
        self.calib_watch_timer = rumps.Timer(lambda _: self._check_calibration_status(p), 1.0)
        self.calib_watch_timer.start()

    def _run_calibration_process(self):
        """Standalone process entry point to run calibration UI."""
        try:
            # Re-initialize necessary components for the new process
            # Note: Camera and Analyser need to be compatible with multiprocessing
            from ui.calibration_ui import CalibrationUI
            from camera import CameraModule
            from posture_analyser import PostureAnalyser

            cam = CameraModule(callback=lambda x: None)
            cam.start()
            analyser = PostureAnalyser()

            cal_ui = CalibrationUI(cam, analyser)
            cal_ui.run()

            # Note: Since this is a separate process, it cannot directly
            # update the main app's config object in memory.
            # calibration_ui.run() already saves the config to disk via save_config().
        except Exception as e:
            print(f"Calibration process error: {e}")
        finally:
            # Clean up camera in the process
            try:
                cam.stop()
            except:
                pass

    def _start_calibration_ui_main(self, _):
        """Main-thread wrapper to launch the calibration UI."""
        # Stop the timer so it only runs once
        self.calibration_timer.stop()

        try:
            # Create and run the calibration UI
            cal_ui = CalibrationUI(self.camera, self.analyser)
            cal_ui.run()

            # After the window is closed, refresh config and resume
            logger.info("Calibration window closed. Refreshing configuration.")
            self.config = load_config()

            # Ensure camera callback is restored and monitoring starts
            self.resume_monitoring()
            self.session_timer.resume()
        except Exception as e:
            logger.error(f"Calibration UI error: {e}")
            self.resume_monitoring()
            self.session_timer.resume()

    def start_app(self):
        """Initializes all modules and starts the app."""
        try:
            # 1. Check for first-run calibration
            if not os.path.exists(CONFIG_FILE):
                logger.info("First run detected. Starting calibration.")
                # Start camera first so calibration UI has a feed
                self.camera.start()
                self.run_calibration()
            else:
                # Normal startup
                self.camera.start()
                self.session_timer.start()
                self.resume_monitoring()

            # Start a timer to handle OpenCV imshow on the main thread
            # Reduced interval to 10ms for a smooth, near-constant refresh rate
            self.debug_timer = rumps.Timer(self._update_debug_window, 0.01)
            self.debug_timer.start()
        except RuntimeError as e:
            logger.error(f"Critical startup error: {e}")
            self._handle_startup_error(str(e))
        except Exception as e:
            logger.error(f"Unexpected startup error: {e}")
            self._handle_startup_error(str(e))

            # Start a timer to handle OpenCV imshow on the main thread
            # Reduced interval to 10ms for a smooth, near-constant refresh rate
            self.debug_timer = rumps.Timer(self._update_debug_window, 0.01)
            self.debug_timer.start()
        except RuntimeError as e:
            logger.error(f"Critical startup error: {e}")
            self._handle_startup_error(str(e))
        except Exception as e:
            logger.error(f"Unexpected startup error: {e}")
            self._handle_startup_error(str(e))

    def _update_debug_window(self, _):
        """Main-thread callback to refresh the OpenCV debug window."""
        if self.config['ui'].get('show_debug_overlay', False) and self.debug_frame_buffer is not None:
            import cv2
            cv2.imshow("PostureGuard Debug View", self.debug_frame_buffer)
            cv2.waitKey(1)

    def _check_calibration_status(self, process):
        """Polls the calibration process and resumes monitoring when it exits."""
        if not process.is_alive():
            logger.info("Calibration process ended. Resuming monitoring.")
            self.calib_watch_timer.stop()
            self.config = load_config() # Refresh baselines from disk
            self.resume_monitoring()
            self.session_timer.resume()
        else:
            # Process is still running, keep the timer going
            pass

    def _handle_startup_error(self, error_msg):
        """Displays error dialog and quits the app if camera is unavailable."""
        import tkinter as tk
        from tkinter import messagebox
        import webbrowser

        # Identify if it's a camera/permission issue
        if "camera" in error_msg.lower() or "Could not open" in error_msg:
            # Try to open System Settings Privacy Camera page
            webbrowser.open("x-apple.systempreferences:com.apple.preference.security?Privacy_Camera")

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Camera Error",
                f"PostureGuard cannot access the camera:\n{error_msg}\n\n"
                "Please ensure the camera is connected and permissions are granted in System Settings."
            )
            root.destroy()
            logger.info("Critical camera error. Exiting app.")
            os._exit(1)
        else:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Startup Error", f"An unexpected error occurred:\n{error_msg}")
            root.destroy()

if __name__ == "__main__":
    app = PostureGuardApp()
    app.start_app()
    app.run()
