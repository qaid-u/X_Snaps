import { cp, mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'
import { createRequire } from 'node:module'
import process from 'node:process'

if (process.platform !== 'win32') throw new Error('Run Windows packaging on Windows.')
const require = createRequire(import.meta.url)
const runtime = require('electron')
const { version } = JSON.parse(await readFile('package.json', 'utf8'))
const output = `release/SNAP-REALITY-${version}-win-${process.arch}-${Date.now()}`
const app = output + '/resources/app'
await mkdir(output, { recursive: true })
await cp(dirname(runtime), output, { recursive: true })
await rename(output + '/electron.exe', output + '/SNAP-REALITY.exe')
await mkdir(app, { recursive: true })
await cp('dist', app + '/dist', { recursive: true })
await cp('electron', app + '/electron', { recursive: true })
await cp('LICENSE.md', app + '/LICENSE.md')
await cp('LICENSE-THIRD-PARTY.md', app + '/LICENSE-THIRD-PARTY.md')
await cp('docs/licenses/MediaPipe-Apache-2.0.txt', app + '/MediaPipe-Apache-2.0.txt')
for (const path of ['react/LICENSE', 'react-dom/LICENSE', 'three/LICENSE']) {
  await cp('node_modules/' + path, app + '/' + path.replace('/', '-'))
}
await writeFile(app + '/package.json', JSON.stringify({
  name: 'snap-reality', productName: 'SNAP//REALITY', version, main: 'electron/main.cjs',
}, null, 2))
globalThis.console.log(output + '/SNAP-REALITY.exe')
