# Limitations

- SNAP//REALITY renders into a TouchDesigner preview and clean window. Effects are applied to the selected captured or generated source.
- CGI-inspired grading and screen-space geometry operate on 2D pixels. Lighting, depth, facets, and shards are visual approximations. True 3D reconstruction would require scene geometry or a depth pipeline.
- Gesture performance depends on hand visibility, camera frame rate, and lighting. A 30 FPS camera can miss fast thumb-to-middle-finger release. Mic confirmation adds timing evidence but may miss a quiet snap or require threshold tuning. Calibrate and measure physical trials on the installation hardware.
- Camera and microphone frames stay local. Device capture is opt-in and the worker's OSC messages carry event and diagnostic data. Configure the capture target deliberately before opening the clean output or turning on recording.
- TouchDesigner Non-Commercial TOP resolution is capped at 1280 × 1280. Paid work requires the appropriate license. Codec, input-device, and multi-monitor support depend on the installed TouchDesigner build, hardware, and drivers. [Derivative Non-Commercial license](https://derivative.ca/product/touchdesigner-non-commercial/77)
- Optional future work includes a separate click-through Windows overlay, segmentation, depth-based compositing, and a timeline editor.
