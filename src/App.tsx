import { useEffect, useRef, useState } from 'react'
import { Engine, outputTitle } from './Engine'
import { effects } from './effects'
import { profiles } from './performance'

const benchmark = import.meta.env.VITE_BENCHMARK === '1' && new URLSearchParams(location.search).has('benchmark')
declare global {
  interface Window { snapBenchmark?: Engine }
}

export function App() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const engine = useRef<Engine | null>(null)
  const [effect, setEffect] = useState(0)
  const [ready, setReady] = useState(false)
  const [clean, setClean] = useState(false)
  const [camera, setCamera] = useState<'demo' | 'starting' | 'live'>('demo')
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [device, setDevice] = useState('')
  const [message, setMessage] = useState('Preparing effects…')
  const [stats, setStats] = useState<ReturnType<Engine['snapshot']>>()
  const [diagnostics, setDiagnostics] = useState(false)
  const [profile, setProfile] = useState(1)
  const [locked, setLocked] = useState(false)
  const [mirror, setMirror] = useState(false)
  const [cover, setCover] = useState(false)
  const [strength, setStrength] = useState(1)
  const [tracking, setTracking] = useState(true)
  const [sensitivity, setSensitivity] = useState(.5)

  useEffect(() => {
    let active = true
    let instance: Engine
    try {
      instance = new Engine(canvas.current!, setMessage)
      engine.current = instance
      instance.onEffect = setEffect
    } catch (error) {
      setMessage('WebGL 2 unavailable. ' + String(error))
      return
    }
    instance.ready.then(() => {
      if (!active) return
      if (benchmark) window.snapBenchmark = instance
      setReady(true)
      setMessage('Demo ready')
    }).catch(error => { if (active) setMessage(String(error)) })
    const refresh = () => navigator.mediaDevices?.enumerateDevices()
      .then(list => { if (active) setDevices(list.filter(item => item.kind === 'videoinput' && !/OBS Virtual Camera/i.test(item.label))) })
      .catch(() => {})
    void refresh()
    navigator.mediaDevices?.addEventListener('devicechange', refresh)
    const release = () => instance.stopCamera()
    window.addEventListener('pagehide', release)
    return () => {
      active = false
      navigator.mediaDevices?.removeEventListener('devicechange', refresh)
      window.removeEventListener('pagehide', release)
      engine.current = null
      delete window.snapBenchmark
      instance.dispose()
    }
  }, [])

  useEffect(() => {
    document.title = clean ? outputTitle : 'SNAP//REALITY'
    if (clean) return
    const interval = setInterval(() => {
      const instance = engine.current
      if (!instance) return
      setStats(instance.snapshot())
      if (!instance.camera.active) setCamera(state => state === 'live' ? 'demo' : state)
    }, 500)
    return () => clearInterval(interval)
  }, [clean])

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setClean(false)
      if (event.repeat || (event.target instanceof Element && event.target.closest('button,input,select,textarea,[contenteditable]'))) return
      const instance = engine.current
      if (!instance) return
      if (event.code === 'Space') {
        event.preventDefault()
        if (instance.next(1, performance.now(), true)) setEffect(instance.effect)
      }
      if (event.key.toLowerCase() === 'r' && instance.select(0)) setEffect(0)
      if (event.key.toLowerCase() === 'd') setDiagnostics(value => !value)
      if (event.key.toLowerCase() === 'f') {
        if (document.fullscreenElement) void document.exitFullscreen()
        else void canvas.current?.parentElement?.requestFullscreen().catch(() => setMessage('Fullscreen unavailable.'))
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])

  async function startCamera() {
    const instance = engine.current
    if (!instance) return
    setCamera('starting')
    setMessage('Requesting camera access…')
    try {
      const started = await instance.startCamera(device)
      setCamera(started ? 'live' : 'demo')
      setMessage(started ? 'Physical camera active' : 'Demo ready')
      const list = await navigator.mediaDevices.enumerateDevices()
      setDevices(list.filter(item => item.kind === 'videoinput' && !/OBS Virtual Camera/i.test(item.label)))
    } catch (error) {
      setCamera('demo')
      setMessage(`Camera unavailable. Check Windows camera permissions and close apps using the device. ${String(error)}`)
    }
  }

  function changeProfile(next: number, lock: boolean) {
    setProfile(next)
    setLocked(lock)
    engine.current?.setProfile(next, lock)
  }

  return <main className={clean ? 'app clean' : 'app'}>
    {!clean && <header>
      <div className="brand"><span className="mark">✦</span> SNAP<span className="slashes">//</span>REALITY</div>
      <div className="top-actions">
        <span className="source">{camera === 'live' ? 'WEBCAM' : 'DEMO'}</span>
        <button type="button" onClick={() => setDiagnostics(value => !value)}>Diagnostics</button>
        <button type="button" className="primary" disabled={!ready} onClick={() => setClean(true)}>Clean OBS output</button>
      </div>
    </header>}
    {!clean && <aside className="catalog" aria-label="Effects">
      <h1>Effects</h1>
      {effects.map(item => <button type="button" key={item.id} disabled={!ready} aria-pressed={item.id === effect} onClick={() => {
        if (engine.current?.select(item.id)) setEffect(item.id)
      }}><span>{String(item.id).padStart(2, '0')}</span>{item.label}</button>)}
    </aside>}
    <section className="output" aria-label="Processed video">
      <canvas ref={canvas} aria-label="Processed video canvas" />
    </section>
    {!clean && <aside className="controls" aria-label="Controls">
      <h2>Video input</h2>
      <label>Camera<select value={device} disabled={camera !== 'demo'} onChange={event => setDevice(event.target.value)}>
        <option value="">System default</option>
        {devices.filter(item => item.deviceId).map((item, index) => <option key={item.deviceId} value={item.deviceId}>{item.label || `Camera ${index + 1}`}</option>)}
      </select></label>
      <label className="check"><input type="checkbox" checked={mirror} onChange={event => {
        setMirror(event.target.checked)
        engine.current?.setMirror(event.target.checked)
      }} />Mirror output</label>
      <label className="check"><input type="checkbox" checked={cover} onChange={event => {
        setCover(event.target.checked)
        if (engine.current) engine.current.cover = event.target.checked
      }} />Fill frame</label>
      <h2>Finger snaps</h2>
      <label className="check"><input type="checkbox" checked={tracking} onChange={event => {
        setTracking(event.target.checked)
        engine.current?.setTracking(event.target.checked)
      }} />Hand tracking</label>
      <label>Sensitivity<input type="range" min="0" max="1" step=".05" value={sensitivity} onChange={event => {
        setSensitivity(event.target.valueAsNumber)
        if (engine.current) engine.current.hands.sensitivity = event.target.valueAsNumber
      }} /></label>
      <p className="stats">{stats?.handStatus ?? 'Hand tracking off'}</p>
      <h2>Processing</h2>
      <label>Quality<select value={profile} onChange={event => changeProfile(Number(event.target.value), locked)}>
        {profiles.map((item, index) => <option key={item.name} value={index}>{item.name}</option>)}
      </select></label>
      <label className="check" title="A locked profile may stutter if the GPU is overloaded."><input type="checkbox" checked={locked} onChange={event => changeProfile(profile, event.target.checked)} />Lock quality</label>
      <label>Effect strength<input type="range" min="0" max="1" step=".01" value={strength} onChange={event => {
        setStrength(event.target.valueAsNumber)
        engine.current?.setStrength(event.target.valueAsNumber)
      }} /></label>
      {diagnostics && <div className="stats">
        <h2>Diagnostics</h2>
        <p>Render {stats?.renderFps?.toFixed(1) ?? '—'} FPS</p>
        <p>Source {stats?.sourceFps?.toFixed(1) ?? '—'} FPS</p>
        <p>Frame interval p95 {stats?.render.p95?.toFixed(1) ?? '—'} ms</p>
        <p>GPU p95 {stats?.gpu.p95?.toFixed(1) ?? '—'} ms</p>
        <p>Hand inference p95 {stats?.hand.p95?.toFixed(1) ?? '—'} ms · skipped {stats?.skippedInference ?? 0}</p>
        <p>Trigger to draw p95 {stats?.latency.p95?.toFixed(1) ?? '—'} ms</p>
        <p>{stats?.width} × {stats?.height} · {stats?.profile}</p>
        <p>{stats?.reason}</p>
      </div>}
    </aside>}
    {!clean && <footer>
      <div className="transport">
        <button type="button" className="primary" disabled={!ready || camera === 'starting'} onClick={() => {
          if (camera === 'live') {
            engine.current?.stopCamera()
            setCamera('demo')
            setMessage('Camera stopped. Demo is active.')
          } else void startCamera()
        }}>{camera === 'live' ? 'Stop camera' : 'Start camera'}</button>
        <button type="button" disabled={!ready} onClick={() => { if (engine.current?.next()) setEffect(engine.current.effect) }}>Next effect</button>
      </div>
      <span role="status">{message}</span>
      <span className="hint">Space next · R original · Esc controls</span>
    </footer>}
  </main>
}
