"""Input, performance panel and export callbacks executed inside TouchDesigner."""

from datetime import datetime
from pathlib import Path
import time

import td

from td_scripts.settings_manager import QUALITY_PROFILES, SOURCE_MODES, save_settings
from td_scripts.tracker_process import TrackerProcess


PARAMETERS = {
    'Source': 'source_mode', 'Playback': 'playback_mode', 'Quality': 'profile',
    'Transition': 'transition_preset', 'Collision': 'transition_policy', 'Duration': 'transition_duration',
    'Strength': 'strength', 'Centerx': 'center_x', 'Centery': 'center_y', 'Cooldown': 'cooldown',
    'Lowflash': 'low_flash', 'Armed': 'armed', 'Videofile': 'video_path', 'Imagefile': 'image_path',
    'Playvideo': 'video_play', 'Loopvideo': 'video_loop', 'Crop': 'crop', 'Mirror': 'camera_flip',
    'Independent': 'camera_independent', 'Monitor': 'output_monitor',
}
INACTIVE_TRACKER = ('KEYBOARD', 'STALE', 'DISCONNECTED', 'STOPPED', 'ERROR', 'MIC_UNAVAILABLE')


def initialize(host, performance, engine, osc, workspace, config, problem, playlist_library, length, sequence):
    global app, panel, controller, receiver, folder, settings_path, status_message, showcase, syncing
    global input_signature, input_due, input_status, last_mode, last_style, help_open, hand_tracker
    app, panel, controller, receiver, folder, settings_path = host, performance, engine, osc, workspace, config
    if 'hand_tracker' not in globals():
        hand_tracker = TrackerProcess(folder)
    status_message = problem or ''
    showcase = length, sequence
    input_signature = last_mode = last_style = None
    input_due = 0
    input_status = 'DEMO'
    syncing = True
    help_open = False
    try:
        for name, setting in PARAMETERS.items():
            set_par(app, name, getattr(controller.settings, setting))
        set_par(app, 'Playlist', ','.join(controller.state.playlist))
    finally:
        syncing = False
    sync_effect_parameters('00')
    apply_output()
    osc_in = app.op('GESTURE_RECEIVER/OSC_LOCAL')
    osc_in.par.active = True


def set_par(node, name, value):
    par = getattr(node.par, name)
    if par.eval() != value:
        par.val = value


