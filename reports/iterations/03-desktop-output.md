# 03 — Dedicated Windows output window

2026-11-12, Windows build 26300, Electron 45.3.0, Chrome 157, RTX 3060 Laptop GPU. Added isolated Electron control and OBS output windows, validated IPC, camera permission scoped to the output process, portable packaging commands, and Windows OBS setup documentation.

- `npm run validate` passed strict typecheck, ESLint, 7 unit tests, the production build, 4 Chrome tests, 1 Electron test and the performance smoke. The Electron test used Chromium's synthetic camera and the real MediaPipe worker.
- Native Electron verified the exact output window title, a single canvas in output, no canvas in controls, rejection of out-of-range IPC, and camera continuity while controls close and reopen. The first reopen test exposed a shortcut delivery issue. Routed the shortcut through the output renderer's restricted bridge and reran the gate.
- Comparable 720p DEMO p95 frame intervals were 36.5–37.0 ms per mode. Carousel p95 was 37.3 ms and trigger-to-draw p95 was 30.4 ms. An isolated Original-selection trigger took 145.8 ms during the short smoke run. Treat the repeated carousel latency as the summary and retain individual samples in the generated report.
- Physical webcam, physical snap accuracy, OBS Window Capture and virtual camera delivery remain **NOT VERIFIED**. The next iteration adds the rest of the shader catalog.
