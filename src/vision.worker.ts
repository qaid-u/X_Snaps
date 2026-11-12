import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision'
import type { VisionRequest, VisionResponse } from './vision.protocol'

let model: HandLandmarker | undefined
const reply = (result: VisionResponse) => self.postMessage(result)

self.addEventListener('message', async ({ data }: MessageEvent<VisionRequest>) => {
  try {
    if (data.type === 'init') {
      const response = await fetch(data.model)
      if (!response.ok) throw new Error('Local hand model missing. Run npm run setup:models.')
      const bytes = new Uint8Array(await response.arrayBuffer())
      if (bytes.length < 1024) throw new Error('Local hand model missing. Run npm run setup:models.')
      const assets = await FilesetResolver.forVisionTasks(data.assets)
      model = await HandLandmarker.createFromOptions(assets, {
        baseOptions: { modelAssetBuffer: bytes, delegate: 'CPU' }, canvas: new OffscreenCanvas(1, 1),
        runningMode: 'VIDEO', numHands: 1, minHandDetectionConfidence: .55,
      })
      reply({ type: 'ready' })
    } else if (model) {
      const started = performance.now()
      const result = model.detectForVideo(data.bitmap, data.at)
      const hand = result.landmarks[0]
      const category = result.handedness[0]?.[0]
      reply({
        type: 'result', at: data.at, inferenceMs: performance.now() - started,
        hand: hand && category ? { side: category.categoryName, score: category.score, points: hand } : null,
      })
    }
  } catch (error) {
    reply({ type: 'error', message: String(error) })
  } finally {
    if (data.type === 'frame') data.bitmap.close()
  }
})
