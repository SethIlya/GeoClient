<template>
  <div v-if="!isAuthReady" class="loading-overlay">
    <div class="spinner-border text-primary" role="status"></div>
    <span class="ms-2">Проверка авторизации...</span>
  </div>

  <div v-else id="app-layout" class="d-flex flex-column vh-100">

    <header class="app-header bg-dark text-white p-3 d-flex justify-content-between align-items-center shadow-sm">
      <h1>Карта RINEX точек TESTIM CI\CD</h1>
      <div v-if="isAuthenticated" class="d-flex align-items-center">
        <button 
          v-if="userPermissions.canUpload"
          class="btn btn-sm btn-outline-info me-3" 
          type="button"
          data-bs-toggle="modal" 
          :data-bs-target="'#' + kmlModalId"
          title="Обогатить данные из KML файла"
        >
          <i class="bi bi-geo-alt-fill me-1"></i> Загрузить KML
        </button>
        <button 
          v-if="userPermissions.canUpload"
          class="btn btn-sm btn-outline-light me-3" 
          type="button"
          data-bs-toggle="modal" 
          :data-bs-target="'#' + manageNamesModalId"
          title="Открыть справочник имен станций"
        >
          <i class="bi bi-journal-bookmark-fill me-1"></i>
          Справочник имен
        </button>
        <span v-if="user" class="navbar-text me-3 small">
          Пользователь: <strong>{{ user.username }}</strong>
        </span>
        <button class="btn btn-sm btn-outline-warning" @click="handleLogout">Выйти</button>
      </div>
    </header>
    
    <!-- Основной контент -->
    <div class="container-fluid flex-grow-1 d-flex p-0 main-content-wrapper">
      
      <!-- Логический контейнер для всего, что требует авторизации -->
      <template v-if="isAuthenticated">
        <!-- Боковая панель -->
        <aside class="sidebar bg-light p-3 border-end shadow-sm" style="width: 380px; min-width:300px; overflow-y: auto;">
            <MessageDisplay :messages="messages" @clear-message="clearUserMessage" class="mb-3"/>
            
            <div v-if="selectedPointIds.length > 0 && userPermissions.canUpload" class="selected-actions-panel card bg-primary-subtle shadow-sm mb-3">
              <div class="card-body p-2">
                <p class="mb-2 small fw-bold">Выбрано точек: {{ selectedPointIds.length }}</p>
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

            <FileUploadForm
                v-if="userPermissions.canUpload"
                @upload-complete="handleUploadComplete" 
                @upload-message="addUserMessage" 
                :api-upload-url="props.djangoSettings.apiUploadUrl"
                class="mb-4"
            />
            <hr v-if="userPermissions.canUpload" class="my-3">
            <PointInfoPanel
              :point="infoPanelPoint"
              :selected-point-ids-in-app="selectedPointIds"
              :available-station-names="availableStationNames" 
              :api-points-url="props.djangoSettings.apiPointsUrl"
              :can-edit="userPermissions.canUpload"
              @point-updated="handlePointUpdated"
              @point-deleted="handleSinglePointDeleted" 
              @delete-failed="handleDeleteFailed"
              @edit-message="addUserMessage"
              @selection-cleared="clearSelection"
            />
        </aside>
      
        <!-- Карта -->
        <main class="map-content-area flex-grow-1 position-relative bg-secondary-subtle">
            <MapComponent
              :key="mapKey"
              :points-data="mapPoints"
              :selected-point-ids="selectedPointIds"
              :active-point-id="infoPanelPointId"
              @point-clicked="handlePointClicked"
              @points-selected-by-area="handleAreaSelection"
            />
            <!-- Оверлей загрузки для карты -->
            <div v-if="isLoadingPoints" class="loading-overlay">
              <div class="spinner-border text-primary" role="status"></div>
            </div>
        </main>
      </template>

      <!-- Заглушка, если пользователь не авторизован (но проверка уже прошла) -->
      <div v-else class="w-100 d-flex align-items-center justify-content-center bg-light">
          <div class="text-center text-muted">
              <i class="bi bi-lock-fill fs-1 mb-3"></i>
              <p>Для доступа к карте и функциям требуется авторизация.</p>
          </div>
      </div>

    </div>
  </div>

  <!-- 3. Модальное окно входа рендерится поверх всего, если нужно -->
  <Login
    v-if="isAuthReady && !isAuthenticated"
    :login-url="props.djangoSettings.apiLoginUrl"
    @login-success="onLoginSuccess"
  />

  <!-- 4. Модальные окна для KML и Имен станций рендерятся, только если пользователь вошел и имеет права -->
  <!-- Они находятся в DOM, но невидимы, пока их не вызовет Bootstrap -->
  <template v-if="isAuthenticated && userPermissions.canUpload">
      <KMLUploadModal :modal-id="kmlModalId" @upload-kml="handleKMLUpload" />
      <ManageStationNamesModal :modal-id="manageNamesModalId" @names-updated="handleStationNamesUpdate" />
  </template>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance, computed, reactive } from 'vue';
