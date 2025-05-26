<template>
  <div id="app-layout" class="d-flex flex-column vh-100">
    <header class="app-header bg-dark text-white p-3 text-center">
      <h1>Карта RINEX точек</h1>
    </header>
    <div class="container-fluid flex-grow-1 d-flex p-0">
      <aside class="sidebar bg-light p-3 border-end" style="width: 380px; overflow-y: auto;">
        <MessageDisplay :messages="messages" @clear-message="clearUserMessage" class="mb-3"/>
        <FileUploadForm @upload-complete="handleUploadComplete" @upload-message="addUserMessage" class="mb-3"/>
        <hr>
        <PointInfoPanel :point="selectedPoint" />
      </aside>
      <main class="map-content-area flex-grow-1 position-relative">
        <MapComponent 
          :points-data="mapPoints" 
          @point-selected="handlePointSelected" 
          ref="mapComponentRef"
        />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance } from 'vue';
import MapComponent from './components/MapComponent.vue';
import PointInfoPanel from './components/PointInfoPanel.vue';
import FileUploadForm from './components/FileUploadForm.vue';
import MessageDisplay from './components/MessageDisplay.vue';

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const mapPoints = ref([]);
const selectedPoint = ref(null);
const messages = ref([]); // { id, type: 'success'|'danger'|'warning'|'info', text }
const mapComponentRef = ref(null);

const fetchMapPoints = async () => {
  try {
    const response = await $axios.get($djangoSettings.apiPointsUrl);
    if (response.data && Array.isArray(response.data.features)) {
      mapPoints.value = response.data.features;
      if (mapPoints.value.length === 0) {
        addUserMessage({ type: 'info', text: 'На карте пока нет точек. Загрузите RINEX файл.' });
      }
    } else {
      mapPoints.value = [];
      addUserMessage({ type: 'danger', text: 'Ошибка формата данных точек с сервера.' });
    }
  } catch (error) {
    console.error('Ошибка загрузки точек:', error);
    addUserMessage({ type: 'danger', text: 'Не удалось загрузить точки с сервера.' });
    mapPoints.value = [];
  }
};

const handlePointSelected = (pointFeature) => {
  selectedPoint.value = pointFeature;
};

const handleUploadComplete = (uploadResult) => {
  if (uploadResult.success) {
    (uploadResult.messages || [{type: 'success', text: 'Файл успешно обработан.'}]).forEach(msg => addUserMessage(msg));
    if (uploadResult.created_count > 0 || mapPoints.value.length === 0) {
      fetchMapPoints();
    }
  } else {
    (uploadResult.messages || [{type: 'danger', text: uploadResult.message || 'Ошибка обработки файла.'}]).forEach(msg => addUserMessage(msg));
  }
};

const addUserMessage = (message) => {
  const newMessage = { id: Date.now(), ...message };
  // Адаптируем типы сообщений для Bootstrap alert классов
  if (message.type === 'error') newMessage.type = 'danger';
  if (message.type === 'warning') newMessage.type = 'warning'; // уже совпадает
  messages.value.push(newMessage);
  setTimeout(() => clearUserMessage(newMessage.id), 7000);
};

const clearUserMessage = (messageId) => {
  messages.value = messages.value.filter(m => m.id !== messageId);
};

onMounted(() => {
  fetchMapPoints();
});

async function fetchAndSetCsrfToken() {
  if (window.DJANGO_SETTINGS && window.DJANGO_SETTINGS.csrfToken && window.DJANGO_SETTINGS.csrfToken !== "dummyCSRFTokenForDev") {
    // Если мы уже получили токен от Django шаблона, используем его
    axios.defaults.headers.common['X-CSRFToken'] = window.DJANGO_SETTINGS.csrfToken;
    return;
  }
  try {
    // Запрашиваем токен, если работаем через Vite dev server
    const response = await axios.get('/api/get-csrf-token/'); // Убедитесь, что прокси настроен для этого
    if (response.data && response.data.csrfToken) {
      axios.defaults.headers.common['X-CSRFToken'] = response.data.csrfToken;
      // Можно также обновить window.DJANGO_SETTINGS.csrfToken для консистентности
      if (window.DJANGO_SETTINGS) {
        window.DJANGO_SETTINGS.csrfToken = response.data.csrfToken;
      }
      console.log("CSRF token fetched and set from API.");
    }
  } catch (error) {
    console.error("Failed to fetch CSRF token:", error);
  }
}

onMounted(async () => {
  await fetchAndSetCsrfToken(); // Вызываем перед первым запросом, который может быть POST
  fetchMapPoints();
});
</script>

<style scoped>
/* Стили, специфичные для App.vue, если они нужны и не покрываются Bootstrap */
.app-header h1 {
  font-size: 1.5rem;
  margin-bottom: 0;
}
/* Убраны общие стили, которые теперь должны браться из Bootstrap или inline */
</style>