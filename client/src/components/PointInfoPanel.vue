<!-- client/src/components/PointInfoPanel.vue -->
<template>
  <div class="point-info-card card shadow-sm">
    <div class="card-body">
      <div class="d-flex flex-wrap justify-content-between align-items-center mb-3">
        <h5 class="card-title mb-0">Информация о пункте</h5>
        
        <div class="d-flex flex-wrap justify-content-end align-items-center" v-if="point && point.properties">
            <template v-if="!isEditing && props.canEdit">
                <button @click="toggleEditMode(true)" class="btn btn-sm btn-outline-primary me-2 mt-1 flex-shrink-0" title="Редактировать">
                    <i class="bi bi-pencil-square"></i> <span class="ms-1 d-none d-lg-inline">Редактировать</span>
                </button>
                <button @click="confirmDeletePoint" class="btn btn-sm btn-outline-danger me-2 mt-1 flex-shrink-0" title="Удалить пункт" :disabled="isDeleting">
                    <span v-if="isDeleting" class="spinner-border spinner-border-sm" role="status"></span>
                    <i v-else class="bi bi-trash"></i> 
                    <span class="ms-1 d-none d-lg-inline">Удалить</span>
                </button>
            </template>
            <button @click="$emit('selection-cleared')" class="btn btn-sm btn-secondary mt-1 flex-shrink-0" title="Сбросить выбор">
                <i class="bi bi-x-lg"></i> <span class="ms-1 d-none d-lg-inline">Сбросить</span>
            </button>
        </div>
      </div>

      <div v-if="point && point.properties">
        <form @submit.prevent="saveChanges" v-if="isEditing && props.canEdit">
            <!-- Ваша полная форма редактирования -->
            <div class="mb-2 small"><strong>ID (Имя пункта):</strong> {{ editablePoint.id_display }}</div>
            <StationNameSelector v-model="editablePoint.station_name" label="Присвоенное имя" :available-names="props.availableStationNames" />
            <div class="mb-3">
              <label for="pointTypeEdit" class="form-label mb-1 small"><strong>Тип точки:</strong></label>
              <select id="pointTypeEdit" class="form-select form-select-sm" v-model="editablePoint.point_type" required>
                <option disabled value="">Выберите тип...</option>
                <option v-for="ptype in pointTypes" :key="ptype.value" :value="ptype.value">{{ ptype.text }}</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="pointDescriptionEdit" class="form-label mb-1 small"><strong>Описание:</strong></label>
              <textarea id="pointDescriptionEdit" class="form-control form-control-sm" v-model.trim="editablePoint.description" rows="2"></textarea>
            </div>
            
            <div class="d-flex flex-wrap justify-content-end align-items-center pt-2 border-top mt-3">
              <button type="button" @click="toggleEditMode(false)" class="btn btn-secondary me-2">Отмена</button>
              <button type="submit" class="btn btn-success" :disabled="isSaving">
                <span v-if="isSaving" class="spinner-border spinner-border-sm me-1"></span>
                <span v-else><i class="bi bi-check-lg me-1"></i></span>
                Сохранить
              </button>
            </div>
            <div v-if="editError" class="alert alert-danger p-2 mt-3 small">{{ editError }}</div>
        </form>

        <div v-else class="details">
            <ul class="list-unstyled mb-0">
                <li class="mb-2"><strong class="me-1 d-block text-muted small">ID Пункта (Marker Name)</strong><span>{{ point.properties.id || '—' }}</span></li>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Присвоенное имя</strong><span :class="{'text-muted fst-italic': !point.properties.station_name}">{{ point.properties.station_name || 'Не присвоено' }}</span></li>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Актуальные координаты (WGS-84)</strong><span class="font-monospace">{{ point.properties.latitude?.toFixed(6) }}, {{ point.properties.longitude?.toFixed(6) }}</span></li>
                <hr class="my-3"><h6 class="text-muted mb-2 small text-uppercase">Данные из KML</h6>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Класс сети</strong><span :class="{'text-muted fst-italic': !point.properties.network_class}">{{ point.properties.network_class || 'Нет данных' }}</span></li>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Индекс</strong><span :class="{'text-muted fst-italic': !point.properties.index_name}">{{ point.properties.index_name || 'Нет данных' }}</span></li>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Тип центра</strong><span :class="{'text-muted fst-italic': !point.properties.center_type}">{{ point.properties.center_type || 'Нет данных' }}</span></li>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Номер марки</strong><span :class="{'text-muted fst-italic': !point.properties.mark_number}">{{ point.properties.mark_number || 'Нет данных' }}</span></li>
                <li class="mb-2"><strong class="me-1 d-block text-muted small">Статус</strong><span :class="{'text-muted fst-italic': !point.properties.status}">{{ point.properties.status || 'Нет данных' }}</span></li>
                <hr class="my-3"><h6 class="mb-2">История наблюдений ({{ point.properties.observations.length }})</h6>
                <div v-if="point.properties.observations && point.properties.observations.length > 0" class="observation-list">
                    <div class="list-group list-group-flush">
                        <div v-for="obs in point.properties.observations" :key="obs.id" class="list-group-item p-3 border rounded mb-2">
                            <p class="mb-2 fw-bold"><i class="bi bi-calendar-event me-2"></i>{{ obs.timestamp_display }}</p>
                            <ul class="list-unstyled small ps-2">
                                <li class="mb-1"><strong>Длительность:</strong> <span :class="{'text-muted fst-italic': !obs.duration_display}">{{ obs.duration_display || 'Нет данных' }}</span></li>
                                <li class="mb-1"><strong>Координаты:</strong> <span class="font-monospace">{{ obs.latitude?.toFixed(6) }}, {{ obs.longitude?.toFixed(6) }}</span></li>
                                <li class="mb-1"><strong>Приемник:</strong> <span :class="{'text-muted fst-italic': !obs.receiver_number}">{{ obs.receiver_number || 'Нет данных' }}</span></li>
                                <li class="mb-2"><strong>Высота антенны (H):</strong> <span :class="{'text-muted fst-italic': obs.antenna_height == null}">{{ obs.antenna_height != null ? `${obs.antenna_height} м` : 'Нет данных' }}</span></li>
                            </ul>
                            
                            <!-- НОВЫЙ "РУЧНОЙ" ВЫПАДАЮЩИЙ СПИСОК -->
                            <div class="btn-group w-100 position-relative" role="group">
                              <button 
                                @click="downloadObservationFileSet(obs, 'zip')" 
                                class="btn btn-sm btn-outline-primary"
                                :disabled="downloadingStatus[obs.id] || !obs.source_file_group"
                                title="Скачать ZIP-архив"
                              >
                                <span v-if="downloadingStatus[obs.id] === 'zip'" class="spinner-border spinner-border-sm me-2"></span>
                                <i v-else class="bi bi-file-earmark-zip me-2"></i>
                                Скачать ZIP
                              </button>
                              <button 
                                type="button" 
                                class="btn btn-sm btn-outline-primary dropdown-toggle dropdown-toggle-split" 
                                @click.stop="toggleDropdown(obs.id)"
                                :disabled="downloadingStatus[obs.id] || !obs.source_file_group"
                              >
                                <span class="visually-hidden">Toggle Dropdown</span>
                              </button>
                              <ul class="dropdown-menu" v-if="openDropdownId === obs.id">
                                <li>
                                  <a 
                                    class="dropdown-item" 
                                    href="#" 
                                    @click.prevent="downloadObservationFileSet(obs, 'individual')"
                                  >
                                    <span v-if="downloadingStatus[obs.id] === 'individual'" class="spinner-border spinner-border-sm me-2"></span>
                                    <i v-else class="bi bi-files me-2"></i>
                                    Скачать по одному
                                  </a>
                                </li>
                              </ul>
                            </div>

                            <!-- НОВЫЙ БЛОК ПРЕДУПРЕЖДЕНИЯ -->
                            <div v-if="obs.file_count_in_group > 0 && obs.file_count_in_group < 3" class="alert alert-warning p-1 small text-center mt-2 mb-0">
                                <i class="bi bi-exclamation-triangle-fill me-1"></i>
                                Неполный комплект ({{ obs.file_count_in_group }} из 3 файлов)
                            </div>
                        </div>
                    </div>
                </div>
                <p v-else class="text-muted small fst-italic mt-2">Нет зарегистрированных наблюдений.</p>
            </ul>
        </div>
      </div>
      <div v-else-if="selectedPointIdsInApp?.length > 0" class="placeholder text-muted text-center py-3">
        <i class="bi bi-check2-all fs-3 d-block mb-2 text-primary"></i>
        <p class="fst-italic mb-0">Выбрано пунктов: <strong>{{ selectedPointIdsInApp.length }}</strong>.<br>Используйте панель действий.</p>
      </div>
      <div v-else class="placeholder text-muted text-center py-3">
        <i class="bi bi-geo-alt fs-3 d-block mb-2"></i>
        <p class="fst-italic mb-0">Кликните на пункт или выделите область на карте.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, getCurrentInstance, reactive, onMounted, onBeforeUnmount } from 'vue';
