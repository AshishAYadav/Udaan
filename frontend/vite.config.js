import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backend = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

// API and docs requests are proxied to the FastAPI backend in development.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': backend, '/docs': backend, '/redoc': backend, '/openapi.json': backend },
  },
})
