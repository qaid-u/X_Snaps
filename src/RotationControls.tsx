import { useState } from 'react'
import { effects } from './effects'
import { defaultPlaylist } from './playlist'
import type { Playlist } from './playlist'
import { defaultTransition, transitions } from './transition'
import type { TransitionSettings } from './transition'

export function RotationControls({ playlist = defaultPlaylist(), save, saveEffects }: {
  playlist?: Playlist
  save: (value: Playlist) => void
  saveEffects: () => void
}) {
  const [selected, setSelected] = useState(1)
  const [saved, setSaved] = useState(false)
  const index = playlist.ids.indexOf(selected)
  function move(step: number) {
    const ids = [...playlist.ids]
    const target = index + step
    if (index < 0 || target < 0 || target >= ids.length) return
    const destination = ids[target]
    ids[target] = ids[index]
    ids[index] = destination
    save({ ...playlist, ids })
  }
  return <details className="obs-guide">
    <summary>Effect rotation and presets</summary>
    <label>Effect in rotation<select value={selected} onChange={event => setSelected(Number(event.target.value))}>
      {effects.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>
    <label className="check"><input type="checkbox" checked={index >= 0} disabled={index >= 0 && playlist.ids.length === 1}
      onChange={event => save({ ...playlist, ids: event.target.checked ? [...playlist.ids, selected] : playlist.ids.filter(id => id !== selected) })} />
      Include effect in rotation
    </label>
    <p className="stats">{index < 0 ? 'Excluded' : `Position ${index + 1} of ${playlist.ids.length}`}</p>
    <div className="transport">
      <button type="button" disabled={index <= 0} onClick={() => move(-1)}>Move earlier</button>
      <button type="button" disabled={index < 0 || index === playlist.ids.length - 1} onClick={() => move(1)}>Move later</button>
    </div>
    <label className="check"><input type="checkbox" checked={playlist.shuffle}
      onChange={event => save({ ...playlist, shuffle: event.target.checked })} />Shuffle</label>
    <div className="transport">
      <button type="button" onClick={() => save(defaultPlaylist())}>Reset rotation</button>
      <button type="button" onClick={() => { saveEffects(); setSaved(true) }}>Save effect settings</button>
    </div>
    {saved && <p className="stats">Effect settings saved locally.</p>}
  </details>
}

export function TransitionControls({ settings = defaultTransition, change }: {
  settings?: TransitionSettings
  change: (value: TransitionSettings) => void
}) {
  return <details className="obs-guide">
    <summary>Transitions</summary>
    <label>Transition style<select value={settings.style} onChange={event => change({ ...settings, style: Number(event.target.value) })}>
      <option value={-1}>Per effect</option>
      <option value={-2}>Random</option>
      {transitions.map((name, id) => <option key={name} value={id}>{name}</option>)}
    </select></label>
    <label>Duration in ms<input type="range" min="120" max="650" step="10" defaultValue={settings.duration}
      onChange={event => change({ ...settings, duration: event.target.valueAsNumber })} /></label>
    <label>Transition strength<input type="range" min="0" max="1" step=".05" defaultValue={settings.strength}
      onChange={event => change({ ...settings, strength: event.target.valueAsNumber })} /></label>
    <label className="check"><input type="checkbox" checked={settings.eased}
      onChange={event => change({ ...settings, eased: event.target.checked })} />Ease out</label>
    <label className="check"><input type="checkbox" checked={settings.reducedFlash}
      onChange={event => change({ ...settings, reducedFlash: event.target.checked })} />Reduce flashes</label>
  </details>
}
