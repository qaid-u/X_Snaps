# 05 — Person, background and split scopes

2026-11-12, Windows, Chrome 157 and RTX 3060 Laptop GPU. The pinned landscape Selfie Segmentation model ran in its own local worker beside hand tracking. Both workers consumed bounded, resized frames from the existing camera track. Added feathered masks, a reused 640 × 360 split background pass, and a camera stall fallback.

- `npm run setup:models` verified both SHA-256 pins. `npm run validate` passed strict TypeScript, ESLint, 7 unit tests, Vite build, 7 Chrome tests, the Electron test and the 21-mode performance smoke.
- The first split implementation made the catalog expensive to compile. Replaced it with one reusable background pass so the effect shader is evaluated once per draw. A short smoke sample then failed with a 405.8 ms Comic Book p95. Increased the sample window to at least 48 intervals per mode and removed frame-clock catch-up bursts. An integration timeout was aligned to the separate startup benchmark. The final comparable 10% p95 gate passed.
- All four scopes produced distinct DEMO pixels. The real segmentation model returned confidence masks from Chromium's synthetic camera without replacing its stream. Forced missing-asset tests verified that the video and whole-scene effect continued.
- 720p carousel measured 29.98 FPS, p95 interval 36.6 ms, and p95 accepted-trigger-to-draw latency 30.9 ms. Per-mode p95 intervals were 36.5–37.6 ms. Mixed Media averaged 23.64 FPS in one short window with a long scheduling interval. Longer profiling remains pending.
- Physical camera, snap accuracy, mask quality on people, OBS and receiving apps remain **NOT VERIFIED**.
