import { existsSync } from 'node:fs'
import { expect, test } from '@playwright/test'

test('four scopes produce different pixels with the device-free fixture', async ({ page }) => {
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  const hashes = await page.evaluate(() => {
    const engine = window.snapBenchmark!
    engine.select(2)
    return [0, 1, 2, 3].map(scope => {
      engine.setScope(scope)
      return engine.sampleAt(4)
    })
  })
  expect(new Set(hashes).size).toBe(4)
})

test('the local selfie model produces masks without replacing the synthetic camera', async ({ page }) => {
  test.skip(!existsSync('public/models/selfie_segmenter_landscape.tflite'), 'Run npm run setup:models.')
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  await page.getByRole('button', { name: 'Start camera' }).click()
  await expect(page.getByRole('status')).toHaveText('Physical camera active')
  const stream = await page.evaluateHandle(() => window.snapBenchmark!.camera.video.srcObject)
  await page.getByRole('combobox', { name: 'Effect scope' }).selectOption('3')
  await expect(page.getByText('Person mask active')).toBeVisible({ timeout: 15000 })
  const result = await page.evaluate(() => window.snapBenchmark!.snapshot())
  expect(result.segmentation.count).toBeGreaterThan(0)
  expect(await stream.evaluate(value => value === window.snapBenchmark!.camera.video.srcObject)).toBe(true)
  await page.getByRole('combobox', { name: 'Effect scope' }).selectOption('0')
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.snapshot().maskStatus)).toBe('Off')
})

test('a missing segmentation asset leaves the selected effect and camera running', async ({ page }) => {
  await page.route('**/models/selfie_segmenter_landscape.tflite', route => route.fulfill({ status: 404 }))
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  await page.getByRole('button', { name: 'Start camera' }).click()
  await expect(page.getByRole('status')).toHaveText('Physical camera active')
  await page.getByRole('combobox', { name: 'Effect scope' }).selectOption('1')
  await expect(page.getByText('Whole scene while mask unavailable. Unavailable.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: '02 Comic Book' }).click()
  await expect(page.getByRole('button', { name: '02 Comic Book' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: 'Stop camera' })).toBeVisible()
})
