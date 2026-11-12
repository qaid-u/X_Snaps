# Perform with SNAP//REALITY

Open the project and press **F1**. The preview shows `OUT_FINAL` and the current mode. Click **SNAP TO SWITCH** or use the following keys while TouchDesigner has focus.

| Key | Action |
| --- | --- |
| **N** or **Right Arrow** | Advance the selected playlist |
| **Left Arrow** | Select the previous effect |
| **Space** | Send a keyboard snap through the controller |
| **R** | Return to Original and clear visual history |
| **Escape** | Leave Perform Mode |

**Output** opens a separate display window for the image. If controls are needed while using a second monitor, keep the performance panel on your primary display. The **Original** button restores the source quickly.

## Inputs

- **DEMO** generates moving shapes, graphics, a counter, a landscape, and color swatches. It is the default startup source.
- **SCREEN** captures the display or window configured in the Screen Grab TOP under `INPUT_MANAGER`. The app can select a secondary display when available. On a single-display setup, choose an application window in that TOP. Keep the clean output outside the captured target to avoid recursive feedback.
- **VIDEO** uses the selected file and the playback and loop settings. Use a supported local codec and file.
- **IMAGE** uses a selected still image.
- **CAMERA** uses the device selected on the Video Device In TOP under `INPUT_MANAGER`. Stop the worker before handing TouchDesigner ownership of the same camera. To use both at once, choose a separate device on that TOP and enable **Controls → Input / Output → Camera separate from tracker**.

Use aspect-fit for general playback and crop when you intend to fill the frame. Select DEMO if a device or file is missing and use the diagnostics to check the selected source.

## Effects and transitions

Select an effect directly or use the active playlist. Use **Add to Playlist** or **Remove from Playlist** to include or exclude the current effect. Use **Controls → Effect Library** to search or edit the playlist IDs in order. Select **Showcase** to play the 72-second reference-inspired DEMO sequence. Reset to Original to clear history effects such as Frame Echo and Neon Trails.

Open **Controls → Performance** to choose the playback mode, transition, intensity, duration, and quality. The default accessibility profile is **LOW_FLASH**. Choose **GentleLowFlash** to reduce transition activity further. Rapid movement, changes in brightness, and high contrast can affect photosensitive viewers.

For gesture control, start the worker with `AUDIO+VISION`, use DEMO or SCREEN, and check the tracker status in the performance panel. **Arm OSC snaps** also gates **Space** and **Snap to Switch**. **N**, the arrow keys and manual effect selection stay available while disarmed or in Manual mode. **Save Config** writes the persistent source, performance and playlist settings to `settings.json` beside the project. Playback starts at Original when you reopen the project. See [gesture calibration](GESTURE_CALIBRATION.md).
