# OBS Virtual Camera on Windows

Use the dedicated Electron output window for OBS. Keep it visible and unminimized during the call. The separate studio controls can stay open, move behind OBS, or close while the output runs.

1. Install [OBS Studio](https://obsproject.com/) and open the SNAP//REALITY app. In the controls, select the physical webcam and click **Start camera**. Allow Windows camera access if prompted. Verify that motion is live. Press **R** in the output window to check framing and use a printed word to check the mirror setting.
2. Click **Show OBS output**. Verify that `SNAP//REALITY — OBS OUTPUT` shows only the canvas in its client area. Press **Ctrl+Shift+O** in the output to reopen controls after closing them.
3. In OBS, create a scene named **SNAP REALITY CAMERA**. Add **Window Capture** and select the window containing that output. Set **Window Match Priority** to **Window title must match**. Turn off **Capture Cursor**. Use **Client Area** if offered and verify the entire capture contains only processed video. Leave other sources out of this scene.
4. In **Settings → Video**, set Base and Output resolution to **1280 × 720** and FPS to **30**. Right-click the source and choose **Transform → Fit to Screen**. Inspect the preview for bars and cropping before starting the virtual camera. For a fixed 720p30 acceptance run, choose **Balanced** and **Lock quality** in SNAP//REALITY.
5. Click **Start Virtual Camera**. In the virtual camera gear menu, choose **Scene** and select **SNAP REALITY CAMERA** to isolate the call feed from other OBS scenes.
6. Select **OBS Virtual Camera** in Discord, Zoom or Google Meet. Pick a separate voice microphone in the call app. Click the SNAP//REALITY output window and press **Space**. Check the change on the local canvas, in OBS preview, and in the call preview.

For browser development, keep the app alone in a dedicated Chrome window, click **Clean OBS output**, then press **F** for a canvas-only fullscreen view if needed. Inspect the OBS preview before going live. Stop Virtual Camera before pressing **Esc** to restore the browser controls.

### Record the hardware acceptance run

The automated Chrome tests use a synthetic camera and a generated scene. Physical webcam, physical snaps, OBS Window Capture, OBS Virtual Camera and the receiving apps are **NOT VERIFIED**.

- Record Windows, webcam model and negotiated resolution, GPU and driver, Chrome and OBS versions, capture method, quality profile, and external app.
- Run for at least 10 minutes with the webcam and virtual camera active. Check local Diagnostics source FPS and render FPS separately. Observe frozen or repeated frames in the OBS preview and in the call preview. Confirm settings, title bar and cursor are absent.
- Start a local video recording while the virtual camera is active. Switch effects and pause, resume, then stop the recording. Check the saved video, OBS preview and call preview for continuity.
- With gesture tracking enabled in a build that supports it, try 30 snaps and 30 ordinary hand motions in good light. Record accepted snaps, misses, false positives and duplicate effect changes. Confirm switching never stops the webcam or blanks the receiving app.
- Repeat in **Visual + audio** with the microphone explicitly enabled. Try claps and taps without the hand motion, then confirm that only paired events advance the effect. Check that disabling the microphone returns to visual detection and leaves the camera active.
- Reopen the call app and select the camera again. Switch OBS scenes and return. Unplug and reconnect the webcam, then verify manual recovery. Stop the virtual camera and verify the receiver detects the change.
- Select **Person only**, **Background only** and **Split style**. Check that the receiving app shows the intended areas and that a mask failure keeps the feed live.
- For physical snap-to-receiver latency, record the hand and receiver screen in the same high-frame-rate video, count frames from finger release to visible effect change, and report the frame rate and measurement uncertainty. The in-app trigger-to-draw timer ends at renderer submission.

See [OBS troubleshooting](OBS_TROUBLESHOOTING.md). [OBS Window Capture](https://obsproject.com/kb/window-capture-sources) · [OBS Virtual Camera](https://obsproject.com/kb/virtual-camera-guide)
