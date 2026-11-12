# Troubleshooting

| Symptom | Check |
| --- | --- |
| Blank or frozen preview | Switch to DEMO and press **R**. Make sure the TouchDesigner timeline is playing. Inspect `OUT_FINAL`, then trace back to the active source and effect. |
| Shader error or magenta output | Open Textport, check the affected GLSL TOP's error messages, and review the build report. Rebuild after correcting the shader file. TouchDesigner supplies its own GLSL version header. |
| Capture repeats the output | Move the clean output window to a display outside the capture, or choose an application window in Screen Grab TOP. |
| File source falls back | Check the exact local path and whether Movie File In can decode the file. Try DEMO to isolate the issue. |
| Camera cannot open | Allow desktop camera access in Windows. Stop competing apps and the gesture worker before using the same camera in TouchDesigner. |
| Bridge shows disconnected | Keep the full project open and verify that the sender and OSC In DAT use UDP port 7400 on localhost. If a second project is open, close it to release the port. Run the test sender with device capture stopped. |
| Sound meter moves but snaps fail | Use a short, distinct snap. Reduce nearby noise and check the calibration thresholds, the camera's view of finger contact, and the worker mode. |
| No mic input | Check Windows desktop microphone permissions and the configured input. Test in VISION mode if the mic is unavailable. |
| Recording fails | Check the output path and disk space, try a supported codec, or use an image sequence. |
| Project startup errors after moving files | Keep the project and source tree together and rebuild from the new absolute path in the TouchDesigner Textport. |

To identify a local process using the default UDP port, run this in PowerShell.

```powershell
Get-NetUDPEndpoint -LocalPort 7400 | Select-Object LocalAddress,LocalPort,OwningProcess
```

Use the [build guide](HOW_TO_BUILD_TOE.md) to validate the saved project after diagnosing an issue. See the [calibration guide](GESTURE_CALIBRATION.md) for snap misses and false triggers.
