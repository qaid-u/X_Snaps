"""Build the full input, OSC, performance and output networks."""

from bootstrap.build_project import button, connect, label, new, put, select, text


def extend(root, app, parts, effects, panel):
    source, control, receiver, output, diag = (
        parts[name] for name in ('INPUT_MANAGER', 'CONTROL_ENGINE', 'GESTURE_RECEIVER',
                                 'OUTPUT_MANAGER', 'DIAGNOSTICS')
    )
    screen = put(new(source, 'screengrabTOP', 'SCREEN', -440, -190), active=False, limitfps=True, fps=30)
    video = put(new(source, 'moviefileinTOP', 'VIDEO', -440, -335), file='', play=True)
    image = put(new(source, 'moviefileinTOP', 'IMAGE', -440, -480), file='', play=False)
    camera = put(new(source, 'videodeviceinTOP', 'CAMERA', -440, -625), active=False)
    camera_flip = connect(new(source, 'flipTOP', 'CAMERA_FLIP', -220, -625), camera)
    branches = []
    for index, node in enumerate((screen, video, image, camera_flip), 1):
        fit = connect(new(source, 'fitTOP', 'FIT_' + ('SCREEN', 'VIDEO', 'IMAGE', 'CAMERA')[index-1],
                          0, -140 * index), node)
        put(fit, fit='fitbest', outputresolution='custom', bgcolora=1, resmult=False)
        fit.par.resolutionw.expr = "op('DEMO').width"
        fit.par.resolutionh.expr = "op('DEMO').height"
        fit.viewer = False
        node.viewer = False
        branches.append(fit)
    source_switch = connect(new(source, 'switchTOP', 'SELECT_SOURCE', 220, 0),
                            source.op('DEMO'), *branches)
    source_switch.viewer = False
    source.op('SOURCE').inputConnectors[0].connect(source_switch)

    socket = put(new(receiver, 'oscinDAT', 'OSC_LOCAL', 0, 0), active=False,
                 port=7400, localaddress='127.0.0.1', addscope='/snap/*', shared=False)
    socket.par.callbacks.eval().text = '''def onReceiveOSC(dat, rowIndex, message, byteData, timeStamp, address, args, peer):
    dat.parent(2).op('CONTROL_ENGINE/runtime').module.osc(address, args, peer)
    return
'''

    text(control, 'full_runtime', (root / 'td_scripts/full_runtime.py').read_text(encoding='utf-8'), 380, -120)
    monitor = put(new(diag, 'performCHOP', 'TIMING', 220, 0), fps=True, msec=True, cook=True,
                  droppedframes=True, gpumemused=True, totalgpumem=True)
    monitor.viewer = False
    text(diag, 'LAST_STATUS', '', 440, 0)
    recorder = connect(new(output, 'moviefileoutTOP', 'RECORD', 220, -150), output.op('DISPLAY'))
    put(recorder, type='imagesequence', imagefiletype='png', uniquesuff=True, n=0,
        leadingzerosdigits=6, record=False)
    recorder.viewer = False
    controls(app, effects, root)
    callback = text(control, 'parameters', '''def onValueChange(par, previous):
    runtime = op('full_runtime').module
    runtime.changed(par.name)
    return
''', 580, -120, kind='parameterexecuteDAT')
    put(callback, op=app.path, pars='*', custom=True, builtin=False, valuechange=True,
        executeloc='here', active=True)
    layout(panel, effects)


def controls(app, effects, root):
    from td_scripts.transition_library import load_transitions
    from td_scripts.settings_manager import PLAYBACK_MODES, QUALITY_PROFILES, SOURCE_MODES, TRANSITION_POLICIES

    def menu(page, name, title, values, labels=None, default=None):
        par = page.appendMenu(name, label=title)[0]
        par.menuNames = list(values)
        par.menuLabels = list(labels if labels is not None else values)
        par.default = default if default is not None else list(values)[0]
        par.val = par.default
        return par

    def option(page, kind, name, title, value, bounds=None):
        par = getattr(page, 'append' + kind)(name, label=title)[0]
        if bounds:
            par.min, par.max = bounds
            par.normMin, par.normMax = bounds
            par.clampMin = par.clampMax = True
        par.default = value
        par.val = value
        return par

    stage = app.appendCustomPage('Performance')
    menu(stage, 'Source', 'Input source', SOURCE_MODES)
    menu(stage, 'Playback', 'Switching mode', PLAYBACK_MODES)
    menu(stage, 'Quality', 'Quality', QUALITY_PROFILES, default='BALANCED')
    menu(stage, 'Transition', 'Transition preset', load_transitions(root), default='SnapChain')
    menu(stage, 'Collision', 'During transition', TRANSITION_POLICIES, default='queue-one')
    option(stage, 'Float', 'Duration', 'Duration (0 = preset)', 0, (0, 3))
    option(stage, 'Float', 'Strength', 'Effect intensity', 1, (0, 1))
    option(stage, 'Float', 'Centerx', 'Effect center X', .5, (0, 1))
    option(stage, 'Float', 'Centery', 'Effect center Y', .5, (0, 1))
    option(stage, 'Float', 'Cooldown', 'Snap cooldown (seconds)', .65, (0, 5))
    option(stage, 'Toggle', 'Lowflash', 'Low flash', True)
    option(stage, 'Toggle', 'Armed', 'Arm OSC snaps', True)

    source = app.appendCustomPage('Input / Output')
    option(source, 'File', 'Videofile', 'Video file', '')
    option(source, 'File', 'Imagefile', 'Image file', '')
    option(source, 'Toggle', 'Playvideo', 'Play video', True)
    option(source, 'Toggle', 'Loopvideo', 'Loop video', True)
    option(source, 'Toggle', 'Crop', 'Fill and crop input', False)
    option(source, 'Toggle', 'Mirror', 'Mirror camera', False)
    option(source, 'Toggle', 'Independent', 'Camera separate from tracker', False)
    option(source, 'Int', 'Monitor', 'Clean output monitor', 0, (0, max(0, len(td_monitors())-1)))
    option(source, 'Toggle', 'Fullscreen', 'Clean output fullscreen', False)
    menu(source, 'Recordformat', 'Capture format', ('png', 'mjpa'), ('PNG sequence', 'Motion JPEG / MOV'))

    library = app.appendCustomPage('Effect Library')
    menu(library, 'Effect', 'Select effect', effects, [entry[0] for entry in effects.values()])
    option(library, 'Str', 'Filter', 'Library search', '')
    option(library, 'Str', 'Playlist', 'Playlist IDs (comma separated)', '')
    for index in range(1, 5):
        option(library, 'Float', f'Fxparam{index}', f'Effect parameter {index}', 0)
    option(library, 'Int', 'Palette', 'Palette', 0, (0, 3))


