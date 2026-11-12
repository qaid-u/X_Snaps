export type RecordingState = 'idle' | 'recording' | 'paused' | 'finishing'

const maxBytes = 96 * 1024 * 1024
const maxDuration = 5 * 60 * 1000

function download(blob: Blob, extension: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'SnapReality-' + new Date().toISOString().replace(/[:.]/g, '-') + '.' + extension
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 3000)
}

export class Capture {
  state: RecordingState = 'idle'
  private still = false
  private savingStill = false
  private disposed = false
  private recorder?: MediaRecorder
  private timer = 0

  constructor(private readonly canvas: HTMLCanvasElement, private readonly status: (message: string) => void) {}

  requestStill() {
    if (!this.savingStill) this.still = true
  }

  drawn() {
    if (!this.still) return
    this.still = false
    this.savingStill = true
    this.canvas.toBlob(blob => {
      this.savingStill = false
      if (this.disposed) return
      if (!blob) {
        this.status('Could not save PNG.')
        return
      }
      download(blob, 'png')
      this.status('PNG ready to save.')
    }, 'image/png')
  }

  start(fps: number) {
    if (this.state !== 'idle' || this.disposed) return
    let stream: MediaStream | undefined
    try {
      if (!this.canvas.captureStream || typeof MediaRecorder === 'undefined') throw new Error('Canvas recording is unavailable.')
      const mimeType = ['video/webm;codecs=vp8', 'video/webm;codecs=vp9', 'video/webm', 'video/mp4']
        .find(type => MediaRecorder.isTypeSupported(type))
      if (!mimeType) throw new Error('This browser does not offer a supported recording format.')
      stream = this.canvas.captureStream(fps)
      const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 4_000_000 })
      const chunks: Blob[] = []
      let bytes = 0
      recorder.ondataavailable = ({ data }) => {
        if (!data.size) return
        if (bytes + data.size <= maxBytes) {
          chunks.push(data)
          bytes += data.size
        } else {
          this.stop()
        }
      }
      recorder.onstop = () => {
        if (this.recorder !== recorder) return
        this.release()
        if (!chunks.length) {
          this.status('Recording contained no video frames.')
          return
        }
        const type = recorder.mimeType || mimeType
        download(new Blob(chunks, { type }), type.startsWith('video/mp4') ? 'mp4' : 'webm')
        this.status('Recording ready to save.')
      }
      recorder.onerror = () => {
        if (this.recorder !== recorder) return
        this.release()
        this.status('Recording stopped after an encoding error.')
      }
      recorder.start(1000)
      this.recorder = recorder
      this.state = 'recording'
      this.timer = window.setTimeout(() => this.stop(), maxDuration)
      this.status('Recording processed video.')
    } catch (error) {
      stream?.getTracks().forEach(track => track.stop())
      this.status(String(error))
    }
  }

  pause() {
    if (this.recorder?.state === 'recording') {
      this.recorder.pause()
      this.state = 'paused'
      this.status('Recording paused.')
    } else if (this.recorder?.state === 'paused') {
      this.recorder.resume()
      this.state = 'recording'
      this.status('Recording processed video.')
    }
  }

  stop() {
    if (!this.recorder || this.recorder.state === 'inactive') return
    this.state = 'finishing'
    this.recorder.stop()
  }

  private release() {
    window.clearTimeout(this.timer)
    this.recorder?.stream.getTracks().forEach(track => track.stop())
    this.recorder = undefined
    this.state = 'idle'
  }

  dispose() {
    this.disposed = true
    this.stop()
    this.release()
  }
}
