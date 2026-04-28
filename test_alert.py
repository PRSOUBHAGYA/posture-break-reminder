"""
Test script for AlertManager.
Simulates continuous bad posture to verify the alert sequence.
"""

import time
import threading
from alert_manager import AlertManager
from posture_analyser import PostureResult
from ui.overlay import PostureWarningOverlay

def test_alert_sequence():
    print("Starting AlertManager test...")

    # Initialize AlertManager with the Overlay class
    manager = AlertManager(overlay_class=PostureWarningOverlay)

    # Define a dummy result for bad posture
    bad_result = PostureResult(
        status="BAD",
        checks={"head_lean": True, "slouch": True, "asymmetry": False, "tilt": False},
        timestamp=time.time()
    )

    # Monkey-patch lock_screen to implement DRY_RUN behavior
    def dry_run_lock():
        print("\n>>> [DRY RUN] WOULD LOCK SCREEN NOW <<<\n")

    manager.lock_screen = dry_run_lock

    print("Simulating bad posture for 11 seconds...")
    start_time = time.time()

    # Feed the manager "BAD" results every second
    while time.time() - start_time < 11:
        manager.update(bad_result)
        print(f"Sustaining bad posture... {int(time.time() - start_time)}s")
        time.sleep(1)

    print("\n11 seconds passed. The alert sequence should have triggered.")
    print("Expected sequence: 3s Overlay -> 'WOULD LOCK SCREEN' message.")

    # The alert sequence runs in a background thread (3s overlay + lock).
    # We wait a bit more to ensure the background thread finishes and prints the lock message.
    time.sleep(5)
    print("Test completed.")

if __name__ == "__main__":
    test_alert_sequence()
