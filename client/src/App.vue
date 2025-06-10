<template>
  <div id="app-layout" class="d-flex flex-column vh-100">
    <header class="app-header bg-dark text-white p-3 d-flex justify-content-between align-items-center shadow-sm">
      <h1>Карта RINEX точек</h1>
      <button 
        class="btn btn-sm btn-outline-light" 
        type="button"
        data-bs-toggle="modal" 
        :data-bs-target="'#' + manageNamesModalId"
        title="Открыть справочник имен станций"
      >
        <i class="bi bi-journal-bookmark-fill me-1"></i>
        Справочник имен
      </button>
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
          :available-station-names="availableStationNames" 
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

    <!-- Модальное окно для управления именами станций -->
    <ManageStationNamesModal 
      :modal-id="manageNamesModalId"
      @names-updated="handleStationNamesUpdate" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance, nextTick, computed } from 'vue';
import MapComponent from './components/MapComponent.vue';
import PointInfoPanel from './components/PointInfoPanel.vue';
import FileUploadForm from './components/FileUploadForm.vue';
import MessageDisplay from './components/MessageDisplay.vue';
import ManageStationNamesModal from './components/ManageStationNamesModal.vue'; // Импорт модального окна

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const mapPoints = ref([]);
const selectedPointIds = ref([]); 
const lastClickedPointId = ref(null); 
const messages = ref([]);
const mapComponentRef = ref(null);
const isLoadingPoints = ref(false);
const isDeletingMultiple = ref(false);
const mapKey = ref(Date.now());

const availableStationNames = ref([]); // Этот список будет обновляться из события модального окна
const manageNamesModalId = 'manageStationNamesModalInstance'; // Уникальный ID для модального окна Bootstrap

const lastSelectedPointDetails = computed(() => {
  if (lastClickedPointId.value && mapPoints.value.length > 0) {
    return mapPoints.value.find(p => p.properties && String(p.properties.id) === lastClickedPointId.value) || null;
  }
  return null;
});

const forceMapRemount = async () => {
  const oldSelectedIds = [...selectedPointIds.value];
  const oldLastClickedId = lastClickedPointId.value;
  mapKey.value = Date.now();
  await nextTick();
  console.log("[App.vue] Карта принудительно перемонтирована с ключом:", mapKey.value);
  selectedPointIds.value = oldSelectedIds;
  lastClickedPointId.value = oldLastClickedId;
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
        if (f.id != null) f.id = String(f.id);
        if (f.properties.id != null) f.properties.id = String(f.properties.id);
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
    const pointId = String(pointFeature.properties.id);
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
    } else if (uploadResult.message) {
        addUserMessage({ type: uploadResult.success ? 'info' : 'danger', text: uploadResult.message });
    } else if (!uploadResult.success && !uploadResult.messages) {
        addUserMessage({ type: 'danger', text: 'Произошла неизвестная ошибка при загрузке файла(ов).' });
    }
    if (uploadResult.success || (uploadResult.total_created_count != null && uploadResult.total_created_count > 0)) {
        await fetchMapPoints(); // Перезагружаем точки
        await fetchInitialStationNames(); // Обновляем справочник имен, так как могли добавиться новые из файлов
    } else {
        console.warn("[App.vue] handleUploadComplete: Проблемы с загрузкой или нет новых точек.", uploadResult);
    }
};

const handlePointUpdated = async (updatedFeatureFromServer) => {
    const targetId = String(updatedFeatureFromServer?.properties?.id); 
    if (!targetId) {
        console.error("[App.vue] handlePointUpdated: Некорректные данные от сервера:", updatedFeatureFromServer);
        addUserMessage({ type: 'warning', text: 'Получены некорректные данные после обновления точки.' });
        return;
    }
    let found = false;
    mapPoints.value = mapPoints.value.map(p => {
        if (p.properties && String(p.properties.id) === targetId) {
            found = true;
            if (updatedFeatureFromServer.id != null) updatedFeatureFromServer.id = String(updatedFeatureFromServer.id);
            if (updatedFeatureFromServer.properties && updatedFeatureFromServer.properties.id != null) {
                updatedFeatureFromServer.properties.id = String(updatedFeatureFromServer.properties.id);
            }
            return updatedFeatureFromServer;
        }
        return p;
    });
    if (found) {
        if (lastClickedPointId.value === targetId) {
            const tempId = lastClickedPointId.value;
            lastClickedPointId.value = null; 
            await nextTick();
            lastClickedPointId.value = tempId;
        }
        await forceMapRemount();
        // Сообщение об успехе уже выводится из PointInfoPanel
    } else {
        console.warn(`[App.vue] handlePointUpdated: Точка с ID '${targetId}' не найдена. Перезагрузка.`);
        await fetchMapPoints(); 
    }
    // После обновления точки, ее station_name мог измениться. Обновим общий список имен.
    await fetchInitialStationNames();
};

const handleSinglePointDeleted = async (deletedPointId) => { 
    const idStr = String(deletedPointId);
    addUserMessage({ type: 'success', text: `Точка ID '${idStr}' была успешно удалена.` });
    mapPoints.value = mapPoints.value.filter(p => p.properties && String(p.properties.id) !== idStr);
    const index = selectedPointIds.value.indexOf(idStr);
    if (index > -1) selectedPointIds.value.splice(index, 1);
    if (lastClickedPointId.value === idStr) {
        lastClickedPointId.value = selectedPointIds.value.length > 0 ? selectedPointIds.value[selectedPointIds.value.length-1] : null;
    }
    await forceMapRemount();
};

