import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/orgs': 'http://localhost:8000',
      '/roles': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/endpoints': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  build: {
    outDir: '../auth-service/static',
    emptyOutDir: true,
  },
})
