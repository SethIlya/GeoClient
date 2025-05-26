// frontend/src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import axios from 'axios' // Если используете axios



// Глобальные стили './assets/styles/main.css' или аналогичные УДАЛЕНЫ

const app = createApp(App)

// Настройка Axios (если используется)
// Предполагается, что DJANGO_SETTINGS будут доступны в window, когда приложение запущено через Django
if (window.DJANGO_SETTINGS && window.DJANGO_SETTINGS.csrfToken) {
  axios.defaults.headers.common['X-CSRFToken'] = window.DJANGO_SETTINGS.csrfToken;
}
app.config.globalProperties.$axios = axios;
app.config.globalProperties.$djangoSettings = window.DJANGO_SETTINGS || {}; // Предоставляем пустой объект, если DJANGO_SETTINGS нет

app.mount('#app')