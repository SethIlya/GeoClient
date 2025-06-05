<template>
  <div id="app-layout" class="d-flex flex-column vh-100">
    <header class="app-header bg-dark text-white p-3 text-center shadow-sm">
      <h1>Карта RINEX точек</h1>
    </header>
    <div class="container-fluid flex-grow-1 d-flex p-0 main-content-wrapper">
      <aside class="sidebar bg-light p-3 border-end shadow-sm" style="width: 380px; min-width:300px; overflow-y: auto;">
        <MessageDisplay :messages="messages" @clear-message="clearUserMessage" class="mb-3"/>
        
        <div v-if="selectedPointIds.length > 0" class="selected-actions-panel card bg-primary-subtle shadow-sm mb-3">
          <div class="card-body p-2">
            <p class="mb-2 small fw-bold">
              Выбрано точек: {{ selectedPointIds.length }}
            </p>
            <div class="btn-group btn-group-sm w-100" role="group">
              <button 
                @click="confirmDeleteSelectedPoints" 
                class="btn btn-danger"
                :disabled="isDeletingMultiple"
                title="Удалить все выбранные точки"
              >
                <i class="bi bi-trash-fill"></i> 
                <span class="ms-1">Удалить выбранные</span>
              </button>
              <button 
                @click="clearSelection" 
                class="btn btn-outline-secondary"
                title="Снять выделение со всех точек"
              >
                <i class="bi bi-x-circle-fill"></i> 
                <span class="ms-1">Сбросить</span>
              </button>
            </div>
          </div>
        </div>

        <FileUploadForm @upload-complete="handleUploadComplete" @upload-message="addUserMessage" class="mb-4"/>
        <hr class="my-3">
        <PointInfoPanel
          :point="lastSelectedPointDetails"
          :selected-point-ids-in-app="selectedPointIds"
          @point-updated="handlePointUpdated"
          @point-deleted="handleSinglePointDeleted" 
          @delete-failed="handleDeleteFailed"
          @edit-message="addUserMessage"
        />
      </aside>
      <main class="map-content-area flex-grow-1 position-relative bg-secondary-subtle">
        <MapComponent
          :key="mapKey"
          ref="mapComponentRef"
          :points-data="mapPoints"
          :selected-point-ids="selectedPointIds"
          @point-clicked="handlePointClicked"
          @map-ready="onMapReady"
        />
        <div v-if="isLoadingPoints || isDeletingMultiple" class="loading-overlay">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">
              {{ isLoadingPoints ? 'Загрузка точек...' : (isDeletingMultiple ? 'Удаление точек...' : 'Загрузка...') }}
            </span>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance, nextTick, computed } from 'vue';
import MapComponent from './components/MapComponent.vue';
import PointInfoPanel from './components/PointInfoPanel.vue';
import FileUploadForm from './components/FileUploadForm.vue';
import MessageDisplay from './components/MessageDisplay.vue';

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const mapPoints = ref([]);
const selectedPointIds = ref([]); 
const lastClickedPointId = ref(null); 
const messages = ref([]); // Массив для хранения объектов сообщений
const mapComponentRef = ref(null);
const isLoadingPoints = ref(false);
const isDeletingMultiple = ref(false);
const mapKey = ref(Date.now());

const lastSelectedPointDetails = computed(() => {
  if (lastClickedPointId.value && mapPoints.value.length > 0) {
    return mapPoints.value.find(p => p.properties && p.properties.id === lastClickedPointId.value) || null;
  }
  return null;
});

const forceMapRemount = async () => {
  mapKey.value = Date.now();
  await nextTick();
  console.log("[App.vue] Карта принудительно перемонтирована с ключом:", mapKey.value);
};

const fetchMapPoints = async () => {
  isLoadingPoints.value = true;
  selectedPointIds.value = []; 
  lastClickedPointId.value = null;
  console.log("[App.vue] fetchMapPoints: Загрузка точек с:", $djangoSettings.apiPointsUrl);
  try {
    const response = await $axios.get($djangoSettings.apiPointsUrl);
    if (response.data && Array.isArray(response.data.features)) {
      mapPoints.value = response.data.features.map(feature => {
        const f = JSON.parse(JSON.stringify(feature));
        if (!f.properties) f.properties = {};
        if (f.id != null && f.properties.id == null) f.properties.id = f.id;
        else if (f.id == null && f.properties.id != null) f.id = f.properties.id;
        return f;
      }).filter(f => f.properties && f.properties.id != null);
      console.log("[App.vue] fetchMapPoints: mapPoints после обработки (количество:", mapPoints.value.length, ")");
      await forceMapRemount();
    } else { 
      mapPoints.value = []; 
      addUserMessage({ type: 'danger', text: 'Ошибка формата данных от сервера при загрузке точек.' });
    }
  } catch (error) { 
    console.error('[App.vue] fetchMapPoints: Ошибка:', error); 
    addUserMessage({ type: 'danger', text: 'Не удалось загрузить точки с карты.' });
    mapPoints.value = [];
  }
  finally { isLoadingPoints.value = false; }
};

