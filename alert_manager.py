"""
Handles bad posture warnings and screen locking logic.
"""

import subprocess
import threading
import time
import logging
from typing import Optional
from posture_analyser import PostureResult

class AlertManager:
    def __init__(self, overlay_class=None):
        """
        Initialize the alert manager.

        Args:
            overlay_class (type): The overlay UI class to instantiate for warnings.
                                  Passed as a class to avoid circular imports.
        """
        self.overlay_class = overlay_class
        self.bad_posture_start_time: Optional[float] = None
        self.is_paused = False
        self.lock_delay = 10.0  # Default 10 seconds from SRD
        self.logger = logging.getLogger(__name__)
        self.correction_overlay_active = False

    def update(self, result: PostureResult):
        """
        Process a new posture result and trigger alerts if necessary.

        Args:
            result: The latest analysis result from PostureAnalyser.
        """
        if self.is_paused or result.status == "UNKNOWN":
            return

        if result.status == "BAD":
            if self.bad_posture_start_time is None:
                # Start the continuous bad posture timer
                self.bad_posture_start_time = time.time()
                self.logger.info("Bad posture detected. Timer started.")

            elapsed = time.time() - self.bad_posture_start_time
            if elapsed >= self.lock_delay:
                self.logger.warning(f"Bad posture sustained for {self.lock_delay}s. Triggering alert.")
                # Reset timer so we don't trigger repeatedly during the lock sequence
                self.bad_posture_start_time = None
                # Run the alert sequence in a separate thread to avoid blocking the camera loop
                threading.Thread(target=self._run_alert_sequence, daemon=True).start()
        else:
            # Status is GOOD: reset the timer
            if self.bad_posture_start_time is not None:
                self.logger.info("Posture returned to GOOD. Timer reset.")
            self.bad_posture_start_time = None

    def _run_alert_sequence(self):
        """Internal sequence: Warning Overlay (3s) -> Correction Overlay."""
        try:
            # 1. Show warning overlay for 3 seconds (simulated since we can't block)
            self.logger.info("Triggering posture warning.")
            time.sleep(3)

            # 2. Launch the Correction Overlay
            # This requires the UI to be handled by the main app's thread
            # because Tkinter on macOS is strict.
            # We'll signal the main app to show the overlay.
            self.logger.info("Bad posture sustained. Launching correction overlay.")

            # Since AlertManager doesn't have a direct reference to the App,
            # we will implement a callback or a flag.
            # For now, we'll assume the App handles the actual window launch
            # when this sequence is triggered.

            # In the current architecture, we'll use a simple flag or a custom event.
            # Let's modify the logic to just 'trigger' the correction state.
            self.correction_overlay_active = True
        except Exception as e:
            self.logger.error(f"Error in alert sequence: {e}")

    def lock_screen(self, dry_run=False):
        """Lock the macOS screen (Deprecated in favor of Correction Overlay)."""
        self.logger.info("Lock screen call ignored - using Correction Overlay instead.")
        pass

    def _handle_accessibility_error(self):
        """Notify user to grant Accessibility permissions."""
        import tkinter as tk
        from tkinter import messagebox

        # We use a temporary root window to show the dialog
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Permissions Required",
            "PostureGuard needs Accessibility permissions to lock your screen.\n\n"
            "Please go to: System Settings > Privacy & Security > Accessibility\n"
            "and enable PostureGuard."
        )
        root.destroy()

    def pause(self):
        """Pause posture monitoring."""
        self.is_paused = True
        self.bad_posture_start_time = None
        self.logger.info("Alert monitoring paused.")

    def resume(self):
        """Resume posture monitoring."""
        self.is_paused = False
        self.logger.info("Alert monitoring resumed.")
