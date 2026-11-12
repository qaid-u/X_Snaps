# SNAP//REALITY

SNAP//REALITY applies real-time GPU effects to a TouchDesigner preview. Cycle the generated demo with a key or connect the local gesture worker for thumb-and-middle-finger snaps. The clean output is a separate TouchDesigner window.

## Run the preview

1. Open `SnapReality.toe` in TouchDesigner. For the five-effect DEMO build, open `checkpoints/SnapReality-stage2.toe`. Keep the project and source files together.
2. The full project opens in Perform Mode. Press **F1** to enter Perform Mode from the editor, including when using the Stage 2 checkpoint. Click inside the panel to give it keyboard focus.
3. Press **N** or **Right Arrow** for the next effect, **Left Arrow** for the previous effect, **Space** for a keyboard snap, and **R** for Original. Use **Output** or the prototype's **Clean Output** for the image without controls. Close the clean window with its title-bar **X**. Press **Escape** to leave Perform Mode.

Use **Showcase** to play the 72-second DEMO timeline in TouchDesigner or watch the [standalone showcase video](artifacts/SnapReality-Showcase.mp4).

With fresh settings, the preview starts in **DEMO** and works without a camera, microphone, or Python environment. TouchDesigner Non-Commercial limits TOP resolution to 1280 × 1280. The supplied profiles fit within that limit. Paid TouchDesigner work requires a Commercial or Pro license. [Derivative licensing](https://docs.derivative.ca/Frequently_Asked_Questions)

## Build from source

Open a new TouchDesigner project, then open **Dialogs → Textport and DATs**. Run this in the **TouchDesigner Textport**. Substitute the path to your own checkout if you move the project.

```python
import runpy; runpy.run_path(r'D:/Side_Projects/X_Snaps/bootstrap/build_project.py', init_globals={'SNAP_STAGE': 6}, run_name='__main__')
```

The builder uses TouchDesigner to compile and render the shaders, writes the build report to `artifacts/stage6/build-report.json`, and saves `SnapReality.toe` after validation. Use `SNAP_STAGE: 2` to rebuild the five-effect checkpoint. See [build and reopen checks](docs/HOW_TO_BUILD_TOE.md).

## Start snap recognition

Install native Windows x64 CPython 3.12. Run these commands from the project folder in PowerShell. Setup downloads the pinned packages and MediaPipe Hand Landmarker model. Inference and OSC run locally after installation.

```powershell
Set-Location 'D:/Side_Projects/X_Snaps'
& .\scripts\setup_windows.ps1
& .\scripts\start_gesture_service.ps1 -Mode 'AUDIO+VISION'
```

For a test without devices or gesture dependencies, launch the full project and send one localhost event from a Python 3.11 or newer interpreter.

```powershell
python -m gesture_service.send_test_snap
```

Use a well-lit view of the fingers at a comfortable distance. Start with your hand about 45–75 cm from the camera and keep the microphone near enough to distinguish the snap from background transients. A 30 FPS webcam may miss contact or release. See [gesture calibration](docs/GESTURE_CALIBRATION.md) for the ten-trial workflow. Use **DEMO** or **SCREEN** while the gesture service owns the webcam.

## Use your own source

Choose **SCREEN**, **VIDEO**, **IMAGE**, or **CAMERA** in the full project. For **SCREEN**, target a specific application or second display in the Screen Grab TOP. Keep the clean output off the captured display to avoid recursive feedback. Set video and image paths through the app controls or saved settings. Source and device behavior is covered in the [user guide](docs/USER_GUIDE.md).

The 21 effects process the live 2D image. Realism CGI adds a tone curve, faux lighting and depth cues, bloom, and grain. The shatter and portal effects simulate displacement in screen space. Start with the **LOW_FLASH** default or select **GentleLowFlash** for a gentler transition. Rapid color and contrast changes may affect photosensitive viewers.

## Verify and troubleshoot

```powershell
& .\scripts\run_tests.ps1
```

The Python test suite covers state, OSC, detector logic, settings, and shader resources. Install the gesture environment to enable the NumPy waveform and `python-osc` parity checks. The UDP wire check also needs permission for local loopback traffic. [Development log](DEVELOPMENT.md) and [native build reports](artifacts/) record observed runtime results.

- [Windows installation](docs/INSTALL_WINDOWS.md)
- [Build and reopen](docs/HOW_TO_BUILD_TOE.md)
- [Operator network](docs/OPERATOR_NETWORK.md)
- [Effect and transition catalog](docs/FX_CATALOG.md)
- [Performance profiles and capture](docs/PERFORMANCE_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Limitations](docs/LIMITATIONS.md)
- [Third-party notices](LICENSE-THIRD-PARTY.md)
