import {
  Camera as ClipCamera, CanvasTexture, DataTexture, Mesh, PlaneGeometry, Scene, ShaderMaterial,
  Vector2, VideoTexture, WebGLRenderer, WebGLRenderTarget,
} from 'three'
import type { Texture } from 'three'
import { Camera } from './Camera'
import { HandTracking } from './HandTracking'
import { effects, fragment, previewFragment, vertex } from './effects'
import { PerformanceGovernor, PerformanceMonitor, profiles } from './performance'

class GpuTimer {
  private readonly extension
  private pending: WebGLQuery | null = null
  private active: WebGLQuery | null = null

  constructor(private readonly gl: WebGL2RenderingContext, private readonly sample: (ms: number) => void) {
    this.extension = gl.getExtension('EXT_disjoint_timer_query_webgl2')
  }

  begin() {
    const ext = this.extension
    if (!ext || this.gl.isContextLost()) return
    if (this.pending && this.gl.getQueryParameter(this.pending, this.gl.QUERY_RESULT_AVAILABLE)) {
      if (!this.gl.getParameter(ext.GPU_DISJOINT_EXT)) {
        this.sample(this.gl.getQueryParameter(this.pending, this.gl.QUERY_RESULT) / 1e6)
      }
      this.gl.deleteQuery(this.pending)
      this.pending = null
    }
    if (this.pending) return
    this.active = this.gl.createQuery()
    if (this.active) this.gl.beginQuery(ext.TIME_ELAPSED_EXT, this.active)
  }

  end() {
    if (!this.extension || !this.active) return
    this.gl.endQuery(this.extension.TIME_ELAPSED_EXT)
    this.pending = this.active
    this.active = null
  }

  dispose() {
    if (this.pending) this.gl.deleteQuery(this.pending)
    this.pending = null
  }
}

export const outputTitle = 'SNAP//REALITY — OBS OUTPUT'

function makeTitle() {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 144
  const context = canvas.getContext('2d')!
  context.font = 'italic 900 122px "Segoe UI", sans-serif'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillStyle = '#fff'
  context.fillText('SNAP', 251, 72, 475)
  return new CanvasTexture(canvas)
}

export class Engine {
  readonly camera = new Camera()
  readonly metrics = new PerformanceMonitor()
  readonly governor = new PerformanceGovernor()
  readonly hands = new HandTracking(this.camera.video, () => profiles[this.governor.level].handHz,
    () => this.next(1, performance.now(), true), ms => this.metrics.hand.add(ms), () => this.metrics.skippedInference++)
  trackingEnabled = true
  onEffect?: (id: number) => void
  private readonly renderer
  private readonly geometry = new PlaneGeometry(2, 2)
  private readonly clip = new ClipCamera()
  private readonly scene = new Scene()
  private readonly videoTexture = new VideoTexture(this.camera.video)
  private readonly blank = new DataTexture()
  private readonly title = makeTitle()
  private readonly history = Array.from({ length: 3 }, () => new WebGLRenderTarget(320, 180, { depthBuffer: false }))
  private readonly amounts = new Map<number, number>()
  private readonly uniforms = {
    live: { value: this.blank as DataTexture | VideoTexture },
    titleMap: { value: this.title }, recentFrame: { value: this.blank as Texture },
    olderFrame: { value: this.blank as Texture }, historyCount: { value: 0 },
    demo: { value: true }, mirrored: { value: false }, fit: { value: new Vector2(1, 1) },
    size: { value: new Vector2(1280, 720) }, effect: { value: 0 }, time: { value: 0 },
    strength: { value: 1 }, amount: { value: .5 }, impact: { value: 0 }, detailLevel: { value: 1 },
  }
  private readonly material = new ShaderMaterial({ uniforms: this.uniforms, vertexShader: vertex, fragmentShader: fragment,
    depthTest: false, depthWrite: false })
  private readonly previewMaterial = new ShaderMaterial({ uniforms: this.uniforms, vertexShader: vertex, fragmentShader: previewFragment,
    depthTest: false, depthWrite: false })
  private readonly mesh = new Mesh(this.geometry, this.previewMaterial)
  private timer: GpuTimer
  private handle = 0
  private due = 0
  private nextQualityCheck = 0
  private historyIndex = 0
  private historyAt = -Infinity
  private transitionAt = -Infinity
  private lastTriggerAt = -Infinity
  private frozen = false
  private disposed = false
  private lost = false
  private shaderError = ''
  private cameraLive = false
  readonly playable: Promise<void>
  readonly ready: Promise<void>
  initialMs = 0
  warmupMs = 0
  cover = false
  transition = true

