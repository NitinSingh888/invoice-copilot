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
    host: true, // listen on 0.0.0.0 so it's reachable from outside the container
    port: 5173,
    proxy: {
      '/api': {
        // In Docker compose this points at the backend service; natively it's localhost.
        target: process.env.VITE_API_PROXY || 'http://localhost:8123',
        changeOrigin: true,
      },
    },
  },
})
