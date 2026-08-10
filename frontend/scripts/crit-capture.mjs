// Capture the auth + account surfaces (desktop + mobile + key states) for the
// impeccable critique. Backend runs with email disabled + a debug file so the
// verification token can be read from disk.
import { mkdirSync, readFileSync } from 'node:fs'
import { chromium } from 'playwright'

const FRONT = 'http://localhost:5173'
const OUT = process.env.SHOOT_OUT || '/tmp/crit'
const MAIL = process.env.MAILFILE
mkdirSync(OUT, { recursive: true })

function token(marker) {
  const t = readFileSync(MAIL, 'utf-8')
  const line = t.split('\n').reverse().find((l) => l.includes(marker) && l.includes('token='))
  return new URL(line.trim()).searchParams.get('token')
}
const shot = (page, name) => page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true })

const browser = await chromium.launch()
const desk = { width: 1200, height: 900 }
const mob = { width: 390, height: 844 }

async function newPage(vp) {
  const p = await browser.newPage({ viewport: vp })
  return p
}

const email = `crit_${Date.now()}@example.com`
const pw = 'sup3r-secret-pw'

// --- Desktop empty states ---
let p = await newPage(desk)
await p.goto(`${FRONT}/login`, { waitUntil: 'networkidle' })
await shot(p, 'd-login')
await p.goto(`${FRONT}/register`, { waitUntil: 'networkidle' })
await shot(p, 'd-register')
await p.goto(`${FRONT}/forgot`, { waitUntil: 'networkidle' })
await shot(p, 'd-forgot')

// --- Real registration → verify → account ---
await p.goto(`${FRONT}/register`, { waitUntil: 'networkidle' })
await p.locator('#name').fill('Jordan Beat')
await p.locator('#email').fill(email)
await p.locator('#password').fill(pw)
await p.getByRole('button', { name: 'Create account' }).click()
await p.getByText('Check your inbox').waitFor({ timeout: 8000 })
await shot(p, 'd-register-sent')
await new Promise((r) => setTimeout(r, 400))
await p.goto(`${FRONT}/verify?token=${token('/verify')}`, { waitUntil: 'networkidle' })
await p.getByText('Email confirmed', { exact: false }).waitFor({ timeout: 8000 })
await shot(p, 'd-verify-ok')
await p.waitForURL('**/account', { timeout: 8000 })
await shot(p, 'd-account-empty')

// AuthNav menu open
await p.locator('.authnav__trigger').click()
await p.locator('.authnav__pop').waitFor({ timeout: 4000 })
await shot(p, 'd-authnav-open')
await p.keyboard.press('Escape')
await p.locator('body').click({ position: { x: 5, y: 5 } })

// Generate + like on the generator
await p.goto(`${FRONT}/`, { waitUntil: 'networkidle' })
await p.getByRole('button', { name: 'Generate' }).click()
await p.waitForFunction(() => document.querySelectorAll('.score svg path').length > 5, {
  timeout: 8000,
})
await shot(p, 'd-generator-like')
await p.getByRole('button', { name: 'Save', exact: false }).click()
await p.getByText('Saved', { exact: true }).waitFor({ timeout: 8000 })

// Account with a favorite + edit profile
await p.goto(`${FRONT}/account`, { waitUntil: 'networkidle' })
await p.locator('.fave').first().waitFor({ timeout: 8000 })
await shot(p, 'd-account-full')

// Reset flow: forgot -> reset page -> reuse-password error
await p.locator('.authnav__trigger').click()
await p.getByRole('menuitem', { name: 'Sign out' }).click()
await p.waitForURL(`${FRONT}/`, { timeout: 8000 })
await p.goto(`${FRONT}/forgot`, { waitUntil: 'networkidle' })
await p.locator('#email').fill(email)
await p.getByRole('button', { name: 'Send reset link' }).click()
await p.getByText('Check your inbox').waitFor({ timeout: 8000 })
await shot(p, 'd-forgot-done')
await new Promise((r) => setTimeout(r, 400))
await p.goto(`${FRONT}/reset?token=${token('/reset')}`, { waitUntil: 'networkidle' })
await shot(p, 'd-reset')
await p.locator('#password').fill(pw) // reuse current password -> error
await p.getByRole('button', { name: 'Save password' }).click()
await p.getByText('recently', { exact: false }).waitFor({ timeout: 8000 })
await shot(p, 'd-reset-reuse-error')

await p.close()

// --- Mobile ---
let m = await newPage(mob)
await m.goto(`${FRONT}/login`, { waitUntil: 'networkidle' })
await shot(m, 'm-login')
await m.goto(`${FRONT}/register`, { waitUntil: 'networkidle' })
await shot(m, 'm-register')
// login on mobile then account
await m.goto(`${FRONT}/login`, { waitUntil: 'networkidle' })
await m.locator('#email').fill(email)
await m.locator('#password').fill(pw)
await m.getByRole('button', { name: 'Sign in' }).click()
await m.waitForURL('**/account', { timeout: 8000 })
await m.locator('.fave').first().waitFor({ timeout: 8000 })
await shot(m, 'm-account')
await m.close()

await browser.close()
console.log('captured to', OUT)
