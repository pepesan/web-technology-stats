// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
import { defineConfig } from '@playwright/test'

// E2E contra la imagen estática en ejecución (BASE_URL); usa el Chrome del sistema, sin descargar navegadores.
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  reporter: [['list']],
  outputDir: './test-results',
  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:8080',
    channel: process.env.E2E_CHANNEL || 'chrome',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'escritorio', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'movil', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
})
