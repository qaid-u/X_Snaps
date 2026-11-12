import { effects } from './effects'

export function ScopeControls({ scope, background, status, onScope, onBackground }: {
  scope: number
  background: number
  status: string
  onScope: (value: number) => void
  onBackground: (value: number) => void
}) {
  return <>
    <label>Effect scope<select value={scope} onChange={event => onScope(Number(event.target.value))}>
      {['Whole scene', 'Person only', 'Background only', 'Split style'].map((name, index) => <option key={name} value={index}>{name}</option>)}
    </select></label>
    {scope === 3 && <label>Background effect<select value={background} onChange={event => onBackground(Number(event.target.value))}>
      {effects.map(effect => <option key={effect.id} value={effect.id}>{effect.label}</option>)}
    </select></label>}
    {scope !== 0 && <p className="stats">{status}</p>}
  </>
}
