import { describe, expect, it } from 'vitest'
import { PerformanceGovernor, PerformanceMonitor, Samples } from './performance'

describe('performance measurements', () => {
  it('keeps a bounded recent window', () => {
    const samples = new Samples(3)
    for (const value of [5, 1, 2, 3]) samples.add(value)
    expect(samples.summary()).toEqual({ count: 3, mean: 2, p50: 2, p95: 3, p99: 3 })
  })

  it('measures source cadence and trigger-to-draw separately', () => {
    const monitor = new PerformanceMonitor()
    monitor.decoded(0)
    monitor.decoded(40)
    monitor.drawn(10, 1)
    monitor.triggered(18)
    monitor.drawn(30, 2)
    expect(monitor.snapshot(60)).toMatchObject({ sourceFps: 25, renderFps: 50, latency: { p95: 12 } })
  })
})

describe('quality hysteresis', () => {
  it('lowers under sustained load and recovers slowly', () => {
    const governor = new PerformanceGovernor()
    expect(governor.observe(.2, 22)).toBe(false)
    expect(governor.observe(.2, 22)).toBe(false)
    expect(governor.observe(.2, 22)).toBe(true)
    expect(governor.level).toBe(0)
    for (let i = 0; i < 17; i++) expect(governor.observe(0, 2)).toBe(false)
    expect(governor.observe(0, 2)).toBe(true)
    expect(governor.level).toBe(1)
  })

  it('does not change a locked quality profile', () => {
    const governor = new PerformanceGovernor(2, true)
    for (let i = 0; i < 20; i++) expect(governor.observe(1, 100)).toBe(false)
    expect(governor.level).toBe(2)
  })
})
