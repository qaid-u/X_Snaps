import { expect, test } from '@playwright/test'

test('all ten warmed transitions render distinct pixels and rotation persists across reload', async ({ page }) => {
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  const hashes = await page.evaluate(() => {
    const engine = window.snapBenchmark!
    return Array.from({ length: 11 }, (_, style) => {
      engine.setTransition({ style, duration: 240, strength: .8, reducedFlash: true, eased: true })
      engine.select(2)
      return engine.sampleAt(4,.65)
    })
  })
  expect(new Set(hashes).size).toBe(11)
  await page.getByText('Effect rotation and presets', { exact: true }).click()
  await page.getByRole('combobox', { name: 'Effect in rotation' }).selectOption('2')
  await page.getByRole('button', { name: 'Move earlier' }).click()
  await expect(page.getByText('Position 1 of 20')).toBeVisible()
  await page.reload()
  await page.waitForFunction(() => !!window.snapBenchmark)
  await page.getByRole('button', { name: 'Next effect' }).click()
  await expect(page.getByRole('button', { name: '02 Comic Book' })).toHaveAttribute('aria-pressed', 'true')
})
