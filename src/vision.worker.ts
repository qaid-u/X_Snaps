import { FilesetResolver, HandLandmarker, ImageSegmenter } from '@mediapipe/tasks-vision'
import type { VisionRequest, VisionResponse } from './vision.protocol'

let model: HandLandmarker | ImageSegmenter | undefined
const reply = self.postMessage.bind(self) as (result: VisionResponse, transfer?: Transferable[]) => void

self.addEventListener('message', async ({ data }: MessageEvent<VisionRequest>) => {
  try {
    if (data.type === 'init') {
      const response = await fetch(data.model)
      if (!response.ok) throw new Error('Local model missing. Run npm run setup:models.')
      const bytes = new Uint8Array(await response.arrayBuffer())
      if (bytes.length < 1024) throw new Error('Local model missing. Run npm run setup:models.')
      const assets = await FilesetResolver.forVisionTasks(data.assets)
      const options = {
        baseOptions: { modelAssetBuffer: bytes, delegate: 'CPU' as const }, canvas: new OffscreenCanvas(1, 1),
        runningMode: 'VIDEO' as const,
      }
      model = data.kind === 'hand'
        ? await HandLandmarker.createFromOptions(assets, { ...options, numHands: 1, minHandDetectionConfidence: .55 })
        : await ImageSegmenter.createFromOptions(assets, { ...options, outputConfidenceMasks: true, outputCategoryMask: false })
      reply({ type: 'ready' })
    } else if (model instanceof HandLandmarker) {
      const started = performance.now()
      const result = model.detectForVideo(data.bitmap, data.at)
      const hand = result.landmarks[0]
      const category = result.handedness[0]?.[0]
      reply({
        type: 'hand', at: data.at, inferenceMs: performance.now() - started,
        hand: hand && category ? { side: category.categoryName, score: category.score, points: hand } : null,
      })
    } else if (model instanceof ImageSegmenter) {
      const started = performance.now()
      model.segmentForVideo(data.bitmap, data.at, result => {
        // The landscape model provides person confidence as its sole or last channel.
        const mask = result.confidenceMasks?.at(-1)
        if (!mask) throw new Error('The segmentation model returned no confidence mask.')
        const values = mask.getAsFloat32Array()
        const pixels = new Uint8Array(values.length)
        for (let i = 0; i < values.length; i++) pixels[i] = Math.round(Math.max(0, Math.min(1, values[i])) * 255)
        reply({ type: 'mask', at: data.at, inferenceMs: performance.now() - started,
          width: mask.width, height: mask.height, pixels }, [pixels.buffer])
      })
    }
  } catch (error) {
    reply({ type: 'error', message: String(error) })
  } finally {
    if (data.type === 'frame') data.bitmap.close()
  }
})
