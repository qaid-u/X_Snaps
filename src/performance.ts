export const profiles = [
  { name: 'Performance', width: 640, height: 360, fps: 30, handHz: 18 },
  { name: 'Balanced', width: 1280, height: 720, fps: 30, handHz: 24 },
  { name: 'Quality', width: 1280, height: 720, fps: 60, handHz: 30 },
] as const

export function percentile(samples: readonly number[], fraction: number) {
  if (!samples.length) return null
  const sorted = [...samples].sort((a, b) => a - b)
  return sorted[Math.max(0, Math.ceil(sorted.length * fraction) - 1)]
}

export class Samples {
  private values: number[] = []
  private cursor = 0

  constructor(private readonly limit = 240) {}

  get count() { return this.values.length }

  add(value: number) {
    this.values[this.cursor] = value
    this.cursor = (this.cursor + 1) % this.limit
  }

  clear() {
    this.values = []
    this.cursor = 0
  }

  summary() {
    return {
      count: this.values.length,
      mean: this.values.length ? this.values.reduce((sum, value) => sum + value, 0) / this.values.length : null,
      p50: percentile(this.values, .5),
      p95: percentile(this.values, .95),
      p99: percentile(this.values, .99),
    }
  }

  slowRatio(budget: number) {
    return this.values.filter(value => value > budget).length / Math.max(1, this.values.length)
  }
}

export class PerformanceMonitor {
  readonly render = new Samples()
  readonly source = new Samples()
  readonly cpu = new Samples()
  readonly gpu = new Samples()
  readonly hand = new Samples()
  readonly segmentation = new Samples()
  readonly latency = new Samples()
  skippedInference = 0
  skippedMasks = 0
  private lastRender: number | null = null
  private lastSource: number | null = null
  private triggerAt: number | null = null

  reset() {
    for (const sample of [this.render, this.source, this.cpu, this.gpu, this.hand, this.segmentation, this.latency]) sample.clear()
    this.lastRender = this.lastSource = this.triggerAt = null
    this.skippedInference = 0
    this.skippedMasks = 0
  }

  decoded(now: number) {
    if (this.lastSource !== null) this.source.add(now - this.lastSource)
    this.lastSource = now
  }

  triggered(now: number) {
    this.triggerAt = now
  }

  drawn(now: number, cpuMs: number) {
    if (this.lastRender !== null) this.render.add(now - this.lastRender)
    if (this.triggerAt !== null) this.latency.add(now - this.triggerAt)
    this.triggerAt = null
    this.lastRender = now
    this.cpu.add(cpuMs)
  }

  snapshot(fps: number) {
    const render = this.render.summary()
    const source = this.source.summary()
    return {
      render, source, renderFps: render.mean ? 1000 / render.mean : null,
      sourceFps: source.mean ? 1000 / source.mean : null,
      longFrameRatio: this.render.slowRatio(1500 / fps),
      cpu: this.cpu.summary(), gpu: this.gpu.summary(), hand: this.hand.summary(),
      segmentation: this.segmentation.summary(), latency: this.latency.summary(),
      skippedInference: this.skippedInference, skippedMasks: this.skippedMasks,
    }
  }
}

export class PerformanceGovernor {
  level = 1
  reason = 'Balanced selected'
  private overload = 0
  private recovery = 0

  constructor(public ceiling = 1, public locked = false) {
    this.level = ceiling
  }

  select(level: number, locked: boolean) {
    this.ceiling = this.level = level
    this.locked = locked
    this.reason = profiles[level].name + ' selected'
    this.overload = this.recovery = 0
  }

  observe(longFrameRatio: number, gpuP95: number | null) {
    if (this.locked) return false
    const gpuBudget = 480 / profiles[this.level].fps
    const overloaded = longFrameRatio > .08 || (gpuP95 !== null && gpuP95 > gpuBudget)
    const recovered = longFrameRatio < .015 && (gpuP95 === null || gpuP95 < gpuBudget * .65)
    this.overload = overloaded ? this.overload + 1 : 0
    this.recovery = recovered ? this.recovery + 1 : 0
    const next = this.overload >= 3 ? Math.max(0, this.level - 1)
      : this.recovery >= 18 ? Math.min(this.ceiling, this.level + 1) : this.level
    if (next === this.level) return false
    this.reason = next < this.level ? 'Sustained frame or GPU load' : 'Sustained recovery'
    this.level = next
    this.overload = this.recovery = 0
    return true
  }
}
