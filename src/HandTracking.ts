import { SnapDetector } from './snap'
import type { VisionRequest, VisionResponse } from './vision.protocol'

export class HandTracking {
  private worker: Worker | null = null
  private busy = false
  private ready = false
  private lastFrame = -Infinity
  private detector = new SnapDetector()
  status = 'Hand tracking off'
  sensitivity = .5
  cooldown = 650

  constructor(
    private readonly video: HTMLVideoElement,
    private readonly hz: () => number,
    private readonly snap: () => void,
    private readonly measured: (inferenceMs: number) => void,
    private readonly skipped: () => void,
  ) {}

  start() {
    if (this.worker) return
    if (typeof OffscreenCanvas === 'undefined' || typeof createImageBitmap === 'undefined') {
      this.status = 'Worker vision unavailable. Use Space.'
      return
    }
    const url = new URL(import.meta.env.BASE_URL, location.href)
    let worker: Worker
    try {
      worker = new Worker(new URL('vision/hand-worker.js', url))
    } catch (error) {
      this.failed(String(error))
      return
    }
    this.worker = worker
    this.detector = new SnapDetector()
    this.status = 'Loading local hand model…'
    worker.onmessage = ({ data }: MessageEvent<VisionResponse>) => {
      if (this.worker !== worker) return
      if (data.type === 'ready') {
        this.ready = true
        this.status = 'Show thumb and middle finger'
      } else if (data.type === 'error') {
        this.failed(data.message)
      } else {
        this.busy = false
        this.measured(data.inferenceMs)
        if (performance.now() - data.at > 170) {
          this.skipped()
          return
        }
        this.detector.sensitivity = this.sensitivity
        this.detector.cooldownMs = this.cooldown
        if (this.detector.step(data.at, data.hand)) this.snap()
        this.status = data.hand ? this.detector.state : 'Show thumb and middle finger'
      }
    }
    worker.onerror = event => this.failed(event.message || 'Worker could not start.')
    const init: VisionRequest = { type: 'init', assets: new URL('vision', url).href, model: new URL('models/hand_landmarker.task', url).href }
    worker.postMessage(init)
  }

  frame(at: number) {
    const worker = this.worker
    if (!worker || !this.ready || at - this.lastFrame < 1000 / this.hz() - 3) return
    if (this.busy) {
      this.skipped()
      return
    }
    this.busy = true
    this.lastFrame = at
    const width = Math.min(480, this.video.videoWidth)
    const height = Math.max(1, Math.round(this.video.videoHeight * width / this.video.videoWidth))
    void createImageBitmap(this.video, { resizeWidth: width, resizeHeight: height, resizeQuality: 'low' }).then(bitmap => {
      if (this.worker !== worker) {
        bitmap.close()
        return
      }
      try {
        const request: VisionRequest = { type: 'frame', bitmap, at }
        worker.postMessage(request, [bitmap])
      } catch (error) {
        bitmap.close()
        this.failed(String(error))
      }
    }).catch(error => { if (this.worker === worker) this.failed(String(error)) })
  }

  private failed(reason: string) {
    this.stop()
    this.status = 'Hand tracking unavailable. ' + reason
  }

  stop() {
    this.worker?.terminate()
    this.worker = null
    this.ready = this.busy = false
    this.lastFrame = -Infinity
    this.status = 'Hand tracking off'
  }
}
