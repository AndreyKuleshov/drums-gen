// Headless smoke + screenshots for the drum-gen app.
// Spawns backend + frontend, drives the UI in Chromium, writes screenshots.
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BACK = 8020
const FRONT = 5180
const OUT = process.env.SHOOT_OUT || '/tmp/drumgen-shots'
mkdirSync(OUT, { recursive: true })

const procs = []
function run(cmd, args, cwd, env) {
  const p = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, stdio: 'ignore' })
  procs.push(p)
  return p
}
function cleanup() {
  for (const p of procs) try { p.kill('SIGKILL') } catch {}
}

async function waitFor(url, ms = 30000) {
  const end = Date.now() + ms
  while (Date.now() < end) {
    try {
      const r = await fetch(url)
      if (r.ok || r.status === 404) return true
    } catch {}
    await new Promise((r) => setTimeout(r, 400))
  }
  throw new Error(`timeout waiting for ${url}`)
}

const repo = new URL('../..', import.meta.url).pathname

try {
  run('uv', ['run', 'uvicorn', 'drumgen.api:app', '--port', String(BACK)], `${repo}/backend`)
  run('npm', ['run', 'dev', '--', '--port', String(FRONT), '--host'], `${repo}/frontend`, {
    VITE_API_BASE: `http://localhost:${BACK}`,
  })
  await waitFor(`http://localhost:${BACK}/rudiments`)
  await waitFor(`http://localhost:${FRONT}/`)

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } })
  const errors = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(String(e)))

  await page.goto(`http://localhost:${FRONT}/`, { waitUntil: 'networkidle' })
  await page.screenshot({ path: `${OUT}/01-empty.png` })

  // First Generate must render on the FIRST click.
  await page.getByRole('button', { name: 'Generate' }).click()
  await page.waitForFunction(
    () => document.querySelectorAll('.score svg path').length > 10,
    { timeout: 8000 },
  )
  await page.waitForTimeout(700)
  await page.screenshot({ path: `${OUT}/02-straight.png` })
  const notesAfterFirst = await page.evaluate(
    () => document.querySelectorAll('.score svg path').length,
  )

  // Authentic feel.
  await page.getByRole('radio', { name: 'Authentic' }).click()
  await page.getByRole('button', { name: 'Generate' }).click()
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${OUT}/03-authentic.png` })

  // Mixed feel.
  await page.getByRole('radio', { name: 'Mixed' }).click()
  await page.getByRole('button', { name: 'Generate' }).click()
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${OUT}/04-mixed.png` })

  // Pro difficulty, straight, 4 bars — regenerate a few times to surface flams/drags.
  await page.getByRole('radio', { name: 'Pro' }).click()
  await page.getByRole('radio', { name: 'Straight' }).click()
  await page.getByRole('button', { name: 'Increase Number of bars' }).click()
  await page.getByRole('button', { name: 'Increase Number of bars' }).click()
  for (let t = 0; t < 5; t++) {
    await page.getByRole('button', { name: 'Generate' }).click()
    await page.waitForTimeout(600)
    await page.locator('.screen').first().screenshot({ path: `${OUT}/07-pro-${t}.png` })
  }

  // Triplet feel — check tuplet brackets on one level + accents above them.
  await page.getByRole('radio', { name: 'Triplet' }).click()
  await page.getByRole('button', { name: 'Generate' }).click()
  await page.waitForTimeout(700)
  await page.locator('.screen').first().screenshot({ path: `${OUT}/08-triplet.png` })

  // Transport close-up (new controls: pattern cluster | metronome + subdivision).
  const transport = page.locator('.transport').first()
  await transport.screenshot({ path: `${OUT}/06-transport.png` })

  // Mobile width.
  await page.setViewportSize({ width: 390, height: 850 })
  await page.waitForTimeout(300)
  await page.screenshot({ path: `${OUT}/05-mobile.png`, fullPage: true })

  await browser.close()
  console.log(JSON.stringify({ ok: true, notesAfterFirst, errors }, null, 2))
} catch (e) {
  console.log(JSON.stringify({ ok: false, error: String(e) }))
  process.exitCode = 1
} finally {
  cleanup()
}
