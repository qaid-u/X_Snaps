# 01 — Camera, renderer and browser clean output

2026-11-12, Windows build 26300, Node 24.15.0, Chrome 157.0.8103.39, ANGLE Direct3D11 on NVIDIA GeForce RTX 3060 Laptop GPU. Modules added include the React studio, camera lifecycle, Three.js renderer, five shader effects, adaptive profiles, performance monitor and Playwright harness.

- `npm ci` and `npm run validate` passed. Validation ran strict typecheck, ESLint, 4 unit tests, the Vite production build, 2 Chrome integration tests and 1 performance smoke. The build reported a bundle-size warning.
- Initial compilation failed because the shader helper collided with Three.js's `luminance` helper. Renaming the helper resolved the compile error. ESLint was scoped away from the existing local Python virtual environment.
- Actual 1280 × 720 generated DEMO fixture measured 29.88–30.13 rendered FPS across the six modes. Frame interval p95 ranged from 36.6 to 37.4 ms, with zero sampled intervals above 50 ms. Carousel stress p95 was 37.8 ms and local trigger-to-draw p95 was 35.5 ms. Shader compile and first draw took 120.4 ms.
- Saved the [first web smoke baseline](../performance/baseline-mvp.json). The existing TouchDesigner result is a separate baseline. Source FPS was unavailable for the procedural fixture.
- A synthetic camera test confirmed one acquisition, a persistent canvas, stable shader program count, and track cleanup. The effect shaders produced distinct pixel hashes. Physical webcam, physical snaps, Windows OBS capture, Virtual Camera and receiving apps are **NOT VERIFIED**.
