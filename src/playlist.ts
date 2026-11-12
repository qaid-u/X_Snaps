export type Playlist = { ids: number[]; shuffle: boolean }
const key = 'snap-reality.playlist.v1'

export function defaultPlaylist(): Playlist {
  return { ids: Array.from({ length: 20 }, (_, index) => index + 1), shuffle: false }
}

export function normalizePlaylist(value: unknown): Playlist {
  if (!value || typeof value !== 'object' || !('ids' in value) || !Array.isArray(value.ids)) return defaultPlaylist()
  const ids = [...new Set(value.ids.filter((id): id is number => Number.isInteger(id) && id >= 0 && id <= 20))]
  return ids.length ? { ids, shuffle: 'shuffle' in value && value.shuffle === true } : defaultPlaylist()
}

export function loadPlaylist() {
  try { return normalizePlaylist(JSON.parse(localStorage.getItem(key) ?? 'null')) } catch { return defaultPlaylist() }
}

export function savePlaylist(value: Playlist) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* The in-memory playlist remains active. */ }
}

export function nextEffect(playlist: Playlist, current: number, step: number, random = Math.random) {
  const { ids } = playlist
  if (playlist.shuffle && step > 0 && ids.length > 1) {
    const choices = ids.filter(id => id !== current)
    return choices[Math.floor(random() * choices.length)]
  }
  const index = ids.indexOf(current)
  if (index < 0) return step > 0 ? ids[0] : ids[ids.length - 1]
  return ids[(index + step + ids.length) % ids.length]
}
