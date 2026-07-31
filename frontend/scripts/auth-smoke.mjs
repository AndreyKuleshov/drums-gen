// E2E smoke for the auth flow: spins up backend (dev DB, email→file) + frontend
// (with the /api proxy), then drives register → verify → login → account and
// screenshots each step.
import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync, rmSync } from 'node:fs'
import { chromium } from 'playwright'

const BACK = 8000
const FRONT = 5199
const OUT = process.env.SHOOT_OUT || '/tmp/auth-smoke'
const MAILFILE = `${OUT}/mail.log`
mkdirSync(OUT, { recursive: true })
try {
  rmSync(MAILFILE)
} catch {}

const repo = new URL('../..', import.meta.url).pathname
const procs = []
const run = (cmd, args, cwd, env) => {
  const p = spawn(cmd, args, { cwd, env: { ...process.env, ...env }, stdio: 'ignore' })
  procs.push(p)
  return p
}
const cleanup = () => procs.forEach((p) => { try { p.kill('SIGKILL') } catch {} })

async function waitFor(url, ms = 45000) {
  const end = Date.now() + ms
  while (Date.now() < end) {
    try {
      const r = await fetch(url)
      if (r.ok || r.status === 404 || r.status === 401) return
    } catch {}
    await new Promise((r) => setTimeout(r, 400))
  }
  throw new Error(`timeout waiting for ${url}`)
}

function tokenFromMail(marker) {
  const text = readFileSync(MAILFILE, 'utf-8')
  const line = text.split('\n').reverse().find((l) => l.includes(marker) && l.includes('token='))
  if (!line) throw new Error(`no ${marker} link in mail log`)
  return new URL(line.trim()).searchParams.get('token')
}

try {
  run('uv', ['run', 'uvicorn', 'drumgen.api:app', '--port', String(BACK)], `${repo}/backend`, {
    DATABASE_URL: 'postgresql+asyncpg://drumgen:drumgen@localhost:55432/drumgen',
    PUBLIC_BASE_URL: `http://localhost:${FRONT}`,
    EMAIL_ENABLED: 'false',
    EMAIL_DEBUG_FILE: MAILFILE,
    COOKIE_SECURE: 'false',
  })
  run('npm', ['run', 'dev', '--', '--port', String(FRONT), '--host'], `${repo}/frontend`, {
    VITE_API_BASE: '/api',
  })
  await waitFor(`http://localhost:${BACK}/rudiments`)
  await waitFor(`http://localhost:${FRONT}/`)

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1100, height: 860 } })
  page.setDefaultTimeout(10000)
  const errors = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(String(e)))

  const email = `smoke_${Date.now()}@example.com`
  const password = 'sup3r-secret-pw'

  // Register.
  await page.goto(`http://localhost:${FRONT}/register`, { waitUntil: 'networkidle' })
  await page.locator('#name').fill('Smoke Tester')
  await page.locator('#email').fill(email)
  await page.locator('#password').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await page.getByText('Check your inbox').waitFor({ timeout: 8000 })
  await page.screenshot({ path: `${OUT}/01-registered.png` })

  // Verify via the emailed link.
  await new Promise((r) => setTimeout(r, 400))
  const verifyToken = tokenFromMail('/verify')
  await page.goto(`http://localhost:${FRONT}/verify?token=${verifyToken}`, {
    waitUntil: 'networkidle',
  })
  await page.getByText('Email confirmed', { exact: false }).waitFor({ timeout: 8000 })
  await page.screenshot({ path: `${OUT}/02-verified.png` })

  // Verify auto-redirects to /account (signed in).
  await page.waitForURL('**/account', { timeout: 8000 })
  await page.getByText('Smoke Tester').first().waitFor({ timeout: 8000 })
  await page.screenshot({ path: `${OUT}/03-account.png` })

  // Log out, then log back in.
  await page.getByRole('button', { name: 'Smoke Tester' }).click()
  await page.getByRole('menuitem', { name: 'Sign out' }).click()
  await page.waitForURL(`http://localhost:${FRONT}/`, { timeout: 8000 })

  await page.goto(`http://localhost:${FRONT}/login`, { waitUntil: 'networkidle' })
  await page.locator('#email').fill(email)
  await page.locator('#password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.waitForURL('**/account', { timeout: 8000 })
  await page.screenshot({ path: `${OUT}/04-relogin.png` })

  // Guard: hitting /account after logout should bounce to /login.
  await page.getByRole('button', { name: 'Smoke Tester' }).click()
  await page.getByRole('menuitem', { name: 'Sign out' }).click()
  await page.waitForURL(`http://localhost:${FRONT}/`, { timeout: 8000 })
  await page.goto(`http://localhost:${FRONT}/account`, { waitUntil: 'networkidle' })
  const guardedTo = new URL(page.url()).pathname

  await browser.close()
  console.log(JSON.stringify({ ok: true, email, guardedTo, errors }, null, 2))
} catch (e) {
  console.log(JSON.stringify({ ok: false, error: String(e) }))
  process.exitCode = 1
} finally {
  cleanup()
}
