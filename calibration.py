"""
Handles the initial and manual calibration of posture baselines.
"""

import numpy as np
from typing import List, Dict
from posture_analyser import PostureAnalyser

class CalibrationManager:
    def __init__(self, analyser: PostureAnalyser):
        """
        Initialize calibration manager.

        Args:
            analyser: An instance of PostureAnalyser to extract landmarks.
        """
        self.analyser = analyser
        self.captured_data = []

    def add_frame_data(self, frame):
        """
        Extract landmarks from a frame and store them for baseline calculation.
        """
        # Use a dummy baseline/threshold just to get the landmarks
        # Since we only need the raw landmarks for calibration
        dummy_baseline = {"nose_y_baseline": 0, "head_to_shoulder_distance_baseline": 0}
        dummy_thresholds = {"nose_drop_threshold": 0, "slouch_threshold_percent": 0}

        # We need to modify PostureAnalyser or use it to get landmarks
        # For now, we'll access the internal pose process logic
        import cv2
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.analyser.pose.process(image_rgb)

        if results.pose_landmarks:
            self.captured_data.append(results.pose_landmarks.landmark)

    def compute_baselines(self) -> Dict[str, float]:
        """
        Compute average baseline values from captured landmark data.

        Returns:
            A dictionary of baseline values.
        """
        if not self.captured_data:
            raise ValueError("No landmark data captured during calibration.")

        num_frames = len(self.captured_data)

        # Initialize accumulators
        nose_y = 0.0
        shoulder_mid_y = 0.0
        head_shoulder_dist = 0.0
        shoulder_width = 0.0
        head_tilt_sum = 0.0

        for landmarks in self.captured_data:
            nose = landmarks[0]
            l_sh = landmarks[11]
            r_sh = landmarks[12]
            l_ear = landmarks[7]
            r_ear = landmarks[8]

            nose_y += nose.y
            mid_y = (l_sh.y + r_sh.y) / 2
            shoulder_mid_y += mid_y
            head_shoulder_dist += abs(mid_y - nose.y)
            shoulder_width += abs(l_sh.x - r_sh.x)

            dx = r_ear.x - l_ear.x
            dy = r_ear.y - l_ear.y
            head_tilt_sum += abs(np.degrees(np.arctan2(dy, dx)))

        return {
            "nose_y_baseline": nose_y / num_frames,
            "shoulder_midpoint_y_baseline": shoulder_mid_y / num_frames,
            "head_to_shoulder_distance_baseline": head_shoulder_dist / num_frames,
            "shoulder_width_baseline": shoulder_width / num_frames,
            "head_tilt_baseline_degrees": head_tilt_sum / num_frames
        }

    def clear_data(self):
        """Clear captured data for a new calibration session."""
        self.captured_data = []
