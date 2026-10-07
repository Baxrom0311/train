import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  // dev: backend alohida portda; prod'da nginx /api/ ni proksilaydi
  server: {
    proxy: { '/api': { target: process.env.VITE_API_TARGET ?? 'http://localhost:8000', changeOrigin: true } },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})