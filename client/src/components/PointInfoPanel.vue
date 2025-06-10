<!-- client/src/components/PointInfoPanel.vue -->
<template>
  <div class="point-info-card card shadow-sm">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="card-title mb-0">Информация о точке</h5>
        <div 
          class="btn-group btn-group-sm" 
          role="group" 
          aria-label="Point actions"
          v-if="point && point.properties && point.properties.id && !isEditing"
        >
          <button 
            @click="toggleEditMode(true)" 
            class="btn btn-outline-primary py-1 px-2" 
            title="Редактировать"
          >
            <i class="bi bi-pencil-square"></i>
            <span class="ms-1 d-none d-md-inline">Редактировать</span>
          </button>
          <button 
            @click="confirmDeletePoint" 
            class="btn btn-outline-danger py-1 px-2" 
            title="Удалить точку" 
            :disabled="isDeleting"
          >
            <i class="bi bi-trash"></i>
            <span class="ms-1 d-none d-md-inline">Удалить</span>
          </button>
        </div>
      </div>

      <div v-if="point && point.properties && point.properties.id">
        <form @submit.prevent="saveChanges" v-if="isEditing">
          <div class="mb-2 small">
            <strong>ID (RINEX Marker):</strong> {{ editablePoint.id_display }}
          </div>
          
          <!-- Используем StationNameSelector -->
          <StationNameSelector
            v-model="editablePoint.station_name" 
            label="Имя точки (присвоенное)"
            placeholder="Введите или выберите имя"
            :available-names="props.availableStationNames" 
          />

          <div class="mb-3">
            <label for="pointTypeEdit" class="form-label mb-1 small"><strong>Тип точки:</strong></label>
            <select 
              id="pointTypeEdit" 
              class="form-select form-select-sm" 
              v-model="editablePoint.point_type" 
              required
            >
              <option disabled value="">Выберите тип...</option>
              <option v-for="ptype in pointTypes" :key="ptype.value" :value="ptype.value">
                {{ ptype.text }}
              </option>
            </select>
          </div>

          <div class="mb-2 small">
            <strong>Координаты (Lat, Lon):</strong> 
            <span class="font-monospace">
              {{ point.properties.latitude?.toFixed(6) || 'N/A' }}, 
              {{ point.properties.longitude?.toFixed(6) || 'N/A' }}
            </span>
          </div>
          <div class="mb-2 small">
            <strong>Время наблюдения:</strong> 
            <span class="font-monospace">{{ point.properties.timestamp_display || 'N/A' }}</span>
          </div>
          
          <div class="mb-2 small" v-if="point.properties.receiver_number">
            <strong>Номер приемника:</strong> {{ point.properties.receiver_number }}
          </div>
          <div class="mb-2 small" v-if="point.properties.antenna_height != null">
            <strong>Высота антенны (H):</strong> {{ point.properties.antenna_height.toFixed(4) }} м
          </div>

          <div class="mb-3">
            <label for="pointDescriptionEdit" class="form-label mb-1 small"><strong>Описание:</strong></label>
            <textarea 
              id="pointDescriptionEdit" 
              class="form-control form-control-sm" 
              v-model.trim="editablePoint.description" 
              rows="2"
            ></textarea>
          </div>

          <div class="d-flex justify-content-end pt-2 border-top mt-3">
            <button type="button" @click="toggleEditMode(false)" class="btn btn-sm btn-secondary me-2">Отмена</button>
            <button type="submit" class="btn btn-sm btn-success" :disabled="isSaving || !isFormValidWhenEditing">
              <span v-if="isSaving" class="spinner-border spinner-border-sm me-1"></span>Сохранить
            </button>
          </div>
          <div v-if="editError" class="alert alert-danger p-2 mt-3 small" role="alert">{{ editError }}</div>
        </form>

        <div v-else class="details">
          <ul class="list-unstyled mb-0">
            <li class="mb-1"><strong class="me-1">ID (RINEX Marker):</strong> {{ point.properties.id }}</li>
            <li class="mb-1" v-if="point.properties.station_name"><strong class="me-1">Имя точки:</strong> {{ point.properties.station_name }}</li>
            <li class="mb-1"><strong class="me-1">Тип:</strong> {{ point.properties.point_type_display || pointTypeToText(point.properties.point_type) || 'Неопределен' }}</li>
            <li class="mb-1">
              <strong class="me-1">Координаты (Lat, Lon):</strong> 
              <span class="font-monospace">
                {{ point.properties.latitude?.toFixed(6) || 'N/A' }}, 
                {{ point.properties.longitude?.toFixed(6) || 'N/A' }}
              </span>
            </li>
            <li class="mb-1"><strong class="me-1">Время наблюдения:</strong> <span class="font-monospace">{{ point.properties.timestamp_display || 'N/A' }}</span></li>
            <li class="mb-1" v-if="point.properties.receiver_number"><strong class="me-1">Номер приемника:</strong> {{ point.properties.receiver_number }}</li>
            <li class="mb-1" v-if="point.properties.antenna_height != null"><strong class="me-1">Высота антенны (H):</strong> {{ point.properties.antenna_height.toFixed(4) }} м</li>
            <li class="mb-0"><strong class="me-1">Описание:</strong> {{ point.properties.description || 'Нет описания' }}</li>
          </ul>
        </div>
      </div>
      <div v-else-if="selectedPointIdsInApp && selectedPointIdsInApp.length > 0" class="placeholder text-muted text-center py-3">
        <i class="bi bi-check2-all fs-3 d-block mb-2 text-primary"></i>
        <p class="fst-italic mb-0">Выбрано точек: <strong>{{ selectedPointIdsInApp.length }}</strong>.<br>Используйте панель действий.</p>
      </div>
      <div v-else class="placeholder text-muted text-center py-3">
        <i class="bi bi-geo-alt fs-3 d-block mb-2"></i>
        <p class="fst-italic mb-0">Кликните на точку для информации или выберите несколько.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, getCurrentInstance, computed } from 'vue';
