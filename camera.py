"""
Camera capture loop. Handles frame acquisition and distribution.
"""

import cv2
import threading
import time
import logging

class CameraModule:
    def __init__(self, callback, interval=2.0):
        """
        Initialize the camera module.

        Args:
            callback (callable): Function to call with the captured frame.
            interval (float): Time in seconds between captures.
        """
        self.callback = callback
        self.interval = interval
        self.cap = None
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(__name__)

    def start(self):
        """
        Start the camera capture loop in a background thread.

        Raises:
            RuntimeError: If the camera cannot be opened.
            PermissionError: If camera access is denied.
        """
        if self.running:
            return

        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Could not open default camera (index 0).")
        except Exception as e:
            # On some macOS versions, permission denial manifests as not being able to open the device
            # or a specific error during read.
            raise RuntimeError(f"Camera access error: {e}")

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        self.logger.info("Camera capture started.")

    def stop(self):
        """Cleanly release the camera and stop the background thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.logger.info("Camera capture stopped.")

    def _capture_loop(self):
        """Internal loop that captures frames at the specified interval."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.callback(frame)
            else:
                self.logger.error("Failed to capture frame from camera.")

            time.sleep(self.interval)