import Login from './components/Login.vue';
import MapComponent from './components/MapComponent.vue';
import PointInfoPanel from './components/PointInfoPanel.vue';
import FileUploadForm from './components/FileUploadForm.vue';
import MessageDisplay from './components/MessageDisplay.vue';
import ManageStationNamesModal from './components/ManageStationNamesModal.vue';
import KMLUploadModal from './components/KMLUploadModal.vue';

const props = defineProps({
    djangoSettings: { type: Object, required: true }
});

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

// --- Состояния ---
const isAuthReady = ref(false);
const isAuthenticated = ref(false);
const user = ref(null);
const userPermissions = reactive({ canUpload: false, canDownloadOrView: false });

const mapKey = ref(Date.now());
const mapPoints = ref([]);
const selectedPointIds = ref([]);
const infoPanelPointId = ref(null);
const messages = ref([]);
const isLoadingPoints = ref(false);
const availableStationNames = ref([]);
const manageNamesModalId = 'manageStationNamesModalInstance';
const kmlModalId = 'kmlUploadModalInstance';
const isDeletingMultiple = ref(false);
const isKMLUploading = ref(false);

const infoPanelPoint = computed(() => {
  if (!infoPanelPointId.value) return null;
  return mapPoints.value.find(p => String(p.properties?.id) === infoPanelPointId.value);
});


// ==============================================================================
// === БЛОК АВТОРИЗАЦИИ И ЗАГРУЗКИ ДАННЫХ ===
// ==============================================================================

const handleSuccessfulLogin = async (data) => {
    if (data.token) { 
        localStorage.setItem('authToken', data.token);
    }
    user.value = { username: data.username, id: data.user_id };
    updatePermissions(data.groups);
    isAuthenticated.value = true;
    await initializeAppData(); 
};

const handleLogout = async () => {
    try {
        if (localStorage.getItem('authToken')) {
            await $axios.post(props.djangoSettings.apiLogoutUrl);
        }
    } catch (error) {
        console.error("Ошибка при выходе на сервере (токен мог уже быть невалидным), но клиентская сессия будет очищена:", error);
    } finally {
        localStorage.removeItem('authToken');
        // Перезагрузка - самый надежный способ сбросить все состояние Vue
        window.location.reload();
    }
};

const updatePermissions = (groups = []) => {
    userPermissions.canUpload = groups.includes('Uploader');
    userPermissions.canDownloadOrView = groups.includes('Uploader') || groups.includes('Viewer');
};

const checkAuthStatus = async () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        try {
            const response = await $axios.get(props.djangoSettings.apiUserStatusUrl);
            await handleSuccessfulLogin({ token, ...response.data });
        } catch (error) {
            // Если токен есть, но он невалиден, чистим и считаем пользователя неавторизованным
            localStorage.removeItem('authToken');
            isAuthenticated.value = false;
        }
    }
    isAuthReady.value = true;
};

const onLoginSuccess = async (data) => {
    await handleSuccessfulLogin(data);
};

onMounted(() => {
    checkAuthStatus();
});


