"""Embedded TouchDesigner DAT. Resolve companion sources from the project folder."""

import json
from pathlib import Path
import sys
import time

import td


def initialize():
    global app, panel, nodes, controller, receiver, order, folder, pressed, ui_due, feedback_version
    global settings_path, last_error
    controls = me.parent()
    app = controls.parent()
    panel = app.op('UI/PERFORMANCE_PANEL')
    project_dir = Path(td.project.folder)
    folders = (project_dir, project_dir.parent, Path(controls.op('BUILD_ROOT').text))
    folder = next((path for path in folders if (path / 'presets/effects.json').is_file()), None)
    if folder is None:
        raise RuntimeError('SNAP//REALITY companion files are missing beside the project.')
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    from td_scripts.effect_controller import EffectController, load_playlists
    from td_scripts.fx_registry import load_registry
    from td_scripts.osc_callbacks import OscReceiver
    from td_scripts.settings_manager import Settings, load_settings
    from td_scripts.transition_library import load_showcase, load_transitions

    order = json.loads(controls.op('EFFECT_ORDER').text)
    registry = {item: definition for item, definition in load_registry(folder).items() if item in order}
    transitions = load_transitions(folder)
    settings_path = folder / 'settings.json'
    settings, last_error = load_settings(settings_path, registry, transitions) if len(order) == 21 else (Settings(), None)
    if len(order) == 21:
        name, playlists = load_playlists(folder, registry, transitions)
        order_default = playlists[name][0]
        duration, cues = load_showcase(folder, registry, transitions)
    else:
        order_default = order
        duration, cues, playlists = 0, (), {}
    controller = EffectController(registry, settings, transitions, default_playlist=order_default,
                                  performance_cues=cues)
    receiver = OscReceiver(controller, max_event_age=1.5)
    nodes = {item: app.op('FX_ENGINE/FX_' + item) for item in order}
    pressed = set()
    ui_due = 0
    feedback_version = -1
    if controls.op('full_runtime'):
        controls.op('full_runtime').module.initialize(
            app, panel, controller, receiver, folder, settings_path, last_error, playlists, duration, cues
        )
    tick()


def update_vectors(node, block, values, skip_time=False):
    for axis, value in zip('yzw' if skip_time else 'xyzw', values[1:] if skip_time else values):
        parameter = getattr(node.par, f'vec{block}value{axis}')
        if parameter.eval() != value:
            parameter.val = value


def set_value(parameter, value):
    if parameter.eval() != value:
        parameter.val = value


def tick():
    if 'controller' not in globals():
        return
    global feedback_version, ui_due
    now = time.monotonic()
    frame = controller.update(now)
    if controller.state.feedback_reset != feedback_version:
        feedback_version = controller.state.feedback_reset
        for item in ('10', '14'):
            history = app.op('FX_ENGINE/HISTORY_' + item)
            if history:
                history.par.resetpulse.pulse()
    for item in {frame.current_effect, frame.previous_effect}:
        uniforms = controller.effect_uniforms(item, now)
        for i, name in enumerate(('uFrame', 'uOptions', 'uParams')):
            update_vectors(nodes[item], i, uniforms[name], skip_time=(name == 'uFrame'))
    set_value(app.op('FX_ENGINE/CURRENT').par.index, order.index(frame.current_effect))
    set_value(app.op('FX_ENGINE/PREVIOUS').par.index, order.index(frame.previous_effect))
    active = frame.phase != 'IDLE'
    if active:
        transition = app.op('TRANSITIONS/TRANSITION')
        for index, values in enumerate((frame.transition, frame.layers, frame.timing)):
            update_vectors(transition, index, values)
        set_value(app.op('TRANSITIONS/TYPOGRAPHY').par.text, frame.typography)
    set_value(app.op('COMPOSITING/ACTIVE_IMAGE').par.index, int(active))
    if now >= ui_due:
        ui_due = now + 0.16
        status = receiver.update(now)
        eid = frame.current_effect
        display_name = controller.registry[eid].name.upper().replace('_', ' ')
        counter = f' / {len(order)}' if len(order) == 21 else ''
        set_value(panel.op('CURRENT_TEXT').par.text, f'{eid}{counter}   {display_name}')
        full = me.parent().op('full_runtime')
        if full:
            full.module.refresh(status, now)


def action(name):
    if 'controller' not in globals():
        return
    if name == 'output':
        app.op('OUTPUT_MANAGER/OUTPUT_WINDOW').par.winopen.pulse()
    elif name in ('next', 'previous', 'random', 'reset', 'snap'):
        getattr(controller, name)()
        tick()
    else:
        full = me.parent().op('full_runtime')
        if full:
            full.module.action(name)
            tick()


def key(key_name, state):
    key_name = str(key_name).lower()
    if not state:
        pressed.discard(key_name)
        return
    if key_name in pressed:
        return
    pressed.add(key_name)
    name = {'n': 'next', 'space': 'snap', ' ': 'snap', 'r': 'reset',
            'left': 'previous', 'right': 'next'}.get(key_name)
    if name:
        action(name)


def shutdown():
    full = me.parent().op('full_runtime')
    if full:
        full.module.shutdown()


def osc(address, args, peer):
    if 'receiver' in globals() and str(peer.address) in ('127.0.0.1', '::1', '::ffff:127.0.0.1'):
        receiver.handle(address, args, time.monotonic())
