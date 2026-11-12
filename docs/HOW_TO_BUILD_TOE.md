# Build and reopen the TouchDesigner project

Use TouchDesigner with GPU drivers installed and a valid TouchDesigner license. Keep `bootstrap/`, `shaders/`, `presets/`, and `td_scripts/` at the root of the same source checkout.

1. Start TouchDesigner and create a new project. If you have another project open, save it before switching.
2. Open **Dialogs → Textport and DATs** and enter the following Python. Update the absolute path if you moved the checkout.

   ```python
   import runpy; runpy.run_path(r'D:/Side_Projects/X_Snaps/bootstrap/build_project.py', init_globals={'SNAP_STAGE': 6}, run_name='__main__')
   ```

3. Read the Textport output. The builder validates shader compiles, output dimensions, representative rendered pixels, and DEMO motion before saving. The JSON report and rendered frames are under `artifacts/stage6/`.
4. Open `SnapReality.toe` through **File → Open**. It opens in Perform Mode. Focus the panel and verify the preview moves, **N** advances one effect, and **R** returns to Original. Open **Output** and close it with its title-bar **X**. Use **Escape** to exit Perform Mode and **F1** to return from the editor.
5. For the reopening smoke check, run the following from the TouchDesigner Textport after opening the saved project.

   ```python
   import runpy; print(runpy.run_path(r'D:/Side_Projects/X_Snaps/bootstrap/validate_project.py')['reopen_check']())
   ```

To produce the prototype, set `SNAP_STAGE` to `2` or omit `init_globals`. The default Stage 2 save path is `checkpoints/SnapReality-stage2.toe`. It has the five initial effects and a keyboard-controlled DEMO.

Rebuilding affects the project's owned `SNAP_REALITY` component and the Perform window target. After validation, the builder archives prior destination files in `checkpoints/` and asks TouchDesigner to save the new project. If validation fails, inspect the staging component and Textport messages before retrying. Saving requires TouchDesigner's embedded Python runtime.

## Shader and script changes

Edit the source under `shaders/`, `presets/`, or `td_scripts/`. Re-run the builder to load shader and embedded DAT changes. Restart TouchDesigner before rebuilding changes to imported Python modules so the interpreter picks up the edited files. The saved project contains the built network and shader DATs. Keep the external source and presets beside the project to support startup, settings, and rebuilds.

For shader-only changes, use the Textport in an open SNAP//REALITY project:

```python
from bootstrap.reload_sources import reload_shaders; print(reload_shaders())
```

This updates the changed GLSL DATs, checks compiler errors and restores the previous shader text if validation fails. Save or rebuild the project to persist the refreshed shaders.

See [Derivative's GLSL TOP documentation](https://docs.derivative.ca/Write_a_GLSL_TOP) for built-in texture uniforms, output swizzle, and shader compilation behavior.
