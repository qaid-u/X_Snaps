import { defineConfig } from '@playwright/test'

export default defineConfig({ testDir: './e2e', testMatch: '*.desktop.ts', workers: 1, timeout: 45_000 })
