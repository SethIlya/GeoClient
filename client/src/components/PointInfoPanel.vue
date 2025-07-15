<!-- client/src/components/PointInfoPanel.vue -->
<template>
  <div class="point-info-card card shadow-sm">
    <div class="card-body">
      <!-- ... (часть шаблона до списка наблюдений без изменений) ... -->
      <div class="d-flex flex-wrap justify-content-between align-items-center mb-3">
        <h5 class="card-title mb-0">Информация о пункте</h5>
        
        <div class="d-flex flex-wrap justify-content-end align-items-center" v-if="point && point.properties">
          <template v-if="!isEditing">
            <button @click="toggleEditMode(true)" class="btn btn-sm btn-outline-primary me-2 mt-1 flex-shrink-0" title="Редактировать">
              <i class="bi bi-pencil-square"></i> <span class="ms-1 d-none d-lg-inline">Редактировать</span>
            </button>
            <button @click="confirmDeletePoint" class="btn btn-sm btn-outline-danger me-2 mt-1 flex-shrink-0" title="Удалить пункт" :disabled="isDeleting">
              <i class="bi bi-trash"></i> <span class="ms-1 d-none d-lg-inline">Удалить</span>
            </button>
          </template>
          <button @click="$emit('selection-cleared')" class="btn btn-sm btn-secondary mt-1 flex-shrink-0" title="Сбросить выбор">
             <i class="bi bi-x-lg"></i> <span class="ms-1 d-none d-lg-inline">Сбросить</span>
          </button>
        </div>
      </div>

      <div v-if="point && point.properties">
        <!-- Форма редактирования -->
        <form @submit.prevent="saveChanges" v-if="isEditing">
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
              <span v-if="isSaving" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
              <span v-else><i class="bi bi-check-lg me-1"></i></span>
              Сохранить
            </button>
          </div>
          <div v-if="editError" class="alert alert-danger p-2 mt-3 small">{{ editError }}</div>
        </form>

        <!-- Режим просмотра -->
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
                                <li class="mb-1">
                                    <strong>Длительность:</strong> 
                                    <span :class="{'text-muted fst-italic': !obs.duration_display}">
                                        {{ obs.duration_display || 'Нет данных' }}
                                    </span>
                                </li>
                                <li class="mb-1"><strong>Координаты:</strong> <span class="font-monospace">{{ obs.latitude?.toFixed(6) }}, {{ obs.longitude?.toFixed(6) }}</span></li>
                                <li class="mb-1"><strong>Приемник:</strong> <span :class="{'text-muted fst-italic': !obs.receiver_number}">{{ obs.receiver_number || 'Нет данных' }}</span></li>
                                <li class="mb-2"><strong>Высота антенны (H):</strong> <span :class="{'text-muted fst-italic': obs.antenna_height == null}">{{ obs.antenna_height != null ? `${obs.antenna_height} м` : 'Нет данных' }}</span></li>
                            </ul>
                            <!-- 
                              --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ССЫЛКИ ЗДЕСЬ ---
                              Теперь ссылка ведет на наш новый, надежный API-endpoint.
                              Она строится из ID наблюдения (obs.id).
                            -->
                            <a :href="`/api/observations/${obs.id}/download/`" class="btn btn-sm btn-outline-primary w-100" download>
                                <i class="bi bi-download me-2"></i>Скачать исходный файл
                            </a>
                        </div>
                    </div>
                </div>
                <p v-else class="text-muted small fst-italic mt-2">Для этого пункта нет зарегистрированных наблюдений.</p>
            </ul>
        </div>
      </div>
      <!-- Заглушки -->
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
// Скриптовая часть этого файла остается без изменений
import { ref, watch, getCurrentInstance } from 'vue';
import StationNameSelector from './StationNameSelector.vue';

const props = defineProps({
  point: { type: Object, default: null },
  selectedPointIdsInApp: { type: Array, default: () => [] },
  availableStationNames: { type: Array, default: () => [] },
  apiPointsUrl: { type: String, required: true }
});

const emit = defineEmits(['point-updated', 'edit-message', 'point-deleted', 'delete-failed', 'selection-cleared']); 
const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

const isEditing = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const editError = ref('');

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
    isEditing.value = state;
    editError.value = '';
};

const saveChanges = async () => {
    if (!props.point?.properties?.id) return;
    isSaving.value = true;
    editError.value = '';
    try {
        const payload = {
            station_name: editablePoint.value.station_name.trim(),
            description: editablePoint.value.description.trim(),
            point_type: editablePoint.value.point_type
        };
        let baseUrl = String(props.apiPointsUrl || '/api/points/').replace(/\/$/, '');
        const url = `${baseUrl}/${props.point.properties.id}/`;
        const response = await $axios.patch(url, payload);
        emit('point-updated', response.data);
        emit('edit-message', { type: 'success', text: 'Данные пункта успешно обновлены.' });
        isEditing.value = false;
    } catch (error) {
        editError.value = error.response?.data?.detail || 'Ошибка сохранения.';
    } finally {
        isSaving.value = false;
    }
};

const confirmDeletePoint = () => {
    if (!props.point?.properties?.id) return;
    const name = props.point.properties.station_name || props.point.properties.id;
    const obsCount = props.point.properties.observations?.length || 0;
    if (window.confirm(`Вы уверены, что хотите удалить пункт "${name}" и все его ${obsCount} наблюдений? Это действие необратимо.`)) {
        deletePoint();
    }
};

const deletePoint = async () => {
    const idToDelete = props.point.properties.id;
    isDeleting.value = true;
    try {
        let baseUrl = String(props.apiPointsUrl || '/api/points/').replace(/\/$/, '');
        await $axios.delete(`${baseUrl}/${idToDelete}/`);
        emit('point-deleted', idToDelete);
    } catch (error) {
        emit('delete-failed', { id: idToDelete, message: error.response?.data?.detail || 'Ошибка сервера.' });
    } finally {
        isDeleting.value = false;
    }
};
</script>

<style scoped>
/* Стили остаются без изменений */
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
</style>