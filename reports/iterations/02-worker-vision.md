# 02 — Local hand tracking worker

2026-11-12, same Chrome/RTX 3060 environment as iteration 01. Added a pinned MediaPipe Tasks Vision 0.10.32 worker, transferable downsized frames, temporal thumb/middle-finger recognition, diagnostics and local model setup.

- `npm run validate` passed strict typecheck, ESLint, 7 unit tests, production build, 4 browser integration tests and performance smoke. The Vite size advisory remains.
- The real CPU-delegate MediaPipe worker initialized with the pinned local model, processed multiple Chromium synthetic-camera frames, and stopped with the track. A forced model 404 kept the video live and manual effects available. Synthetic landmarks covered contact, palmward release, cooldown, hand changes, tracking loss and nonmonotonic timing.
- Comparable 720p synthetic fixture measured 29.81–30.01 FPS per mode, p95 36.5–37.0 ms. Carousel p95 was 36.9 ms versus 37.8 ms at baseline. The 10% p95 regression gate passed. This render-only fixture did not start vision.
- Real finger-snap accuracy, camera cadence and OBS remain **NOT VERIFIED**. Next iteration targets a dedicated native window for OBS.
