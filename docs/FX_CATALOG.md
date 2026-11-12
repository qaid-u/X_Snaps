# Effects and transitions

All styles take the live source as their input. The full build renders representative frames into `artifacts/stage6/` and records the shader and output checks in its build report.

| ID | Style | Processing |
| --- | --- | --- |
| 00 | Original | Source pass-through |
| 01 | Realism CGI | Cinematic grade, detail contrast, bloom, and grain |
| 02 | Illustrated 2D | Simplified colors, drawn edges, and paper grain |
| 03 | Comic Pop Art | Three-tone ink, printed dots, and panel framing |
| 04 | Halftone Print | Luminance-driven dots and optional color plates |
| 05 | Cel Shaded | Banded brightness, luminance-gradient lighting, and ink |
| 06 | Posterized | Adjustable quantization and dithering |
| 07 | Speed Lines | Radial or linear streaks around the effect center |
| 08 | Radial Zoom Blur | Quality-scaled taps pulsing toward the center |
| 09 | RGB Glitch | Channel offsets, jitter, and intermittent block shifts |
| 10 | Frame Echo | Decaying, offset ghost of preceding frames |
| 11 | Ink Splash | Animated ink noise and directional brush fibers |
| 12 | Prismatic Fracture | Cell refraction with chromatic separation |
| 13 | Geometric Shatter | Rotated 2D shards with displaced source samples |
| 14 | Neon Trails | Directional glow and fading luminous history |
| 15 | Color Remap | Four palette ramps driven by source hue and luminance |
| 16 | Vortex Portal | Polar warp, moving rings, and rim glow |
| 17 | Synthwave Grid | Perspective grid and stars over the live image |
| 18 | Comic Starburst | Animated jagged shape and speedline fan |
| 19 | Mixed Media | Illustration, color split, and newsprint in moving cutouts |
| 20 | Graphic Monochrome | High contrast, hatching, and a diagonal accent slash |

The Stage 2 checkpoint includes 00, 06, 03, 04, and 09 in that order.

## Transition presets

| Preset | Main elements |
| --- | --- |
| SnapChain | Radial wipe, impact frame, SNAP typography, and shards |
| ComicHit | Diagonal wipe, impact frame, POP typography, and beams |
| InkPortal | Brush reveal and a shard portal |
| GlitchBreak | Digital reveal and offset blocks |
| NeonSwitch | Radial wipe, neon beams, and a perspective tunnel |
| GentleLowFlash | Crossfade and pastel polygons |
| SolarBurst | Expanding radial burst and beams |
| GoldenGate | Golden geometric rings and shards |
| PastelDrift | Crossfade with floating polygons |
| PerspectiveRush | Concentric tunnel and expanding burst |
| InkImpact | Ink wipe with a short impact |

See [transition timings](../presets/transitions.json) for the composable layer windows. The [showcase timeline](../presets/reference_inspired_timeline.json) associates timestamp labels with original archetypes and supplies a separate DEMO performance sequence.
