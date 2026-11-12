import { readFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'

test('PNG and recorded video come from the continuing clean canvas', async ({ page }) => {
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  await page.getByRole('button', { name: '02 Comic Book' }).click()
  const stillPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Save PNG' }).click()
  const still = await stillPromise
  const png = await readFile(await still.path())
  expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a')
  expect(png.readUInt32BE(16)).toBe(1280)
  expect(png.readUInt32BE(20)).toBe(720)

  await page.getByRole('button', { name: 'Record video' }).click()
  await expect(page.getByRole('button', { name: 'Stop recording' })).toBeVisible()
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Resume', exact: true }).click()
  await page.getByRole('button', { name: 'Clean OBS output' }).click()
  await expect(page.getByRole('button')).toHaveCount(0)
  await page.waitForTimeout(500)
  await page.keyboard.press('Space')
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.effect)).toBe(3)
  await page.waitForTimeout(700)
  await page.keyboard.press('Escape')
  const videoPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Stop recording' }).click()
  const video = await videoPromise
  const recording = await readFile(await video.path())
  expect(recording.length).toBeGreaterThan(1000)
  expect(recording.subarray(0, 4).toString('hex')).toBe('1a45dfa3')
  await expect(page.getByRole('button', { name: 'Record video' })).toBeVisible()
})
