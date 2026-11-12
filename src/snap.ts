export type Hand = { side: string; score: number; points: readonly Point[] }
type Point = { x: number; y: number; z: number }
type Geometry = { separation: number; middle: number }

function distance(a: Point, b: Point) {
  return Math.hypot(a.x - b.x, a.y - b.y, (a.z - b.z) * .6)
}

export function handGeometry(points: readonly Point[]): Geometry | null {
  if (points.length !== 21) return null
  const palm = (distance(points[0], points[9]) + distance(points[5], points[17])) * .5
  if (!Number.isFinite(palm) || palm < .035) return null
  return { separation: distance(points[4], points[12]) / palm, middle: distance(points[0], points[12]) / palm }
}

export class SnapDetector {
  state: 'Idle' | 'Contact' | 'Armed' | 'Cooldown' = 'Idle'
  sensitivity = .5
  cooldownMs = 650
  private lastAt = -Infinity
  private lastSnap = -Infinity
  private contactAt = 0
  private contact: Geometry | null = null
  private side = ''

  private resetPose() {
    this.contact = null
    this.state = 'Idle'
  }

  step(at: number, hand: Hand | null) {
    if (!Number.isFinite(at) || at <= this.lastAt) return false
    const gap = at - this.lastAt
    this.lastAt = at
    if (at - this.lastSnap < this.cooldownMs) return false
    const value = hand && hand.score >= .55 ? handGeometry(hand.points) : null
    if (!hand || !value || !Number.isFinite(value.separation + value.middle)) {
      this.resetPose()
      return false
    }
    if (gap > 140 || hand.side !== this.side) this.resetPose()
    this.side = hand.side
    const close = .19 + this.sensitivity * .13
    if (this.state === 'Cooldown') {
      if (value.separation > close + .13) this.resetPose()
      return false
    }
    if (value.separation < close) {
      this.contactAt = at
      if (!this.contact) {
        this.contact = value
        this.state = 'Contact'
      } else {
        this.state = 'Armed'
      }
      return false
    }
    if (value.separation < close + .13) return false
    const age = at - this.contactAt
    const released = this.state === 'Armed' && !!this.contact && age <= 285 &&
      this.contact.middle - value.middle > .095 - this.sensitivity * .06 &&
      value.separation - this.contact.separation < 1.15
    this.resetPose()
    if (!released) return false
    this.state = 'Cooldown'
    this.lastSnap = at
    return true
  }
}
