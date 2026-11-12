import { spawnSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'
import process from 'node:process'

const cli = fileURLToPath(new URL('../node_modules/@playwright/test/cli.js', import.meta.url))
const result = spawnSync(process.execPath, [cli, 'test', '--config', 'playwright.perf.config.ts'], {
  env: { ...process.env, SNAP_FULL_BENCHMARK: '1' },
  stdio: 'inherit',
})
process.exitCode = result.status ?? 1