// ==============================================================================
// === ЛОГИКА ПРИЛОЖЕНИЯ ===
// ==============================================================================

const initializeAppData = async () => {
    if (!isAuthenticated.value) return; 
    
    isLoadingPoints.value = true;
    const promises = [fetchMapPoints()];
    if (userPermissions.canUpload) {
        promises.push(fetchInitialStationNames());
    }
    try {
        await Promise.all(promises);
    } catch (error) {
        console.error("Ошибка при инициализации данных приложения:", error);
    } finally {
        isLoadingPoints.value = false;
    }
};

const fetchMapPoints = async () => {
  if (!isAuthenticated.value) return;

  clearSelection();
  try {
    const response = await $axios.get(props.djangoSettings.apiPointsUrl);
    
    if (response.data && response.data.results && Array.isArray(response.data.results.features)) {
      mapPoints.value = response.data.results.features;
    } else {
      console.warn("Получен неожиданный формат данных для точек карты:", response.data);
      mapPoints.value = [];
    }
    
  } catch (error) {
    addUserMessage({ type: 'danger', text: 'Не удалось загрузить точки.' });
    throw error;
  }
};

const fetchInitialStationNames = async () => {
    if (!isAuthenticated.value) return;
    try {
        const response = await $axios.get(props.djangoSettings.apiStationNamesUrl);
        availableStationNames.value = (response.data.results || response.data).map(item => item.name).sort();
    } catch (error) {
        addUserMessage({ type: 'warning', text: 'Не удалось загрузить справочник имен.' });
        throw error;
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

const handlePointUpdated = (updatedFeature) => {
    const index = mapPoints.value.findIndex(p => p.properties.id === updatedFeature.properties.id);
    if (index !== -1) {
        mapPoints.value[index] = updatedFeature;
    }
    if (userPermissions.canUpload) {
      fetchInitialStationNames();
    }
};

const handleSinglePointDeleted = (deletedPointId) => { 
    const idStr = String(deletedPointId);
    addUserMessage({ type: 'success', text: `Точка ID '${idStr}' удалена.` });
    mapPoints.value = mapPoints.value.filter(p => String(p.properties?.id) !== idStr);
    
    if(infoPanelPointId.value === idStr) infoPanelPointId.value = null;
    if(selectedPointIds.value.includes(idStr)) {
        selectedPointIds.value = selectedPointIds.value.filter(id => id !== idStr);
    }
};

const confirmDeleteSelectedPoints = () => {
  if (window.confirm(`Удалить ${selectedPointIds.value.length} выбранные точки?`)) {
    deleteSelectedPoints();
  }
};

const deleteSelectedPoints = async () => {
  isDeletingMultiple.value = true;
  const idsToDelete = [...selectedPointIds.value];
  if (!idsToDelete.length) { 
      isDeletingMultiple.value = false; return; 
  }
  const deleteUrl = `${String(props.djangoSettings.apiPointsUrl).replace(/\/$/, '')}/delete-multiple/`;
  try {
    const response = await $axios.post(deleteUrl, { ids: idsToDelete });
    addUserMessage({ type: 'success', text: response.data.message || 'Точки удалены.' });
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
        if (userPermissions.canUpload) {
          await fetchInitialStationNames();
        }
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

const handleDeleteFailed = (errorInfo) => { 
    addUserMessage({ type: 'danger', text: `Ошибка удаления точки ID ${errorInfo.id}: ${errorInfo.message}`});
};

const handleStationNamesUpdate = (updatedNames) => {
  availableStationNames.value = [...updatedNames].sort();
};
</script>

<style>
html, body { height: 100%; overflow: hidden; }
#app-layout { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.app-header h1 { font-size: 1.6rem; font-weight: 300; }
.main-content-wrapper { overflow: hidden; }
.sidebar { flex-shrink: 0; z-index: 1000; }
.map-content-area { min-height: 0; } 
.loading-overlay { 
  position: fixed; 
  top: 0; left: 0; right: 0; bottom: 0; 
  background-color: rgba(255, 255, 255, 0.85); 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  z-index: 2000;
}
</style>