import StationNameSelector from './StationNameSelector.vue';

const props = defineProps({
  point: { type: Object, default: null },
  selectedPointIdsInApp: { type: Array, default: () => [] },
  availableStationNames: { type: Array, default: () => [] },
  apiPointsUrl: { type: String, required: true },
  canEdit: { type: Boolean, default: false }
});

const emit = defineEmits(['point-updated', 'edit-message', 'point-deleted', 'delete-failed', 'selection-cleared']);
const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

const isEditing = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const editError = ref('');
const downloadingStatus = reactive({});
const openDropdownId = ref(null);

const pointTypes = ref([
    { value: 'ggs', text: 'Пункты гос. геодезической сети' },
    { value: 'ggs_kurgan', text: 'Пункты ГГС на курганах' },
    { value: 'survey', text: 'Точки съемочной сети' },
    { value: 'survey_kurgan', text: 'Точки съемочной сети на курганах' },
    { value: 'astro', text: 'Астрономические пункты/Высокоточная сеть' },
    { value: 'leveling', text: 'Нивелирная марка/ГНСС' },
    { value: 'default', text: 'Неопределенный тип' },
]);

const editablePoint = ref({});

const toggleDropdown = (obsId) => {
  openDropdownId.value = openDropdownId.value === obsId ? null : obsId;
};