const handleDeleteFailed = (errorInfo) => { 
    addUserMessage({ type: 'danger', text: `Ошибка удаления точки ID ${String(errorInfo.id)}: ${errorInfo.message}`});
};

const addUserMessage = (message) => {
  const defaultMessageId = Date.now() + Math.random();
  let processedMessage = { id: defaultMessageId, type: 'info', text: '' };
  if (typeof message === 'string') {
    processedMessage.text = message;
  } else if (message && typeof message === 'object' && message.text != null) {
    processedMessage = { ...processedMessage, ...message }; 
    if (message.id == null) {
        processedMessage.id = defaultMessageId;
    } else {
        processedMessage.id = message.id;
    }
    if (processedMessage.type === 'error') {
        processedMessage.type = 'danger';
    }
    if (!['success', 'info', 'warning', 'danger', 'secondary', 'light', 'dark', 'primary'].includes(processedMessage.type)) {
      console.warn(`[App.vue] addUserMessage: Неизвестный тип сообщения '${processedMessage.type}', используется 'secondary'.`);
      processedMessage.type = 'secondary';
    }
  } else {
    console.warn("[App.vue] addUserMessage: получен некорректный формат сообщения или отсутствует текст:", message);
    return; 
  }
  messages.value.push(processedMessage);
  console.log("[App.vue] addUserMessage: Добавлено сообщение:", JSON.parse(JSON.stringify(processedMessage)), "Всего сообщений:", messages.value.length);
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
  const idsToDelete = selectedPointIds.value.map(id => String(id)); 
  const baseUrl = String($djangoSettings.apiPointsUrl).replace(/\/$/, '');
  const deleteMultipleUrl = `${baseUrl}/delete-multiple/`;
    
  try {
    const response = await $axios.post(deleteMultipleUrl, { ids: idsToDelete });
    if (response.data) {
        const { deleted_ids, errors, message } = response.data; 
        if (message) {
            addUserMessage({ 
                type: (errors && errors.length > 0 && (!deleted_ids || deleted_ids.length === 0)) ? 'warning' : 'success', 
                text: message 
            });
        }
        if (deleted_ids && Array.isArray(deleted_ids) && deleted_ids.length > 0) {
            const deletedIdsStr = deleted_ids.map(id => String(id));
            mapPoints.value = mapPoints.value.filter(p => p.properties && !deletedIdsStr.includes(String(p.properties.id)));
        }
        if (errors && Array.isArray(errors) && errors.length > 0) {
            errors.forEach(err => addUserMessage({ type: 'danger', text: `Ошибка для ID ${err.id}: ${err.error}`}));
        }
        if (!message && (!deleted_ids || deleted_ids.length === 0) && (!errors || errors.length === 0)) {
            addUserMessage({ type: 'info', text: 'Запрос на групповое удаление обработан, но нет информации о результате.' });
        }
    } else {
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

// --- Управление списком имен станций ---
const fetchInitialStationNames = async () => {
    const stationNamesApiUrl = ($djangoSettings && $djangoSettings.apiStationNamesUrl)
        ? String($djangoSettings.apiStationNamesUrl).replace(/\/$/, '')
        : ($djangoSettings && $djangoSettings.apiBaseUrl ? String($djangoSettings.apiBaseUrl) + 'station-names' : '/api/station-names');
    try {
        console.log("[App.vue] Первоначальная загрузка имен станций с:", `${stationNamesApiUrl}/`);
        const response = await $axios.get(`${stationNamesApiUrl}/`);
        const results = response.data.results || response.data; // Учитываем пагинацию DRF
        if (Array.isArray(results)) {
            // API возвращает объекты {id, name, ...}, нам нужны только name (строки)
            availableStationNames.value = results.map(item => item.name).sort((a,b) => a.localeCompare(b));
            console.log("[App.vue] Имена станций загружены при монтировании App:", availableStationNames.value);
        } else {
             console.warn("[App.vue] Ответ API для имен станций не является массивом:", results);
             availableStationNames.value = [];
        }
    } catch (error) {
        console.error("[App.vue] Ошибка первоначальной загрузки имен станций:", error);
        addUserMessage({ type: 'warning', text: 'Не удалось загрузить справочник имен станций.' });
        availableStationNames.value = []; // В случае ошибки оставляем пустым
    }
};

// Вызывается, когда ManageStationNamesModal успешно обновил данные на сервере
// и эмитит событие 'names-updated' с массивом строк (имен)
const handleStationNamesUpdate = (updatedNameStrings) => {
  if (Array.isArray(updatedNameStrings)) {
    availableStationNames.value = [...updatedNameStrings].sort((a,b) => a.localeCompare(b));
    console.log("[App.vue] Справочник имен станций обновлен (получено событие от модалки):", availableStationNames.value);
  } else {
    console.warn("[App.vue] handleStationNamesUpdate: получены некорректные данные от модального окна", updatedNameStrings);
  }
};

onMounted(() => { 
  fetchMapPoints();
  fetchInitialStationNames();
});
</script>

<style>
html, body { height: 100%; overflow: hidden; }
#app-layout { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.app-header {
  padding-right: 1rem; 
}
.app-header h1 { font-size: 1.6rem; margin-bottom: 0; font-weight: 300; }
.main-content-wrapper { overflow: hidden; }
.sidebar { flex-shrink: 0; }
.map-content-area { min-height: 0; } 
.loading-overlay {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(255, 255, 255, 0.75);
  display: flex; justify-content: center; align-items: center;
  z-index: 1050; 
}
.selected-actions-panel .card-body {
  font-size: 0.9rem;
}
.selected-actions-panel .btn i.bi {
  font-size: 1rem; 
  vertical-align: text-bottom;
}
</style>