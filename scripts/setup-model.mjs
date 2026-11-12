import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { Buffer } from 'node:buffer'

const models = [
  ['hand_landmarker.task', 'hand_landmarker/hand_landmarker', 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1'],
  ['selfie_segmenter_landscape.tflite', 'image_segmenter/selfie_segmenter_landscape', '490e9ea734313e0de10fa0cd9e3c6133e36ea4db2b7a49bde9ef019f72796b8e'],
]
await mkdir('public/models', { recursive: true })
for (const [name, category, checksum] of models) {
  const modelPath = 'public/models/' + name
  const valid = bytes => createHash('sha256').update(bytes).digest('hex') === checksum
  const cached = await readFile(modelPath).catch(error => {
    if (error.code !== 'ENOENT') throw error
    return null
  })
  if (!cached || !valid(cached)) {
    const url = `https://storage.googleapis.com/mediapipe-models/${category}/float16/1/${name}`
    const response = await globalThis.fetch(url)
    if (!response.ok) throw new Error(`${name} download failed: HTTP ${response.status}`)
    const bytes = Buffer.from(await response.arrayBuffer())
    if (!valid(bytes)) throw new Error(`${name} SHA-256 mismatch.`)
    await writeFile(modelPath, bytes)
  }
  globalThis.console.log('Verified ' + name)
}
