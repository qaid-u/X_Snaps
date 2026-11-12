# Operator network

The app is built under `/project1/SNAP_REALITY`. The five-effect checkpoint contains the same core path with a smaller catalog and a DEMO-only source.

```mermaid
flowchart LR
    Sources["INPUT_MANAGER<br/>source selection and fallback"] --> Effects["FX_ENGINE<br/>active and previous effects"]
    Worker["Local gesture worker"] --> Receiver["GESTURE_RECEIVER<br/>OSC on UDP 7400"]
    Receiver --> Control["CONTROL_ENGINE<br/>state and playlist"]
    UI --> Control
    Control --> Effects
    Control --> Transitions["TRANSITIONS<br/>wipe, typography, overlays"]
    Effects --> Transitions
    Effects --> Composite["COMPOSITING"]
    Transitions --> Composite
    Composite --> Final["OUT_FINAL"]
    Final --> UI
    Final --> Output["OUTPUT_MANAGER<br/>clean window and capture"]
```

- `INPUT_MANAGER` supplies DEMO or a user-selected source at the working resolution.
- `CONTROL_ENGINE` owns transitions, modes, cooldown, event policy, playlist order, and reset. Its frame callback updates TOP state. The receiver parses OSC data without running tracker inference.
- `FX_ENGINE` uses GLSL TOPs and switches to request the active effect. The previous effect is requested during a transition. Frame Echo and Neon Trails use bounded feedback.
- `TRANSITIONS` mixes the two images and composites procedural overlays and generated typography. The compositor uses the active image directly while idle.
- `DIAGNOSTICS` contains build information. Runtime status is available through the performance controls.

The full effect catalog is declared in [effects.json](../presets/effects.json). Transition layer composition is declared in [transitions.json](../presets/transitions.json), and the [reference-inspired timeline](../presets/reference_inspired_timeline.json) schedules the DEMO showcase. See [DEVELOPMENT.md](../DEVELOPMENT.md) for observed validation.
