class SnapProcessor extends AudioWorkletProcessor {
  noise = .002
  previous = 0
  onset = -1
  peak = 0
  sensitivity = .5
  meterAt = 0
  lastPulse = -1
  ignoreUntilQuiet = false

  constructor() {
    super()
    this.port.onmessage = ({ data }) => {
      if (Number.isFinite(data)) this.sensitivity = Math.max(0, Math.min(1, data))
    }
  }

  process(inputs) {
    const samples = inputs[0]?.[0]
    if (!samples?.length) return true
    let power = 0
    let high = 0
    for (const sample of samples) {
      const delta = sample - this.previous
      power += sample * sample
      high += delta * delta
      this.previous = sample
    }
    const rms = Math.sqrt(power / samples.length)
    const spectral = high / Math.max(power, .000001)
    const threshold = Math.max(.012 + (1 - this.sensitivity) * .026, this.noise * (4 + (1 - this.sensitivity) * 4))
    if (rms < threshold * .7) this.ignoreUntilQuiet = false
    if (this.onset < 0 && rms < threshold) this.noise = this.noise * .986 + rms * .014
    if (!this.ignoreUntilQuiet && this.onset < 0 && rms > threshold && spectral > .36 && currentTime - this.lastPulse > .14) {
      this.onset = currentTime
      this.peak = rms
    } else if (this.onset >= 0) {
      this.peak = Math.max(this.peak, rms)
      const duration = currentTime - this.onset
      if (rms < this.peak * .33 || duration > .045) {
        if (duration <= .045 && this.peak > threshold) {
          this.lastPulse = currentTime
          this.port.postMessage({ onset: this.onset })
        }
        if (duration > .045) this.ignoreUntilQuiet = true
        this.onset = -1
      }
    }
    if (currentTime > this.meterAt) {
      this.meterAt = currentTime + .2
      this.port.postMessage({ level: Math.min(1, rms * 8) })
    }
    return true
  }
}

registerProcessor('snap-transient', SnapProcessor)
