<!-- client/src/components/PointInfoPanel.vue -->
<template>
  <div class="point-info-card card shadow-sm">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="card-title mb-0">Информация о точке</h5>
        <!-- Кнопки действий для ОДНОЙ выбранной точки (когда point не null) -->
        <div
          class="btn-group btn-group-sm"
          role="group"
          aria-label="Point actions"
          v-if="point && point.properties && point.properties.id != null && !isEditing"
        >
          <button
            @click="toggleEditMode(true)"
            class="btn btn-outline-primary py-1 px-2"
            title="Редактировать"
            aria-label="Редактировать точку"
          >
            <i class="bi bi-pencil-square"></i>
            <span class="ms-1 d-none d-md-inline">Редактировать</span>
          </button>
          <button
            @click="confirmDeletePoint"
            class="btn btn-outline-danger py-1 px-2"
            title="Удалить точку"
            aria-label="Удалить точку"
            :disabled="isDeleting"
          >
            <i class="bi bi-trash"></i>
            <span class="ms-1 d-none d-md-inline">Удалить</span>
          </button>
        </div>
      </div>

      <!-- Отображение информации или формы редактирования для ОДНОЙ точки -->
      <div v-if="point && point.properties">
        <form @submit.prevent="saveChanges" v-if="isEditing">
          <div class="mb-2 small">
            <strong>ID:</strong> {{ editablePoint.id_display }}
          </div>
          <div class="mb-3">
            <label for="pointName" class="form-label mb-1 small"><strong>Имя точки:</strong></label>
            <input
              type="text"
              id="pointName"
              class="form-control form-control-sm"
              v-model.trim="editablePoint.name"
              required
              aria-describedby="nameHelp"
            >
            <div id="nameHelp" class="form-text small">Обязательное поле.</div>
          </div>
          <div class="mb-3">
            <label for="pointType" class="form-label mb-1 small"><strong>Тип точки:</strong></label>
            <select
              id="pointType"
              class="form-select form-select-sm"
              v-model="editablePoint.point_type"
              required
              aria-describedby="typeHelp"
            >
              <option disabled value="">Выберите тип...</option>
              <option v-for="ptype in pointTypes" :key="ptype.value" :value="ptype.value">
                {{ ptype.text }}
              </option>
            </select>
            <div id="typeHelp" class="form-text small">Обязательное поле.</div>
          </div>
          <div class="mb-2 small">
            <strong>Координаты:</strong>
            <span v-if="point.properties.latitude !== null && point.properties.longitude !== null" class="font-monospace">
              {{ parseFloat(point.properties.latitude).toFixed(6) }},
              {{ parseFloat(point.properties.longitude).toFixed(6) }}
            </span>
            <span v-else class="text-muted">N/A</span>
          </div>
          <div class="mb-2 small">
            <strong>Время:</strong>
            <span class="font-monospace">{{ point.properties.timestamp_display || 'N/A' }}</span>
          </div>
          <div class="mb-3">
            <label for="pointDescription" class="form-label mb-1 small"><strong>Описание:</strong></label>
            <textarea
              id="pointDescription"
              class="form-control form-control-sm"
              v-model.trim="editablePoint.description"
              rows="3"
            ></textarea>
          </div>
          <div class="d-flex justify-content-end pt-2 border-top mt-3">
            <button
              type="button"
              @click="toggleEditMode(false)"
              class="btn btn-sm btn-secondary me-2"
            >
              Отмена
            </button>
            <button
              type="submit"
              class="btn btn-sm btn-success"
              :disabled="isSaving || !isFormValid"
            >
              <span v-if="isSaving" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
              Сохранить
            </button>
          </div>
          <div v-if="editError" class="alert alert-danger p-2 mt-3 small" role="alert">
            {{ editError }}
          </div>
        </form>

        <div v-else class="details">
          <ul class="list-unstyled mb-0">
            <li class="mb-1"><strong class="me-1">ID:</strong> {{ point.properties.id }}</li>
            <li class="mb-1"><strong class="me-1">Имя:</strong> {{ point.properties.name || 'N/A' }}</li>
            <li class="mb-1"><strong class="me-1">Тип:</strong> {{ point.properties.point_type_display || pointTypeToText(point.properties.point_type) || 'Неопределен' }}</li>
            <li class="mb-1">
              <strong class="me-1">Координаты:</strong>
              <span v-if="point.properties.latitude !== null && point.properties.longitude !== null" class="font-monospace">
                {{ parseFloat(point.properties.latitude).toFixed(6) }},
                {{ parseFloat(point.properties.longitude).toFixed(6) }}
              </span>
              <span v-else class="text-muted">N/A</span>
            </li>
            <li class="mb-1"><strong class="me-1">Время:</strong> <span class="font-monospace">{{ point.properties.timestamp_display || 'N/A' }}</span></li>
            <li class="mb-0"><strong class="me-1">Описание:</strong> {{ point.properties.description || 'Нет описания' }}</li>
          </ul>
        </div>
      </div>
      <!-- Сообщение, если выбрано несколько точек (передаем selectedPointIdsInApp из App.vue) -->
      <div v-else-if="selectedPointIdsInApp && selectedPointIdsInApp.length > 0" class="placeholder text-muted text-center py-3">
        <i class="bi bi-check2-all fs-3 d-block mb-2" style="color: var(--bs-primary);"></i>
        <p class="fst-italic mb-0">
            Выбрано точек: <strong>{{ selectedPointIdsInApp.length }}</strong>.<br>
            Используйте панель действий выше для групповых операций.
        </p>
      </div>
      <!-- Сообщение по умолчанию, если ничего не выбрано -->
      <div v-else class="placeholder text-muted text-center py-3">
        <i class="bi bi-geo-alt fs-3 d-block mb-2"></i>
        <p class="fst-italic mb-0">Кликните на точку на карте для просмотра информации или выберите несколько точек для групповых действий.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits, getCurrentInstance, computed } from 'vue';

