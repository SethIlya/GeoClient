// client/src/main.js
import { createApp } from 'vue';
import App from './App.vue';
import axios from 'axios';

// Импортируем стили Leaflet
import 'leaflet/dist/leaflet.css';

// --- НАДЕЖНОЕ ПОЛУЧЕНИЕ НАСТРОЕК ИЗ ШАБЛОНА ---
// Мы получаем настройки один раз и сохраняем в константу.
// Это избавляет от проблем с порядком инициализации.
const djangoSettings = window.djangoSettings || {
    // Предоставляем запасные значения на случай, если что-то пойдет не так
    csrfToken: null,
    apiPointsUrl: "/api/points/",
    apiUploadUrl: "/api/upload-rinex/",
    apiKmlUploadUrl: "/api/upload-kml/",
    apiStationNamesUrl: "/api/station-names/",
    apiCsrfUrl: "/api/get-csrf-token/"
};

// --- СОЗДАНИЕ ПРИЛОЖЕНИЯ С ПЕРЕДАЧЕЙ НАСТРОЕК ЧЕРЕЗ PROPS ---
// Это самый надежный способ передать данные в корневой компонент.
const app = createApp(App, {
    djangoSettings: djangoSettings
});

// --- НАСТРОЙКА AXIOS ---
// Функция для настройки Axios. Мы вызовем ее после получения CSRF-токена.
function setupAxios(csrfToken) {
    axios.defaults.headers.common['X-CSRFToken'] = csrfToken;
    console.log("Axios configured with CSRF token:", csrfToken);
    
    // Делаем настроенный экземпляр Axios доступным глобально
    app.config.globalProperties.$axios = axios;
}

// --- ИНИЦИАЛИЗАЦИЯ CSRF-ТОКЕНА ---
// Эта логика остается похожей на вашу, но использует константу djangoSettings
async function initializeCsrfTokenAndMountApp() {
    let finalCsrfToken = djangoSettings.csrfToken;

    if (finalCsrfToken) {
        // Если токен уже есть из шаблона, используем его
        console.log("CSRF token found in initial djangoSettings.");
    } else {
        // Если токена нет, запрашиваем его с сервера
        try {
            console.log("Initial CSRF token not found, fetching from API...");
            const response = await axios.get(djangoSettings.apiCsrfUrl);
            if (response.data && response.data.csrfToken) {
                finalCsrfToken = response.data.csrfToken;
                console.log("CSRF token fetched successfully from API.");
            } else {
                console.error("Failed to get CSRF token from API: Invalid response format.");
            }
        } catch (error) {
            console.error("Error fetching CSRF token from API:", error);
        }
    }

    if (finalCsrfToken) {
        setupAxios(finalCsrfToken);
    } else {
        console.warn("CSRF token is not available. POST/PATCH/DELETE requests might fail.");
        // Все равно делаем Axios доступным, чтобы GET-запросы работали
        app.config.globalProperties.$axios = axios;
    }

    // Монтируем приложение только после завершения всех асинхронных операций
    app.mount('#app');
}

// Запускаем весь процесс
initializeCsrfTokenAndMountApp();