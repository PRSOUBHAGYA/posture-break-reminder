"""
Tracks 30-minute sitting sessions and 5-minute walk breaks.
"""

import threading
import time
import subprocess
import logging
from typing import Callable, Optional

class SessionTimer:
    def __init__(self, on_break_complete: Callable[[], None], on_break_trigger: Callable[[], None], lock_callback: Optional[Callable[[], None]] = None):
        """
        Initialize session timer.

        Args:
            on_break_complete (callable): Callback to run when the 5-minute walk is finished.
            on_break_trigger (callable): Callback to launch the walk break UI.
            lock_callback (callable, optional): Callback to use for locking the screen.
                                              If None, the default AppleScript lock is used.
        """
        self.on_break_complete = on_break_complete
        self.on_break_trigger = on_break_trigger
        self.lock_callback = lock_callback

        self.cumulative_seconds = 0
        self.is_running = False
        self.is_paused = False

        self.timer_thread = None
        self.logger = logging.getLogger(__name__)

        # Settings from SRD
        self.sitting_limit_seconds = 30 * 60  # 30 minutes
        self.walk_break_seconds = 5 * 60      # 5 minutes

    def start(self):
        """Start the session timer background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.is_paused = False
        self.timer_thread = threading.Thread(target=self._tick, daemon=True)
        self.timer_thread.start()
        self.logger.info("Session timer started.")

    def stop(self):
        """Stop the session timer thread."""
        self.is_running = False
        if self.timer_thread:
            self.timer_thread.join(timeout=1.0)
        self.logger.info("Session timer stopped.")

    def pause(self):
        """Pause the cumulative sitting timer."""
        self.is_paused = True
        self.logger.info("Session timer paused.")

    def resume(self):
        """Resume the cumulative sitting timer."""
        self.is_paused = False
        self.logger.info("Session timer resumed.")

    def reset(self):
        """Reset the cumulative sitting time to zero."""
        self.cumulative_seconds = 0
        self.logger.info("Session timer reset to 0.")

    def _tick(self):
        """Background loop that increments sitting time every second."""
        while self.is_running:
            if not self.is_paused:
                self.cumulative_seconds += 1

                if self.cumulative_seconds >= self.sitting_limit_seconds:
                    self._trigger_walk_break()
                    # Reset timer immediately to avoid multiple triggers
                    self.cumulative_seconds = 0
                    # Pause until walk break is completed
                    self.pause()

            time.sleep(1)

    def _trigger_walk_break(self):
        """Executes the lock screen and walk reminder sequence."""
        self.logger.info("Sitting limit reached. Triggering walk break.")

        # 1. Lock the screen
        if self.lock_callback:
            self.lock_callback()
        else:
            self._default_lock()

        # 2. Trigger the UI for the walk reminder
        if self.on_break_trigger:
            self.on_break_trigger()

    def _default_lock(self):
        """Default AppleScript screen lock."""
        try:
            subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to keystroke "q" using {command down, control down}'],
                check=True
            )
        except Exception as e:
            self.logger.error(f"Default lock failed: {e}")

    def notify_break_finished(self):
        """
        Call this when the user confirms they finished their walk break.
        """
        self.logger.info("Walk break finished.")
        self.resume()
        self.on_break_complete()