const props = defineProps({
  point: { // Это lastSelectedPointDetails из App.vue (детали последней кликнутой точки)
    type: Object,
    default: null
  },
  selectedPointIdsInApp: { // Массив ID всех выбранных точек из App.vue
      type: Array,
      default: () => []
  }
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
  id_from_properties: null,
  id_display: '',
  name: '',
  description: '',
  point_type: 'default'
});

const isFormValid = computed(() => {
    return editablePoint.value.name && editablePoint.value.name.trim() !== '' &&
           editablePoint.value.point_type && editablePoint.value.point_type !== '';
});

const pointTypeToText = (value) => {
  const found = pointTypes.value.find(pt => pt.value === value);
  return found ? found.text : value;
};

watch(() => props.point, (newPoint) => {
  // Эта панель работает только с одной точкой (последней кликнутой)
  if (newPoint && newPoint.properties && newPoint.properties.id != null) {
    // Если режим редактирования активен и ID точки изменился, сбрасываем редактирование
    if (isEditing.value && editablePoint.value.id_from_properties !== newPoint.properties.id) {
        isEditing.value = false;
    }
    // Заполняем editablePoint, только если не в режиме редактирования для текущей точки,
    // или если точка изменилась
    if (!isEditing.value || editablePoint.value.id_from_properties !== newPoint.properties.id) {
        editablePoint.value.id_from_properties = newPoint.properties.id;
        editablePoint.value.id_display = String(newPoint.properties.id);
        editablePoint.value.name = newPoint.properties.name || '';
        editablePoint.value.description = newPoint.properties.description || '';
        editablePoint.value.point_type = newPoint.properties.point_type || 'default';
    }
  } else {
    // Если точка не передана (например, снято выделение с последней кликнутой),
    // сбрасываем редактирование и данные
    isEditing.value = false;
    editablePoint.value.id_from_properties = null;
    editablePoint.value.id_display = '';
    editablePoint.value.name = '';
    editablePoint.value.description = '';
    editablePoint.value.point_type = 'default';
  }
  editError.value = ''; // Сбрасываем ошибку при смене точки
}, { immediate: true, deep: true });

const toggleEditMode = (editingState) => {
  if (editingState && props.point && props.point.properties && props.point.properties.id != null) {
    // Включаем режим редактирования, копируем текущие данные точки
    isEditing.value = true;
    editablePoint.value.id_from_properties = props.point.properties.id; // Убедимся, что ID установлен
    editablePoint.value.id_display = String(props.point.properties.id);
    editablePoint.value.name = props.point.properties.name || '';
    editablePoint.value.description = props.point.properties.description || '';
    editablePoint.value.point_type = props.point.properties.point_type || 'default';
  } else if (!editingState) {
    // Выключаем режим редактирования, данные в editablePoint уже должны быть актуальны от watch
    isEditing.value = false;
  } else if (editingState) { // Попытка редактировать, когда нет props.point
    emit('edit-message', { type: 'warning', text: 'Выберите одну точку для редактирования.' });
  }
  editError.value = '';
};

