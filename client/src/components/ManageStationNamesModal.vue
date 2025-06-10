<!-- client/src/components/ManageStationNamesModal.vue -->
<template>
  <div class="modal fade" :id="modalId" tabindex="-1" :aria-labelledby="modalLabelId" aria-hidden="true" ref="modalElement">
    <!-- ИЗМЕНЕНО: Окно стало шире для удобства -->
    <div class="modal-dialog modal-dialog-centered modal-xl"> 
      <div class="modal-content">
        <div class="modal-header bg-light">
          <h5 class="modal-title" :id="modalLabelId">
            <i class="bi bi-journal-bookmark-fill me-2"></i>Справочник имен станций
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div v-if="isLoadingInitial" class="text-center py-4">
            <div class="spinner-border text-primary me-2" role="status"></div>
            Загрузка справочника...
          </div>
          <div v-if="errorLoading" class="alert alert-danger">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>{{ errorLoading }}
          </div>
          
          <div v-if="!isLoadingInitial && !errorLoading" class="row g-4">
            <!-- ============================================================== -->
            <!-- === ЛЕВАЯ ПАНЕЛЬ: УПРАВЛЕНИЕ, РЕДАКТИРОВАНИЕ ИЛИ ДОБАВЛЕНИЕ === -->
            <!-- ============================================================== -->
            <div class="col-md-5 border-end pe-md-4">
              
              <!-- Секция 1: Панель управления выбранным именем (появляется после двойного клика) -->
              <div v-if="selectedItem && !editingItem.id">
                <h6 class="mb-3">
                  <i class="bi bi-hand-index-thumb me-1"></i>Управление именем:
                </h6>
                <div class="card p-3 bg-light border-primary-subtle">
                  <h5 class="text-center text-primary-emphasis mb-3">"{{ selectedItem.name }}"</h5>
                  <div class="d-grid gap-2">
                    <button class="btn btn-primary btn-sm" @click="startEdit(selectedItem)">
                      <i class="bi bi-pencil-square me-2"></i>Редактировать
                    </button>
                    <button class="btn btn-outline-danger btn-sm" @click="confirmAndRemoveSelected">
                      <i class="bi bi-trash me-2"></i>Удалить
                    </button>
                    <button class="btn btn-outline-secondary btn-sm mt-2" @click="cancelSelection">
                      <i class="bi bi-x-circle me-2"></i>Отменить выбор
                    </button>
                  </div>
                </div>
              </div>

              <!-- Секция 2: Форма редактирования (появляется после нажатия "Редактировать") -->
              <div v-else-if="editingItem.id">
                <h6 class="mb-3">
                  <i class="bi bi-pencil-square me-1"></i>Редактировать: 
                  <em class="text-muted small">"{{ editingItem.originalName }}"</em>
                </h6>
                <form @submit.prevent="handleSubmitName">
                  <div class="input-group mb-2">
                    <input type="text" class="form-control" v-model.trim="currentNameInput" ref="nameInputRef" required />
                    <button class="btn btn-success" type="submit" :disabled="isSubmitting || !currentNameInput.trim() || currentNameInput.trim() === editingItem.originalName">
                      <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-1" role="status"></span>
                      <i v-if="!isSubmitting" class="bi bi-check-lg"></i> Сохранить
                    </button>
                  </div>
                   <button class="btn btn-sm btn-outline-secondary" type="button" @click="cancelEdit" :disabled="isSubmitting">
                     <i class="bi bi-x-lg me-1"></i>Отменить редактирование
                   </button>
                </form>
              </div>
              
              <!-- Секция 3: Форма добавления нового имени (видна по умолчанию) -->
              <div v-else>
                <h6 class="mb-3">
                  <i class="bi bi-plus-circle-dotted me-1"></i>Добавить новое имя:
                </h6>
                <form @submit.prevent="handleSubmitName">
                   <div class="input-group">
                    <input type="text" class="form-control" v-model.trim="currentNameInput" placeholder="Название станции" required />
                    <button class="btn btn-primary" type="submit" :disabled="isSubmitting || !currentNameInput.trim() || isNameInList(currentNameInput.trim())">
                       <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-1" role="status"></span>
                       <i v-if="!isSubmitting" class="bi bi-plus-lg"></i> Добавить
                    </button>
                  </div>
                  <div v-if="currentNameInput.trim() && isNameInList(currentNameInput.trim())" class="form-text text-warning small mt-1">
                    <i class="bi bi-exclamation-triangle me-1"></i>Такое имя уже существует.
                  </div>
                </form>
              </div>

              <!-- Область для сообщений об ошибках/успехе -->
              <div v-if="formMessage.text" :class="['alert small py-2 mt-3', formMessage.type === 'success' ? 'alert-success' : 'alert-danger']" role="alert">
                <i :class="formMessage.type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-circle-fill'" class="bi me-2"></i>{{ formMessage.text }}
              </div>

            </div>

            <!-- ============================================ -->
            <!-- === ПРАВАЯ ПАНЕЛЬ: СПИСОК СУЩЕСТВУЮЩИХ ИМЕН === -->
            <!-- ============================================ -->
            <div class="col-md-7 ps-md-4">
              <h6 class="mb-2">Существующие имена ({{ stationNames.length }}):</h6>
              <p class="text-muted small mt-0 mb-2">Дважды кликните по имени для управления.</p>
              <div v-if="stationNames.length > 0" class="list-group list-group-flush border rounded" style="max-height: 350px; overflow-y: auto;">
                <div 
                  v-for="item in sortedStationNames" 
                  :key="item.id" 
                  class="list-group-item list-group-item-action py-2 px-3"
                  :class="{
                    'list-group-item-primary': selectedItem && item.id === selectedItem.id,
                    'list-group-item-info': item.name === recentlyModifiedName,
                    'disabled-item': selectedItem && (!selectedItem || item.id !== selectedItem.id)
                  }"
                  @dblclick="selectItem(item)" 
                  style="cursor: pointer;"
                >
                  {{ item.name }}
                </div>
              </div>
              <p v-else class="text-muted small fst-italic mt-2">Справочник имен пока пуст.</p>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">
            <i class="bi bi-x-lg me-1"></i>Закрыть
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick, getCurrentInstance } from 'vue';
import { Modal } from 'bootstrap';

