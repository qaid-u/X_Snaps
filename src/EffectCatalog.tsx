import { useState } from 'react'
import { effects } from './effects'

export function EffectCatalog({ selected, disabled, choose, children }: {
  selected: number | undefined
  disabled: boolean
  choose: (id: number) => void
  children?: React.ReactNode
}) {
  const [search, setSearch] = useState('')
  const visible = effects.filter(item => item.label.toLowerCase().includes(search.trim().toLowerCase()))
  return <aside className="catalog" aria-label="Effects">
    <h1>Effects</h1>
    <input type="search" aria-label="Search effects" placeholder="Search effects" value={search} onChange={event => setSearch(event.target.value)} />
    <div className="effect-list">{visible.map(item => <button type="button" key={item.id} disabled={disabled}
      aria-pressed={item.id === selected} onClick={() => choose(item.id)}>
      <span>{String(item.id).padStart(2, '0')}</span>{item.label}
    </button>)}</div>
    {children}
  </aside>
}
