import { describe, expect, it } from 'vitest'
import { SnapFusion } from './audio'

describe('audio and vision fusion', () => {
  it('pairs a nearby pulse once in either event order', () => {
    const fusion = new SnapFusion()
    expect(fusion.visual(100)).toBe(false)
    expect(fusion.audio(190)).toBe(true)
    expect(fusion.audio(200)).toBe(false)
    expect(fusion.visual(270)).toBe(true)
    expect(fusion.visual(290)).toBe(false)
  })

  it('does not pair distant events or input that was reset', () => {
    const fusion = new SnapFusion()
    expect(fusion.audio(100)).toBe(false)
    expect(fusion.visual(250)).toBe(false)
    fusion.clear()
    expect(fusion.audio(260)).toBe(false)
  })
})