// --- Props, Emits, Services ---
const props = defineProps({ modalId: { type: String, required: true } });
const emit = defineEmits(['names-updated']);
const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

// --- State ---
const stationNames = ref([]);
const isLoadingInitial = ref(false);
const isSubmitting = ref(false);
const errorLoading = ref(null);
const currentNameInput = ref('');
const nameInputRef = ref(null);
const formMessage = ref({ text: '', type: 'info', timerId: null });
const recentlyModifiedName = ref(null);

// === НОВЫЕ И ИЗМЕНЕННЫЕ СОСТОЯНИЯ ===
const selectedItem = ref(null); // Хранит объект выбранного имени
const editingItem = ref({ id: null, originalName: '' }); // Хранит объект редактируемого имени

// --- Modal Logic ---
const modalElement = ref(null);
let bsModal = null;
const modalLabelId = computed(() => `${props.modalId}LabelText`);

const API_URL = computed(() => {
    const baseApiUrl = ($djangoSettings?.apiStationNamesUrl) 
           ? String($djangoSettings.apiStationNamesUrl)
           : ($djangoSettings?.apiBaseUrl ? `${String($djangoSettings.apiBaseUrl)}station-names` : '/api/station-names');
    return baseApiUrl.replace(/\/$/, '');
});

// --- Lifecycle Hooks ---
onMounted(() => {
  if (modalElement.value) {
    bsModal = new Modal(modalElement.value);
    modalElement.value.addEventListener('shown.bs.modal', () => {
      fetchStationNames(); // При открытии модалки загружаем данные
      const prefillName = localStorage.getItem('prefillStationNameModal');
      if (prefillName) {
        currentNameInput.value = prefillName;
        localStorage.removeItem('prefillStationNameModal');
      }
    });
  }
});
onBeforeUnmount(() => bsModal?.dispose());

// --- Computed Properties ---
const sortedStationNames = computed(() => {
  return [...stationNames.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }));
});

// --- Methods ---
const resetAllSelections = () => {
    selectedItem.value = null;
    editingItem.value = { id: null, originalName: '' };
    currentNameInput.value = '';
    setFormMessage('', 'info', 0);
};

const fetchStationNames = async () => {
  isLoadingInitial.value = true;
  errorLoading.value = null;
  resetAllSelections();
  try {
    const response = await $axios.get(`${API_URL.value}/`);
    stationNames.value = response.data.results || response.data;
    emitNamesUpdated();
  } catch (e) {
    console.error("Ошибка загрузки имен станций:", e);
    errorLoading.value = `Не удалось загрузить справочник. ${e.response?.data?.detail || e.message}`;
  } finally {
    isLoadingInitial.value = false;
  }
};

const isNameInList = (nameToCheck) => {
  if (!nameToCheck?.trim()) return false;
  const searchName = nameToCheck.trim().toLowerCase();
  return stationNames.value.some(item => item.name.toLowerCase() === searchName && item.id !== editingItem.value.id);
};

// === НОВЫЕ МЕТОДЫ УПРАВЛЕНИЯ ===
const selectItem = (item) => {
  if (editingItem.value.id) {
    setFormMessage('Сначала завершите или отмените редактирование.', 'danger');
    return;
  }
  if (selectedItem.value && selectedItem.value.id === item.id) {
    // Если кликнули по уже выбранному, отменяем выбор
    cancelSelection();
  } else {
    selectedItem.value = item;
    currentNameInput.value = '';
    setFormMessage('', 'info', 0);
  }
};

