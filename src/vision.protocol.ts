import type { Hand } from './snap'

export type VisionRequest = { type: 'init'; assets: string; model: string } |
  { type: 'frame'; bitmap: ImageBitmap; at: number }

export type VisionResponse = { type: 'ready' } | { type: 'error'; message: string } |
  { type: 'result'; at: number; inferenceMs: number; hand: Hand | null }