import StationNameSelector from './StationNameSelector.vue'; // Упрощенный селектор

const props = defineProps({
  point: { type: Object, default: null },
  selectedPointIdsInApp: { type: Array, default: () => [] },
  availableStationNames: { type: Array, default: () => [] } // Принимаем этот проп
});

const emit = defineEmits(['point-updated', 'edit-message', 'point-deleted', 'delete-failed']); 

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const isEditing = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const editError = ref('');

const pointTypes = ref([
    { value: 'ggs', text: 'Пункты гос. геодезической сети' },
    { value: 'ggs_kurgan', text: 'Пункты ГГС на курганах' },
    { value: 'survey', text: 'Точки съемочной сети' },
    { value: 'survey_kurgan', text: 'Точки съемочной сети на курганах' },
    { value: 'astro', text: 'Астрономические пункты' },
    { value: 'leveling', text: 'Нивелирные марки/реперы' },
    { value: 'default', text: 'Неопределенный тип' },
]);

const editablePoint = ref({
  id_display: '', 
  station_name: '', 
  description: '',
  point_type: 'default'
});

const isFormValidWhenEditing = computed(() => {
    return editablePoint.value.point_type && editablePoint.value.point_type !== '';
});

const pointTypeToText = (value) => {
  const found = pointTypes.value.find(pt => pt.value === value);
  return found ? found.text : (value || 'N/A'); 
};

watch(() => props.point, (newPoint) => {
  const currentPointIdInForm = String(props.point?.properties?.id);
  const newPointId = String(newPoint?.properties?.id);

  if (newPoint && newPoint.properties && newPoint.properties.id) {
    if (isEditing.value && currentPointIdInForm !== newPointId) {
        isEditing.value = false;
    }
    if (!isEditing.value || currentPointIdInForm !== newPointId) {
        editablePoint.value.id_display = newPointId;
        editablePoint.value.station_name = newPoint.properties.station_name || '';
        editablePoint.value.description = newPoint.properties.description || '';
        editablePoint.value.point_type = newPoint.properties.point_type || 'default';
    }
  } else {
    isEditing.value = false;
    editablePoint.value.id_display = '';
    editablePoint.value.station_name = '';
    editablePoint.value.description = '';
    editablePoint.value.point_type = 'default';
  }
  editError.value = '';
}, { immediate: true, deep: true });

const toggleEditMode = (editingState) => {
  if (editingState && props.point && props.point.properties && props.point.properties.id) {
    isEditing.value = true;
  } else if (!editingState) {
    isEditing.value = false;
    if (props.point && props.point.properties) { // Восстанавливаем значения при отмене
        editablePoint.value.station_name = props.point.properties.station_name || '';
        editablePoint.value.description = props.point.properties.description || '';
        editablePoint.value.point_type = props.point.properties.point_type || 'default';
    }
  } else if (editingState) {
    emit('edit-message', { type: 'warning', text: 'Выберите одну точку для редактирования.' });
  }
  editError.value = '';
};

