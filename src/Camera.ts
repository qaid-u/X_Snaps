export class Camera {
  readonly video = document.createElement('video')
  private stream: MediaStream | null = null
  private generation = 0
  private pending = false
  private frameHandle = 0
  private animationHandle = 0

  constructor() {
    this.video.muted = true
    this.video.playsInline = true
  }

  get active() { return this.stream !== null && this.video.readyState >= 2 }

  async start(deviceId: string, fps: number, frame: (timestamp: number) => void, ended: () => void) {
    if (this.pending) return false
    this.stop()
    const generation = this.generation
    this.pending = true
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Camera access requires localhost or HTTPS.')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: fps }, ...(deviceId && { deviceId: { exact: deviceId } }) },
        audio: false,
      })
      if (generation !== this.generation) {
        stream.getTracks().forEach(track => track.stop())
        return false
      }
      this.stream = stream
      const track = stream.getVideoTracks()[0]
      if (!track) throw new Error('The device provided no video track.')
      if (/OBS Virtual Camera/i.test(track.label)) throw new Error('Choose the physical webcam in the camera list.')
      track.addEventListener('ended', () => {
        if (generation !== this.generation) return
        this.stop()
        ended()
      }, { once: true })
      this.video.srcObject = stream
      await this.video.play()
      if (generation !== this.generation) return false
      if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
        const receive: VideoFrameRequestCallback = now => {
          if (generation !== this.generation) return
          this.frameHandle = this.video.requestVideoFrameCallback(receive)
          frame(now)
        }
        this.frameHandle = this.video.requestVideoFrameCallback(receive)
      } else {
        let last = -1
        const receive = (now: number) => {
          if (generation !== this.generation) return
          this.animationHandle = requestAnimationFrame(receive)
          if (last === this.video.currentTime || this.video.readyState < 2) return
          last = this.video.currentTime
          frame(now)
        }
        this.animationHandle = requestAnimationFrame(receive)
      }
      return true
    } catch (error) {
      if (generation !== this.generation) return false
      this.stop()
      throw error
    } finally {
      this.pending = false
    }
  }

  stop() {
    this.generation++
    if (this.frameHandle) this.video.cancelVideoFrameCallback(this.frameHandle)
    cancelAnimationFrame(this.animationHandle)
    this.frameHandle = this.animationHandle = 0
    this.stream?.getTracks().forEach(track => track.stop())
    this.stream = null
    this.video.srcObject = null
  }
}
