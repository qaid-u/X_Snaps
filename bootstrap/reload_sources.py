"""Refresh and validate embedded shader DATs in the open SNAP//REALITY project."""

from pathlib import Path

import td

from bootstrap.validate_project import inspect


def reload_shaders():
    app = td.op('/project1/SNAP_REALITY')
    if app is None:
        raise RuntimeError('Open the SNAP//REALITY project first')
    runtime = app.op('CONTROL_ENGINE/runtime').module
    root = Path(runtime.folder)
    common = (root / 'shaders/common.glsl').read_text(encoding='utf-8-sig') + '\n'
    sources = {
        app.op('INPUT_MANAGER/DEMO'): common + (root / 'shaders/demo.frag').read_text(encoding='utf-8-sig'),
        app.op('TRANSITIONS/TRANSITION'): (root / 'shaders/transition_compositor.frag').read_text(encoding='utf-8-sig'),
    }
    for key, definition in runtime.controller.registry.items():
        sources[runtime.nodes[key]] = common + (root / definition.shader).read_text(encoding='utf-8-sig')
    previous = {}
    try:
        for node, source in sources.items():
            dat = node.par.pixeldat.eval()
            if dat.text != source:
                previous[dat] = dat.text
                dat.text = source
                # Compile the updated node even when it isn't selected.
                node.cook(force=True)
                if errors := node.errors():
                    raise RuntimeError(f'{node.path}: {errors}')
        inspect(app.op('OUT_FINAL'))
    except Exception:
        for dat, original in previous.items():
            dat.text = original
        raise
    runtime.controller.invalidate_feedback()
    return len(previous)