const handlePointClicked = (pointFeature) => {
  if (!pointFeature || !pointFeature.properties || pointFeature.properties.id == null) {
    console.warn("[App.vue] handlePointClicked: получен некорректный объект точки.");
    return;
  }
  const pointId = pointFeature.properties.id;
  lastClickedPointId.value = pointId;

  const index = selectedPointIds.value.indexOf(pointId);
  if (index > -1) {
    selectedPointIds.value.splice(index, 1);
    if (lastClickedPointId.value === pointId) {
        lastClickedPointId.value = selectedPointIds.value.length > 0 ? selectedPointIds.value[selectedPointIds.value.length - 1] : null;
    }
  } else {
    selectedPointIds.value.push(pointId);
  }
  console.log("[App.vue] handlePointClicked: ID точки", pointId, "Выбранные ID:", selectedPointIds.value);
};

const clearSelection = () => {
  selectedPointIds.value = [];
  lastClickedPointId.value = null;
  addUserMessage({type: 'info', text: 'Выделение с точек снято.'});
};

const handleUploadComplete = async (uploadResult) => {
  console.log("[App.vue] handleUploadComplete - Получен результат:", JSON.parse(JSON.stringify(uploadResult)));
  if (uploadResult.messages && Array.isArray(uploadResult.messages)) {
    uploadResult.messages.forEach(msg => addUserMessage(msg));
  } else if (uploadResult.message) { // Запасной вариант для одиночного сообщения
    addUserMessage({ type: uploadResult.success ? 'info' : 'danger', text: uploadResult.message });
  } else if (!uploadResult.success && !uploadResult.messages) { // Если неудача и нет кастомных сообщений
    addUserMessage({ type: 'danger', text: 'Произошла неизвестная ошибка при загрузке файла(ов).' });
  }

  if (uploadResult.success || (uploadResult.total_created_count != null && uploadResult.total_created_count > 0)) {
    await fetchMapPoints();
  } else {
    console.warn("[App.vue] handleUploadComplete: Процесс загрузки сообщил о проблемах или не создал новые точки.", uploadResult);
  }
};

const handlePointUpdated = async (updatedFeatureFromServer) => {
  const targetId = updatedFeatureFromServer?.properties?.id;
  if (!targetId) {
      console.error("[App.vue] handlePointUpdated: Некорректные данные от сервера:", updatedFeatureFromServer);
      addUserMessage({ type: 'warning', text: 'Получены некорректные данные после обновления точки.' });
      return;
  }
  mapPoints.value = mapPoints.value.map(p => (p.properties?.id === targetId) ? updatedFeatureFromServer : p);
  await forceMapRemount(); 
};

const handleSinglePointDeleted = async (deletedPointId) => {
  addUserMessage({ type: 'success', text: `Точка ID ${deletedPointId} была успешно удалена.` });
  mapPoints.value = mapPoints.value.filter(p => p.properties && p.properties.id !== deletedPointId);
  
  const index = selectedPointIds.value.indexOf(deletedPointId);
  if (index > -1) {
    selectedPointIds.value.splice(index, 1);
  }
  if (lastClickedPointId.value === deletedPointId) {
    lastClickedPointId.value = selectedPointIds.value.length > 0 ? selectedPointIds.value[selectedPointIds.value.length-1] : null;
  }
  await forceMapRemount();
};

const handleDeleteFailed = (errorInfo) => { 
    addUserMessage({ type: 'danger', text: `Ошибка удаления точки ID ${errorInfo.id}: ${errorInfo.message}`})
};

const addUserMessage = (message) => {
  const defaultMessageId = Date.now() + Math.random(); // Уникальный ID
  let processedMessage = { id: defaultMessageId, type: 'info', text: '' }; // Сообщение по умолчанию

  if (typeof message === 'string') { // Если передана просто строка
    processedMessage.text = message;
  } else if (message && typeof message === 'object' && message.text != null) { // Если передан объект с полем text
    processedMessage = { ...processedMessage, ...message }; // Объединяем с дефолтным, message может перезаписать id, type, text
    
    // Гарантируем наличие ID. Если в message был id, он останется. Иначе будет defaultMessageId.
    if (message.id == null) { // Если в message не было id
        processedMessage.id = defaultMessageId;
    } else {
        processedMessage.id = message.id; // Используем ID из message
    }
    
    if (processedMessage.type === 'error') { // Преобразуем 'error' в 'danger' для Bootstrap
        processedMessage.type = 'danger';
    }
    // Проверка на допустимые типы для alert-классов Bootstrap
    if (!['success', 'info', 'warning', 'danger', 'secondary', 'light', 'dark', 'primary'].includes(processedMessage.type)) {
      console.warn(`[App.vue] addUserMessage: Неизвестный тип сообщения '${processedMessage.type}', используется 'secondary'.`);
      processedMessage.type = 'secondary'; // Безопасный тип по умолчанию
    }
  } else { // Некорректный формат сообщения
    console.warn("[App.vue] addUserMessage: получен некорректный формат сообщения или отсутствует текст:", message);
    return; // Не добавляем некорректное сообщение
  }
  
  messages.value.push(processedMessage);
  console.log("[App.vue] addUserMessage: Добавлено сообщение:", JSON.parse(JSON.stringify(processedMessage)), "Всего сообщений:", messages.value.length);

  // Автоматическое удаление сообщения через 7 секунд
  setTimeout(() => {
    clearUserMessage(processedMessage.id);
  }, 7000);
};

