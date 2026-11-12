# SNAP//REALITY development

- Keep TouchDesigner project construction in `bootstrap/`. Run that code from the TouchDesigner Textport. Keep vision and audio inference in `gesture_service/` in a separate Windows CPython process.
- Save a `.toe` through TouchDesigner after operator and image validation. Preserve the last working checkpoint before rebuilding and record the TouchDesigner version, GPU, resolution, and observed results in `DEVELOPMENT.md`.
- Route output through `/project1/SNAP_REALITY/OUT_FINAL` and effect changes through the effect controller.
- Update `presets/effects.json` and the corresponding GLSL source together. Run the Python tests after modifying data models, presets, routing, or shaders. Verify GLSL and interaction inside TouchDesigner before reporting native runtime results.
- Keep the generated DEMO independent of files and capture devices. Keep audio, video and desktop capture opt-in.
