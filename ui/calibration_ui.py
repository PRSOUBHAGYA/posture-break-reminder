"""
Tkinter window for the calibration wizard.
"""

import tkinter as tk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
from calibration import CalibrationManager
from config import save_config, load_config

class CalibrationUI:
    def __init__(self, camera_module, analyser):
        """
        Initialize the calibration UI.

        Args:
            camera_module: The CameraModule instance for live preview.
            analyser: The PostureAnalyser instance.
        """
        self.camera_module = camera_module
        self.analyser = analyser
        self.calibrator = CalibrationManager(analyser)

        # Window setup
        self.root = tk.Tk()
        self.root.title("PostureGuard Calibration")
        self.root.geometry("800x700")

        # Instructions label
        self.instr_label = tk.Label(
            self.root,
            text="Sit up straight, look at the camera.\nHold for 5 seconds.",
            font=("Arial", 16, "bold"),
            pady=20
        )
        self.instr_label.pack()

        # Video preview label
        self.video_label = tk.Label(self.root)
        self.video_label.pack(expand=True)

        # Countdown label
        self.countdown_label = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 24),
            fg="red",
            pady=10
        )
        self.countdown_label.pack()

        # Start button
        self.start_btn = tk.Button(
            self.root,
            text="Start Calibration",
            command=self.start_calibration,
            font=("Arial", 14),
            padx=20,
            pady=10
        )
        self.start_btn.pack(pady=20)

        self.is_calibrating = False
        self.last_frame = None

    def update_preview(self):
        """Updates the Tkinter label with the current camera frame."""
        if self.last_frame is not None:
            # Resize for display
            frame = cv2.resize(self.last_frame, (640, 480))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            self.video_label.config(image=img_tk)
            self.video_label.image = img_tk

        self.root.after(30, self.update_preview)

    def start_calibration(self):
        """Starts the 5-second calibration countdown and data capture."""
        self.start_btn.config(state=tk.DISABLED)
        self.is_calibrating = True

        # Start capture thread to avoid freezing UI
        threading.Thread(target=self._calibration_thread, daemon=True).start()

    def _calibration_thread(self):
        """Handles the countdown and landmark data collection."""
        # 1. Countdown period (where we don't capture yet, just wait)
        for i in range(5, 0, -1):
            self.countdown_label.config(text=f"Get ready... {i}")
            time.sleep(1)

        self.countdown_label.config(text="Capturing! Stay still...")

        # 2. Actual capture period (e.g., 3 seconds of frames)
        start_time = time.time()
        while time.time() - start_time < 3:
            if self.last_frame is not None:
                self.calibrator.add_frame_data(self.last_frame)
            time.sleep(0.1) # Sample at ~10fps

        self.countdown_label.config(text="Processing...")

        try:
            baselines = self.calibrator.compute_baselines()

            # Update and save config
            current_config = load_config()
            current_config['calibration'].update(baselines)
            save_config(current_config)

            self.root.after(0, lambda: self._finish_calibration(True))
        except Exception as e:
            self.root.after(0, lambda: self._finish_calibration(False, str(e)))

    def _finish_calibration(self, success, error_msg=""):
        """Displays completion message and closes the window."""
        if success:
            messagebox.showinfo("Calibration", "Calibration complete!\nYour baseline posture has been saved.")
        else:
            messagebox.showerror("Calibration Error", f"Calibration failed: {error_msg}")

        self.root.destroy()

    def run(self):
        """Run the Tkinter main loop."""
        # We need to connect the camera module's callback to set self.last_frame
        def frame_callback(frame):
            self.last_frame = frame

        # Temporary override of camera callback for preview
        original_callback = self.camera_module.callback
        self.camera_module.callback = frame_callback

        self.update_preview()
        self.root.mainloop()

        # Restore original callback
        self.camera_module.callback = original_callback
