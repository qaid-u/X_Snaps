import { existsSync } from 'node:fs'
import { expect, test } from '@playwright/test'

test('local MediaPipe worker processes the existing synthetic camera stream', async ({ page }) => {
  test.skip(!existsSync('public/models/hand_landmarker.task'), 'Install the pinned model with npm run setup:models.')
  await page.goto('/?benchmark')
  await page.getByRole('button', { name: 'Start camera' }).click()
  await expect(page.getByRole('status')).toContainText('Physical camera active')
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.snapshot().handStatus), { timeout: 20000 })
    .toBe('Show thumb and middle finger')
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.snapshot().hand.count)).toBeGreaterThan(2)
  await page.getByRole('button', { name: 'Stop camera' }).click()
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.snapshot().handStatus)).toBe('Hand tracking off')
})

test('missing model falls back to manual switching while camera continues', async ({ page }) => {
  await page.route('**/models/hand_landmarker.task', route => route.fulfill({ status: 404 }))
  await page.goto('/?benchmark')
  await page.getByRole('button', { name: 'Start camera' }).click()
  await expect(page.getByRole('status')).toContainText('Physical camera active')
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.snapshot().handStatus)).toContain('Hand tracking unavailable')
  await page.getByRole('button', { name: 'Next effect' }).click()
  await expect(page.getByRole('button', { name: '02 Comic Book' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: 'Stop camera' })).toBeVisible()
})
