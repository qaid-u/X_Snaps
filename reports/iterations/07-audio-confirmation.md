# 07 — Optional audio confirmation

2026-11-12, Windows, Chrome 157, Electron 45.3.0 and RTX 3060 Laptop GPU. Added an opt-in muted AudioWorklet, an audio transient detector, temporal fusion, a local level meter and guided manual calibration.

- `npm run validate` passed strict TypeScript, ESLint, 9 unit tests, production build, 9 Chrome tests, the Electron test and performance smoke. Two new unit cases verified event order, one-shot consumption and rejection outside the fusion window.
- Chromium and Electron used synthetic microphones. Selecting a mode did not request the mic. Enabling then disabling it released the track while the existing camera kept running.
- An earlier short Speed Lines sample measured a 46.5 ms p95. The gate now retains any flagged sample and checks a 120-interval confirmation before attributing a regression. The final run flagged Synthwave Grid at 47.3 ms, then confirmed 36.9 ms. Carousel measured 29.96 FPS, 36.8 ms interval p95, and 31.4 ms trigger-to-draw p95. First draw took 42.0 ms. Catalog warm-up took 3.36 s.
- The preceding portable executable passed the dedicated-window, synthetic-camera, worker and PNG test. Physical webcam and microphone, snap accuracy, OBS and receiving apps remain **NOT VERIFIED**.
