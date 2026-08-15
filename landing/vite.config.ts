import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Static marketing site for Voxa. Builds to dist/ for any CDN (S3+CloudFront,
// Vercel, Netlify…). In dev it proxies /api → the backend so the contact form
// works locally without CORS. In prod, set VITE_API_BASE to the backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    // +01 = secondary frontend in voxa's 53xx block (~/Dev/PORTS.md), the role
    // reserved for a landing/admin site. 5173 was Vite's default and clashed
    // with both clocky and voxa's own app frontend.
    port: 5301,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5310', // +10 = backend
        changeOrigin: true,
      },
    },
  },
  // `vite preview` serves the production build; same role, same port (dev and
  // preview never run at once). Without this it would default to 4173, outside
  // the block.
  preview: {
    port: 5301,
    strictPort: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
