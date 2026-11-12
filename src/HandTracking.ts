import { SnapDetector } from './snap'
import { VideoInference } from './VideoInference'
import type { VisionResult } from './vision.protocol'

export class HandTracking {
  private readonly worker: VideoInference<Extract<VisionResult, { type: 'hand' }>>
  private detector = new SnapDetector()
  private visible = false
  sensitivity = .5
  cooldown = 650

  constructor(video: HTMLVideoElement, hz: () => number, snap: (at: number) => void,
    measured: (inferenceMs: number) => void, skipped: () => void) {
    this.worker = new VideoInference('hand', video, hz, () => 480, result => {
      measured(result.inferenceMs)
      this.detector.sensitivity = this.sensitivity
      this.detector.cooldownMs = this.cooldown
      this.visible = !!result.hand
      if (this.detector.step(result.at, result.hand)) snap(result.at)
    }, skipped)
  }

  get status() {
    if (this.worker.status === 'Off') return 'Hand tracking off'
    if (this.worker.status === 'Active') return this.visible ? this.detector.state : 'Show thumb and middle finger'
    if (this.worker.status.startsWith('Unavailable')) return 'Hand tracking unavailable. ' + this.worker.status.slice(13)
    return this.worker.status
  }

  start() {
    this.detector = new SnapDetector()
    this.visible = false
    this.worker.start()
  }

  frame(at: number) { this.worker.frame(at) }
  stop() { this.worker.stop() }
}
