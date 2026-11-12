import { useEffect, useRef, useState } from 'react'
import { Engine } from './Engine'
import { effects } from './effects'
import { profiles } from './performance'
import type { Command, DesktopState } from './desktop-protocol'

export function DesktopOutput() {
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const bridge = window.snapDesktop
    if (bridge?.role !== 'output') return
    let message = 'Preparing effects…'
    let camera: DesktopState['camera'] = 'demo'
    let ready = false
    let active = true
    let lastSequence = 0
    let devices: DesktopState['devices'] = []
    let instance: Engine
    const publish = () => {
      if (!active) return
      bridge.publish({ ready, camera, status: message, devices, available: true, metrics: instance?.snapshot() })
    }
    try {
      instance = new Engine(canvas.current!, status => { message = status; publish() })
    } catch (error) {
      message = 'WebGL 2 unavailable. ' + String(error)
      publish()
      return
    }
    const refreshDevices = async () => {
      const list = await navigator.mediaDevices.enumerateDevices().catch(() => [])
      devices = list.filter(item => item.kind === 'videoinput' && item.deviceId && !/OBS Virtual Camera/i.test(item.label))
        .map((item, index) => ({ id: item.deviceId, label: item.label || `Camera ${index + 1}` }))
    }
    void instance.ready.then(async () => {
      ready = true
      message = 'Demo ready'
      publish()
      await refreshDevices()
      publish()
    }).catch(error => { message = String(error); publish() })
    async function start(device: string) {
      if (camera === 'starting' || camera === 'live') return
      camera = 'starting'
      message = 'Starting physical camera…'
      publish()
      try {
        const started = await instance.startCamera(device)
        camera = started ? 'live' : 'demo'
        message = started ? 'Physical camera active' : 'Demo ready'
        await refreshDevices()
      } catch (error) {
        camera = 'demo'
        message = 'Camera unavailable. ' + String(error)
      }
      publish()
    }
    const receive = bridge.onCommand((command, seq) => {
      if (seq <= lastSequence || !ready) return
      lastSequence = seq
      switch (command.action) {
        case 'start': void start(command.device); break
        case 'stop':
          if (camera === 'starting') return
          instance.stopCamera()
          camera = 'demo'
          message = 'Camera stopped. Demo is active.'
          break
        case 'next': instance.next(1, performance.now(), true); break
        case 'previous': instance.next(-1, performance.now(), true); break
        case 'effect': instance.select(command.value); break
        case 'mirror': instance.setMirror(command.value); break
        case 'cover': instance.cover = command.value; break
        case 'tracking': instance.setTracking(command.value); break
        case 'strength': instance.setStrength(command.value); break
        case 'sensitivity': instance.hands.sensitivity = command.value; break
        case 'transition': instance.transition = command.value; break
        case 'profile': instance.setProfile(command.level, command.locked); break
      }
      publish()
    })
    const timer = setInterval(() => {
      if (camera === 'live' && !instance.camera.active) camera = 'demo'
      publish()
    }, 500)
    const key = (event: KeyboardEvent) => {
      if (event.repeat) return
      if (event.ctrlKey && event.shiftKey && event.code === 'KeyO') {
        event.preventDefault()
        void bridge.showControls()
      }
      if (event.code === 'Space') instance.next(1, performance.now(), true)
      if (event.key.toLowerCase() === 'r') instance.select(0)
    }
    const release = () => instance.dispose()
    window.addEventListener('keydown', key)
    window.addEventListener('pagehide', release, { once: true })
    return () => {
      active = false
      clearInterval(timer)
      receive()
      window.removeEventListener('keydown', key)
      window.removeEventListener('pagehide', release)
      instance.dispose()
    }
  }, [])
  return <main className="app clean">
    <section className="output" aria-label="Processed video">
      <canvas ref={canvas} aria-label="Processed video canvas" />
    </section>
  </main>
}