def asset(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else folder / path


def source_change(status, now):
    global input_signature, input_due, input_status
    settings = controller.settings
    part = app.op('INPUT_MANAGER')
    source = settings.source_mode
    screen, camera, video, image = (part.op(name) for name in ('SCREEN', 'CAMERA', 'VIDEO', 'IMAGE'))
    camera_in_use = hand_tracker.running or status not in (*INACTIVE_TRACKER, 'AUDIO_ONLY')
    camera_blocked = camera_in_use and not settings.camera_independent
    signature = (
        source, settings.video_path, settings.image_path, settings.video_play, settings.video_loop,
        settings.crop, settings.camera_flip, settings.profile, camera_blocked,
    )
    dirty = signature != input_signature
    if dirty:
        input_signature = signature
        controller.invalidate_feedback()
        width, height, fps, _ = QUALITY_PROFILES[settings.profile]
        demo = part.op('DEMO')
        set_par(demo, 'resolutionw', width)
        set_par(demo, 'resolutionh', height)
        title = app.op('TRANSITIONS/TYPOGRAPHY')
        set_par(title, 'resolutionw', width)
        set_par(title, 'resolutionh', height)
        td.project.cookRate = fps
        if source == 'SCREEN' and len(td.monitors) > 1 and screen.par.source.eval() == '0':
            other = next((i + 1 for i in range(len(td.monitors)) if i != td.monitors.primary), 0)
            if str(other) in screen.par.source.menuNames:
                screen.par.source = str(other)
        set_par(screen, 'active', source == 'SCREEN')
        set_par(camera, 'active', source == 'CAMERA' and not camera_blocked)
        set_par(video, 'play', settings.video_play)
        set_par(video, 'textendright', 'cycle' if settings.video_loop else 'hold')
        set_par(part.op('CAMERA_FLIP'), 'flipx', settings.camera_flip)
        for name in SOURCE_MODES[1:]:
            set_par(part.op('FIT_' + name), 'fit', 'fitoutside' if settings.crop else 'fitbest')
    if not dirty and now < input_due:
        return
    input_due = now + 1.0
    valid = True
    input_status = source
    node = part.op(source)
    if source == 'SCREEN' and screen.par.source.eval() == '0':
        valid = False
        input_status = 'DEMO / CHOOSE A SCREEN TARGET'
        set_par(screen, 'active', False)
    elif source == 'SCREEN':
        set_par(screen, 'active', True)
    if source in ('VIDEO', 'IMAGE'):
        value = settings.video_path if source == 'VIDEO' else settings.image_path
        path = asset(value) if value else None
        valid = path is not None and path.is_file()
        set_par(node, 'file', path.as_posix() if valid else '')
        if not valid:
            input_status = 'DEMO / SELECT A LOCAL ' + source
    if source == 'CAMERA' and camera_blocked:
        valid = False
        input_status = 'DEMO / TRACKER OWNS CAMERA'
    if source != 'DEMO' and valid:
        node.cook()
        valid = node.width > 16 and node.height > 16 and not node.errors()
        if not valid:
            input_status = f'DEMO / {source} UNAVAILABLE'
    switch = part.op('SELECT_SOURCE')
    requested = SOURCE_MODES.index(source) if valid else 0
    if switch.par.index.eval() != requested:
        switch.par.index = requested
        controller.invalidate_feedback()


def apply_output():
    node = app.op('OUTPUT_MANAGER/OUTPUT_WINDOW')
    set_par(node, 'justifyoffsetto', 'specifydisplay')
    set_par(node, 'display', min(controller.settings.output_monitor, max(0, len(td.monitors) - 1)))
    fullscreen = app.par.Fullscreen.eval()
    set_par(node, 'size', 'fill' if fullscreen else 'automatic')
    set_par(node, 'borders', not fullscreen)


def sync_effect_parameters(eid):
    global syncing
    syncing = True
    try:
        set_par(app, 'Effect', eid)
        effect = controller.registry[eid]
        overrides = (controller.settings.effect_parameters or {}).get(eid, {})
        for index in range(4):
            par = getattr(app.par, 'Fxparam' + str(index + 1))
            par.enable = index < len(effect.parameters)
            if par.enable:
                spec = effect.parameters[index]
                par.label = spec.name.replace('_', ' ').title()
                par.min = par.normMin = spec.minimum
                par.max = par.normMax = spec.maximum
                par.clampMin = par.clampMax = True
                par.val = overrides.get(spec.name, spec.default)
        app.par.Palette.val = int(overrides.get('palette', 0))
        app.par.Palette.enable = eid in ('07', '14', '15', '16', '17', '18', '20')
    finally:
        syncing = False


def set_playlist(items):
    allowed = tuple(dict.fromkeys(item.strip() for item in items if item.strip() in controller.registry))
    if allowed:
        controller.configure(playlist=allowed)
    set_par(app, 'Playlist', ','.join(controller.state.playlist))


def changed(name):
    global status_message
    if 'app' not in globals() or syncing:
        return
    try:
        value = getattr(app.par, name).eval()
        if name in PARAMETERS:
            controller.configure(**{PARAMETERS[name]: value})
            if name in ('Monitor', 'Fullscreen'):
                apply_output()
        elif name == 'Fullscreen':
            apply_output()
        elif name == 'Effect':
            controller.set_effect(value, 'manual')
        elif name == 'Playlist':
            set_playlist(value.split(','))
        elif name in ('Palette', 'Fxparam1', 'Fxparam2', 'Fxparam3', 'Fxparam4'):
            eid = controller.state.current_effect
            effect = controller.registry[eid]
            index = int(name[-1]) - 1 if name.startswith('Fxparam') else None
            if index is None or index < len(effect.parameters):
                values = {key: dict(item) for key, item in (controller.settings.effect_parameters or {}).items()}
                key = 'palette' if index is None else effect.parameters[index].name
                values.setdefault(eid, {})[key] = value
                controller.configure(effect_parameters=values)
    except Exception as exc:
        status_message = str(exc)


def read_channel(node, name, default=0):
    channel = node[name]
    return channel.eval() if channel is not None else default


def refresh(status, now):
    global status_message, last_mode, last_style
    try:
        tracker_exit = hand_tracker.poll(now)
        if tracker_exit:
            status_message = tracker_exit
        source_change(status, now)
    except Exception as exc:
        status_message = str(exc)
    current = controller.state.current_effect
    settings = controller.settings
    if current != last_mode:
        last_mode = current
        sync_effect_parameters(current)
    query = app.par.Filter.eval().casefold().strip()
    style = current, controller.state.playlist, query
    if style != last_style:
        last_style = style
        for eid, definition in controller.registry.items():
            item = panel.op('LIB_' + eid)
            enabled = eid in controller.state.playlist
            matches = query in f'{eid} {definition.name} {definition.group}'.casefold().replace('_', ' ')
            set_par(item, 'enable', matches)
            set_par(item, 'opacity', 1.0 if enabled and matches else 0.34)
            red, green, blue = (0.29, 0.48, 0.18) if eid == current else (0.17, 0.25, 0.32)
            set_par(item, 'colorr', red)
            set_par(item, 'colorg', green)
            set_par(item, 'colorb', blue)
        set_par(panel.op('ENABLE'), 'label', 'REMOVE FROM PLAYLIST' if current in controller.state.playlist else 'ADD TO PLAYLIST')
    timing = app.op('DIAGNOSTICS/TIMING')
    final = app.op('OUT_FINAL')
    fps = read_channel(timing, 'fps')
    cpu = read_channel(timing, 'msec')
    playback = 'SHOWCASE' if controller.showcase_playing else settings.playback_mode
    next_mode = controller.registry[controller.neighbor()].name.upper().replace('_', ' ')
    set_par(panel.op('UP_NEXT_TEXT'), 'text', f'NEXT  {next_mode}  /  {playback}')
    set_par(panel.op('SECTION_TEXT'), 'text', f'{input_status}  ·  {fps:.0f} FPS')
    state = controller.state
    metrics = receiver.last_metrics
    external_tracker = not hand_tracker.running and status not in INACTIVE_TRACKER
    tracker = status.replace('_', ' ') if status not in INACTIVE_TRACKER else 'KEYBOARD MODE'
    if hand_tracker.stopping:
        tracker = 'TRACKER STOPPING'
    elif hand_tracker.running and status in INACTIVE_TRACKER:
        tracker = 'TRACKER STARTING'
    health = receiver.last_health
    health_detail = health.detail if health and status not in ('KEYBOARD', 'STALE', 'DISCONNECTED') else ''
    _, _, camera_detail = health_detail.partition(' | ')
    if metrics and status not in INACTIVE_TRACKER:
        if metrics.phase == 'NO_HAND':
            detail = 'NO HAND · SHOW ONE HAND'
        elif metrics.phase == 'MULTIPLE_HANDS':
            detail = 'MULTIPLE HANDS · SHOW ONE HAND'
        else:
            phase = metrics.phase.replace('_', ' ')
            detail = f'HAND TRACKED · {phase}' if metrics.separation >= 0 else phase
    else:
        detail = health_detail.split(' | ', 1)[0] or 'Space or N to switch'
    if help_open:
        detail = 'Start the tracker, then show one hand.\nPress thumb to middle finger and snap.'
        camera_detail = ''
    tracker_title = 'OSC DISARMED' if not settings.armed else tracker
    if settings.playback_mode == 'MANUAL' and settings.armed:
        tracker_title = 'MANUAL · SNAPS OFF'
    status_lines = [f'{tracker_title}  ·  {state.snap_count} SNAPS', detail]
    if camera_detail:
        status_lines.append(camera_detail)
    status_lines.append(f'{state.cooldown_remaining:.2f}s cooldown')
    status_label = '\n'.join(status_lines)
    set_par(panel.op('STATUS_TEXT'), 'text', status_label)
    start_button = panel.op('HAND_TRACKER')
    if hand_tracker.stopping:
        button_label = 'STOPPING HAND TRACKER'
    elif hand_tracker.running:
        button_label = 'STOP HAND TRACKER'
    elif external_tracker:
        button_label = 'TRACKER RUNNING EXTERNALLY'
    else:
        button_label = 'START HAND TRACKER'
    set_par(start_button, 'label', button_label)
    set_par(start_button, 'enable', not (external_tracker or hand_tracker.stopping))
    socket_error = app.op('GESTURE_RECEIVER/OSC_LOCAL').errors()
    recorder_error = app.op('OUTPUT_MANAGER/RECORD').errors() if state.recording else ''
    if recorder_error:
        app.op('OUTPUT_MANAGER/RECORD').par.record = False
        state.recording = False
    msg = status_message or recorder_error or socket_error or receiver.last_error or ''
    capture = 'REC  /  ' if state.recording else ''
    set_par(panel.op('FOOTER_TEXT'), 'text', f'{capture}{final.width} × {final.height}  /  {settings.profile}  /  {cpu:.1f} ms   {msg}')
    diagnostics = app.op('DIAGNOSTICS/LAST_STATUS')
    diagnostic_text = f'{input_status}\n{tracker}\n{health_detail}\n{msg}\n{folder / "artifacts"}'
    if diagnostics.text != diagnostic_text:
        diagnostics.text = diagnostic_text
    set_par(panel.op('RECORD'), 'label', 'STOP' if state.recording else 'REC')
    set_par(panel.op('SHOWCASE'), 'label', 'STOP' if controller.showcase_playing else 'SHOWCASE')


def capture_path(suffix):
    capture = folder / 'captures'
    capture.mkdir(parents=True, exist_ok=True)
    return capture / (datetime.now().strftime('SnapReality-%Y%m%d-%H%M%S-%f') + suffix)


def shutdown():
    if 'hand_tracker' in globals():
        hand_tracker.stop()


def action(name):
    global status_message, help_open
    try:
        if name.startswith('source:'):
            app.par.Source = name.split(':', 1)[1]
        elif name.startswith('effect:'):
            controller.set_effect(name.split(':', 1)[1], 'manual')
        elif name == 'toggle_effect':
            eid = controller.state.current_effect
            current = controller.state.playlist
            set_playlist([item for item in current if item != eid] if eid in current else [*current, eid])
        elif name == 'save':
            save_settings(settings_path, controller.settings)
            status_message = 'Configuration saved'
        elif name == 'screenshot':
            target = capture_path('.png')
            app.op('OUT_FINAL').save(target.as_posix())
            if not target.is_file() or not target.stat().st_size:
                raise RuntimeError('Screenshot was not written')
            status_message = 'Saved ' + target.name
        elif name == 'record':
            recorder = app.op('OUTPUT_MANAGER/RECORD')
            if controller.state.recording:
                recorder.par.record = False
                controller.state.recording = False
                status_message = 'Recording ended'
            else:
                png = app.par.Recordformat.eval() == 'png'
                target = capture_path('' if png else '.mov')
                recorder.par.type = 'imagesequence' if png else 'movie'
                recorder.par.videocodec = 'mjpa'
                recorder.par.fps = QUALITY_PROFILES[controller.settings.profile][2]
                if png:
                    recorder.par.file.expr = f"{target.as_posix()!r} + me.fileSuffix"
                else:
                    recorder.par.file.val = target.as_posix()
                recorder.par.record = True
                controller.state.recording = True
                status_message = target.name
        elif name == 'showcase':
            if controller.showcase_playing:
                controller.stop_showcase()
            else:
                controller.start_showcase(*showcase)
                app.par.Source = 'DEMO'
        elif name == 'hand_tracker':
            if hand_tracker.running:
                hand_tracker.stop()
            else:
                now = time.monotonic()
                if receiver.update(now) not in INACTIVE_TRACKER:
                    status_message = 'An external tracker is already connected.'
                    return
                hand_tracker.check_setup()
                # Release a shared effect camera before opening it in the worker.
                source_change('STARTING', now)
                hand_tracker.start(int(app.op('GESTURE_RECEIVER/OSC_LOCAL').par.port.eval()))
                status_message = ''
        elif name == 'help':
            help_open = not help_open
        elif name == 'parameters':
            app.openParameters()
    except Exception as exc:
        status_message = str(exc)
