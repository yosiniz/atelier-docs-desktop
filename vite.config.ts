import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Electron üretimde index.html'i file:// ile açar; asset yolları mutlak olamaz.
  base: './',
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', globals: true },
})
