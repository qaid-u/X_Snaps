import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { Buffer } from 'node:buffer'

const modelPath = 'public/models/hand_landmarker.task'
const checksum = 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1'
const valid = bytes => createHash('sha256').update(bytes).digest('hex') === checksum
const cached = await readFile(modelPath).catch(error => {
  if (error.code !== 'ENOENT') throw error
  return null
})
if (!cached || !valid(cached)) {
  const url = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
  const response = await globalThis.fetch(url)
  if (!response.ok) throw new Error(`Model download failed: HTTP ${response.status}`)
  const bytes = Buffer.from(await response.arrayBuffer())
  if (!valid(bytes)) throw new Error('Hand Landmarker SHA-256 mismatch.')
  await mkdir('public/models', { recursive: true })
  await writeFile(modelPath, bytes)
}
globalThis.console.log('Verified local Hand Landmarker model.')
