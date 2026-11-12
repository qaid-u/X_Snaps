import type { VisionRequest, VisionResponse, VisionResult } from './vision.protocol'

export class VideoInference<Result extends VisionResult> {
  private worker: Worker | null = null
  private busy = false
  private ready = false
  private due = -Infinity
  private timer = 0
  status = 'Off'

  constructor(
    private readonly kind: Result['type'],
    private readonly video: HTMLVideoElement,
    private readonly hz: () => number,
    private readonly width: () => number,
    private readonly consume: (result: Result) => void,
    private readonly skipped: () => void,
  ) {}

  start() {
    if (this.worker) return
    if (typeof OffscreenCanvas === 'undefined' || typeof createImageBitmap === 'undefined') {
      this.fail('Worker vision is unavailable in this browser.')
      return
    }
    const root = new URL(import.meta.env.BASE_URL, location.href)
    let worker: Worker
    try {
      worker = new Worker(new URL('vision/hand-worker.js', root))
    } catch (error) {
      this.fail(String(error))
      return
    }
    this.worker = worker
    this.status = 'Loading local model…'
    this.timer = window.setTimeout(() => this.fail('Model initialization timed out.'), 15000)
    worker.onmessage = ({ data }: MessageEvent<VisionResponse>) => {
      if (this.worker !== worker) return
      window.clearTimeout(this.timer)
      if (data.type === 'ready') {
        this.ready = true
        this.status = 'Active'
      } else if (data.type === 'error') {
        this.fail(data.message)
      } else if (data.type === this.kind) {
        this.busy = false
        if (performance.now() - data.at > (this.kind === 'hand' ? 170 : 350)) this.skipped()
        else this.consume(data as Result)
      }
    }
    worker.onerror = event => this.fail(event.message || 'Worker could not start.')
    const model = this.kind === 'hand' ? 'hand_landmarker.task' : 'selfie_segmenter_landscape.tflite'
    const init: VisionRequest = { type: 'init', kind: this.kind,
      assets: new URL('vision', root).href, model: new URL('models/' + model, root).href }
    worker.postMessage(init)
  }

  frame(at: number) {
    const worker = this.worker
    if (!worker || !this.ready || at + 2 < this.due || !this.video.videoWidth) return
    if (this.busy) {
      this.skipped()
      return
    }
    this.busy = true
    const interval = 1000 / this.hz()
    this.due = this.due === -Infinity ? at + interval : Math.max(this.due + interval, at + 1)
    const width = Math.min(this.width(), this.video.videoWidth)
    const height = Math.max(1, Math.round(this.video.videoHeight * width / this.video.videoWidth))
    this.timer = window.setTimeout(() => this.fail('Frame inference timed out.'), 1800)
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
        this.fail(String(error))
      }
    }).catch(error => { if (this.worker === worker) this.fail(String(error)) })
  }

  private fail(reason: string) {
    this.stop()
    this.status = 'Unavailable. ' + reason
  }

  stop() {
    this.worker?.terminate()
    this.worker = null
    window.clearTimeout(this.timer)
    this.ready = this.busy = false
    this.due = -Infinity
    this.status = 'Off'
  }
}
