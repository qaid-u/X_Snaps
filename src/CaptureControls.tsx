import type { RecordingState } from './Capture'
import { outputTitle } from './Engine'
import { useState } from 'react'

export function CaptureControls({ state, disabled, still, record, pause }: {
  state: RecordingState
  disabled: boolean
  still: () => void
  record: () => void
  pause: () => void
}) {
  return <div className="transport">
    <button type="button" disabled={disabled} onClick={still}>Save PNG</button>
    <button type="button" disabled={disabled || state === 'finishing'} onClick={record}>
      {state === 'idle' ? 'Record video' : state === 'finishing' ? 'Saving…' : 'Stop recording'}
    </button>
    {(state === 'recording' || state === 'paused') && <button type="button" onClick={pause}>
      {state === 'paused' ? 'Resume' : 'Pause'}
    </button>}
  </div>
}

export function OBSGuide({ camera, show, copy, testPattern }: {
  camera: string
  show: () => void
  copy: () => Promise<void>
  testPattern: () => void
}) {
  const [copyStatus, setCopyStatus] = useState('')
  return <details className="obs-guide">
    <summary>OBS setup</summary>
    <p>Source: {camera}</p>
    <ol>
      <li>Show the output window and keep it visible.</li>
      <li>In OBS, add a Window Capture source for the window below.</li>
      <li>Use client-area capture, disable cursor capture, and fit the source to the canvas.</li>
      <li>Set OBS Video to 1280 × 720 at 30 FPS.</li>
      <li>Start Virtual Camera in OBS.</li>
      <li>Select OBS Virtual Camera in the call app.</li>
    </ol>
    <label>Window title<input readOnly value={outputTitle} onFocus={event => event.currentTarget.select()} /></label>
    <div className="transport">
      <button type="button" onClick={show}>Show output</button>
      <button type="button" onClick={() => {
        void copy().then(() => setCopyStatus('Copied')).catch(() => setCopyStatus('Select the title and press Ctrl+C.'))
      }}>Copy title</button>
      <button type="button" onClick={testPattern}>Stop camera and show DEMO</button>
    </div>
    {copyStatus && <p className="stats">{copyStatus}</p>}
  </details>
}