const closeAllDropdowns = () => {
  openDropdownId.value = null;
};

onMounted(() => {
  document.addEventListener('click', closeAllDropdowns);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', closeAllDropdowns);
});

watch(() => props.point, (newPoint) => {
    isEditing.value = false;
    editError.value = '';
    if (newPoint?.properties) {
        editablePoint.value = {
            id_display: newPoint.properties.id,
            station_name: newPoint.properties.station_name || '',
            description: newPoint.properties.description || '',
            point_type: newPoint.properties.point_type || 'default',
        };
        if (newPoint.properties.observations) {
          newPoint.properties.observations.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        }
    }
}, { immediate: true, deep: true });

const toggleEditMode = (state) => {
    if (!props.canEdit) return;
    isEditing.value = state;
    editError.value = '';
};

const saveChanges = async () => {
    if (!props.point?.properties?.id || !props.canEdit) return;
    isSaving.value = true;
    editError.value = '';
    try {
        const payload = {
            station_name: editablePoint.value.station_name.trim(),
            description: editablePoint.value.description.trim(),
            point_type: editablePoint.value.point_type
        };
        const url = `${String(props.apiPointsUrl).replace(/\/$/, '')}/${props.point.properties.id}/`;
        const response = await $axios.patch(url, payload);
        emit('point-updated', response.data);
        emit('edit-message', { type: 'success', text: 'Данные пункта обновлены.' });
        isEditing.value = false;
    } catch (error) {
        editError.value = error.response?.data?.detail || 'Ошибка сохранения.';
    } finally {
        isSaving.value = false;
    }
};

