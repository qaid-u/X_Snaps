import type { Hand } from './snap'

export type VisionKind = 'hand' | 'mask'
export type VisionRequest = { type: 'init'; kind: VisionKind; assets: string; model: string } |
  { type: 'frame'; bitmap: ImageBitmap; at: number }

export type VisionResult =
  | { type: 'hand'; at: number; inferenceMs: number; hand: Hand | null }
  | { type: 'mask'; at: number; inferenceMs: number; width: number; height: number; pixels: Uint8Array<ArrayBuffer> }

export type VisionResponse = { type: 'ready' } | { type: 'error'; message: string } | VisionResult
