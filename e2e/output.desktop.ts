import { _electron as electron, expect, test } from '@playwright/test'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

test('native output owns camera and renderer while controls can close and reopen', async () => {
  const packaged = process.env.SNAP_PACKAGED_EXE
  const fakeMedia = ['--use-fake-device-for-media-stream', '--enable-unsafe-swiftshader']
  const app = await electron.launch(packaged
    ? { executablePath: resolve(packaged), args: fakeMedia }
    : { executablePath: require('electron') as string, args: [resolve('.'), ...fakeMedia] })
  try {
    await expect.poll(() => app.windows().length).toBe(2)
    const pages = app.windows()
    const windows = await Promise.all(pages.map(async page => {
      await page.waitForFunction(() => !!window.snapDesktop)
      return { page, role: await page.evaluate(() => window.snapDesktop?.role) }
    }))
    const outputPage = windows.find(item => item.role === 'output')!.page
    const control = windows.find(item => item.role === 'control')!.page
    await expect(control.getByRole('status')).toHaveText('Demo ready')
    await expect(outputPage.locator('canvas')).toHaveCount(1)
    await expect(outputPage.getByRole('button')).toHaveCount(0)
    await expect(control.locator('canvas')).toHaveCount(0)
    expect(await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().map(window => window.getTitle())))
      .toContain('SNAP//REALITY — OBS OUTPUT')
    const invalid = await control.evaluate(async () => {
      const bridge = window.snapDesktop
      return bridge?.role === 'control' && bridge.command({ action: 'effect', value: 999 })
    })
    expect(invalid).toBe(false)
    await control.getByRole('button', { name: 'Start camera' }).click()
    await expect(control.getByRole('status')).toHaveText('Physical camera active')
    if (existsSync('public/models/hand_landmarker.task')) {
      await expect(control.getByText('Show thumb and middle finger')).toBeVisible()
    }
    await control.getByRole('button', { name: 'Next effect' }).click()
    await expect(control.getByRole('button', { name: '01 2D / 3D Style' })).toHaveAttribute('aria-pressed', 'true')
    await control.close()
    await expect(outputPage.locator('canvas')).toHaveCount(1)
    await outputPage.keyboard.press('Space')
    const reopened = app.waitForEvent('window', { timeout: 6000 })
    await outputPage.keyboard.press('Control+Shift+O')
    const newControl = await reopened
    await expect(newControl.getByRole('status')).toHaveText('Physical camera active')
    await expect(newControl.getByRole('button', { name: 'Stop camera' })).toBeVisible()
    await newControl.getByRole('button', { name: 'Stop camera' }).click()
    await expect(newControl.getByRole('status')).toContainText('Camera stopped')
  } finally {
    await app.close()
  }
})
