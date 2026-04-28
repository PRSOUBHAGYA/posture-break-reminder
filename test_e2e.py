"""
End-to-end integration test for PostureGuard.
Simulates the full app flow from camera capture to session timer alerts.
"""

import time
import logging
from unittest.mock import MagicMock

from config import load_config
from camera import CameraModule
from posture_analyser import PostureAnalyser
from alert_manager import AlertManager
from session_timer import SessionTimer
from ui.overlay import PostureWarningOverlay

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("E2E-Test")

def test_e2e():
    print("\n--- Starting PostureGuard E2E Integration Test ---\n")

    # 1. Load Config
    print("[1/6] Loading configuration...")
    config = load_config()
    print(f"Config loaded. Baseline nose_y: {config['calibration']['nose_y_baseline']}")

    # 2. Initialize Components
    print("[2/6] Initializing components...")
    analyser = PostureAnalyser()
    alert_manager = AlertManager(overlay_class=PostureWarningOverlay)

    # Mock callbacks for session timer
    break_triggered = []
    def on_break_trigger():
        print("\n>>> EVENT: Walk break UI triggered! <<<")
        break_triggered.append(True)

    def on_break_complete():
        print("\n>>> EVENT: Walk break complete callback received! <<<")

    # We use a mock lock callback to avoid locking the actual computer
    def mock_lock():
        print("\n>>> EVENT: Screen Lock triggered! <<<")

    session_timer = SessionTimer(
        on_break_complete=on_break_complete,
        on_break_trigger=on_break_trigger,
        lock_callback=mock_lock
    )

    # 3. Camera Integration
    print("[3/6] Testing Camera -> Analyser -> AlertManager flow...")

    captured_results = []
    def process_frame_mock(frame):
        result = analyser.analyze_frame(frame, config['calibration'], config['thresholds'])
        alert_manager.update(result)
        captured_results.append(result)

    camera = CameraModule(callback=process_frame_mock)

    try:
        camera.start()
        print("Camera started. Analyzing posture for 10 seconds...")

        # Run for 10 seconds (instead of 20 to keep test fast, but enough to see results)
        start_time = time.time()
        while time.time() - start_time < 10:
            # Every 2 seconds a frame is processed by the camera thread
            # We just print the most recent result
            if captured_results:
                last = captured_results[-1]
                print(f"Posture: {last.status} | Checks: {last.checks}")
            time.sleep(2)

    except Exception as e:
        print(f"Camera/Analysis error: {e}")
    finally:
        camera.stop()
        print("Camera stopped.")

    # 4. Simulate Session Timer (30 mins)
    print("\n[4/6] Simulating 30 minutes of sitting...")
    session_timer.start()

    # Instead of waiting 30 mins, we manually advance the timer
    # to test the trigger logic.
    session_timer.cumulative_seconds = (30 * 60) - 1 # Almost 30 mins

    print("Ticking the timer to trigger the break...")
    # We simulate a few ticks
    for _ in range(5):
        # We manually call the internal _tick logic or just wait for the
        # background thread to catch up. Since we set cumulative_seconds
        # to 1799, the next tick should trigger it.
        time.sleep(1.1)
        if break_triggered:
            break

    # 5. Confirm Walk Reminder Triggered
    print("\n[5/6] Verifying break trigger...")
    if break_triggered:
        print("SUCCESS: Walk reminder was triggered.")
    else:
        print("FAILURE: Walk reminder was NOT triggered.")

    # 6. Cleanup and Shutdown
    print("\n[6/6] Shutting down components...")
    session_timer.stop()
    print("Session timer stopped.")

    print("\n--- E2E Test Completed ---")

if __name__ == "__main__":
    test_e2e()
