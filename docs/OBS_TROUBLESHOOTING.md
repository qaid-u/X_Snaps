# OBS troubleshooting

- **Black preview.** Check that SNAP//REALITY is visible, the source targets the right window, and Window Capture can see its client area. Try **Automatic**, then Windows Graphics Capture if available, then **BitBlt** for compatibility. Compare smoothness on the actual GPU.
- **Controls or browser chrome in frame.** Stop Virtual Camera and select the dedicated **SNAP//REALITY — OBS OUTPUT** window with client-area capture. For browser development, re-enter Clean OBS output and inspect the whole source. Use canvas fullscreen or crop persistent browser chrome if needed.
- **Camera unavailable.** Confirm Windows and Chrome allow camera access, then stop the physical webcam in other apps. Use the physical device in SNAP//REALITY and the virtual device in the call app.
- **Virtual camera missing.** Start Virtual Camera in OBS, check its selected scene, then close and reopen the receiving app's camera preview. Relaunch the receiver if it cached the device list.
- **Stutter.** Compare local render cadence, OBS preview and the receiving app first. Use 720p30, remove other active OBS sources and filters, test capture methods, and check CPU and GPU load. A 30 FPS source supplies at most 30 unique camera frames even when output draws at 60 Hz.
- **Recursive feed.** Remove Display Capture and any virtual-camera input from the scene. Keep only a Window Capture source aimed at the processed output.
