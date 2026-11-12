import { copyFile, mkdir, readdir } from 'node:fs/promises'
import { build } from 'vite'

await mkdir('public/vision', { recursive: true })
await mkdir('public/models', { recursive: true })
const wasm = 'node_modules/@mediapipe/tasks-vision/wasm'
for (const file of await readdir(wasm)) await copyFile(wasm + '/' + file, 'public/vision/' + file)
try {
  await copyFile('assets/models/hand_landmarker.task', 'public/models/hand_landmarker.task')
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}
await build({
  configFile: false,
  publicDir: false,
  logLevel: 'warn',
  build: {
    outDir: 'public/vision',
    emptyOutDir: false,
    lib: { entry: 'src/vision.worker.ts', name: 'SnapVision', formats: ['iife'], fileName: () => 'hand-worker.js' },
  },
})