  constructor(readonly canvas: HTMLCanvasElement, private readonly status: (status: string) => void) {
    this.renderer = new WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance' })
    this.renderer.debug.onShaderError = (gl, program, vert, frag) => {
      this.shaderError = [gl.getProgramInfoLog(program), gl.getShaderInfoLog(vert), gl.getShaderInfoLog(frag)].filter(Boolean).join(' ')
      console.error('Shader compilation failed', this.shaderError)
    }
    this.blank.image = { data: new Uint8Array([0, 0, 0, 255]), width: 1, height: 1 }
    this.blank.needsUpdate = true
    this.timer = this.makeTimer()
    this.scene.add(this.mesh)
    this.applyProfile()
    canvas.addEventListener('webglcontextlost', this.onContextLost)
    canvas.addEventListener('webglcontextrestored', this.onContextRestored)
    const started = performance.now()
    this.playable = this.renderer.compileAsync(this.scene, this.clip).then(() => {
      if (this.disposed) return
      this.renderer.render(this.scene, this.clip)
      if (this.shaderError) throw new Error('Video preview shader failed. ' + this.shaderError)
      this.initialMs = performance.now() - started
      this.handle = requestAnimationFrame(this.frame)
    })
    this.ready = this.playable.then(async () => {
      // Give the browser a presentation opportunity before preparing the catalog.
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      if (this.disposed) return
      const warming = new Scene()
      warming.add(new Mesh(this.geometry, this.material))
      await this.renderer.compileAsync(warming, this.clip)
      if (this.disposed) return
      for (const target of this.history) this.renderer.initRenderTarget(target)
      this.renderer.setRenderTarget(this.history[0])
      const historyShader = this.renderer.compileAsync(warming, this.clip)
      this.renderer.setRenderTarget(null)
      await historyShader
      if (this.disposed) return
      for (let index = 0; index < effects.length; index += 4) {
        await new Promise<void>(resolve => requestAnimationFrame(() => resolve()))
        if (this.disposed) return
        const priorImpact = this.uniforms.impact.value
        try {
          this.renderer.setRenderTarget(this.history[0])
          this.uniforms.impact.value = .5
          for (const effect of effects.slice(index, index + 4)) {
            this.uniforms.effect.value = effect.id
            this.renderer.render(warming, this.clip)
          }
        } finally {
          this.uniforms.effect.value = 0
          this.uniforms.impact.value = priorImpact
          this.renderer.setRenderTarget(null)
        }
      }
      this.renderer.render(warming, this.clip)
      if (this.shaderError) throw new Error('The effects shader could not be prepared. ' + this.shaderError)
      this.mesh.material = this.material
      this.previewMaterial.dispose()
      this.warmupMs = performance.now() - started
    })
  }

  private makeTimer() {
    const gl = this.renderer.getContext()
    if (!(gl instanceof WebGL2RenderingContext)) throw new Error('WebGL 2 required.')
    return new GpuTimer(gl, ms => this.metrics.gpu.add(ms))
  }

  private onContextLost = (event: Event) => {
    event.preventDefault()
    this.lost = true
    this.status('GPU context lost. Waiting for restoration.')
  }

  private onContextRestored = () => {
    this.timer.dispose()
    this.timer = this.makeTimer()
    this.lost = false
    this.metrics.reset()
    this.status('GPU context restored.')
  }

  private applyProfile() {
    const { width, height } = profiles[this.governor.level]
    this.renderer.setSize(width, height, false)
    this.uniforms.size.value.set(width, height)
    this.uniforms.detailLevel.value = this.governor.level
    this.due = 0
    this.metrics.reset()
  }

  get effect() { return this.uniforms.effect.value }
  get effectAmount() { return this.uniforms.amount.value }

  select(id: number, at = performance.now(), cooldown = false) {
    if (this.disposed || this.lost || !this.warmupMs || !effects.some(effect => effect.id === id)) return false
    if (cooldown && at - this.lastTriggerAt < 420) return false
    this.lastTriggerAt = at
    this.transitionAt = this.transition && id !== 0 ? at : -Infinity
    this.metrics.triggered(at)
    this.uniforms.effect.value = id
    this.uniforms.amount.value = this.amounts.get(id) ?? .5
    this.onEffect?.(id)
    return true
  }

  next(step = 1, at = performance.now(), cooldown = false) {
    const index = effects.findIndex(effect => effect.id === this.effect)
    const first = step > 0 ? 1 : effects.length - 1
    const next = index < 1 ? first : 1 + ((index - 1 + step + effects.length - 1) % (effects.length - 1))
    return this.select(effects[next].id, at, cooldown)
  }

  setMirror(value: boolean) { this.uniforms.mirrored.value = value }
  setStrength(value: number) { this.uniforms.strength.value = value }
  setAmount(value: number) {
    if (!Number.isFinite(value)) return
    const clamped = Math.max(0, Math.min(1, value))
    this.amounts.set(this.effect, clamped)
    this.uniforms.amount.value = clamped
  }
  setProfile(value: number, locked: boolean) {
    this.governor.select(value, locked)
    this.applyProfile()
  }

  async startCamera(device: string) {
    this.cameraLive = false
    this.clearHistory()
    this.hands.stop()
    const started = await this.camera.start(device, profiles[this.governor.ceiling].fps, now => {
      this.metrics.decoded(now)
      this.hands.frame(now)
    }, () => {
      this.cameraLive = false
      this.clearHistory()
      this.hands.stop()
      this.status('Camera disconnected. Demo is active.')
    })
    this.cameraLive = started
    if (started && this.trackingEnabled) this.hands.start()
    return started
  }

