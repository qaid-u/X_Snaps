# 08 — Warmed transitions and persistent rotation

2026-11-12, Windows, Chrome 157, Electron 45.3.0 and RTX 3060 Laptop GPU. Added ten shader transitions, per-effect and randomized policies, duration/easing/intensity controls, reduced flash, editable effect rotation, and local numeric preset settings.

- `npm run validate` passed strict TypeScript, ESLint, 11 unit tests, production build, 10 Chrome tests, one Electron test and the compatible smoke benchmark. The native Python suite passed 51 tests with 2 environment skips.
- Chrome verified 11 distinct transition images including Off. It reordered the rotation through the UI, reloaded, and confirmed the new first effect. Unit tests verified playlist validation, wrap, shuffle and inclusion of Original.
- The 720p smoke carousel measured 29.98 FPS, 36.9 ms interval p95, 0.34 ms GPU p95 and 36.1 ms trigger-to-draw p95. Per-mode p95 intervals were 36.5–37.6 ms, within the compatible baseline threshold. One Impact Frame window averaged 25.73 FPS despite a 37.1 ms p95.
- Physical camera, microphone, snap accuracy, OBS capture, Virtual Camera delivery, receiving apps and release soak remain **NOT VERIFIED**.