export function DesktopControl() {
  const [state, setState] = useState<DesktopState | null>(null)
  const [device, setDevice] = useState('')
  const [profile, setProfile] = useState(1)
  const [locked, setLocked] = useState(false)
  const bridge = window.snapDesktop?.role === 'control' ? window.snapDesktop : null

  useEffect(() => {
    if (!bridge) return
    const unsubscribe = bridge.onState(setState)
    void bridge.read().then(setState)
    return unsubscribe
  }, [bridge])

  const run = (command: Command) => { void bridge?.command(command) }
  const usable = !!state?.available && state.ready
  const live = state?.camera === 'live'
  const waiting = state?.camera === 'starting'
  const metrics = state?.metrics

  return <main className="desktop-control">
    <header>
      <div className="brand"><span className="mark">✦</span> SNAP<span className="slashes">//</span>REALITY</div>
      <button type="button" onClick={() => { void bridge?.showOutput() }} disabled={!state?.available}>Show OBS output</button>
    </header>
    <div className="desktop-grid">
      <aside className="catalog" aria-label="Effects">
        <h1>Effects</h1>
        {effects.map(effect => <button key={effect.id} type="button" disabled={!usable}
          aria-pressed={effect.id === metrics?.effect} onClick={() => run({ action: 'effect', value: effect.id })}>
          <span>{String(effect.id).padStart(2, '0')}</span>{effect.label}
        </button>)}
        <div className="transport">
          <button type="button" disabled={!usable} onClick={() => run({ action: 'previous' })}>Previous</button>
          <button type="button" disabled={!usable} onClick={() => run({ action: 'next' })}>Next effect</button>
        </div>
      </aside>
      <aside className="controls" aria-label="Controls">
        <h2>Video input</h2>
        <label>Camera<select disabled={live || waiting} value={device} onChange={event => setDevice(event.target.value)}>
          <option value="">System default</option>
          {state?.devices.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select></label>
        <button type="button" className="primary" disabled={!usable || waiting}
          onClick={() => run(live ? { action: 'stop' } : { action: 'start', device })}>{live ? 'Stop camera' : 'Start camera'}</button>
        <label className="check"><input type="checkbox" onChange={event => run({ action: 'mirror', value: event.target.checked })} />Mirror output</label>
        <label className="check"><input type="checkbox" onChange={event => run({ action: 'cover', value: event.target.checked })} />Fill frame</label>
        <h2>Finger snaps</h2>
        <label className="check"><input type="checkbox" defaultChecked onChange={event => run({ action: 'tracking', value: event.target.checked })} />Hand tracking</label>
        <label>Sensitivity<input type="range" min="0" max="1" step=".05" defaultValue=".5"
          onChange={event => run({ action: 'sensitivity', value: event.target.valueAsNumber })} /></label>
        <p className="stats">{metrics?.handStatus}</p>
        <h2>Processing</h2>
        <label>Quality<select value={profile} onChange={event => {
          const level = Number(event.target.value)
          setProfile(level)
          run({ action: 'profile', level, locked })
        }}>{profiles.map((item, index) => <option key={item.name} value={index}>{item.name}</option>)}</select></label>
        <label className="check"><input type="checkbox" checked={locked} onChange={event => {
          setLocked(event.target.checked)
          run({ action: 'profile', level: profile, locked: event.target.checked })
        }} />Lock quality</label>
        <label>Effect strength<input type="range" min="0" max="1" step=".01" defaultValue="1"
          onChange={event => run({ action: 'strength', value: event.target.valueAsNumber })} /></label>
        <label className="check"><input type="checkbox" defaultChecked onChange={event => run({ action: 'transition', value: event.target.checked })} />Transition</label>
        <div className="stats">
          <p>{metrics?.width ?? '—'} × {metrics?.height ?? '—'} · {metrics?.profile} · {metrics?.reason}</p>
          <p>Source {metrics?.sourceFps?.toFixed(1) ?? '—'} FPS · Render {metrics?.renderFps?.toFixed(1) ?? '—'} FPS</p>
          <p>Frame p95 {metrics?.render.p95?.toFixed(1) ?? '—'} ms · GPU p95 {metrics?.gpu.p95?.toFixed(1) ?? '—'} ms</p>
          <p>Inference p95 {metrics?.hand.p95?.toFixed(1) ?? '—'} ms · Skipped {metrics?.skippedInference ?? 0}</p>
          <p>Trigger to draw p95 {metrics?.latency.p95?.toFixed(1) ?? '—'} ms</p>
        </div>
      </aside>
    </div>
    <footer><span role="status">{state?.status ?? 'Opening OBS output…'}</span>
      <span className="hint">Ctrl+Shift+O in the output reopens controls</span></footer>
  </main>
}
