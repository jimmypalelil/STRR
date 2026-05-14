import { type Page } from '@playwright/test'

import { LoginSource } from '../enums/login-source'
import { fillBceidTotpAndContinue } from './generate-otp'
import { loadPlaywrightEnv } from './load-playwright-env'

export async function completeLogin (page: Page, loginMethod: LoginSource) {
  loadPlaywrightEnv()
  const baseUrl = process.env.NUXT_BASE_URL
  if (!baseUrl) {
    throw new Error('NUXT_BASE_URL is required for completeLogin')
  }

  await page.goto(baseUrl + 'en-CA/auth/login', { waitUntil: 'networkidle', timeout: 60_000 })

  if (loginMethod === LoginSource.IDIR) {
    const username = process.env.PLAYWRIGHT_TEST_USERNAME
    const password = process.env.PLAYWRIGHT_TEST_PASSWORD
    if (!username?.trim() || !password) {
      throw new Error('PLAYWRIGHT_TEST_USERNAME and PLAYWRIGHT_TEST_PASSWORD are required for IDIR e2e')
    }
    await page.getByRole('button', { name: 'Continue with IDIR' }).click()
    await page.locator('#user').fill(username)
    await page.getByRole('textbox', { name: 'Password' }).fill(password)
    await page.getByRole('button', { name: 'Continue' }).click()
  } else if (loginMethod === LoginSource.BCEID) {
    const username = process.env.PLAYWRIGHT_TEST_BCEID_USERNAME
    const password = process.env.PLAYWRIGHT_TEST_BCEID_PASSWORD
    if (!username?.trim() || !password) {
      throw new Error('PLAYWRIGHT_TEST_BCEID_USERNAME and PLAYWRIGHT_TEST_BCEID_PASSWORD are required for BCeID e2e')
    }
    await page.getByRole('button', { name: 'Continue with BCeID' }).click()
    await page.locator('#user').fill(username)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Continue' }).click()
    await page.waitForLoadState('networkidle', { timeout: 25_000 }).catch(() => {})
    const openPages = page.context().pages()
    const totpPage = openPages.length > 1 ? openPages[openPages.length - 1]! : page
    await fillBceidTotpAndContinue(totpPage)
  } else {
    throw new Error(`Unsupported login method: ${String(loginMethod)}`)
  }

  await page.waitForURL(baseUrl + '**')
}
