// client/src/main.js
import { createApp } from 'vue';
import App from './App.vue';
import axios from 'axios';

// Импорт стилей Leaflet (если вы не используете CDN в index.html для Vite)
import 'leaflet/dist/leaflet.css';
// Если у вас были глобальные стили в assets/main.css, раскомментируйте:
// import './assets/main.css'; // Предполагая, что такой файл есть

const app = createApp(App);

// --- Начало Настройки Axios и CSRF ---
// Обеспечиваем, что $djangoSettings всегда объект
// Это нужно сделать до того, как мы пытаемся использовать djangoSettings в initializeCsrfToken
app.config.globalProperties.$djangoSettings = window.DJANGO_SETTINGS || {
    csrfToken: null, // По умолчанию null, если не передано
    apiPointsUrl: "/api/points/",
    apiUploadUrl: "/api/upload-rinex/",
    apiCsrfUrl: "/api/get-csrf-token/" // Запасной URL, если не передан из Django
};

// Функция для получения и установки CSRF токена
async function initializeCsrfToken() {
  
    const djangoSettings = app.config.globalProperties.$djangoSettings;
    if (djangoSettings.csrfToken) { // Токен из Django-шаблона
        axios.defaults.headers.common['X-CSRFToken'] = djangoSettings.csrfToken;
        console.log("CSRF token set from initial DJANGO_SETTINGS:", djangoSettings.csrfToken);
    } else if (djangoSettings.apiCsrfUrl) {
        // Если начальный токен не предоставлен, запросим его
        try {
            console.log("Initial CSRF token not found, fetching from API:", djangoSettings.apiCsrfUrl);
            const response = await axios.get(djangoSettings.apiCsrfUrl); // GET-запрос, CSRF-токен для него не нужен
            if (response.data && response.data.csrfToken) {
                const fetchedToken = response.data.csrfToken;
                axios.defaults.headers.common['X-CSRFToken'] = fetchedToken;
                // Обновляем значение в нашем глобальном объекте $djangoSettings
                djangoSettings.csrfToken = fetchedToken;
                console.log("CSRF token fetched and set from API:", fetchedToken);
            } else {
                console.error("Failed to get CSRF token from API: Invalid response format.", response.data);
            }
        } catch (error) {
            console.error("Error fetching CSRF token from API:", error);
        }
    } else {
        console.warn("CSRF token not available and no API URL to fetch it.");
    }
}

// Axios будет доступен глобально после инициализации CSRF
app.config.globalProperties.$axios = axios;
// --- Конец Настройки Axios и CSRF ---


// Вызываем инициализацию CSRF токена перед монтированием приложения
// и монтируем приложение только после завершения (успешного или нет) этой асинхронной операции.
initializeCsrfToken().then(() => {
    app.mount('#app');
}).catch(error => {
    // Обработка критической ошибки при инициализации, если необходимо
    console.error("Critical error during CSRF token initialization, app might not work correctly:", error);
    // Можно все равно смонтировать приложение, но с предупреждением
    app.mount('#app');
});