const cancelSelection = () => {
  selectedItem.value = null;
  setFormMessage('', 'info', 0);
};

const confirmAndRemoveSelected = () => {
    if (selectedItem.value) {
        confirmRemoveName(selectedItem.value);
    }
};

const startEdit = (item) => {
  editingItem.value = { id: item.id, originalName: item.name };
  currentNameInput.value = item.name;
  setFormMessage('', 'info', 0);
  nextTick(() => nameInputRef.value?.focus());
};

const cancelEdit = () => {
  editingItem.value = { id: null, originalName: '' };
  currentNameInput.value = ''; // Очищаем поле ввода
  // Остаемся на панели управления тем же элементом
};

const handleSubmitName = async () => {
  if (editingItem.value.id) {
    await updateStationName();
  } else {
    await addStationName();
  }
};

// --- CRUD Operations ---
const addStationName = async () => {
  const nameToAdd = currentNameInput.value.trim();
  if (!nameToAdd) return;
  
  isSubmitting.value = true;
  try {
    const response = await $axios.post(`${API_URL.value}/`, { name: nameToAdd });
    stationNames.value.push(response.data);
    emitNamesUpdated();
    setFormMessage(`Имя "${nameToAdd}" успешно добавлено.`, 'success');
    recentlyModifiedName.value = nameToAdd;
    currentNameInput.value = '';
    setTimeout(() => { recentlyModifiedName.value = null; }, 3000);
  } catch (e) {
    setFormMessage(`Ошибка добавления: ${e.response?.data?.name?.join(', ') || e.message}`, 'danger');
  } finally {
    isSubmitting.value = false;
  }
};

const updateStationName = async () => {
  const newName = currentNameInput.value.trim();
  if (!newName || newName === editingItem.value.originalName) return;

  isSubmitting.value = true;
  try {
    const response = await $axios.put(`${API_URL.value}/${editingItem.value.id}/`, { name: newName });
    const index = stationNames.value.findIndex(item => item.id === editingItem.value.id);
    if (index > -1) stationNames.value.splice(index, 1, response.data);
    
    setFormMessage(`Имя обновлено на "${newName}".`, 'success');
    recentlyModifiedName.value = newName;
    resetAllSelections(); // Сбрасываем все, возвращаемся к добавлению
    emitNamesUpdated();
    setTimeout(() => { recentlyModifiedName.value = null; }, 3000);
  } catch (e) {
    setFormMessage(`Ошибка обновления: ${e.response?.data?.name?.join(', ') || e.message}`, 'danger');
  } finally {
    isSubmitting.value = false;
  }
};

const confirmRemoveName = (item) => {
  if (window.confirm(`Удалить имя "${item.name}" из справочника?`)) {
    removeStationNameApi(item);
  }
};

const removeStationNameApi = async (itemToRemove) => {
  isSubmitting.value = true;
  try {
    await $axios.delete(`${API_URL.value}/${itemToRemove.id}/`);
    stationNames.value = stationNames.value.filter(item => item.id !== itemToRemove.id);
    setFormMessage(`Имя "${itemToRemove.name}" удалено.`, 'success');
    resetAllSelections(); // Сбрасываем все, возвращаемся к добавлению
    emitNamesUpdated();
  } catch (e) {
    setFormMessage(`Ошибка удаления: ${e.response?.data?.detail || e.message}`, 'danger');
  } finally {
    isSubmitting.value = false;
  }
};


// --- Helpers ---
const emitNamesUpdated = () => {
  emit('names-updated', [...stationNames.value].map(item => item.name).sort((a,b) => a.localeCompare(b, 'ru')));
};

const setFormMessage = (text, type = 'info', duration = 4000) => {
    if (formMessage.value.timerId) clearTimeout(formMessage.value.timerId);
    formMessage.value = { text, type, timerId: null };
    if (duration > 0 && text) {
        formMessage.value.timerId = setTimeout(() => {
            if (formMessage.value.text === text) { 
                 formMessage.value = { text: '', type: 'info', timerId: null };
            }
        }, duration);
    }
};
</script>

<style scoped>
.disabled-item {
  opacity: 0.6;
  background-color: var(--bs-tertiary-bg);
  pointer-events: none;
}
.list-group-item-primary {
  border-left-width: 4px;
  border-left-color: var(--bs-primary);
  font-weight: 500;
}
.list-group-item-action:hover {
  background-color: var(--bs-primary-bg-subtle);
}
.list-group-item-info { 
    background-color: var(--bs-info-bg-subtle) !important; 
    border-color: var(--bs-info-border-subtle) !important;
    transition: background-color 0.5s ease;
}
</style>