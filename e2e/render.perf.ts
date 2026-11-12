import { expect, test } from '@playwright/test'
import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { cpus, release } from 'node:os'
import { effects } from '../src/effects'
import type { Engine } from '../src/Engine'

type Stats = ReturnType<Engine['snapshot']>
const full = process.env.SNAP_FULL_BENCHMARK === '1'
const adopt = process.env.SNAP_WRITE_BASELINE === '1'
const reportDir = 'reports/performance'

test('animated GPU fixture meets its compatible performance baseline', async ({ page, browser }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(String(error)))
  page.on('console', entry => { if (entry.type() === 'error') errors.push(entry.text()) })
  await page.goto('/?benchmark')
  await page.waitForFunction(() => !!window.snapBenchmark)
  await page.evaluate(() => window.snapBenchmark!.setProfile(1, true))
  await page.waitForTimeout(900)
  const rows: Array<{ label: string; id: number; stats: Stats }> = []
  for (const { label, id } of effects) {
    await page.evaluate(value => {
      const engine = window.snapBenchmark!
      engine.metrics.reset()
      engine.select(value)
    }, id)
    await page.waitForFunction(target => window.snapBenchmark!.metrics.render.count >= target,
      full ? 120 : 48, { polling: 100, timeout: 12000 })
    rows.push({ label, id, stats: await page.evaluate(() => window.snapBenchmark!.snapshot()) })
  }
  const stress = await page.evaluate(async ids => {
    const engine = window.snapBenchmark!
    engine.metrics.reset()
    for (const id of [...ids, ...ids]) {
      engine.select(id)
      await new Promise(resolve => setTimeout(resolve, 95))
    }
    return engine.snapshot()
  }, effects.map(item => item.id))
  const settings = {
    fixture: 'procedural-demo-v1', mode: full ? 'full' : 'smoke', os: process.platform + ' ' + release(),
    cpu: cpus()[0]?.model, browser: browser.version(), gpu: rows[0].stats.gpuName, width: 1280, height: 720,
    fpsTarget: 30, profile: 'Balanced locked', source: 'procedural shader', obs: 'not running',
  }
  const startups = [{ initialMs: rows[0].stats.initialMs, warmupMs: rows[0].stats.warmupMs }]
  const report = { at: new Date().toISOString(), settings, rows, stress, errors, startups }
  await mkdir(reportDir, { recursive: true })
  const baseFile = `${reportDir}/baseline-${settings.mode}.json`
  const baseline = await readFile(baseFile, 'utf8').then(value => JSON.parse(value) as typeof report, error => {
    if (error.code !== 'ENOENT') throw error
    return null
  })
  const comparable = !!baseline && JSON.stringify(baseline.settings) === JSON.stringify(settings)
  const regression: string[] = []
  if (comparable && !adopt) {
    const sameCarousel = JSON.stringify(baseline.rows.map(row => row.id)) === JSON.stringify(rows.map(row => row.id))
    for (const row of [...rows, { label: 'Carousel stress', id: -1, stats: stress }]) {
      const prior = row.id === -1 ? sameCarousel && baseline.stress : baseline.rows.find(old => old.id === row.id)?.stats
      if (!prior) continue
      const p95 = row.stats.render.p95 ?? Infinity
      const priorP95 = prior.render.p95 ?? Infinity
      if (p95 > priorP95 * 1.10) regression.push(`${row.label}: interval p95 ${p95.toFixed(1)} vs ${priorP95.toFixed(1)} ms`)
      if (row.stats.longFrameRatio > prior.longFrameRatio + .10) regression.push(`${row.label}: long frame ratio increased by >10 percentage points`)
    }
    const oldPreview = baseline.rows[0].stats.initialMs ?? baseline.rows[0].stats.warmupMs
    const oldWarmup = baseline.rows[0].stats.warmupMs
    const slowPreview = (time: number) => time > Math.max(oldPreview * 2, oldPreview + 150)
    const slowCatalog = (time: number) => sameCarousel && time > Math.max(oldWarmup * 2, oldWarmup + 150)
    if (slowPreview(startups[0].initialMs) || slowCatalog(startups[0].warmupMs)) {
      // Confirm a startup outlier in two fresh application instances and retain every measurement.
      for (let run = 0; run < 2; run++) {
        await page.reload()
        await page.waitForFunction(() => !!window.snapBenchmark)
        startups.push(await page.evaluate(() => {
          const { initialMs, warmupMs } = window.snapBenchmark!
          return { initialMs, warmupMs }
        }))
      }
      if (startups.filter(sample => slowPreview(sample.initialMs)).length >= 2) regression.push('First playable frame repeatedly exceeded startup tolerance')
      if (startups.filter(sample => slowCatalog(sample.warmupMs)).length >= 2) regression.push('Catalog warm-up repeatedly exceeded baseline tolerance')
    }
  }
  const comparison = adopt ? 'Baseline requested' : comparable ? 'Comparable baseline' : 'No compatible baseline'
  const path = `${reportDir}/run-${Date.now()}-${settings.mode}`
  await writeFile(path + '.json', JSON.stringify({ ...report, comparison, regression }, null, 2) + '\n')
  const table = ['| Effect | Render FPS | Interval p95 ms | CPU p95 ms | GPU p95 ms | Trigger-to-draw p95 ms |',
    '| --- | ---: | ---: | ---: | ---: | ---: |']
  for (const { label, stats } of [...rows, { label: 'Carousel stress', stats: stress }]) {
    table.push(`| ${label} | ${[stats.renderFps, stats.render.p95, stats.cpu.p95, stats.gpu.p95, stats.latency.p95].map(value => value?.toFixed(2) ?? '—').join(' | ')} |`)
  }
  await writeFile(path + '.md', ['# Animated render benchmark', '', settings.gpu, '',
    `First draw ${startups.map(sample => sample.initialMs.toFixed(1)).join(', ')} ms. Full catalog warm-up ${startups.map(sample => sample.warmupMs.toFixed(1)).join(', ')} ms. ${comparison}.`, '', ...table, '', ...regression, ''].join('\n'))
  for (const old of (await readdir(reportDir)).filter(name => /^run-\d+-(smoke|full)\.(json|md)$/.test(name)).sort().slice(0, -20)) {
    await rm(`${reportDir}/${old}`)
  }
  console.log(comparison, '\n' + table.join('\n'), '\nReport', path)
  expect(errors).toEqual([])
  expect(regression).toEqual([])
  for (const { stats } of rows) {
    expect(stats.render.count).toBeGreaterThanOrEqual(full ? 120 : 48)
    expect(stats.programs).toBe(rows[0].stats.programs)
    expect(stats.textures).toBe(rows[0].stats.textures)
  }
  expect(stress.programs).toBe(rows[0].stats.programs)
  expect(stress.textures).toBe(rows[0].stats.textures)
  expect(stress.latency.p95 ?? Infinity).toBeLessThanOrEqual(100)
  if (adopt) await writeFile(baseFile, JSON.stringify(report, null, 2) + '\n')
})
