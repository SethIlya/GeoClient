<template>
  <div id="app-layout" class="d-flex flex-column vh-100">
    <header class="app-header bg-dark text-white p-3 d-flex justify-content-between align-items-center shadow-sm">
      <h1>Карта RINEX точек</h1>
      
      <div class="d-flex align-items-center">
        <button 
          class="btn btn-sm btn-outline-info me-3" 
          type="button"
          data-bs-toggle="modal" 
          :data-bs-target="'#' + kmlModalId"
          title="Обогатить данные из KML файла"
        >
          <i class="bi bi-geo-alt-fill me-1"></i> Загрузить KML
        </button>
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
      </div>

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
              <button @click="confirmDeleteSelectedPoints" class="btn btn-danger" :disabled="isDeletingMultiple">
                <i class="bi bi-trash-fill"></i> <span class="ms-1">Удалить</span>
              </button>
              <button @click="clearSelection" class="btn btn-outline-secondary">
                <i class="bi bi-x-circle-fill"></i> <span class="ms-1">Сбросить</span>
              </button>
            </div>
          </div>
        </div>
        
        <!-- --- ИЗМЕНЕНИЕ ЗДЕСЬ --- -->
        <FileUploadForm 
            @upload-complete="handleUploadComplete" 
            @upload-message="addUserMessage" 
            :api-upload-url="props.djangoSettings.apiUploadUrl"
            class="mb-4"
        />
        <!-- --- КОНЕЦ ИЗМЕНЕНИЯ --- -->
        
        <hr class="my-3">
        <PointInfoPanel
          :point="infoPanelPoint"
          :selected-point-ids-in-app="selectedPointIds"
          :available-station-names="availableStationNames" 
          :api-points-url="props.djangoSettings.apiPointsUrl"
          @point-updated="handlePointUpdated"
          @point-deleted="handleSinglePointDeleted" 
          @delete-failed="handleDeleteFailed"
          @edit-message="addUserMessage"
        />
      </aside>
      <main class="map-content-area flex-grow-1 position-relative bg-secondary-subtle">
        <MapComponent
          v-if="!isLoadingPoints"
          :key="mapKey"
          :points-data="mapPoints"
          :selected-point-ids="selectedPointIds"
          :active-point-id="infoPanelPointId"
          @point-clicked="handlePointClicked"
          @points-selected-by-area="handleAreaSelection"
        />
        <div v-if="isLoadingPoints || isDeletingMultiple || isKMLUploading" class="loading-overlay">
          <div class="spinner-border text-primary" role="status"></div>
        </div>
      </main>
    </div>

    <KMLUploadModal 
        :modal-id="kmlModalId"
        @upload-kml="handleKMLUpload"
    />
    <ManageStationNamesModal 
      :modal-id="manageNamesModalId"
      @names-updated="handleStationNamesUpdate" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance, computed, defineProps, watch } from 'vue';
import MapComponent from './components/MapComponent.vue';
import PointInfoPanel from './components/PointInfoPanel.vue';
import FileUploadForm from './components/FileUploadForm.vue';
import MessageDisplay from './components/MessageDisplay.vue';
import ManageStationNamesModal from './components/ManageStationNamesModal.vue';
import KMLUploadModal from './components/KMLUploadModal.vue';

const props = defineProps({
    djangoSettings: {
        type: Object,
        required: true,
        default: () => ({})
    }
});

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

const mapKey = ref(Date.now());
const mapPoints = ref([]);
const selectedPointIds = ref([]);
const infoPanelPointId = ref(null);
const messages = ref([]);
const isLoadingPoints = ref(true);
const isDeletingMultiple = ref(false);
const availableStationNames = ref([]);
const manageNamesModalId = 'manageStationNamesModalInstance';
const kmlModalId = 'kmlUploadModalInstance';
const isKMLUploading = ref(false);

const infoPanelPoint = computed(() => {
  if (!infoPanelPointId.value) return null;
  return mapPoints.value.find(p => String(p.properties?.id) === infoPanelPointId.value);
});

// Этот метод больше не нужен для обновления, но может пригодиться для полной перезагрузки в других местах
const forceMapRemount = () => { mapKey.value = Date.now(); };

const fetchMapPoints = async () => {
  isLoadingPoints.value = true;
  clearSelection();
  try {
    const response = await $axios.get(props.djangoSettings.apiPointsUrl);
    mapPoints.value = response.data.features || [];
  } catch (error) { 
    addUserMessage({ type: 'danger', text: 'Не удалось загрузить точки.' });
  } finally {
    isLoadingPoints.value = false;
    // forceMapRemount(); // Можно убрать и отсюда, чтобы не было "моргания" при первой загрузке
  }
};

const handlePointClicked = (pointFeature) => {
    infoPanelPointId.value = String(pointFeature.properties.id);
};

const handleAreaSelection = (idsFromArea) => {
  selectedPointIds.value = idsFromArea;
  infoPanelPointId.value = idsFromArea.length === 1 ? idsFromArea[0] : null;
};