def td_monitors():
    import td
    return td.monitors


def layout(panel, effects):
    put(panel.op('PREVIEW'), x=24, y=130, w=916, h=515)
    cyan = (0.31, 0.89, 0.93)
    lime = (0.84, 0.98, 0.53)
    label(panel, 'SECTION', 'DEMO / READY', 967, 659, 285, 40, 19, cyan)
    label(panel, 'CURRENT', '00 / ORIGINAL', 965, 611, 287, 36, 24, lime)
    label(panel, 'UP_NEXT', '', 966, 582, 283, 24, 15)
    button(panel, 'NEXT', 'SNAP TO SWITCH', 965, 521, 289, 49, 'snap', accent=True)
    button(panel, 'PREVIOUS', 'PREV', 965, 474, 91, 36, 'previous')
    button(panel, 'RANDOM', 'RANDOM', 1064, 474, 91, 36, 'random')
    button(panel, 'ORIGINAL', 'ORIGINAL', 1163, 474, 91, 36, 'reset')
    label(panel, 'LIBRARY', 'EFFECT LIBRARY', 965, 437, 245, 28, 17, cyan)
    for index, (eid, effect) in enumerate(effects.items()):
        title = effect[0].replace('_', ' ').upper()
        compact = {
            '00': 'ORIGINAL', '01': 'CGI', '02': 'ILLUSTR.', '03': 'COMIC',
            '04': 'HALFTONE', '05': 'CEL', '06': 'POSTER', '07': 'LINES',
            '08': 'ZOOM', '09': 'GLITCH', '10': 'ECHO', '11': 'INK',
            '12': 'PRISM', '13': 'SHATTER', '14': 'NEON', '15': 'PALETTE',
            '16': 'VORTEX', '17': 'GRID', '18': 'STAR', '19': 'MIXED', '20': 'MONO',
        }.get(eid, title)
        item = button(panel, 'LIB_' + eid, compact, 965 + (index % 3) * 99,
                      396 - (index // 3) * 35, 91, 29, 'effect:' + eid)
        item.par.fontsize = 13
    button(panel, 'ENABLE', 'TOGGLE IN PLAYLIST', 965, 135, 289, 36, 'toggle_effect')
    label(panel, 'STATUS', '', 965, 48, 289, 79, 14)
    button(panel, 'HAND_TRACKER', 'START HAND TRACKER', 965, 13, 289, 29,
           'hand_tracker').par.fontsize = 14
    label(panel, 'FOOTER', '', 24, 91, 916, 31, 15, cyan)
    for index, name in enumerate(('DEMO', 'SCREEN', 'VIDEO', 'IMAGE', 'CAMERA')):
        item = button(panel, 'INPUT_' + name, name, 24 + 100 * index, 51, 92, 34, 'source:' + name)
        item.par.fontsize = 14
    for index, (name, title, action) in enumerate((
        ('CLEAN', 'OUTPUT', 'output'), ('SHOT', 'PNG', 'screenshot'), ('RECORD', 'REC', 'record'),
        ('SHOWCASE', 'SHOWCASE', 'showcase'), ('CONFIG', 'SAVE', 'save'),
    )):
        item = button(panel, name, title, 526 + 84 * index, 51, 78, 34, action)
        item.par.fontsize = 12
    label(panel, 'SHORTCUTS', 'N / Space  Switch    ·    ← / →  Step    ·    R  Original    ·    Esc  Exit Perform',
          24, 13, 630, 28, 15)
    button(panel, 'HELP', 'HELP', 681, 13, 90, 28, 'help').par.fontsize = 13
    button(panel, 'SETTINGS', 'CONTROLS', 780, 13, 160, 28, 'parameters').par.fontsize = 13
