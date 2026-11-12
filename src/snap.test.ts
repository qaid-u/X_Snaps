import { describe, expect, it } from 'vitest'
import { SnapDetector, handGeometry } from './snap'
import type { Hand } from './snap'

function pose(separation: number, middle: number, side = 'Right'): Hand {
  const points = Array.from({ length: 21 }, () => ({ x: .5, y: .5, z: 0 }))
  points[0].y = .75
  points[9].y = .55
  points[5].x = .4
  points[17].x = .6
  points[12].y = .75 - middle
  points[4] = { ...points[12], x: .5 + separation }
  return { points, side, score: .96 }
}
const contact = pose(.026, .29)
const release = pose(.09, .25)

describe('snap recognizer', () => {
  it('normalizes against palm scale', () => {
    const smaller = contact.points.map(point => ({ x: point.x * .5, y: point.y * .5, z: point.z * .5 }))
    expect(handGeometry(smaller)?.separation).toBeCloseTo(handGeometry(contact.points)!.separation)
  })

  it('arms on two frames, accepts palmward release and holds cooldown', () => {
    const detector = new SnapDetector()
    expect(detector.step(100, contact)).toBe(false)
    expect(detector.step(136, contact)).toBe(false)
    expect(detector.state).toBe('Armed')
    expect(detector.step(169, release)).toBe(true)
    expect(detector.step(200, release)).toBe(false)
    expect(detector.step(500, contact)).toBe(false)
    expect(detector.step(850, release)).toBe(false)
    expect(detector.step(885, contact)).toBe(false)
    expect(detector.step(920, contact)).toBe(false)
    expect(detector.step(955, release)).toBe(true)
  })

  it('rejects loss, hand changes, stale timing and a pinch opening', () => {
    for (const rejected of [null, { ...release, side: 'Left' }, pose(.09, .33)]) {
      const detector = new SnapDetector()
      detector.step(100, contact)
      detector.step(136, contact)
      expect(detector.step(150, rejected)).toBe(false)
      expect(detector.step(149, release)).toBe(false)
    }
    const detector = new SnapDetector()
    detector.step(100, contact)
    detector.step(136, contact)
    expect(detector.step(300, release)).toBe(false)
  })
})
