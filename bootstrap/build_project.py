"""Build SNAP//REALITY in TouchDesigner's embedded Python runtime."""

import json
import sys
from datetime import datetime
from pathlib import Path

import td


def new(parent, kind, name, x=0, y=0):
    node = parent.create(getattr(td, kind), name)
    if node.name != name:
        node.name = name
    node.nodeX, node.nodeY = x, y
    return node


def put(node, **values):
    for name, value in values.items():
        parameter = getattr(node.par, name, None)
        if parameter is None:
            raise RuntimeError(f'{node.path} has no parameter {name}')
        parameter.val = value
    return node


def connect(node, *sources):
    for index, source in enumerate(sources):
        node.inputConnectors[index].connect(source)
    return node


def select(parent, name, source, x=0, y=0):
    return put(new(parent, 'selectTOP', name, x, y), top=source.path)


def text(parent, name, contents, x=0, y=0, kind='textDAT'):
    node = new(parent, kind, name, x, y)
    node.text = contents
    return node


def dimensions(node, width, height):
    return put(node, outputresolution='custom', resolutionw=width, resolutionh=height, resmult=False)


def vector(node, block, values):
    for axis, value in zip('xyzw', values):
        parameter = getattr(node.par, f'vec{block}value{axis}')
        if isinstance(value, str):
            parameter.expr = value
        else:
            parameter.val = value


def shader(parent, name, source, inputs, uniforms, x, y):
    dat = text(parent, name + '_pixel', source, x, y - 105)
    node = new(parent, 'glslTOP', name, x, y)
    node.viewer = False
    connect(node, *inputs)
    put(node, glslversion='glsl460', pixeldat=dat.path)
    node.seq.vec.numBlocks = len(uniforms)
    for index, (key, values) in enumerate(uniforms.items()):
        put(node, **{f'vec{index}name': key})
        vector(node, index, values)
    return node


def read(folder, file):
    return (folder / file).read_text(encoding='utf-8-sig')


def save_toe(root, destination):
    """Keep previous versions and let TouchDesigner write the new project."""
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup_folder = root / 'checkpoints'
    archives = {}
    numbered_versions = (
        path for path in destination.parent.glob(f'{destination.stem}.*.toe')
        if path.stem.removeprefix(destination.stem + '.').isdigit()
    )
    prior_versions = [destination, *numbered_versions]
    try:
        for prior in prior_versions:
            if prior.is_file():
                backup_folder.mkdir(parents=True, exist_ok=True)
                backup = backup_folder / f'{prior.stem}-{stamp}.toe'
                prior.replace(backup)
                archives[prior] = backup
        if not td.project.save(destination.as_posix()) or not destination.is_file() or not destination.stat().st_size:
            raise RuntimeError(f'TouchDesigner did not save {destination}')
    except Exception:
        for prior, backup in archives.items():
            if not prior.exists():
                backup.replace(prior)
        raise


PROTOTYPE = {
    '00': ('Original', 'original.frag', ()),
    '06': ('Posterized', 'posterized.frag', (5, 0.24)),
    '03': ('Comic Pop Art', 'comic_pop_art.frag', (0.75, 1.55, 104)),
    '04': ('Halftone Print', 'halftone_print.frag', (93, 0.85, 0.0)),
    '09': ('RGB Glitch', 'rgb_glitch.frag', (0.55, 0.75, 0.4)),
}


