import { defineConfig } from '@playwright/test'
import base from './playwright.config'

export default defineConfig({
  ...base,
  testMatch: '*.perf.ts',
  timeout: 240_000,
  use: { ...base.use, permissions: [] },
})
