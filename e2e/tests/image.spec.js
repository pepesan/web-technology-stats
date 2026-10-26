// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
import { expect, test } from '@playwright/test'

// Datos reales del informe 2026 (lote 1: top 1M de Tranco).
const TOTAL = '1.000.000'
const FINISHED = '851.742'

test.beforeEach(async ({ page }) => {
  page.apiCalls = []
  page.errors = []
  page.on('request', (r) => {
    if (new URL(r.url()).pathname.startsWith('/api/')) page.apiCalls.push(r.url())
  })
  page.on('pageerror', (e) => page.errors.push(e.message))
  page.on('console', (m) => m.type() === 'error' && page.errors.push(m.text()))
})

test.afterEach(async ({ page }) => {
  expect(page.errors, 'sin errores de consola ni excepciones').toEqual([])
  expect(page.apiCalls, 'el modo estático no llama a /api').toEqual([])
})

test('muestra el informe 2026 con separador de millares y sin servidor de API', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByLabel('Informe')).toHaveValue('2026')
  await expect(page.getByLabel('Informe').locator('option:checked')).toContainText('Tranco 2026')
  await expect(page.getByText('Sitios importados').locator('..')).toContainText(TOTAL)
  await expect(page.getByText('Sitios analizados', { exact: true }).locator('..')).toContainText(FINISHED)
  await expect(page.getByText('Escaneo incompleto')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Lenguajes de back' })).toBeVisible()
  await expect(page.getByText('PHP', { exact: true }).first()).toBeVisible()
})

test('el selector de sitios ofrece los cortes y carga el fichero del corte', async ({ page }) => {
  await page.goto('/')
  const top = page.getByLabel('Número de sitios')
  await expect(top.locator('option')).toHaveText(
    ['Todos', 'Top 100', 'Top 1k', 'Top 10k', 'Top 100k', 'Top 200k', 'Top 300k', 'Top 400k',
     'Top 500k', 'Top 600k', 'Top 700k', 'Top 800k', 'Top 900k', 'Top 1M'],
  )
  const cut = page.waitForResponse((r) => r.url().endsWith('/reports/2026/top-1000.json') && r.ok())
  await top.selectOption('1000')
  await cut
  await expect(page.getByText('Sitios importados').locator('..')).toContainText('1.000')
  await expect(page.getByText('Sitios importados').locator('..')).not.toContainText(TOTAL)
  expect(new URL(page.url()).searchParams.get('top')).toBe('1000')
})

test('la URL restaura informe y corte al recargar', async ({ page }) => {
  await page.goto('/?report=2026&top=10000')
  await expect(page.getByLabel('Número de sitios')).toHaveValue('10000')
  await expect(page.getByText('Sitios importados').locator('..')).toContainText('10.000')
})

test('cambia de pestaña, filtra por categoría y muestra más', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('tab', { name: /Bases de datos/ }).click()
  await expect(page.getByRole('heading', { name: 'Bases de datos' })).toBeVisible()
  await expect(page.getByText('MySQL', { exact: true }).first()).toBeVisible()

  await page.getByRole('tab', { name: /Otras tecnologías/ }).click()
  const rows = page.locator('.panel li, .panel tbody tr, .panel [role=listitem]')
  const before = await rows.count()
  await page.getByRole('button', { name: 'Mostrar más' }).click()
  await expect.poll(() => rows.count()).toBeGreaterThan(before)

  const category = page.getByLabel('Categoría')
  await category.selectOption({ index: 1 })
  await expect.poll(() => rows.count()).toBeGreaterThan(0)
})

test('sin desbordamiento horizontal y con los dos selectores visibles', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page.getByLabel('Informe')).toBeVisible()
  await expect(page.getByLabel('Número de sitios')).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
  await page.screenshot({ path: `test-results/captura-${testInfo.project.name}.png`, fullPage: true })
})

test('config.json no se cachea y la imagen sirve los informes comprimidos', async ({ request }) => {
  const config = await request.get('/config.json')
  expect(config.headers()['cache-control']).toBe('no-store')
  expect(await config.json()).toEqual({ source: 'reports' })
  const index = await request.get('/reports/index.json', { headers: { 'Accept-Encoding': 'gzip' } })
  expect(index.ok()).toBe(true)
  expect((await index.json()).reports.map((r) => r.id)).toContain('2026')
  const cut = await request.get('/reports/2026/top-all.json', { headers: { 'Accept-Encoding': 'gzip' } })
  expect(cut.headers()['content-encoding']).toBe('gzip')
})

test('el selector de ámbito cambia entre mundo y España (.es) con sus datos propios', async ({ page }) => {
  await page.goto('/')
  const scope = page.getByLabel('Ámbito')
  await expect(scope.locator('option')).toHaveText(['Mundo', 'España (.es)'])
  await expect(scope).toHaveValue('all')
  await expect(page.getByText('Sitios importados').locator('..')).toContainText(TOTAL)

  const es = page.waitForResponse((r) => r.url().endsWith('/reports/2026-es/top-all.json') && r.ok())
  await scope.selectOption('es')
  await es
  await expect(page.getByLabel('Informe')).toHaveValue('2026-es')
  await expect(page.getByText('Sitios importados').locator('..')).toContainText('5.615')
  await expect(page.getByText('Sitios analizados', { exact: true }).locator('..')).toContainText('5.264')
  await expect(page.getByText('PHP', { exact: true }).first()).toBeVisible()
  // en España el primer corte con datos suficientes es el Top 10k
  await expect(page.getByLabel('Número de sitios').locator('option')).toHaveText(
    ['Todos', 'Top 10k', 'Top 100k', 'Top 200k', 'Top 300k', 'Top 400k', 'Top 500k', 'Top 600k', 'Top 700k', 'Top 800k', 'Top 900k', 'Top 1M'],
  )
  expect(new URL(page.url()).searchParams.get('report')).toBe('2026-es')
})

test('una URL con ?report=2026-es abre directamente España', async ({ page }) => {
  await page.goto('/?report=2026-es&top=100000')
  await expect(page.getByLabel('Ámbito')).toHaveValue('es')
  await expect(page.getByLabel('Número de sitios')).toHaveValue('100000')
  await expect(page.getByText('Sitios importados').locator('..')).toContainText('548')
})
