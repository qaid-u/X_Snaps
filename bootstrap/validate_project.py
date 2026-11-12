"""GPU readback acceptance checks. Run in TouchDesigner only."""

import json
from pathlib import Path

import numpy as np
import td


def inspect(top):
    top.cook(force=True)
    if errors := top.errors():
        raise RuntimeError(f'{top.path}: {errors}')
    pixels = top.numpyArray(delayed=False)
    if pixels is None or pixels.ndim != 3 or min(pixels.shape[:2]) < 32:
        raise RuntimeError(f'{top.path}: missing output pixels')
    pixels = pixels[::6, ::6, :3].copy()
    if not np.isfinite(pixels).all() or float(np.std(pixels)) < 0.012:
        raise RuntimeError(f'{top.path}: blank, uniform or non-finite output')
    return pixels


def delta(first, second):
    return float(np.abs(first - second).mean())


def validate(app, effects, root, stage):
    # Read back the canonical output through each selection, including source and transition.
    demo = app.op('INPUT_MANAGER/DEMO')
    current = app.op('FX_ENGINE/CURRENT')
    previous = app.op('FX_ENGINE/PREVIOUS')
    final = app.op('OUT_FINAL')
    route = app.op('COMPOSITING/ACTIVE_IMAGE')
    transition = app.op('TRANSITIONS/TRANSITION')
    folder = Path(root) / 'artifacts' / f'stage{stage}'
    folder.mkdir(parents=True, exist_ok=True)
    saved = {'00', '03', '04', '06', '09', '14', '20'}
    images = {}
    motions = {}
    try:
        for time_index, moment in enumerate((3.125, 4.375)):
            demo.par.vec0valuex = moment
            source = inspect(demo)
            for index, effect_id in enumerate(effects):
                node = app.op(f'FX_ENGINE/FX_{effect_id}')
                history = app.op(f'FX_ENGINE/HISTORY_{effect_id}')
                if history:
                    history.par.resetpulse.pulse()
                node.par.vec0valuex = moment
                node.par.vec1valuex = moment
                current.par.index = index
                inspect(node)
                image = inspect(final)
                if time_index == 0:
                    images[effect_id] = image
                    if effect_id in saved:
                        final.save((folder / f'{effect_id}.png').as_posix())
                else:
                    motions[effect_id] = delta(image, images[effect_id])
                if effect_id == '00' and delta(image, source) > 0.001:
                    raise RuntimeError('Original does not match the source')
            if final.width > 1280 or final.height > 1280:
                raise RuntimeError(f'Output {final.width}×{final.height} exceeds processing limit')
        minimum_deltas = {
            effect_id: min(delta(image, other) for key, other in images.items() if key != effect_id)
            for effect_id, image in images.items()
        }
        if min(minimum_deltas.values()) < 0.002:
            raise RuntimeError(f'Effects produced indistinguishable images: {minimum_deltas}')
        if min(motions.values()) < 0.002:
            raise RuntimeError(f'Output did not respond to motion: {motions}')

        current.par.index = list(effects).index('03')
        previous.par.index = 0
        route.par.index = 1
        transition.par.vec0valuex = 0.43
        transition.par.vec1valuez = 2
        transition.par.vec2valuex = 0.35
        transition.par.vec2valuew = 0.35
        app.op('TRANSITIONS/TYPOGRAPHY').par.text = 'SNAP!'
        impact = inspect(final)
        final.save((folder / 'transition.png').as_posix())
        route.par.index = 0
        target = inspect(final)
        if delta(impact, target) < 0.005:
            raise RuntimeError('Transition did not visibly change the output')
    finally:
        current.par.index = previous.par.index = route.par.index = 0
        transition.par.vec0valuex = 1.0
        app.op('TRANSITIONS/TYPOGRAPHY').par.text = ''
        demo.par.vec0valuex.expr = 'absTime.seconds'
        for effect_id in effects:
            app.op(f'FX_ENGINE/FX_{effect_id}').par.vec0valuex.expr = 'absTime.seconds'
    operators = app.findChildren()
    report = {
        'stage': stage,
        'touchdesigner': td.app.build,
        'license': getattr(td.licenses, 'type', 'unavailable'),
        'processing_ceiling': [1280, 1280],
        'gpu': td.sysinfo.GPUName,
        'operators': len(operators),
        'connections': sum(len(connector.connections) for node in operators
                           for connector in node.inputConnectors),
        'final_resolution': [final.width, final.height],
        'shaders_passed': ['DEMO', *effects, 'TRANSITION'],
        'minimum_pairwise_rgb_delta': minimum_deltas,
        'moving_demo_rgb_delta': motions,
        'transition_vs_destination_rgb_delta': delta(impact, target),
        'operator_warnings': {node.name: warning for node in (demo, final, transition)
                              if (warning := node.warnings())},
    }
    (folder / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def reopen_check():
    app = td.op('/project1/SNAP_REALITY')
    if app is None:
        raise RuntimeError('SNAP_REALITY was not found after reopen')
    frame = app.op('CONTROL_ENGINE/frame')
    runtime = app.op('CONTROL_ENGINE/runtime').module
    if not frame.par.active or not app.op('CONTROL_ENGINE/KEYBOARD').par.active:
        raise RuntimeError('Frame or keyboard callbacks are disabled after reopen')
    if not hasattr(runtime, 'controller'):
        raise RuntimeError('Embedded startup did not initialize the effect controller')
    final = app.op('OUT_FINAL')
    baseline = inspect(final)
    runtime.controller.set_effect('06', 'reopen verification', immediate=True)
    runtime.tick()
    changed = inspect(final)
    runtime.action('reset')
    if delta(baseline, changed) < 0.005:
        raise RuntimeError('Effect change had no visible result after reopen')
    return {'project': td.project.name, 'resolution': [final.width, final.height],
            'selected_shader_delta': delta(baseline, changed), 'keyboard_active': True,
            'perform_mode': bool(td.ui.performMode)}


def overlay_check():
    """Verify independent overlay and wipe contributions at a frozen DEMO time."""
    from td_scripts.transition_library import OVERLAY_IDS, TYPE_TEXT, WIPE_IDS

    app = td.op('/project1/SNAP_REALITY')
    frame = app.op('CONTROL_ENGINE/frame')
    runtime = app.op('CONTROL_ENGINE/runtime').module
    demo = app.op('INPUT_MANAGER/DEMO')
    current = app.op('FX_ENGINE/CURRENT')
    route = app.op('COMPOSITING/ACTIVE_IMAGE')
    transition = app.op('TRANSITIONS/TRANSITION')
    title = app.op('TRANSITIONS/TYPOGRAPHY')
    final = app.op('OUT_FINAL')
    active = frame.par.active.eval()
    frame.par.active = False
    try:
        runtime.action('reset')
        demo.par.vec0valuex = 3.125
        current.par.index = runtime.order.index('03')
        route.par.index = 1

        def render(wipe=0, overlay=0, flash=0.0, typography=''):
            for block, values in enumerate(((0.42, 1, 0.5, 0.5), (wipe, flash, overlay, 0),
                                             (0.45, 0, 0.36, 0.4 if typography else -1))):
                runtime.update_vectors(transition, block, values)
            title.par.text = typography
            return inspect(final)

        baseline = render()
        overlays = {name: delta(baseline, render(overlay=number)) for name, number in OVERLAY_IDS.items()}
        overlays.update({name: delta(baseline, render(typography=word)) for name, word in TYPE_TEXT.items()})
        overlays['IMPACT_FRAME'] = delta(baseline, render(flash=0.2))
        wipes = {name: delta(baseline, render(wipe=number)) for name, number in WIPE_IDS.items() if number}
        if min((*overlays.values(), *wipes.values())) < 0.001:
            raise RuntimeError(f'An overlay or wipe produced an indistinguishable image: {overlays}, {wipes}')
        return {'overlay_rgb_deltas': overlays, 'wipe_rgb_deltas': wipes, 'baseline': 'CROSSFADE'}
    finally:
        demo.par.vec0valuex.expr = 'absTime.seconds'
        title.par.text = ''
        runtime.action('reset')
        frame.par.active = active
