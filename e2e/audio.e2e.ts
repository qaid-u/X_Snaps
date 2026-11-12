import { expect, test } from '@playwright/test'

test('the microphone is separately acquired and released', async ({ page, context }) => {
  await context.grantPermissions(['microphone', 'camera'])
  await page.addInitScript(() => {
    const acquire = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
    let track: MediaStreamTrack | undefined
    Object.defineProperty(window, 'testMicTrack', { get: () => track })
    navigator.mediaDevices.getUserMedia = async request => {
      const stream = await acquire(request)
      if (request?.audio) track = stream.getAudioTracks()[0]
      return stream
    }
  })
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  await page.getByRole('combobox', { name: 'Detection mode' }).selectOption('1')
  await expect(page.getByRole('button', { name: 'Enable microphone' })).toBeVisible()
  expect(await page.evaluate(() => Reflect.get(window, 'testMicTrack'))).toBeUndefined()
  await page.getByRole('button', { name: 'Enable microphone' }).click()
  await expect(page.getByRole('button', { name: 'Disable microphone' })).toBeVisible()
  expect(await page.evaluate(() => Reflect.get(window, 'testMicTrack').readyState)).toBe('live')
  await page.getByRole('button', { name: 'Disable microphone' }).click()
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'testMicTrack').readyState)).toBe('ended')
  await expect(page.getByText('Using visual detection', { exact: false })).toBeVisible()
})
