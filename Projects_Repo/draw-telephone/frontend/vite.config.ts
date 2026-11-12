import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8099'
  const wsTarget = backendTarget.replace(/^http/, 'ws')

  return {
    plugins: [react()],
    server: {
      port: 5199,
      proxy: {
        '/api': { target: backendTarget, changeOrigin: true },
        '/uploads': { target: backendTarget, changeOrigin: true },
        '/ws': { target: wsTarget, ws: true, changeOrigin: true },
      },
    },
  }
})
