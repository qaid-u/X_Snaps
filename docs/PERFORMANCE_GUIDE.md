# Performance and measurement

| Quality | Internal output | Target cook rate |
| --- | --- | --- |
| LOW | 640 × 360 | 30 FPS |
| BALANCED | 960 × 540 | 60 FPS |
| HIGH | 1280 × 720 | 60 FPS |

The target cook rate is a setting. The panel shows the FPS measured by TouchDesigner. All profiles fit within the 1280 × 1280 texture limit of TouchDesigner Non-Commercial. The size of the Perform window is independent of the internal effect resolution.

## Run the 60-second benchmark

1. Open `SnapReality.toe`, select DEMO and choose a quality profile. Keep the project timeline running.
2. To measure a moving sequence of effects, click **SHOWCASE**. To measure one effect, select it from the effect library.
3. Open the Textport with **Alt+T** and enter these lines. Close the Textport and press **F1** to measure the live performance panel.

   ```python
   from pathlib import Path
   import sys
   folder = Path(project.folder)
   sys.path.insert(0, str(folder))
   from bootstrap.benchmark import start
   report_path = start(folder)
   ```

4. Leave the preview visible and let the benchmark run for the two-second warm-up and 60-second sample. Use **Esc** to exit Perform Mode after the report appears at `reports/benchmark-<UTC timestamp>.json` under the project folder. The `report_path` variable holds the full path.

The JSON report contains the measured rolling FPS, cook times, skipped frames reported by the Perform CHOP, independent absolute-frame gaps, effects and transition phases, and the number of times `OUT_FINAL` cooked. It records the GPU, quality, resolution and Perform Mode state. These are TouchDesigner process measurements. Measuring presentation at the display requires separate display instrumentation. [Derivative Perform CHOP](https://docs.derivative.ca/Perform_CHOP), [Derivative Perform Mode](https://docs.derivative.ca/Perform_Mode)

## Measured baseline

TouchDesigner 2025.33230 ran the DEMO showcase in Perform Mode at BALANCED quality (960 × 540) on an NVIDIA GeForce RTX 3060 Laptop GPU. The 60.017-second run sampled 3,602 frames, about 60 FPS, and logged zero dropped frames or absolute timeline gaps. Mean frame cook time was 2.41 ms, with a 3.47 ms 95th percentile. The run sampled all 21 effects and all five transition states. [Native benchmark report](../reports/benchmark-20261111T160719845811Z.json)

## Capture the clean output

- **PNG** saves a timestamped frame from `OUT_FINAL` into `captures/`.
- **Rec** starts a capture and **Stop** ends it. Choose **PNG sequence** or **Motion JPEG / MOV** in **Controls → Input / Output → Capture format**. Motion JPEG availability depends on your TouchDesigner build and system. PNG sequence is the fallback.
- **Output** opens the clean image. Choose the monitor and fullscreen behavior in **Controls → Input / Output**.
- Close windowed clean output with its title-bar **X**. For borderless output, pulse **Close** on the `OUTPUT_MANAGER/OUTPUT_WINDOW` COMP in Designer Mode.

## Isolate a bottleneck

- Use DEMO to measure the graphics pipeline without the variability of camera or screen capture. For capture diagnostics, repeat with that source and compare reports at the same quality.
- The effect switches request only the current effect in steady state and current plus previous during a transition. Keep diagnostic viewers of unused effects closed while measuring.
- `FRAME_ECHO` and `NEON_TRAILS` use a feedback texture. Their history is cleared on source and effect changes to avoid carrying a previous scene into the next look.
- Try LOW when using feedback or multi-tap blur on a constrained GPU. Screen capture, video decode, capture encoding and additional visible windows also use system resources.
