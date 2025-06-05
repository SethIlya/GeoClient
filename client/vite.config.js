// frontend/vite.config.js (или client/vite.config.js)
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// ... другие импорты ...

export default defineConfig({
  plugins: [
    vue(),

  ],
  resolve: {
  },
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
      }
    }
  },

})