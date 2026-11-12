# 00 — Existing project audit and regression repair

2026-11-12, Windows. The working tree initially contained a TouchDesigner project without Git metadata. The GitHub default branch had a README-only history. The workspace was attached to that branch without replacing working files.

- Detected Node 24.15.0, npm 10.7.0, Git 2.53.0, native Python 3.12, and Chrome. No TypeScript app or npm gates existed in this iteration.
- Existing performance evidence is a 60.017 s native DEMO run at 960 × 540 on TouchDesigner 2025.33230 and an RTX 3060 Laptop GPU. It recorded 3,602 samples, p95 cook time 3.472 ms, and zero reported drops. This is a historical native result with a different workload and clock than the web renderer.
- `scripts/run_tests.ps1 -PythonExe C:/Python312/python.exe` initially failed one of 53 tests because the microphone permission diagnostic was overwritten. Preserved that diagnostic in `gesture_service/main.py`. Rerun passed 51 and skipped 2 (UDP loopback unavailable in sandbox, optional python-osc parity).
- No native shader, operator, or saved project was changed. Physical camera, snap, OBS and receiving apps were not exercised.
