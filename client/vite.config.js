// client/vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  // Убедитесь, что base указывает на /static/
  base: '/static/', 
  build: {
    // Эта часть для продакшена, ее можно не трогать
    outDir: 'dist',
    manifest: true,
    rollupOptions: {
      input: {
        main: 'src/main.js',
      }
    },
  },
  server: {
    // Настройки для Vite Dev Server
    host: '0.0.0.0', // Слушать на всех интерфейсах
    port: 5173,
    strictPort: true, // Не занимать другой порт, если 5173 занят
  }
});