# Windows studio validation

Install Google Chrome, then run `npm ci` and `npm run setup:models` in the project root. The desktop test installs the pinned Electron binary on first use. For an offline test machine, run `npx --no install-electron` while connected before running the gates offline.

```powershell
npm run validate
npm run perf:benchmark
```

The combined gate runs strict TypeScript, ESLint, Vitest, Vite production build, Chrome integration tests, the Electron window test and the per-effect smoke. Camera tests use Chromium's synthetic camera. Asset tests marked skipped require the pinned model files. Install the assets for a complete run.

The benchmark runs an animated procedural DEMO at locked Balanced 1280 × 720, 30 FPS, followed by a carousel stress run. It records machine, browser, GPU, fixture, profile, resolution and clock settings. It compares only matching workloads and uses the common effect IDs when the catalog changes. For a new environment, record a reviewed baseline with:

```powershell
$env:SNAP_WRITE_BASELINE = '1'
npm run perf:smoke
npm run perf:benchmark
Remove-Item Env:SNAP_WRITE_BASELINE
```

The 10% p95 frame-interval gate compares equivalent runs and retains the initial sample and any confirmation runs. The first playable draw and full shader preparation use separate startup measurements. Stable shader-program and texture counts catch allocation during switches. GPU time is reported when WebGL's timer query returns a valid sample. Source FPS is blank for the procedural DEMO. Trigger-to-draw measures accepted event to renderer submission using the app clock.

For physical media devices, true snap accuracy, OBS delivery and release soak, follow [OBS setup and hardware acceptance](OBS_SETUP.md). Record each environment and result with the iteration. See [iteration reports](../ITERATION_REPORT.md).
