import { describe, expect, it } from 'vitest'
import { defaultPlaylist, nextEffect, normalizePlaylist } from './playlist'

describe('effect rotation', () => {
  it('uses 1–20 by default and wraps in both directions', () => {
    expect(nextEffect(defaultPlaylist(), 0, 1)).toBe(1)
    expect(nextEffect(defaultPlaylist(), 20, 1)).toBe(1)
    expect(nextEffect(defaultPlaylist(), 1, -1)).toBe(20)
  })

  it('validates imported data, keeps order and permits Original', () => {
    const playlist = normalizePlaylist({ ids: [7, 0, 4, 7, 1.2, '3', -4, 21], shuffle: true })
    expect(playlist).toEqual({ ids: [7, 0, 4], shuffle: true })
    expect(nextEffect(playlist, 7, 1, () => 0)).toBe(0)
    expect(nextEffect(playlist, 7, 1, () => .99)).toBe(4)
    expect(normalizePlaylist({ ids: [] })).toEqual(defaultPlaylist())
  })
})
