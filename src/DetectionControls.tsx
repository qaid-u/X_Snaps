import { detectionModes } from './audio'
import type { Engine } from './Engine'

export function DetectionControls({ metrics, mode, mic, sensitivity, cooldown }: {
  metrics?: ReturnType<Engine['snapshot']>
  mode: (value: number) => void
  mic: () => void
  sensitivity: (value: number) => void
  cooldown: (value: number) => void
}) {
  const value = metrics?.detectionMode ?? 0
  return <>
    <label>Detection mode<select value={value} onChange={event => mode(Number(event.target.value))}>
      {detectionModes.map((name, index) => <option key={name} value={index}>{name}</option>)}
    </select></label>
    {(value === 1 || value === 2) && <>
      <button type="button" disabled={metrics?.micState === 'starting'} onClick={mic}>
        {metrics?.micState === 'active' ? 'Disable microphone' : 'Enable microphone'}
      </button>
      <p className="stats">{metrics?.micMessage}{value === 1 && metrics?.micState !== 'active' ? ' · Using visual detection' : ''}</p>
      {value === 2 && <p className="stats">Claps and taps can trigger this mode.</p>}
      {metrics?.micState === 'active' && <label>Mic level<meter min={0} max={1} value={metrics.micLevel} /></label>}
      <label>Mic sensitivity<input type="range" min="0" max="1" step=".05" defaultValue={metrics?.micSensitivity ?? .5}
        onChange={event => sensitivity(event.target.valueAsNumber)} /></label>
    </>}
    <details className="obs-guide">
      <summary>Calibrate snaps</summary>
      <ol>
        <li>Start the camera in good light and keep your hand in frame.</li>
        <li>Hold thumb and middle finger together until the hand status shows Armed, then snap.</li>
        <li>Try five to ten snaps. Adjust sensitivity if the counter misses releases.</li>
        <li>Try ordinary pinches and waves, then check for unwanted counts.</li>
      </ol>
      <p>Confirmed snaps: {metrics?.snapCount ?? 0}</p>
      <label>Cooldown in ms<input type="range" min="250" max="1500" step="50" defaultValue={metrics?.cooldown ?? 650}
        onChange={event => cooldown(event.target.valueAsNumber)} /></label>
    </details>
  </>
}
