# SNAP//REALITY development log

## 2026-11-12 — Windows OBS application audit

Preserved the existing TouchDesigner project and its DEMO benchmark. Re-ran the native tests, fixed the lost microphone error detail, and passed 51 of 53 tests with two environment skips. See the [audit report](reports/iterations/00-native-audit.md).

The first React/Three.js iteration passed the complete npm gate and established a 720p30 synthetic baseline on the RTX 3060 Laptop GPU. See [browser MVP results](reports/iterations/01-browser-mvp.md).

The separate MediaPipe worker ran against a synthetic camera in Chrome. Manual switching remained available when the model failed to load. The comparable smoke gate passed. See [worker vision results](reports/iterations/02-worker-vision.md).

Electron passed the synthetic two-window camera and control lifecycle test. The dedicated output stays active when controls close. See [desktop output results](reports/iterations/03-desktop-output.md) and the [OBS acceptance steps](docs/OBS_SETUP.md).

The full GPU catalog passed shader readback and the comparable frame-time gate. Pass-through video now draws before the full catalog warms, and the catalog uses bounded GPU history for temporal effects. See [catalog results](reports/iterations/04-effect-catalog.md).

## 2026-11-11 — Windows discovery and Stage 2 checkpoint

The workspace started without source files or Git metadata. The implementation plan was to establish the native DEMO → five effects → transition → Perform Mode path first, preserve that project, then add the tracker, catalog, performance controls and verification.

| Component | Observed |
| --- | --- |
| Windows | NT 10.0 build 26300 |
| TouchDesigner | 2025.33230, Non-Commercial, installed on the D: drive |
| Embedded Python | 3.11.15, Windows x64 |
| External Python | Native CPython 3.12.4 at `C:/Python312/python.exe` |
| PATH Python | MSYS2 MinGW 3.12.11. The Windows `py` launcher reported no registered interpreters. |
| GPU | TouchDesigner used the NVIDIA GeForce RTX 3060 Laptop GPU. Vulkan reported NVIDIA driver 591.86 and a second Intel UHD adapter. |
| Displays | 1920 × 1080 primary and 1920 × 1200 secondary |
| Camera and audio inventory | Integrated Camera, USB CAMERA, Realtek external microphone and microphone array, USB microphone |
| Other tools | Git 2.53, VS Code, Node.js, PowerShell, Vulkan utilities and bundled FFmpeg/FFprobe |

Probed GLSL TOP, OSC In DAT, Keyboard In DAT, native panels and capture operator parameters on the installed build. The embedded Keyboard In DAT passes a named tuple and TOP readback is `numpyArray`. Absolute OP paths set through Python did not follow a COMP rename. The builder now creates the replacement at the canonical path and restores the previous component on pre-save validation failures.

- Built and saved [the Stage 2 checkpoint](checkpoints/SnapReality-stage2.toe) in TouchDesigner. Verified Original, Posterized, Comic Pop Art, Halftone Print and RGB Glitch at 960 × 540. Each mode produced a distinct frame and responded to the moving DEMO.
- Pressed **N** in the Perform window and observed Original advance to Posterized with a SNAP transition. Reopened the saved checkpoint, rechecked GPU output and confirmed the controller and keyboard DAT initialized.
- [Stage 2 build report](artifacts/stage2/build-report.json), [reopen report](artifacts/stage2/reopen-report.json), and [representative frames](artifacts/stage2/).

## 2026-11-12 — Gesture, catalog and full project

- Added a local x64 Python 3.12 gesture worker with temporal contact and release, hand identity, optional mic confirmation, health and metric messages, keyboard and vision fallbacks, and a ten-trial calibration command. All sensor streams are opt-in. This machine enumerated the devices. Dependency installation and physical gesture trials remain pending because the execution environment could not resolve the package host and had no cached MediaPipe wheel.
- Verified the native OSC listener on `127.0.0.1:7400` with a synthetic OSC int64/double snap. The event and its duplicate produced exactly one advancement. The native result is separate from the shell sandbox's skipped UDP transport test.
- Implemented 21 persistent shaders, two bounded feedback chains, procedural wipes and overlays, 11 transition presets including the six required presets, and the reference-inspired DEMO showcase. TouchDesigner compiled and rendered all 21 styles. GPU readback confirmed Original matches its source and all modes produce distinct images at the reference frame and change across two DEMO times. Independent readback also verified every overlay and four non-crossfade wipes.
- Built the native Perform panel, custom controls, three quality profiles, clean output, local settings and capture. Verified mouse selection, low-profile 640 × 360 at a configured 30 FPS, image and Motion JPEG input, missing-video fallback, still PNG, PNG sequence and Motion JPEG recording.
- Verified 37 passing Python tests with `scripts/run_tests.ps1 -PythonExe 'C:/Python312/python.exe'`. Two tests skipped for unavailable `python-osc` parity and shell UDP loopback. Native TouchDesigner loopback was tested separately.
- Benchmarked the DEMO showcase in Perform Mode at 960 × 540 on the RTX 3060 Laptop GPU. The 60.017-second run sampled 3,602 frames, all 21 effects and all five transition phases. TouchDesigner reported zero frame drops and zero absolute timeline gaps. Mean cook time was 2.41 ms. [Native benchmark](reports/benchmark-20261111T160719845811Z.json)
- Recorded the full 72-second DEMO timeline in TouchDesigner as Motion JPEG and encoded the standalone H.264 MP4 with bundled FFmpeg. FFprobe confirmed 960 × 540, 60 FPS, and 4,320 frames. [Showcase video](artifacts/SnapReality-Showcase.mp4)
- Reopened the final project in Perform Mode. Space advanced Original to Posterized once, the clean window showed the selected effect, and Escape returned to Designer Mode. Reloaded one changed shader DAT from disk and confirmed zero active callback errors. TouchDesigner selected its numbered save, which matched the canonical project byte for byte. [Reopen report](artifacts/stage6/reopen-report.json)

### Artifacts

- [Native full project](SnapReality.toe), [Stage 2 checkpoint](checkpoints/SnapReality-stage2.toe)
- [Full GPU build report](artifacts/stage6/build-report.json), [native runtime checks](artifacts/stage6/runtime-report.json), [overlay readback](artifacts/stage6/overlay-report.json)
- Example renders for [Original](artifacts/stage6/00.png), [Comic Pop Art](artifacts/stage6/03.png), [Halftone Print](artifacts/stage6/04.png), [Neon Trails](artifacts/stage6/14.png), and [the SNAP transition](artifacts/stage6/transition.png)

## Remaining device checks

Run the [gesture setup and physical calibration](docs/GESTURE_CALIBRATION.md) with the intended camera and microphone. Verify Screen Grab using the production capture target and monitor layout. CAMERA uses a separate device when the local tracker owns its webcam. The supplied motion, depth and shatter effects are screen-space processing.
