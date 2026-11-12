export const detectionModes = ['Visual', 'Visual + audio', 'Audio only', 'Keyboard / manual'] as const

export class SnapFusion {
  private hand = -Infinity
  private pulse = -Infinity

  visual(at: number) {
    if (Math.abs(at - this.pulse) <= 120) {
      this.clear()
      return true
    }
    this.hand = at
    return false
  }

  audio(at: number) {
    if (Math.abs(at - this.hand) <= 120) {
      this.clear()
      return true
    }
    this.pulse = at
    return false
  }

  clear() { this.hand = this.pulse = -Infinity }
}

export class Microphone {
  private context?: AudioContext
  private stream?: MediaStream
  private node?: AudioWorkletNode
  private generation = 0
  private requesting = false
  state: 'off' | 'starting' | 'active' = 'off'
  message = 'Microphone off'
  level = 0
  sensitivity = .5

  constructor(private readonly onset: (at: number) => void) {}

  async start() {
    if (this.state !== 'off' || this.requesting) return
    const generation = ++this.generation
    this.requesting = true
    this.state = 'starting'
    this.message = 'Requesting microphone…'
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: { echoCancellation: false, autoGainControl: false, noiseSuppression: false, channelCount: 1 },
      })
      if (generation !== this.generation) {
        stream.getTracks().forEach(track => track.stop())
        return
      }
      this.stream = stream
      const context = new AudioContext({ latencyHint: 'interactive' })
      this.context = context
      const root = new URL(import.meta.env.BASE_URL, location.href)
      await context.audioWorklet.addModule(new URL('audio/snap-processor.js', root).href)
      if (generation !== this.generation) return
      const node = new AudioWorkletNode(context, 'snap-transient')
      this.node = node
      const mute = context.createGain()
      mute.gain.value = 0
      context.createMediaStreamSource(stream).connect(node).connect(mute).connect(context.destination)
      node.port.postMessage(this.sensitivity)
      node.port.onmessage = ({ data }: MessageEvent<{ onset?: number; level?: number }>) => {
        if (typeof data.level === 'number') this.level = data.level
        if (typeof data.onset === 'number' && this.state === 'active') {
          const at = performance.now() - Math.max(0, context.currentTime - data.onset) * 1000
          this.onset(at)
        }
      }
      stream.getAudioTracks()[0]?.addEventListener('ended', () => {
        if (generation !== this.generation) return
        this.stop()
        this.message = 'Microphone disconnected'
      }, { once: true })
      await context.resume()
      if (generation !== this.generation) return
      this.state = 'active'
      this.message = 'Microphone active'
    } catch (error) {
      if (generation !== this.generation) return
      this.stop()
      this.message = 'Microphone unavailable. ' + String(error)
    } finally {
      this.requesting = false
    }
  }

  setSensitivity(value: number) {
    this.sensitivity = value
    this.node?.port.postMessage(value)
  }

  stop() {
    this.generation++
    this.node?.port.close()
    this.node?.disconnect()
    this.node = undefined
    this.stream?.getTracks().forEach(track => track.stop())
    this.stream = undefined
    void this.context?.close().catch(() => {})
    this.context = undefined
    this.state = 'off'
    this.message = 'Microphone off'
    this.level = 0
  }
}
