// geoclient/client/src/main.js --- ВЕРСИЯ С РУЧНЫМ ПОЛУЧЕНИЕМ CSRF ---

import { createApp } from 'vue';
import App from './App.vue';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap';

// Axios interceptor для токена АВТОРИЗАЦИИ (оставляем его)
axios.interceptors.request.use(config => {
    const token = localStorage.getItem('authToken');
    if (token) {
        config.headers.Authorization = `Token ${token}`;
    }
    return config;
}, error => {
    return Promise.reject(error);
});

// --- ЛОГИКА РУЧНОГО ПОЛУЧЕНИЯ CSRF-ТОКЕНА ---
// Эта функция будет запущена немедленно

(async () => {
    // Вспомогательная функция для чтения cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Сначала пытаемся получить токен из cookie, которые установил Django
    let csrfToken = getCookie('csrftoken');

    // Если в cookie токена нет, запрашиваем его у API
    if (!csrfToken) {
        console.log("Initial CSRF token not found in cookies, fetching from API...");
        try {
            const response = await axios.get(window.djangoSettings.apiCsrfUrl);
            csrfToken = response.data.csrfToken;
            console.log("CSRF token fetched successfully from API.");
        } catch (error) {
            console.error("Error fetching CSRF token from API:", error);
        }
    }

    // Устанавливаем токен как заголовок по умолчанию для всех запросов
    if (csrfToken) {
        axios.defaults.headers.common['X-CSRFToken'] = csrfToken;
        console.log("Axios configured with CSRF token:", csrfToken);
    } else {
        console.warn("CSRF token is not available. POST/PATCH/DELETE requests might fail.");
    }
    
    // --- Создание и монтирование Vue приложения ПОСЛЕ настройки axios ---
    
    const djangoSettings = window.djangoSettings || {};

    const app = createApp(App, {
        djangoSettings: djangoSettings
    });

    app.config.globalProperties.$axios = axios;

    app.mount('#app');

})(); // <-- Немедленный вызов async-функции