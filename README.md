# SNAP//REALITY

A local Windows webcam effects studio with finger-snap control and a dedicated output window for OBS Studio Virtual Camera.

`Physical webcam → MediaPipe snap recognition + Three.js effects → SNAP//REALITY — OBS OUTPUT → OBS Window Capture → OBS Virtual Camera → Discord / Zoom / Google Meet`

## Run on Windows

Install Node.js 22.12+ and OBS Studio. In PowerShell, from the repository root:

```powershell
npm ci
npm run setup:models
npm run electron:dev
```

Electron opens the control panel and **SNAP//REALITY — OBS OUTPUT**. The output starts with an animated DEMO. Select a physical webcam and click **Start camera**. With **Hand tracking** enabled, bring your thumb and middle finger together in view, then snap. **Space** in the output window and **Next effect** in controls also advance the effect. Press **R** in output for Original. Close the control panel while broadcasting or use **Ctrl+Shift+O** in the output window to reopen it.

In OBS create a scene containing one **Window Capture** source aimed at **SNAP//REALITY — OBS OUTPUT**. Disable cursor capture, use client-area capture when available, and set canvas and output to **1280×720 at 30 FPS**. Start OBS Virtual Camera and select **OBS Virtual Camera** in the receiving app. Select your microphone there separately. Follow the [OBS setup and hardware acceptance checklist](docs/OBS_SETUP.md) and [troubleshooting guide](docs/OBS_TROUBLESHOOTING.md).

### Portable Windows build

```powershell
npm run setup:models
npm run electron:build
```

Open `SNAP-REALITY.exe` inside the generated `release` directory. Keep its adjacent files together. The local build is unsigned. The first setup downloads dependencies and the pinned vision model. Frames and inference stay on the machine. Camera acquisition requires **Start camera**. The DEMO uses neither a camera nor files.

### Browser development

```powershell
npm run dev
```

Open the localhost address printed by Vite. **Clean OBS output** uses the same canvas and camera as the controls. Press **Esc** to return to controls after stopping OBS capture. Use Electron for a dedicated output window.

## Verification

```powershell
npm run validate
npm run perf:smoke
npm run perf:benchmark
```

Automated checks use installed Google Chrome and a synthetic camera. The performance scripts emit JSON and Markdown in `reports/performance/` and check compatible baselines. Source-frame cadence, render cadence, and trigger-to-draw latency are separate measurements.

Physical webcam, real snap recognition, OBS Window Capture, OBS Virtual Camera, and video-call output are **NOT VERIFIED**. See [development results](DEVELOPMENT.md), [architecture](docs/WEB_ARCHITECTURE.md), [licensing](LICENSE.md) and [third-party notices](LICENSE-THIRD-PARTY.md).

The existing [TouchDesigner project](TOUCHDESIGNER.md) and its saved DEMO checkpoint remain available in this repository.
