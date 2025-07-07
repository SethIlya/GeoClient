// vite.config.js

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [
    vue(),
  ],

  // --- УДАЛЯЕМ `base` ---
  // `base` по умолчанию ('/'), что нам и нужно, когда пути в rollupOptions настроены.

  // Настройки для сервера разработки (остаются без изменений, на сборку не влияют)
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  },

  // --- ИЗМЕНЯЕМ ВЕСЬ БЛОК `build` ---
  // Настройки для сборки проекта (команда `npm run build`)
  build: {
    // Папка, куда будут складываться собранные файлы.
    outDir: 'dist',
    // Очищать папку `dist` перед каждой сборкой.
    emptyOutDir: true,
    
    // Прямо указываем Rollup, как называть файлы и куда их класть.
    // Это ключевое изменение, которое убирает папку `assets`.
    rollupOptions: {
      output: {
        // JS-файл точки входа (например, main.js) будет называться index.js
        entryFileNames: `index.js`,
        // Остальные JS-файлы (если они есть) будут называться по своим именам
        chunkFileNames: `[name].js`,
        // CSS и другие файлы (картинки, шрифты) будут называться по своим именам
        assetFileNames: `[name].[ext]`,
      }
    }
  }
  // --- КОНЕЦ ИЗМЕНЕНИЙ ---
});