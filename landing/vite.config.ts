import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Static marketing site for Voxa. Builds to dist/ for any CDN (S3+CloudFront,
// Vercel, Netlify…). In dev it proxies /api → the backend so the contact form
// works locally without CORS. In prod, set VITE_API_BASE to the backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
