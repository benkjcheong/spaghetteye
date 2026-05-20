import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwind from '@tailwindcss/vite';

export default defineConfig({
  plugins: [vue(), tailwind()],
  server: {
    host: true,
    allowedHosts: 'all',
    port: 1026,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:1027',
        changeOrigin: true,
      },
    },
  },
});
