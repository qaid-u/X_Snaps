import { expect, test } from '@playwright/test'

test('effects are distinct and clean output keeps the same canvas and camera', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(String(error)))
  page.on('console', entry => { if (entry.type() === 'error') errors.push(entry.text()) })
  await page.addInitScript(() => {
    const media = navigator.mediaDevices
    const acquire = media.getUserMedia.bind(media)
    let cameraCalls = 0
    Object.defineProperty(window, 'cameraCalls', { get: () => cameraCalls })
    media.getUserMedia = request => {
      if (request?.video) cameraCalls++
      return acquire(request)
    }
  })
  await page.goto('/?benchmark')
  await expect(page.getByText('Demo ready')).toBeVisible()
  const hashes = await page.evaluate(async () => {
    const { effects } = await import('/src/effects.ts' as string) as typeof import('../src/effects')
    const engine = window.snapBenchmark!
    return effects.map(({ id }) => {
      engine.select(id)
      return engine.sampleAt(4)
    })
  })
  expect(new Set(hashes).size).toBe(hashes.length)
  await page.getByRole('checkbox', { name: 'Hand tracking' }).uncheck()
  await page.getByRole('button', { name: 'Start camera' }).click()
  await expect(page.getByText('Physical camera active')).toBeVisible()
  const initial = await page.evaluate(() => window.snapBenchmark!.snapshot().programs)
  const canvas = await page.locator('canvas').elementHandle()
  const track = await page.evaluateHandle(() => (window.snapBenchmark!.camera.video.srcObject as MediaStream).getVideoTracks()[0])
  await page.getByRole('button', { name: 'Clean OBS output' }).click()
  await expect(page).toHaveTitle('SNAP//REALITY — OBS OUTPUT')
  await expect(page.getByRole('button')).toHaveCount(0)
  expect(await canvas?.evaluate(element => document.querySelector('canvas') === element)).toBe(true)
  const before = await page.evaluate(() => window.snapBenchmark!.effect)
  await page.waitForTimeout(450)
  await page.keyboard.press('Space')
  await expect.poll(() => page.evaluate(() => window.snapBenchmark!.effect)).not.toBe(before)
  for (let i = 0; i < 10; i++) await page.keyboard.press('Space')
  expect(await page.evaluate(() => Reflect.get(window, 'cameraCalls'))).toBe(1)
  expect(await page.evaluate(() => window.snapBenchmark!.snapshot().programs)).toBe(initial)
  expect(await track.evaluate(value => value.readyState)).toBe('live')
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Stop camera' }).click()
  expect(await track.evaluate(value => value.readyState)).toBe('ended')
  expect(errors).toEqual([])
})

test('camera permission failure keeps effects available', async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('Denied', 'NotAllowedError'))
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Start camera' }).click()
  await expect(page.getByRole('status')).toContainText('Camera unavailable')
  await page.getByRole('button', { name: 'Next effect' }).click()
  await expect(page.getByRole('button', { name: '02 Comic Book' })).toHaveAttribute('aria-pressed', 'true')
})
