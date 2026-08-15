import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // voxa's reserved block is 53xx (~/Dev/PORTS.md): +00 = primary frontend.
    // strictPort makes a collision FAIL instead of letting Vite hop silently to
    // 5301 — a silent hop is how the previous clash with clocky went unnoticed,
    // and it would also steal the landing's port.
    port: 5300,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5310', // +10 = backend
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
