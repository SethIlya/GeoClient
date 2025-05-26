// frontend/vite.config.js (или client/vite.config.js)
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// ... другие импорты ...

export default defineConfig({
  plugins: [
    vue(),
    // ...
  ],
  resolve: {
    // ...
  },
  server: {
    port: 5174, // Порт, на котором работает Vite dev server (у вас 5174)
    proxy: {
      // Проксируем все запросы, начинающиеся с /api
      '/api': {
        target: 'http://127.0.0.1:8000', // URL вашего Django сервера
        changeOrigin: true, // Необходимо для виртуальных хостов
        // secure: false, // Если у Django самоподписанный SSL-сертификат в разработке
        // ws: true, // Если нужно проксировать WebSockets
        // rewrite: (path) => path.replace(/^\/api/, '') // Раскомментируйте, если Django API не имеет префикса /api
      },
      // Если у вас есть /media/ файлы, которые должен отдавать Django
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  },
  // Если вы готовитесь к сборке для Django, не забудьте вернуть настройки base и build:
  /*
  base: process.env.NODE_ENV === 'production' ? '/static/geoclient/vue_dist/' : '/',
  build: {
    outDir: '../geoclient/static/geoclient/vue_dist', // Относительно корня Vue проекта
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      // ...
    }
  }
  */
})