const clearSelection = () => {
    selectedPointIds.value = [];
    infoPanelPointId.value = null;
};

// --- ИЗМЕНЕННЫЙ МЕТОД ---
const handlePointUpdated = (updatedFeature) => {
    const index = mapPoints.value.findIndex(p => p.properties.id === updatedFeature.properties.id);
    if (index !== -1) {
        // Правильно обновляем массив, чтобы Vue среагировал
        mapPoints.value[index] = updatedFeature;
    }
    // Запрашиваем обновленный список имен, если он мог измениться
    fetchInitialStationNames();

    // УБИРАЕМ ПРИНУДИТЕЛЬНУЮ ПЕРЕЗАГРУЗКУ КАРТЫ
    // forceMapRemount(); // <--- ЭТА СТРОКА ВЫЗЫВАЛА ПРОБЛЕМУ
};

const handleSinglePointDeleted = (deletedPointId) => { 
    const idStr = String(deletedPointId);
    addUserMessage({ type: 'success', text: `Точка ID '${idStr}' удалена.` });
    mapPoints.value = mapPoints.value.filter(p => String(p.properties?.id) !== idStr);
    
    if(infoPanelPointId.value === idStr) {
        infoPanelPointId.value = null;
    }
    if(selectedPointIds.value.includes(idStr)) {
        selectedPointIds.value = selectedPointIds.value.filter(id => id !== idStr);
    }
};

// ... Остальной код App.vue остается без изменений ...
const deleteSelectedPoints = async () => {
  isDeletingMultiple.value = true;
  const idsToDelete = [...selectedPointIds.value];
  if (!idsToDelete.length) { 
      isDeletingMultiple.value = false; 
      return; 
  }
  
  const deleteUrl = `${String(props.djangoSettings.apiPointsUrl).replace(/\/$/, '')}/delete-multiple/`;
  try {
    const response = await $axios.post(deleteUrl, { ids: idsToDelete });
    const { deleted_ids, message } = response.data || {};
    addUserMessage({ type: 'success', text: message || `Удалено ${deleted_ids?.length || 0} точек.` });
    await fetchMapPoints();
  } catch (error) {
    addUserMessage({ type: 'danger', text: error.response?.data?.detail || 'Ошибка группового удаления.' });
  } finally {
      isDeletingMultiple.value = false;
  }
};

const handleUploadComplete = async (uploadResult) => {
    (uploadResult.messages || []).forEach(msg => addUserMessage(msg));
    if (uploadResult.success || uploadResult.total_created_count > 0) {
        await fetchMapPoints();
        await fetchInitialStationNames();
    }
};

const handleKMLUpload = async ({ formData }) => {
  isKMLUploading.value = true;
  try {
    const response = await $axios.post(props.djangoSettings.apiKmlUploadUrl, formData);
    (response.data.messages || []).forEach(msg => addUserMessage(msg));
    if (response.data.success && response.data.updated_count > 0) {
      await fetchMapPoints();
    }
  } catch (error) {
    const errorMsg = error.response?.data?.messages?.[0]?.text || 'Ошибка при обработке KML файла.';
    addUserMessage({ type: 'danger', text: errorMsg });
  } finally {
    isKMLUploading.value = false;
  }
};

const addUserMessage = (message) => {
  const id = Date.now() + Math.random();
  messages.value.push({ ...message, id });
  setTimeout(() => { messages.value = messages.value.filter(m => m.id !== id); }, 7000);
};

const clearUserMessage = (id) => {
    messages.value = messages.value.filter(m => m.id !== id);
};

const confirmDeleteSelectedPoints = () => {
  if (window.confirm(`Удалить ${selectedPointIds.value.length} выбранные точки?`)) {
    deleteSelectedPoints();
  }
};

const handleDeleteFailed = (errorInfo) => { 
    addUserMessage({ type: 'danger', text: `Ошибка удаления точки ID ${errorInfo.id}: ${errorInfo.message}`});
};

const fetchInitialStationNames = async () => {
    try {
        const response = await $axios.get(props.djangoSettings.apiStationNamesUrl);
        availableStationNames.value = (response.data.results || response.data).map(item => item.name).sort();
    } catch (error) {
        addUserMessage({ type: 'warning', text: 'Не удалось загрузить справочник имен.' });
    }
};

const handleStationNamesUpdate = (updatedNames) => {
  availableStationNames.value = [...updatedNames].sort();
};

onMounted(() => {
  fetchMapPoints();
  fetchInitialStationNames();
});
</script>

<style>
html, body { height: 100%; overflow: hidden; }
#app-layout { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.app-header h1 { font-size: 1.6rem; font-weight: 300; }
.main-content-wrapper { overflow: hidden; }
.sidebar { flex-shrink: 0; z-index: 1000; }
.map-content-area { min-height: 0; } 
.loading-overlay { 
  position: absolute; 
  top: 0; left: 0; right: 0; bottom: 0; 
  background-color: rgba(255, 255, 255, 0.75); 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  z-index: 1050; 
}
.selected-actions-panel .card-body { font-size: 0.9rem; }
</style>