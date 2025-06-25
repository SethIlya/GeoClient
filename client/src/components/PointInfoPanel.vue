<template>
  <div class="point-info-card card shadow-sm">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="card-title mb-0">Информация об объекте</h5>
        <div class="btn-group btn-group-sm" role="group" v-if="point && point.properties && !isEditing">
          <button @click="toggleEditMode(true)" class="btn btn-outline-primary py-1 px-2" title="Редактировать">
            <i class="bi bi-pencil-square"></i> <span class="ms-1 d-none d-md-inline">Редактировать</span>
          </button>
          <button @click="confirmDeletePoint" class="btn btn-outline-danger py-1 px-2" title="Удалить точку" :disabled="isDeleting">
            <i class="bi bi-trash"></i> <span class="ms-1 d-none d-md-inline">Удалить</span>
          </button>
        </div>
      </div>

      <div v-if="point && point.properties">
        <!-- Режим редактирования -->
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
          <div class="d-flex justify-content-end pt-2 border-top mt-3">
            <button type="button" @click="toggleEditMode(false)" class="btn btn-sm btn-secondary me-2">Отмена</button>
            <button type="submit" class="btn btn-sm btn-success" :disabled="isSaving">
              <span v-if="isSaving" class="spinner-border spinner-border-sm me-1"></span>Сохранить
            </button>
          </div>
          <div v-if="editError" class="alert alert-danger p-2 mt-3 small">{{ editError }}</div>
        </form>

        <!-- Режим просмотра -->
        <div v-else class="details">
            <ul class="list-unstyled mb-0">
                <li class="mb-2">
                    <strong class="me-1 d-block text-muted small">Название</strong>
                    {{ point.properties.station_name || point.properties.id || 'None' }}
                </li>
                <li v-if="point.properties.network_class" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Класс сети</strong>
                    {{ point.properties.network_class }}
                </li>
                <li v-if="point.properties.index_name" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Индекс</strong>
                    {{ point.properties.index_name }}
                </li>
                <li v-if="point.properties.center_type" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Тип центра</strong>
                    {{ point.properties.center_type }}
                </li>
                <li v-if="point.properties.mark_number" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Номер марки</strong>
                    {{ point.properties.mark_number }}
                </li>
                <li v-if="point.properties.status" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Статус</strong>
                    {{ point.properties.status }}
                </li>
                <li class="mb-2">
                    <strong class="me-1 d-block text-muted small">Широта и долгота</strong>
                    <span class="font-monospace">{{ point.properties.latitude?.toFixed(6) }}, {{ point.properties.longitude?.toFixed(6) }}</span>
                </li>
                <li v-if="point.properties.timestamp_display" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Время измерения (из RINEX)</strong>
                    <span class="font-monospace">{{ point.properties.timestamp_display }}</span>
                </li>
                 <li v-if="point.properties.description" class="mb-2">
                    <strong class="me-1 d-block text-muted small">Описание</strong>
                    {{ point.properties.description }}
                </li>
                <li v-if="point.properties.source_file" class="mt-3 border-top pt-2">
                    <a :href="downloadUrl" class="btn btn-sm btn-outline-secondary w-100" download>
                        <i class="bi bi-download me-2"></i>Скачать исходный RINEX
                    </a>
                </li>
            </ul>
        </div>
      </div>
      <!-- Заглушки -->
      <div v-else-if="selectedPointIdsInApp?.length > 0" class="placeholder text-muted text-center py-3">
        <i class="bi bi-check2-all fs-3 d-block mb-2 text-primary"></i>
        <p class="fst-italic mb-0">Выбрано точек: <strong>{{ selectedPointIdsInApp.length }}</strong>.<br>Используйте панель действий.</p>
      </div>
      <div v-else class="placeholder text-muted text-center py-3">
        <i class="bi bi-geo-alt fs-3 d-block mb-2"></i>
        <p class="fst-italic mb-0">Кликните на точку или выделите область на карте.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, getCurrentInstance, computed } from 'vue';
import StationNameSelector from './StationNameSelector.vue';

const props = defineProps({
  point: { type: Object, default: null },
  selectedPointIdsInApp: { type: Array, default: () => [] },
  availableStationNames: { type: Array, default: () => [] },
  // --- ПРИНИМАЕМ НОВЫЙ PROP ---
  apiPointsUrl: { type: String, required: true }
});
const emit = defineEmits(['point-updated', 'edit-message', 'point-deleted', 'delete-failed']); 
const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

// --- УДАЛЯЕМ СТАРЫЙ СПОСОБ ПОЛУЧЕНИЯ НАСТРОЕК ---
// const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const isEditing = ref(false), isSaving = ref(false), isDeleting = ref(false), editError = ref('');
const pointTypes = ref([
    { value: 'ggs', text: 'Пункты гос. геодезической сети' }, { value: 'ggs_kurgan', text: 'Пункты ГГС на курганах' },
    { value: 'survey', text: 'Точки съемочной сети' }, { value: 'survey_kurgan', text: 'Точки съемочной сети на курганах' },
    { value: 'astro', text: 'Астрономические пункты' }, { value: 'leveling', text: 'Нивелирные марки/реперы' },
    { value: 'default', text: 'Неопределенный тип' },
]);
const editablePoint = ref({});

// --- ИСПОЛЬЗУЕМ PROP ВМЕСТО $djangoSettings ---
const downloadUrl = computed(() => {
  if (!props.point?.properties?.id) return '#';
  let baseUrl = String(props.apiPointsUrl || '/api/points/').replace(/\/$/, '');
  return `${baseUrl}/${props.point.properties.id}/download-source-file/`;
});

watch(() => props.point, (newPoint) => {
    isEditing.value = false; editError.value = '';
    if (newPoint?.properties) {
        editablePoint.value = {
            id_display: newPoint.properties.id,
            station_name: newPoint.properties.station_name || '',
            description: newPoint.properties.description || '',
            point_type: newPoint.properties.point_type || 'default',
        };
    }
}, { immediate: true, deep: true });

const toggleEditMode = (state) => { isEditing.value = state; editError.value = ''; };

const saveChanges = async () => {
  if (!props.point?.properties?.id) return;
  isSaving.value = true; editError.value = '';
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
    emit('edit-message', { type: 'success', text: 'Данные точки успешно обновлены.' });
    isEditing.value = false;
  } catch (error) { 
    editError.value = error.response?.data?.detail || 'Ошибка сохранения.';
  } finally { isSaving.value = false; }
};

const confirmDeletePoint = () => {
  if (!props.point?.properties?.id) return;
  const name = props.point.properties.station_name || props.point.properties.id;
  if (window.confirm(`Вы уверены, что хотите удалить точку "${name}"?`)) {
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
  } finally { isDeleting.value = false; }
};
</script>

<style scoped>
.details li { margin-bottom: 0.5rem; font-size: 0.9rem; line-height: 1.4; }
.details li strong { color: #6c757d; font-size: 0.8rem; font-weight: 500; }
.form-label.small { font-weight: 500; }
.placeholder i.bi { color: #6c757d; }
</style>