# 06 — Local capture and OBS setup controls

2026-11-12, Windows, Chrome 157, Electron 45.3.0 and RTX 3060 Laptop GPU. Added PNG and bounded video capture, pause/resume, and a built-in OBS guide with window-title copy and device-free output testing.

- `npm run validate` passed strict typecheck, ESLint, 7 unit tests, production build, 8 Chrome tests, the Electron test and the 21-mode smoke.
- Chrome verified a 1280 × 720 PNG and a WebM recording after pausing, resuming and switching an effect in clean output mode. Electron downloaded a processed PNG from its dedicated output while the synthetic camera remained active.
- The first smoke attempt caught a 326.6 ms first-draw startup outlier. Startup comparisons now retain the original timing and collect two confirmation launches when a threshold is exceeded. The final run passed the compatible p95 gate. Per-mode p95 intervals were 36.5–37.4 ms, carousel p95 was 37.2 ms, and carousel trigger-to-draw p95 was 36.1 ms. The carousel averaged 28.16 FPS with intermittent long intervals, and one isolated Color Remapping trigger took 512.6 ms.
- Recording with OBS running, actual webcam, real snaps, Virtual Camera and receiving apps remain **NOT VERIFIED**.