def build(root_path, stage=2, filename=None):
    root = Path(root_path).resolve()
    filename = filename or ('checkpoints/SnapReality-stage2.toe' if stage == 2 else 'SnapReality.toe')
    destination = (root / filename).resolve()
    project_root = td.op('/project1')
    if project_root is None:
        raise RuntimeError('Create or open an empty project with a /project1 Base COMP.')
    existing = project_root.op('SNAP_REALITY')
    if existing and not existing.op('CONTROL_ENGINE/BUILD_OWNER'):
        raise RuntimeError(f'Refusing to replace unowned component {existing.path}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    perform = td.op('/perform')
    # Keep the previous application available until the replacement is validated and saved.
    staging = project_root.op('SNAP_REALITY_BUILD')
    if staging:
        if not staging.op('CONTROL_ENGINE/BUILD_OWNER'):
            raise RuntimeError(f'Refusing to replace unowned component {staging.path}')
        staging.destroy()
    saved_perform = perform.par.winop.val if perform else None
    saved_start_mode = td.project.performOnStart
    suspended = []
    if existing:
        for path in ('CONTROL_ENGINE/frame', 'CONTROL_ENGINE/KEYBOARD', 'GESTURE_RECEIVER/OSC_LOCAL'):
            node = existing.op(path)
            if node and node.par.active.eval():
                node.par.active = False
                suspended.append(node)
        existing.name = 'SNAP_REALITY_PREVIOUS'
    app = new(project_root, 'baseCOMP', 'SNAP_REALITY', 0, 0)
    app.color = (0.12, 0.46, 0.49)
    parts = {}
    for index, name in enumerate((
        'INPUT_MANAGER', 'GESTURE_RECEIVER', 'CONTROL_ENGINE', 'FX_ENGINE', 'TRANSITIONS',
        'COMPOSITING', 'OUTPUT_MANAGER', 'UI', 'DIAGNOSTICS',
    )):
        parts[name] = new(app, 'baseCOMP', name, (index % 5) * 235, -(index // 5) * 160)
    input_comp, fx, transition, composite, output, controls, ui, diag = (
        parts[k] for k in ('INPUT_MANAGER', 'FX_ENGINE', 'TRANSITIONS', 'COMPOSITING',
                          'OUTPUT_MANAGER', 'CONTROL_ENGINE', 'UI', 'DIAGNOSTICS')
    )
    text(controls, 'BUILD_OWNER', 'SNAP//REALITY managed network', -240, -120)
    from bootstrap.validate_project import inspect, validate

    try:
        common = read(root, 'shaders/common.glsl') + '\n'
        demo = shader(input_comp, 'DEMO', common + read(root, 'shaders/demo.frag'), (), {
            'uFrame': ('absTime.seconds', 1, 0.5, 0.5),
            'uOptions': (0, 0, 0, 1),
            'uParams': (0, 0, 0, 0),
        }, 0, 0)
        dimensions(demo, 960, 540)
        source = connect(new(input_comp, 'nullTOP', 'SOURCE', 220), demo)
        source.viewer = False
        fx_source = select(fx, 'SOURCE', source, -270)
        effects = dict(PROTOTYPE)
        registry_path = root / 'presets/effects.json'
        if registry_path.is_file():
            registry = json.loads(read(root, 'presets/effects.json'))['effects']
            for item in registry:
                eid = item['id']
                if stage > 2 or eid in effects:
                    effects[eid] = (item['name'], Path(item['shader']).name,
                                    tuple(param['default'] for param in item['parameters']))
        effect_nodes = []
        for index, (effect_id, (_, frag, parameters)) in enumerate(effects.items()):
            x, y = (index % 7) * 230, -(index // 7) * 260
            args = [fx_source]
            feedback = None
            if effect_id in ('10', '14'):
                feedback = connect(new(fx, 'feedbackTOP', f'HISTORY_{effect_id}', x, y + 95), fx_source)
                feedback.viewer = False
                args.append(feedback)
            node = shader(fx, f'FX_{effect_id}', common + read(root, 'shaders/' + frag), args, {
                'uFrame': ('absTime.seconds', 1, 0.5, 0.5),
                'uOptions': ('absTime.seconds', int(effect_id) + 1, 0, 1),
                'uParams': (*parameters, *([0] * (4 - len(parameters)))),
            }, x, y)
            if feedback:
                put(feedback, top=node.path)
            effect_nodes.append(node)
        current = connect(new(fx, 'switchTOP', 'CURRENT', 1550, 0), *effect_nodes)
        previous = connect(new(fx, 'switchTOP', 'PREVIOUS', 1550, -180), *effect_nodes)
        current.viewer = previous.viewer = False
        previous_ref = select(transition, 'PREVIOUS', previous, -240, 0)
        current_ref = select(transition, 'CURRENT', current, -240, -150)
        title = new(transition, 'textTOP', 'TYPOGRAPHY', -240, -300)
        put(title, text='', font='Bahnschrift', bgalpha=0, fontsizex=110, fontsizey=110,
            fontsizexunit='pixels', fontsizeyunit='pixels', fontautosize='fitiffat')
        dimensions(title, 960, 540)
        transition_top = shader(transition, 'TRANSITION',
                                read(root, 'shaders/transition_compositor.frag'),
                                (previous_ref, current_ref, title), {
            'uTransition': (1, 1, 0.5, 0.5),
            'uLayers': (1, 0.15, 0, 0),
            'uTiming': (0, 0, 0, -1),
        }, 0, 0)
        active = connect(new(composite, 'switchTOP', 'ACTIVE_IMAGE', 220),
                         select(composite, 'CURRENT', current, -180),
                         select(composite, 'TRANSITION', transition_top, -180, -150))
        active.viewer = False
        final = connect(new(app, 'nullTOP', 'OUT_FINAL', 1020, -160),
                        select(app, 'COMPOSITE', active, 1020, 0))
        connect(new(app, 'outTOP', 'OUT', 1230, -160), final)
        display = select(output, 'DISPLAY', final)
        window = put(new(output, 'windowCOMP', 'OUTPUT_WINDOW', 220), winop=display.path,
                     title='SNAP//REALITY | Clean Output', size='automatic', closeescape=True, borders=True)
        text(controls, 'EFFECT_ORDER', json.dumps(list(effects)))
        text(controls, 'EFFECT_NAMES', json.dumps({k: v[0] for k, v in effects.items()}), 190)
        text(controls, 'BUILD_ROOT', root.as_posix(), 380)
        script = text(controls, 'runtime', read(root, 'td_scripts/prototype_runtime.py'), 0, -120)
        callback = text(controls, 'frame', '''def onStart():
    op('runtime').module.initialize()
    return

def onFrameStart(frame):
    op('runtime').module.tick()
    return

def onExit():
    op('runtime').module.shutdown()
    return
''', 200, -120, kind='executeDAT')
        put(callback, active=False, executeloc='here', start=True, framestart=True, exit=True)
        keyboard = new(controls, 'keyboardinDAT', 'KEYBOARD', 0, -260)
        put(keyboard, active=False, keys='n space r left right', perform=True)
        keyboard_callback = keyboard.par.callbacks.eval()
        keyboard_callback.text = '''def onKey(dat, keyInfo):
    if not (keyInfo.alt or keyInfo.ctrl or keyInfo.cmd or keyInfo.shift):
        dat.parent().op('runtime').module.key(keyInfo.key, keyInfo.state)
    return
'''
        put(keyboard, lrmodifiers=True)
        report = text(diag, 'BUILD_REPORT', 'Build validation in progress.', 0, 0)
        panel = make_panel(ui, final, stage)
        if stage > 2:
            from bootstrap.full_project import extend
            extend(root, app, parts, effects, panel)
        result = validate(app, effects, root, stage)
        if perform:
            put(perform, winop=panel.path, title='SNAP//REALITY', closeescape=True, borders=False,
                size='automatic')
        put(callback, active=True)
        put(keyboard, active=True)
        script.module.initialize()
        inspect(final)
        if final.width != demo.width or final.height != demo.height:
            raise RuntimeError(f'Unexpected final resolution: {final.width}×{final.height}')
        report.text = json.dumps(result, indent=2)
        td.project.performOnStart = stage > 2
        if existing:
            old_runtime = existing.op('CONTROL_ENGINE/full_runtime')
            if old_runtime and hasattr(old_runtime.module, 'shutdown'):
                old_runtime.module.shutdown()
            existing.destroy()
        save_toe(root, destination)
        print(report.text)
        print(f'Saved {destination} ({destination.stat().st_size:,} bytes)')
        return app
    except Exception:
        app.name = 'SNAP_REALITY_BUILD'
        if existing and existing.valid:
            existing.name = 'SNAP_REALITY'
            for node in suspended:
                node.par.active = True
        if perform:
            perform.par.winop = saved_perform
        td.project.performOnStart = saved_start_mode
        raise


def make_panel(parent, final, stage):
    panel = put(new(parent, 'containerCOMP', 'PERFORMANCE_PANEL', 0), w=1280, h=720,
                bgcolorr=0.039, bgcolorg=0.054, bgcolorb=0.071, bgalpha=1)
    put(new(panel, 'containerCOMP', 'PREVIEW', 0), x=26, y=151, w=866, h=488,
        top=final.path, topfill='best')
    label(panel, 'TITLE', 'SNAP//REALITY', 26, 650, 566, 54, 39, (0.89, 0.97, 0.98))
    if stage > 2:
        return panel
    label(panel, 'SECTION', 'LIVE INPUT / DEMO', 922, 597, 326, 33, 20, (0.29, 0.87, 0.92))
    label(panel, 'CURRENT', '00 / ORIGINAL', 922, 531, 330, 61, 24, (0.84, 0.98, 0.53))
    label(panel, 'STATUS', 'KEYBOARD MODE\nN / Space   Next effect\nR   Original', 922, 380, 326, 124, 20)
    label(panel, 'FOOTER', 'DEMO / LIVE GPU PREVIEW', 26, 79, 866, 42, 19, (0.29, 0.87, 0.92))
    button(panel, 'NEXT', 'SNAP TO SWITCH', 922, 310, 326, 55, 'next', accent=True)
    button(panel, 'ORIGINAL', 'ORIGINAL', 922, 244, 158, 50, 'reset')
    button(panel, 'CLEAN', 'CLEAN OUTPUT', 1090, 244, 158, 50, 'output')
    return panel


def label(panel, name, value, x, y, width, height, size, rgb=(0.73, 0.79, 0.83)):
    skin = put(new(panel, 'textTOP', name + '_TEXT', x, y), text=value, font='Roboto',
               fontsizex=size, fontsizey=size, bgalpha=0, fontcolorr=rgb[0], fontcolorg=rgb[1],
               fontcolorb=rgb[2], alignx='left', aligny='center', fontautosize='fitiffat',
               fontsizexunit='pixels', fontsizeyunit='pixels')
    dimensions(skin, width, height)
    put(new(panel, 'containerCOMP', name, x, y - 85), x=x, y=y, w=width, h=height,
        top=skin.path, topfill='off', clickthrough=True)
    return skin


def button(panel, name, title, x, y, width, height, action, accent=False):
    rgb = (0.29, 0.48, 0.18) if accent else (0.17, 0.25, 0.32)
    item = put(new(panel, 'buttonCOMP', name, x, y), x=x, y=y, w=width, h=height,
               label=title, fontsize=16, buttontype='momentary', colorr=rgb[0], colorg=rgb[1], colorb=rgb[2])
    callback = text(panel, name + '_CLICK', f'''def onOffToOn(panelValue):
    me.parent(3).op('CONTROL_ENGINE/runtime').module.action({action!r})
    return
''', x, y - 85, kind='panelexecuteDAT')
    put(callback, panels=item.path, panelvalue='select', offtoon=True, executeloc='here')
    return item


if __name__ == '__main__':
    folder = Path(__file__).resolve().parents[1]
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    build(folder, globals().get('SNAP_STAGE', 2), globals().get('SNAP_TOE'))
