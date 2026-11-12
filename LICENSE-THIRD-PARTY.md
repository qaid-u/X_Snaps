# Third-party notices

The browser app uses [React and React DOM (MIT)](https://github.com/facebook/react/blob/main/LICENSE) and [Three.js (MIT)](https://github.com/mrdoob/three.js/blob/dev/LICENSE). The pinned build, lint and test dependencies are listed in `package-lock.json`. Keep upstream license files when redistributing a bundle.

The local web vision worker uses [MediaPipe Tasks Vision (Apache-2.0)](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE). `npm run setup:models` fetches Google's Hand Landmarker float16 version 1 asset and verifies its SHA-256. The model is excluded from source control and subject to its upstream terms.

The same setup downloads and verifies Google's landscape Selfie Segmentation float16 version 1 model, licensed under Apache-2.0. [Selfie Segmentation model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Selfie%20Segmentation.pdf)

[OBS Studio](https://github.com/obsproject/obs-studio/blob/master/COPYING) is installed separately by the operator and supplies the virtual camera device.

The Windows package includes [Electron (MIT)](https://github.com/electron/electron/blob/main/LICENSE). Keep the Electron license and Chromium notices distributed alongside the executable.

Derivative TouchDesigner is separately installed and used under the applicable Derivative license. [Derivative licensing](https://docs.derivative.ca/Frequently_Asked_Questions)

The optional gesture environment installs these packages. Preserve the license and third-party notices included in the installed distributions if you redistribute a bundled environment.

| Component | Upstream license and notices |
| --- | --- |
| MediaPipe | [Apache License 2.0](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE) |
| OpenCV | [Apache License 2.0](https://opencv.org/license/) and [Python wheel packaging notices](https://github.com/opencv/opencv-python/blob/4.x/README.md) |
| NumPy | [BSD-3-Clause and bundled component licenses](https://github.com/numpy/numpy/blob/main/doc/source/license.rst) |
| python-osc | [Upstream license file](https://github.com/attwad/python-osc/blob/main/LICENSE.txt) |
| sounddevice | [MIT License](https://github.com/spatialaudio/python-sounddevice/blob/master/LICENSE) and [PortAudio packaging information](https://python-sounddevice.readthedocs.io/en/latest/installation.html) |

The setup script downloads Google's float16 Hand Landmarker model separately. Consult its upstream documentation and model terms before redistribution. [Hand Landmarker model documentation](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)

The demo scene, transition geometry, and preset timing reinterpretations are generated in this project. Typography uses system fonts where available. Source footage and character artwork from the animation reference are excluded.