const confirmDeletePoint = () => {
    if (!props.point?.properties?.id || !props.canEdit) return;
    const name = props.point.properties.station_name || props.point.properties.id;
    const obsCount = props.point.properties.observations?.length || 0;
    const message = `Вы уверены, что хотите удалить пункт "${name}"?\n\nВНИМАНИЕ: Это также безвозвратно удалит все ${obsCount} наблюдений и ВСЕ связанные с ними комплекты RINEX файлов с сервера.`;
    if (window.confirm(message)) {
        deletePoint();
    }
};

const deletePoint = async () => {
    const idToDelete = props.point.properties.id;
    isDeleting.value = true;
    try {
        const url = `${String(props.apiPointsUrl).replace(/\/$/, '')}/delete-points/`;
        const response = await $axios.post(url, { ids: [idToDelete] });
        emit('point-deleted', response.data.deleted_point_ids);
        emit('edit-message', { type: 'success', text: response.data.message });
    } catch (error) {
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || 'Ошибка сервера при удалении.';
        emit('delete-failed', { id: idToDelete, message: errorMessage });
    } finally {
        isDeleting.value = false;
    }
};

const downloadObservationFileSet = async (observation, type = 'zip') => {
  if (!observation.source_file_group) return;
  closeAllDropdowns();
  downloadingStatus[observation.id] = type;
  try {
    if (type === 'zip') {
      const url = `/api/download/rinex/${observation.source_file_group}/`;
      const response = await $axios.get(url, { responseType: 'blob' });
      let filename = `rinex_set.zip`;
      const disposition = response.headers['content-disposition'];
      if (disposition && disposition.includes('attachment')) {
        const match = /filename="?([^"]+)"?/.exec(disposition);
        if (match && match[1]) filename = match[1];
      }
      const downloadUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } else if (type === 'individual') {
      const response = await $axios.get(`/api/observations/${observation.id}/get-individual-urls/`);
      const files = response.data.files;
      if (!files || files.length === 0) throw new Error("Нет URL для скачивания.");
      for (const file of files) {
        const fileResponse = await $axios.get(file.url, { responseType: 'blob' });
        const individualUrl = window.URL.createObjectURL(new Blob([fileResponse.data]));
        const individualLink = document.createElement('a');
        individualLink.href = individualUrl;
        individualLink.setAttribute('download', file.filename);
        document.body.appendChild(individualLink);
        individualLink.click();
        document.body.removeChild(individualLink);
        window.URL.revokeObjectURL(individualUrl);
        await new Promise(resolve => setTimeout(resolve, 300));
      }
    }
  } catch (error) {
    console.error(`Ошибка скачивания (тип: ${type}):`, error);
    const errorMsg = error.response?.status === 401 ? 'Ошибка авторизации.' : 'Ошибка скачивания.';
    emit('edit-message', { type: 'danger', text: errorMsg });
  } finally {
    setTimeout(() => { downloadingStatus[observation.id] = null; }, 1000);
  }
};
</script>

<style scoped>
.details li {
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  line-height: 1.4;
}
.details li strong {
  color: #6c757d;
  font-size: 0.8rem;
  font-weight: 500;
}
.observation-list .list-group-item {
    background-color: #f8f9fa;
}
.card-body {
  padding: 1.25rem;
}
.placeholder {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
/* НОВЫЕ СТИЛИ ДЛЯ РУЧНОГО DROPDOWN */
.dropdown-menu {
  display: block; /* Vue будет управлять видимостью через v-if */
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  min-width: 100%;
}
</style>