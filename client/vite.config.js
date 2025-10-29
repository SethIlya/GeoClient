// client/vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  base: '/static/', 
  build: {
    outDir: 'dist',
    manifest: true,
    rollupOptions: {
      input: {
        main: 'src/main.js',
      }
    },
  },
  server: {
    host: '0.0.0.0', 
    port: 5173,
    strictPort: true, 
  }
});