"""
Test script for PostureAnalyser.
Captures a live frame and runs it through the analyzer with dummy baselines.
"""

import cv2
from camera import CameraModule
from posture_analyser import PostureAnalyser

def test_posture():
    # Dummy baseline and thresholds based on SRD section 7
    dummy_baseline = {
        "nose_y_baseline": 0.42,
        "shoulder_midpoint_y_baseline": 0.61,
        "head_to_shoulder_distance_baseline": 0.19,
        "shoulder_width_baseline": 0.28,
        "head_tilt_baseline_degrees": 1.2
    }

    dummy_thresholds = {
        "nose_drop_threshold": 0.07,
        "slouch_threshold_percent": 15,
        "shoulder_asymmetry_threshold": 0.05,
        "head_tilt_threshold_degrees": 15,
        "bad_checks_to_trigger": 2
    }

    analyser = PostureAnalyser()
    captured_frame = None

    def frame_callback(frame):
        nonlocal captured_frame
        captured_frame = frame

    print("Opening camera to capture a test frame...")
    camera = CameraModule(callback=frame_callback)

    try:
        camera.start()
        # Wait for a frame to be captured
        import time
        timeout = 5
        start_time = time.time()
        while captured_frame is None and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if captured_frame is not None:
            print("Frame captured! Analyzing posture...")
            result = analyser.analyze_frame(captured_frame, dummy_baseline, dummy_thresholds)
            print("\n--- Posture Analysis Result ---")
            print(f"Status:    {result.status}")
            print(f"Timestamp:  {result.timestamp}")
            print(f"Checks:     {result.checks}")
            print("-------------------------------\n")
        else:
            print("Error: Failed to capture a frame within timeout.")

    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        camera.stop()

if __name__ == "__main__":
    test_posture()