const saveChanges = async () => {
  if (editablePoint.value.id_from_properties == null) {
    editError.value = "Ошибка: ID точки для сохранения не определен.";
    return;
  }
  if (!isFormValid.value) {
      editError.value = "Пожалуйста, заполните все обязательные поля (Имя, Тип точки).";
      return;
  }
  isSaving.value = true;
  editError.value = '';

  try {
    const payload = {
      name: editablePoint.value.name.trim(),
      description: editablePoint.value.description.trim(),
      point_type: editablePoint.value.point_type
    };
    let baseUrl = String($djangoSettings.apiPointsUrl || '/api/points/');
    if (!baseUrl.endsWith('/')) baseUrl += '/';
    const url = `${baseUrl}${editablePoint.value.id_from_properties}/`;

    const response = await $axios.patch(url, payload);
    emit('point-updated', response.data);
    emit('edit-message', { type: 'success', text: 'Данные точки успешно обновлены.' });
    isEditing.value = false; // Выходим из режима редактирования
  } catch (error) {
    console.error('[PointInfoPanel] Ошибка сохранения данных точки:', error);
    if (error.response) {
        const errors = error.response.data;
        // ... (логика обработки ошибок сервера остается прежней) ...
        if (typeof errors === 'object' && errors !== null) {
            let errorMessages = [];
            if (errors.name) errorMessages.push(`Имя: ${Array.isArray(errors.name) ? errors.name.join(', ') : errors.name}`);
            if (errors.description) errorMessages.push(`Описание: ${Array.isArray(errors.description) ? errors.description.join(', ') : errors.description}`);
            if (errors.point_type) errorMessages.push(`Тип точки: ${Array.isArray(errors.point_type) ? errors.point_type.join(', ') : errors.point_type}`);
            if (errors.detail && errorMessages.length === 0) { errorMessages.push(String(errors.detail));}
            if (errorMessages.length > 0) { editError.value = errorMessages.join('; '); }
            else { editError.value = 'Ошибка валидации на сервере.'; console.warn("Не удалось разобрать ошибки: ", errors)}
        } else if (typeof errors === 'string') { editError.value = errors; }
        else { editError.value = 'Не удалось сохранить изменения. Неизвестная ошибка сервера.'; }

    } else if (error.request) { editError.value = 'Сервер не ответил.'; }
    else { editError.value = `Ошибка при отправке запроса: ${error.message}`; }
  } finally {
    isSaving.value = false;
  }
};

const confirmDeletePoint = () => { // Для удаления одной точки из этой панели
  if (!props.point || !props.point.properties || props.point.properties.id == null) {
    emit('edit-message', { type: 'warning', text: 'Не выбрана точка для удаления.' });
    return;
  }
  const pointNameToDelete = props.point.properties.name || `ID ${props.point.properties.id}`;
  if (window.confirm(`Вы уверены, что хотите удалить точку "${pointNameToDelete}"? Это действие необратимо.`)) {
    deletePoint();
  }
};

const deletePoint = async () => { // Для удаления одной точки из этой панели
  const pointIdToDelete = props.point.properties.id;
  isDeleting.value = true;
  // emit('edit-message', { type: 'info', text: `Удаление точки ID ${pointIdToDelete}...` });

  try {
    let baseUrl = String($djangoSettings.apiPointsUrl || '/api/points/');
    if (!baseUrl.endsWith('/')) baseUrl += '/';
    const url = `${baseUrl}${pointIdToDelete}/`;

    await $axios.delete(url);
    emit('point-deleted', pointIdToDelete); // Сообщаем App.vue, что ОДНА точка удалена
    // emit('edit-message', { type: 'success', text: `Точка ID ${pointIdToDelete} успешно удалена.` });
    // App.vue теперь сам даст сообщение об удалении
    isEditing.value = false; // Если были в режиме редактирования этой точки
  } catch (error) {
    console.error('[PointInfoPanel] Ошибка удаления точки:', error);
    let deleteErrorMessage = `Не удалось удалить точку ID ${pointIdToDelete}.`;
    // ... (логика формирования сообщения об ошибке остается прежней) ...
    if (error.response) {
        if (error.response.data && error.response.data.detail) {
            deleteErrorMessage = error.response.data.detail;
        } else if (error.response.statusText) {
            deleteErrorMessage += ` Статус: ${error.response.statusText} (${error.response.status})`;
        }
    } else if (error.message) {
        deleteErrorMessage += ` ${error.message}`;
    }
    emit('delete-failed', { id: pointIdToDelete, message: deleteErrorMessage });
    // emit('edit-message', { type: 'danger', text: deleteErrorMessage });
  } finally {
    isDeleting.value = false;
  }
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