  setTracking(enabled: boolean) {
    this.trackingEnabled = enabled
    if (enabled && this.cameraLive) this.hands.start()
    else this.hands.stop()
  }

  stopCamera() {
    this.cameraLive = false
    this.clearHistory()
    this.hands.stop()
    this.camera.stop()
  }

  snapshot() {
    const gl = this.renderer.getContext()
    const info = gl.getExtension('WEBGL_debug_renderer_info')
    return {
      ...this.metrics.snapshot(profiles[this.governor.level].fps),
      initialMs: this.initialMs, warmupMs: this.warmupMs, effect: this.effect, width: this.canvas.width, height: this.canvas.height,
      gpuName: String(info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)),
      programs: this.renderer.info.programs?.length ?? 0,
      textures: this.renderer.info.memory.textures,
      profile: profiles[this.governor.level].name,
      reason: this.governor.reason,
      handStatus: this.hands.status,
      effectAmount: this.effectAmount,
      historyFrames: this.uniforms.historyCount.value,
    }
  }

  // The benchmark uses deterministic timestamps when checking pixel identity.
  sampleAt(time: number) {
    this.uniforms.time.value = time
    this.uniforms.impact.value = 0
    this.renderer.render(this.scene, this.clip)
    const gl = this.renderer.getContext()
    const pixels = new Uint8Array(this.canvas.width * this.canvas.height * 4)
    gl.readPixels(0, 0, this.canvas.width, this.canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
    let hash = 2166136261
    for (let i = 0; i < pixels.length; i += 16) hash = Math.imul(hash ^ pixels[i], 16777619)
    return hash >>> 0
  }

  private clearHistory() {
    this.historyAt = -Infinity
    this.uniforms.historyCount.value = 0
    this.uniforms.recentFrame.value = this.blank
    this.uniforms.olderFrame.value = this.blank
  }

  private updateHistory(now: number) {
    const active = this.effect === 10 || this.effect === 15
    if (!active || now - this.historyAt < (this.governor.level === 0 ? 150 : 100)) return
    if (now - this.historyAt > 450) this.clearHistory()
    const effect = this.effect
    const impact = this.uniforms.impact.value
    this.uniforms.effect.value = 0
    this.uniforms.impact.value = 0
    const target = this.history[this.historyIndex]
    this.renderer.setRenderTarget(target)
    try {
      this.renderer.render(this.scene, this.clip)
    } finally {
      this.renderer.setRenderTarget(null)
      this.uniforms.effect.value = effect
      this.uniforms.impact.value = impact
    }
    this.uniforms.olderFrame.value = this.uniforms.recentFrame.value
    this.uniforms.recentFrame.value = target.texture
    this.uniforms.historyCount.value = Math.min(2, this.uniforms.historyCount.value + 1)
    this.historyIndex = (this.historyIndex + 1) % this.history.length
    this.historyAt = now
  }

  private frame = (now: number) => {
    this.handle = requestAnimationFrame(this.frame)
    if (this.lost || this.frozen) return
    const { fps } = profiles[this.governor.level]
    if (now + .5 < this.due) return
    this.due = Math.max(this.due + 1000 / fps, now + .5)
    const began = performance.now()
    const live = this.cameraLive && this.camera.active
    this.uniforms.demo.value = !live
    this.uniforms.live.value = live ? this.videoTexture : this.blank
    if (live) {
      const ratio = (this.canvas.width / this.canvas.height) / (this.camera.video.videoWidth / this.camera.video.videoHeight)
      this.uniforms.fit.value.set(this.cover ? Math.min(1, ratio) : Math.max(1, ratio),
        this.cover ? Math.min(1, 1 / ratio) : Math.max(1, 1 / ratio))
    }
    this.uniforms.time.value = now / 1000
    this.uniforms.impact.value = Math.max(0, 1 - (now - this.transitionAt) / 240)
    this.timer.begin()
    try {
      this.renderer.render(this.scene, this.clip)
      this.updateHistory(now)
    } catch (error) {
      this.frozen = true
      this.stopCamera()
      this.status('Rendering stopped. Reload to recover. ' + String(error))
    } finally {
      this.timer.end()
    }
    this.metrics.drawn(performance.now(), performance.now() - began)
    if (now >= this.nextQualityCheck && this.metrics.render.summary().count >= fps * 2) {
      this.nextQualityCheck = now + 1000
      if (this.governor.observe(this.metrics.render.slowRatio(1500 / fps), this.metrics.gpu.summary().p95)) this.applyProfile()
    }
  }

  dispose() {
    this.disposed = true
    this.stopCamera()
    cancelAnimationFrame(this.handle)
    this.canvas.removeEventListener('webglcontextlost', this.onContextLost)
    this.canvas.removeEventListener('webglcontextrestored', this.onContextRestored)
    this.timer.dispose()
    this.videoTexture.dispose()
    this.blank.dispose()
    this.title.dispose()
    for (const target of this.history) target.dispose()
    this.geometry.dispose()
    this.material.dispose()
    this.previewMaterial.dispose()
    this.renderer.dispose()
  }
}
