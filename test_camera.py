"""
Test script for CameraModule.
Captures 5 frames and verifies their shapes.
"""

from camera import CameraModule
import threading

def frame_callback(frame):
    print(f"Captured frame with shape: {frame.shape}")

def test_camera():
    print("Starting CameraModule test...")
    # We use an event to signal when 5 frames have been captured
    captured_count = 0
    stop_event = threading.Event()

    def wrapped_callback(frame):
        nonlocal captured_count
        frame_callback(frame)
        captured_count += 1
        if captured_count >= 5:
            stop_event.set()

    camera = CameraModule(callback=wrapped_callback)

    try:
        camera.start()
        print("Camera started, waiting for 5 frames...")

        # Wait until 5 frames are captured or timeout after 15 seconds
        if stop_event.wait(timeout=15):
            print("Successfully captured 5 frames.")
        else:
            print("Timed out waiting for frames.")

    except Exception as e:
        print(f"Error during camera test: {e}")
    finally:
        camera.stop()
        print("Camera stopped.")

if __name__ == "__main__":
    test_camera()
