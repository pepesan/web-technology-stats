// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En desarrollo (`npm run dev`) /api se redirige al servidor FastAPI.
export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { environment: 'jsdom', include: ['tests/**/*.test.js'] },
})
