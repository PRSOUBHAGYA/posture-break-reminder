# Software Requirements Document (SRD)
## PostureGuard — Mac Desktop Posture Tracking App
**Version:** 1.0  
**Platform:** macOS (12 Monterey and above)  
**Target User:** Personal use (single user)  
**Last Updated:** 2026-04-28

---

## 1. Project Overview

PostureGuard is a macOS menu bar application that uses the laptop's built-in front camera and MediaPipe pose/face landmark detection to monitor the user's sitting posture in real time. When bad posture is detected for more than 10 seconds, the system displays a warning overlay and then locks the screen. After every 30 minutes of tracked sitting, the user is prompted to take a 5-minute walk break before the screen unlocks.

---

## 2. Goals & Non-Goals

### Goals
- Detect poor sitting posture using the front-facing camera
- Warn the user after 10 seconds of bad posture, then lock the screen
- Enforce a 5-minute walk break every 30 minutes of continuous sitting
- Run silently in the macOS menu bar
- All processing is 100% on-device (no video leaves the machine)

### Non-Goals
- Direct spinal cord tracking (not possible via front camera)
- Cloud sync or remote monitoring
- Multi-user support
- Mobile or Windows support

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────┐
│                  PostureGuard App                │
│                                                  │
│  ┌─────────────┐     ┌──────────────────────┐   │
│  │  Camera     │────▶│  MediaPipe Processor  │   │
│  │  Module     │     │  (Face + Pose Mesh)   │   │
│  └─────────────┘     └──────────┬───────────┘   │
│                                  │               │
│                       ┌──────────▼───────────┐   │
│                       │  Posture Analyser    │   │
│                       │  (Score & Classify)  │   │
│                       └──────────┬───────────┘   │
│                                  │               │
│            ┌─────────────────────┼─────────────┐ │
│            ▼                     ▼             ▼ │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────┐ │
│  │ Posture      │  │ Session Timer   │  │ Menu │ │
│  │ Alert/Lock   │  │ (30-min + walk) │  │ Bar  │ │
│  └──────────────┘  └─────────────────┘  └──────┘ │
└──────────────────────────────────────────────────┘
```

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Camera access | OpenCV (`cv2`) |
| Pose detection | MediaPipe (`mediapipe`) — Pose + Face Mesh solutions |
| UI / Menu bar | `rumps` (macOS menu bar framework) |
| Overlay windows | `tkinter` (warning popups and walk reminder) |
| Screen lock | `subprocess` + AppleScript (`osascript`) |
| Notifications | `plyer` or `osascript` notifications |
| Config storage | JSON file in `~/.postureGuard/config.json` |
| Threading | Python `threading` module |

### Install Requirements (`requirements.txt`)
```
opencv-python
mediapipe
rumps
plyer
```

---

## 5. File Structure

```
postureGuard/
├── main.py                   # Entry point — starts menu bar app
├── camera.py                 # Camera capture loop (runs in thread)
├── posture_analyser.py       # Posture scoring logic using landmarks
├── alert_manager.py          # Warning overlay + screen lock logic
├── session_timer.py          # 30-min session + walk break timer
├── calibration.py            # First-run baseline capture
├── config.py                 # Load/save user config
├── ui/
│   ├── overlay.py            # Tkinter bad posture warning window
│   ├── walk_reminder.py      # Tkinter 5-min walk break window
│   └── calibration_ui.py     # Calibration wizard window
├── assets/
│   └── icon.png              # Menu bar icon (template image)
├── requirements.txt
└── README.md
```

---

## 6. Core Features & Functional Requirements

### 6.1 Calibration (First Run)

- On first launch, show a calibration window
- Instruct user: *"Sit up straight, look at the camera. Hold for 5 seconds."*
- Capture 5 seconds of landmark data and compute baseline values:
  - Baseline nose Y position (normalised)
  - Baseline shoulder midpoint Y (normalised)
  - Baseline head-to-shoulder vertical distance
  - Baseline shoulder width (to detect leaning)
  - Baseline head tilt angle
- Save baseline to `~/.postureGuard/config.json`
- Allow re-calibration from menu bar at any time

### 6.2 Camera Module (`camera.py`)

- Open the default camera (index 0) using OpenCV
- Capture frames every **2 seconds** (not continuous) to reduce CPU/battery usage
- Pass each frame to `posture_analyser.py`
- Expose a `stop()` method to cleanly release the camera

### 6.3 Posture Analyser (`posture_analyser.py`)

Use **MediaPipe Pose** to extract the following landmarks per frame:

| Landmark | MediaPipe ID | Used For |
|---|---|---|
| Nose | 0 | Head height, forward lean |
| Left shoulder | 11 | Shoulder level |
| Right shoulder | 12 | Shoulder level |
| Left ear | 7 | Head tilt |
| Right ear | 8 | Head tilt |

#### Posture Checks

**Check 1 — Forward Head Lean**
- Compute: `nose_y` relative to baseline `nose_y`
- Bad if: nose drops more than `threshold_drop` (default: 0.07 normalised units) below baseline

**Check 2 — Slouch Detection**
- Compute: vertical distance between nose and shoulder midpoint
- Bad if: this distance shrinks by more than 15% compared to baseline (head moving toward shoulders = rounding forward)

**Check 3 — Shoulder Asymmetry**
- Compute: `abs(left_shoulder_y - right_shoulder_y)`
- Bad if: difference exceeds 0.05 normalised units

**Check 4 — Head Tilt**
- Compute: angle between left ear and right ear relative to horizontal
- Bad if: tilt exceeds 15 degrees

#### Scoring
- Each check returns `True` (bad) or `False` (good)
- Overall posture is `BAD` if **2 or more** checks are `True`
- Overall posture is `GOOD` if fewer than 2 checks fail
- Return a `PostureResult` dataclass: `{ status: "GOOD"|"BAD", checks: dict, timestamp: float }`

### 6.4 Alert Manager (`alert_manager.py`)

#### Bad Posture Timer
- When `PostureResult.status == "BAD"`:
  - Start a 10-second countdown timer
  - If posture returns to `GOOD` before 10 seconds: reset timer
  - If 10 seconds of continuous bad posture: trigger alert sequence

#### Alert Sequence
1. Show `overlay.py` warning window (full-screen semi-transparent red overlay) for 3 seconds
   - Message: *"Fix your posture!"*
   - Non-blocking — user can still see screen briefly
2. After 3 seconds: lock the screen using AppleScript:
   ```python
   subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "q" using {command down, control down}'])
   ```
3. After locking, pause posture detection (no point checking while locked)
4. Unlock detection resumes when the session timer next unlocks the machine

### 6.5 Session Timer (`session_timer.py`)

- Tracks cumulative active sitting time (only counts when posture detection is running)
- After **30 minutes** of active sitting:
  1. Lock the screen (same AppleScript command)
  2. Show `walk_reminder.py` window on top of lock screen (or as a notification)
     - Message: *"You've been sitting for 30 minutes. Time for a 5-minute walk! 🚶"*
     - Show a **5-minute countdown timer** in the window
  3. After 5 minutes: show *"Welcome back! Click to unlock."* button
  4. User clicks → screen unlocks via:
     ```python
     subprocess.run(['osascript', '-e', 'tell application "System Events" to key code 53'])
     ```
     (This simulates pressing Escape, prompting password entry — actual unlock requires user password for security)
  5. Reset sitting timer to 0

### 6.6 Menu Bar App (`main.py`)

Built with `rumps`. Menu items:

```
PostureGuard ✅          ← icon changes based on posture status
├── Status: Good         ← live status text (updates every 2 sec)
├── Session: 12:34       ← time since last break
├── ─────────────
├── Pause Monitoring
├── Re-Calibrate
├── Preferences...
├── ─────────────
└── Quit PostureGuard
```

Icon states:
- `✅` Green — good posture
- `⚠️` Yellow — posture warning (bad posture detected, countdown running)
- `🔴` Red — locked due to bad posture
- `⏸` Grey — monitoring paused

---

## 7. Configuration (`config.json`)

```json
{
  "calibration": {
    "nose_y_baseline": 0.42,
    "shoulder_midpoint_y_baseline": 0.61,
    "head_to_shoulder_distance_baseline": 0.19,
    "shoulder_width_baseline": 0.28,
    "head_tilt_baseline_degrees": 1.2
  },
  "thresholds": {
    "nose_drop_threshold": 0.07,
    "slouch_threshold_percent": 15,
    "shoulder_asymmetry_threshold": 0.05,
    "head_tilt_threshold_degrees": 15,
    "bad_checks_to_trigger": 2
  },
  "timers": {
    "bad_posture_lock_delay_seconds": 10,
    "sitting_session_minutes": 30,
    "walk_break_minutes": 5,
    "camera_check_interval_seconds": 2
  },
  "ui": {
    "show_debug_overlay": false
  }
}
```

---

## 8. Non-Functional Requirements

| Requirement | Target |
|---|---|
| CPU usage (idle monitoring) | < 5% on Apple Silicon |
| Memory usage | < 150 MB |
| Camera check frequency | Every 2 seconds |
| Detection latency | < 500ms per frame analysis |
| Privacy | No video stored or transmitted. All processing is local. |
| macOS compatibility | macOS 12 Monterey and above |
| Python version | 3.10+ |
| Startup time | < 3 seconds |

---

## 9. Permissions Required

| Permission | Reason |
|---|---|
| Camera | Capture frames for posture analysis |
| Accessibility | AppleScript screen lock commands |
| Notifications | Walk break reminders (optional) |

User must grant camera + accessibility permissions on first run. App should detect missing permissions and guide the user to System Settings.

---

## 10. Known Limitations

1. **No direct spine tracking** — posture is inferred from head and shoulder position as a proxy for spinal alignment.
2. **Requires upper body visibility** — user should sit 50–80cm from the laptop screen.
3. **Lighting sensitivity** — very dark environments may cause detection failure; the app will log a warning and skip that frame.
4. **Screen lock bypass** — since this is for personal use and the lock is macOS native, the user can always enter their password immediately. This is by design (self-discipline tool, not enforcement).
5. **MediaPipe may not detect pose if face is not centred** — the camera capture should be at eye level for best results.

---

## 11. Build & Run Instructions

### Setup
```bash
# Clone repo
git clone https://github.com/yourname/postureGuard
cd postureGuard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run
```bash
python main.py
```

### Package as Mac App (optional)
```bash
pip install py2app
python setup.py py2app
```

---

## 12. Future Improvements (Out of Scope for v1.0)

- Historical posture score charts (daily/weekly)
- Custom alert sounds
- Desk exercise suggestions during walk break
- Integration with Apple Health (stand minutes)
- Auto-pause when screen is idle (user stepped away)
- Face recognition to resume monitoring after walk (confirm user is back)

---

*End of SRD*
