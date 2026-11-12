# Gesture calibration

Use the keyboard preview first. With the TouchDesigner preview focused, **N** or **Space** advances and **R** resets.

## Install and start

Open PowerShell in the repository. Use native x64 Windows CPython 3.12. The setup checks the regular per-user install, `C:/Python312/python.exe`, the Python launcher and PATH. If you know the interpreter path, pass it as `-PythonExe`.

```powershell
.\scripts\setup_windows.ps1
.\scripts\start_gesture_service.ps1 -Mode 'AUDIO+VISION'
```

Setup installs the pinned packages in `.venv-gesture` and downloads Google's Hand Landmarker model to `assets/models/hand_landmarker.task`. The worker runs offline after setup. It processes frames and audio locally, discards them, and transmits numerical metrics and event IDs over loopback only. [Google Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)

| Mode | Capture and behavior |
| --- | --- |
| `AUDIO+VISION` | Camera and microphone. Requires both a tracked thumb–middle-finger release and a nearby microphone transient while the microphone is working. Reports `VISION_LOW_CONFIDENCE` and uses vision when the microphone is unavailable. |
| `VISION` | Camera only. The event confidence is lower. |
| `AUDIO_ONLY` | Microphone only. Experimental. Nearby sharp sounds can trigger a switch. |
| `KEYBOARD` | No camera or microphone. Use TouchDesigner keys or the synthetic OSC tester. This is the default bridge mode. |

Keep the TouchDesigner source on DEMO or SCREEN while the bridge owns the webcam. To use a camera as the effect source, stop the bridge or select a separate device. In Windows, enable desktop app access in **Settings → Privacy & security → Camera** and **Microphone** as needed. Ctrl+C stops the bridge and releases its devices. A camera read failure drops partial gesture evidence and retries the camera about every two seconds.

## Run ten trials

Stop the running bridge so the calibration program can open the camera and optional microphone.

```powershell
.\.venv-gesture\Scripts\python.exe -m gesture_service.calibration
```

1. Select a camera index starting at `0`, enable the microphone if desired, and choose sensitivity and pulse threshold. The wizard accepts an explicit microphone device index or uses the system default.
2. Frame one hand about an arm's length or closer, with the wrist and all fingers visible in even light. Press the thumb against the middle fingertip while the index finger stays extended. Release the middle finger toward the palm with a snap. The wizard displays hand and contact phases.
3. Follow the ten prompts and snap once per trial. The wizard counts missed and extra detections. The final movement trial measures false triggers from normal hand motion.
4. Save the settings to `config/gesture_settings.json` and restart the bridge. The document stores only thresholds and device indices. Test again with TouchDesigner and compare ten physical snaps against its snap counter.

If you see `NO_HAND`, check lighting, framing, camera permissions and the camera index. If contact is visible but snaps are missed, start with a clean pose and an extended index finger. A 30 FPS webcam can miss the release between frames. A 60 FPS mode can provide more samples when the camera supports it. For audio confirmation, start with the microphone about 20–50 cm from the hand and use a quiet room. If the camera and mic have a consistent timing offset, adjust `audio_window` in the saved file and rerun the trials.

## Verify the OSC bridge without devices

```powershell
.\.venv-gesture\Scripts\python.exe -m gesture_service.send_test_snap
```

Each invocation sends one synthetic event to `127.0.0.1:7400`. Check the TouchDesigner snap counter. If it does not advance, check that OSC is armed and that the OSC In DAT can bind UDP port 7400. The sender uses an ephemeral local source port. A UDP send by itself does not confirm reception.

You can also run the test with a native Python 3.12 interpreter before installing the gesture packages.

```powershell
& 'C:/Python312/python.exe' -m gesture_service.send_test_snap
```

The worker sends `/snap/event` as `hdfs` (int64 event ID, double monotonic seconds, float confidence, string hand label), `/snap/health` as `ss` (status and detail), and `/snap/metrics` as `ffsff` (separation, signed velocity, phase, audio score, candidate confidence). A missing hand is represented by separation `-1`. Health is sent once a second and metrics up to ten times a second. The receiver can compare event timestamps with the Windows process monotonic clock. [Derivative OSC In DAT](https://docs.derivative.ca/OSC_In_DAT)
