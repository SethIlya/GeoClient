// vite.config.js

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path'; // Рекомендуется для работы с путями

export default defineConfig({
  plugins: [
    vue(),
  ],

  // Базовый публичный путь. Полезно для корректной сборки.
  // Если фронтенд и бэкенд на одном домене, это '/'.
  base: '/', 

  // Настройки для сервера разработки
  server: {
    // Явно указываем порт (у вас это уже было, что хорошо)
    port: 5174, 

    // Настройки прокси для перенаправления запросов на Django-сервер
    proxy: {
      // Все запросы, начинающиеся с /api, будут перенаправлены на Django
      '/api': {
        target: 'http://127.0.0.1:8000', // Адрес вашего Django-сервера
        changeOrigin: true, // Необходимо для корректной работы прокси
        // secure: false, // Можно раскомментировать при проблемах с самоподписанными SSL-сертификатами
      },
 
      // Перенаправляем запросы к медиа-файлам (загруженные пользователем)
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      // ДОБАВЛЕНО: Перенаправляем запросы к статическим файлам Django.
      // Это полезно, если у вас есть статика, которую отдает не Vite, а Django
      // (например, из админки или других Django-приложений).
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  },

  // Настройки для сборки проекта (команда `npm run build`)
  build: {
    // Папка, куда будут складываться собранные файлы (относительно корня фронтенда)
    outDir: 'dist', 
    // Папка для ассетов внутри outDir
    assetsDir: 'assets',
    // Очищать папку dist перед каждой сборкой
    emptyOutDir: true,
    
    rollupOptions: {
      output: {
        // Убедитесь, что эти имена файлов соответствуют тем, что вы подключаете в HTML-шаблоне Django
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]',
      }
    }
  }
});