"""
Posture scoring logic using MediaPipe landmarks.
"""

import cv2
import mediapipe as mp
import time
import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PostureResult:
    status: str  # "GOOD", "BAD", or "UNKNOWN"
    checks: Dict[str, bool]
    timestamp: float

class PostureAnalyser:
    def __init__(self):
        """Initialize MediaPipe Pose solution."""
        self.logger = logging.getLogger(__name__)
        # On some macOS ARM64 wheels, mediapipe.solutions is not available.
        # We use a dynamic import to handle this.
        try:
            from mediapipe.python.solutions import pose as mp_pose
            self.mp_pose = mp_pose
        except ImportError:
            try:
                self.mp_pose = mp.solutions.pose
            except AttributeError:
                raise ImportError(
                    "MediaPipe 'solutions.pose' not found. This is a known issue with some "
                    "macOS ARM64 wheel builds. Please ensure mediapipe is installed correctly."
                )

        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def analyze_frame(self, frame, baseline: Dict, thresholds: Dict) -> PostureResult:
        """
        Analyze a single frame for posture markers based on baseline and thresholds.

        Args:
            frame: OpenCV image array (BGR).
            baseline: Baseline values from calibration.
            thresholds: Threshold values for posture checks.

        Returns:
            PostureResult containing the status and individual check outcomes.
        """
        timestamp = time.time()

        # Convert BGR to RGB for MediaPipe
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)

        if not results.pose_landmarks:
            # Log warning for poor lighting/centering as per SRD section 10.3
            self.logger.warning("MediaPipe could not detect pose. Frame skipped (possible poor lighting or face not centered).")
            return PostureResult(status="UNKNOWN", checks={}, timestamp=timestamp)

        landmarks = results.pose_landmarks.landmark

        # Extract relevant landmarks
        # MediaPipe Pose IDs: Nose(0), L_Shoulder(11), R_Shoulder(12), L_Ear(7), R_Ear(8)
        nose = landmarks[0]
        l_shoulder = landmarks[11]
        r_shoulder = landmarks[12]
        l_ear = landmarks[7]
        r_ear = landmarks[8]

        # Compute shoulder midpoint
        shoulder_mid_y = (l_shoulder.y + r_shoulder.y) / 2

        # --- Check 1: Forward Head Lean ---
        # Nose drops more than threshold below baseline
        nose_drop = nose.y - baseline['nose_y_baseline']
        head_lean_bad = nose_drop > thresholds['nose_drop_threshold']

        # --- Check 2: Slouch Detection ---
        # Vertical distance between nose and shoulder midpoint shrinks by > X%
        current_dist = abs(shoulder_mid_y - nose.y)
        baseline_dist = baseline['head_to_shoulder_distance_baseline']
        # a 15% shrink means current_dist < 85% of baseline
        slouch_bad = current_dist < (baseline_dist * (1 - thresholds['slouch_threshold_percent'] / 100))

        # --- Check 3: Shoulder Asymmetry ---
        # abs(L_shoulder_y - R_shoulder_y) exceeds threshold
        shoulder_diff = abs(l_shoulder.y - r_shoulder.y)
        asymmetry_bad = shoulder_diff > thresholds['shoulder_asymmetry_threshold']

        # --- Check 4: Head Tilt ---
        # Difference between current angle and baseline angle
        dx = r_ear.x - l_ear.x
        dy = r_ear.y - l_ear.y
        angle_rad = np.arctan2(dy, dx)
        angle_deg = abs(np.degrees(angle_rad))

        # Calculate tilt relative to baseline
        baseline_tilt = baseline.get('head_tilt_baseline_degrees', 0)
        tilt_diff = abs(angle_deg - baseline_tilt)
        tilt_bad = tilt_diff > thresholds['head_tilt_threshold_degrees']

        checks = {
            "head_lean": head_lean_bad,
            "slouch": slouch_bad,
            "asymmetry": asymmetry_bad,
            "tilt": tilt_bad
        }

        # Overall posture is BAD if 2 or more checks fail
        fail_count = sum(checks.values())
        status = "BAD" if fail_count >= thresholds['bad_checks_to_trigger'] else "GOOD"

        return PostureResult(status=status, checks=checks, timestamp=timestamp)