const clearUserMessage = (messageId) => {
  if (messageId == null) {
    console.warn("[App.vue] clearUserMessage: Попытка удалить сообщение с неопределенным ID.");
    return;
  }
  const initialLength = messages.value.length;
  messages.value = messages.value.filter(m => m.id !== messageId);
  
  if (messages.value.length < initialLength) {
    console.log("[App.vue] clearUserMessage: Удалено сообщение ID", messageId, "Осталось сообщений:", messages.value.length);
  } else {
    // Этот лог может быть слишком частым, если setTimeout пытается удалить уже удаленное сообщение
    // console.log("[App.vue] clearUserMessage: Сообщение с ID", messageId, "не найдено для удаления. Текущие ID:", messages.value.map(m => m.id));
  }
};

const onMapReady = (mapLeafletInstance) => { 
  console.log("[App.vue] Карта Leaflet готова:", mapLeafletInstance ? 'Instance OK' : 'Instance NULL');
};

const confirmDeleteSelectedPoints = () => {
  if (selectedPointIds.value.length === 0) {
    addUserMessage({ type: 'warning', text: 'Нет выбранных точек для удаления.' });
    return;
  }
  if (window.confirm(`Вы уверены, что хотите удалить ${selectedPointIds.value.length} выбранные точки? Это действие необратимо.`)) {
    deleteSelectedPoints();
  }
};

const deleteSelectedPoints = async () => {
  if (selectedPointIds.value.length === 0) return;
  isDeletingMultiple.value = true;
  
  const baseUrl = String($djangoSettings.apiPointsUrl).replace(/\/$/, '');
  const deleteMultipleUrl = `${baseUrl}/delete-multiple/`;
    
  try {
    const response = await $axios.post(deleteMultipleUrl, { ids: selectedPointIds.value });
    
    if (response.data) {
        const { deleted_ids, errors, message } = response.data;
        if (message) { // Основное сообщение от сервера
            addUserMessage({ type: (errors && errors.length > 0 && (!deleted_ids || deleted_ids.length === 0)) ? 'warning' : 'success', text: message });
        }

        if (deleted_ids && Array.isArray(deleted_ids) && deleted_ids.length > 0) {
            mapPoints.value = mapPoints.value.filter(p => p.properties && !deleted_ids.includes(p.properties.id));
             // addUserMessage({ type: 'success', text: `Удалено ${deleted_ids.length} точек.` }); // Дублирует общее сообщение
        }
        if (errors && Array.isArray(errors) && errors.length > 0) {
            errors.forEach(err => addUserMessage({ type: 'danger', text: `Ошибка для ID ${err.id}: ${err.error}`}));
        }
        // Если нет ни message, ни deleted_ids, ни errors, но запрос прошел успешно (200 OK)
        if (!message && (!deleted_ids || deleted_ids.length === 0) && (!errors || errors.length === 0)) {
            addUserMessage({ type: 'info', text: 'Запрос на групповое удаление обработан, но нет информации о результате.' });
        }

    } else { // Неожиданный ответ без data
         addUserMessage({ type: 'warning', text: `Неожиданный пустой ответ от сервера при групповом удалении.` });
    }

  } catch (error) {
    console.error('Ошибка группового удаления точек:', error);
    let errorMsg = 'Произошла ошибка при групповом удалении.';
    if (error.response && error.response.data) {
        if (error.response.data.detail) errorMsg = error.response.data.detail;
        else if (typeof error.response.data.message === 'string') errorMsg = error.response.data.message;
    }
    addUserMessage({ type: 'danger', text: errorMsg });
  } finally {
    selectedPointIds.value = []; 
    lastClickedPointId.value = null;
    isDeletingMultiple.value = false;
    await forceMapRemount(); 
  }
};

onMounted(() => { fetchMapPoints(); });
</script>

<style>
html, body { height: 100%; overflow: hidden; }
#app-layout { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.app-header h1 { font-size: 1.6rem; margin-bottom: 0; font-weight: 300; }
.main-content-wrapper { overflow: hidden; }
.sidebar { flex-shrink: 0; }
.map-content-area { min-height: 0; } /* Для корректного flex-grow */
.loading-overlay {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(255, 255, 255, 0.75); /* Немного плотнее фон */
  display: flex; justify-content: center; align-items: center;
  z-index: 1050; /* Выше, чем стандартные модальные окна Bootstrap, если они используются */
}
.selected-actions-panel .card-body {
  font-size: 0.9rem;
}
.selected-actions-panel .btn i.bi {
  font-size: 1rem; 
  vertical-align: text-bottom;
}
</style>