const saveChanges = async () => {
  if (!props.point || !props.point.properties || !props.point.properties.id) {
    editError.value = "Ошибка: ID точки для сохранения не определен."; return;
  }
  if (!isFormValidWhenEditing.value) {
      editError.value = "Пожалуйста, выберите тип точки."; return;
  }
  isSaving.value = true; editError.value = '';
  try {
    const payload = {
      station_name: editablePoint.value.station_name.trim(),
      description: editablePoint.value.description.trim(),
      point_type: editablePoint.value.point_type
    };
    const pointIdForUrl = String(props.point.properties.id);
    let baseUrl = String($djangoSettings.apiPointsUrl || '/api/points/');
    if (!baseUrl.endsWith('/')) baseUrl += '/';
    const url = `${baseUrl}${pointIdForUrl}/`;

    const response = await $axios.patch(url, payload);
    emit('point-updated', response.data);
    emit('edit-message', { type: 'success', text: 'Данные точки успешно обновлены.' });
    isEditing.value = false;
  } catch (error) { 
    console.error('[PointInfoPanel] Ошибка сохранения:', error);
    if (error.response && error.response.data) {
        const errors = error.response.data;
        let errorMessages = [];
        if (errors.station_name) errorMessages.push(`Имя станции: ${Array.isArray(errors.station_name) ? errors.station_name.join(', ') : errors.station_name}`);
        if (errors.description) errorMessages.push(`Описание: ${Array.isArray(errors.description) ? errors.description.join(', ') : errors.description}`);
        if (errors.point_type) errorMessages.push(`Тип точки: ${Array.isArray(errors.point_type) ? errors.point_type.join(', ') : errors.point_type}`);
        if (errors.detail && errorMessages.length === 0) { errorMessages.push(String(errors.detail));}
        
        if (errorMessages.length > 0) { editError.value = errorMessages.join('; '); }
        else if (typeof errors === 'string' ) { editError.value = errors; }
        else { editError.value = 'Ошибка валидации на сервере. Подробности в консоли.'; console.warn("Не удалось разобрать ошибки от сервера: ", errors)}
    } else if (error.request) { editError.value = 'Сервер не ответил на запрос сохранения.'; }
    else { editError.value = `Ошибка при отправке запроса на сохранение: ${error.message}`; }
  } 
  finally { isSaving.value = false; }
};

const confirmDeletePoint = () => {
  if (!props.point || !props.point.properties || !props.point.properties.id) {
    emit('edit-message', { type: 'warning', text: 'Не выбрана точка для удаления.' }); return;
  }
  const pointDisplayId = props.point.properties.station_name || props.point.properties.id;
  if (window.confirm(`Вы уверены, что хотите удалить точку "${pointDisplayId}"?`)) {
    deletePoint();
  }
};

const deletePoint = async () => {
  const pointIdToDelete = String(props.point.properties.id);
  isDeleting.value = true;
  try {
    let baseUrl = String($djangoSettings.apiPointsUrl || '/api/points/');
    if (!baseUrl.endsWith('/')) baseUrl += '/';
    const url = `${baseUrl}${pointIdToDelete}/`;
    await $axios.delete(url);
    emit('point-deleted', pointIdToDelete);
    isEditing.value = false;
  } catch (error) { 
    console.error('[PointInfoPanel] Ошибка удаления:', error);
    let deleteErrorMessage = `Не удалось удалить точку ID ${pointIdToDelete}.`;
    if (error.response && error.response.data && error.response.data.detail) {
        deleteErrorMessage = error.response.data.detail;
    } else if (error.response && error.response.statusText) {
        deleteErrorMessage += ` Статус: ${error.response.statusText} (${error.response.status})`;
    } else if (error.message) {
        deleteErrorMessage += ` ${error.message}`;
    }
    emit('delete-failed', { id: pointIdToDelete, message: deleteErrorMessage });
  }
  finally { isDeleting.value = false; }
};
</script>

<style scoped>
.details li { margin-bottom: 0.3rem; font-size: 0.9rem; }
.details li strong { color: #495057; }
.form-label.small { font-weight: 500; color: #495057; }
.form-text.small { font-size: 0.75rem; }
.alert.small { font-size: 0.875rem; padding: 0.5rem 0.75rem; }
.placeholder i.bi { color: #6c757d; }
.btn .ms-1.d-none.d-md-inline { vertical-align: middle; }
.btn-group-sm > .btn i.bi { 
  font-size: 0.9rem;
  vertical-align: text-bottom;
}
</style>