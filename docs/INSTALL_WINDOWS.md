# Install on Windows

Install TouchDesigner, activate your license, and open the supplied project. TouchDesigner uses embedded Python for project construction. Native Windows x64 CPython 3.12 is needed only for the optional gesture worker. DEMO and keyboard controls work before the worker is installed. [Getting started with TouchDesigner](https://docs.derivative.ca/Getting_Started_With_TouchDesigner)

From the source folder in PowerShell, run the setup script. If it cannot find your Python, pass the full interpreter path with `-PythonExe`.

```powershell
Set-Location 'D:/Side_Projects/X_Snaps'
& .\scripts\setup_windows.ps1
& .\scripts\start_gesture_service.ps1 -Mode 'AUDIO+VISION'
```

The setup script runs the equivalent of creating `.venv-gesture` with Python's `venv` module, installing the packages pinned in `requirements-gesture.txt`, checking their imports, and putting the Hand Landmarker model under `assets/models`. It does not change the system Python or use the TouchDesigner interpreter. The model download and package installation require network access. After setup, recognition runs locally.

If you need to supply packages or the model manually, create the environment with the native Python executable, install the wheel requirements, and place the upstream Hand Landmarker task file at `assets/models/hand_landmarker.task`.

```powershell
py -3.12 -m venv .venv-gesture
& .\.venv-gesture\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-gesture.txt
& .\.venv-gesture\Scripts\python.exe -m pip check
```

Choose `-Mode VISION` for camera only, `-Mode 'AUDIO+VISION'` for camera plus transient confirmation, or `-Mode KEYBOARD` to test the worker without devices. `AUDIO_ONLY` is experimental. Windows camera and microphone privacy settings must allow desktop apps to access the chosen devices. Use **Ctrl+C** to stop the worker. See [calibration](GESTURE_CALIBRATION.md).
