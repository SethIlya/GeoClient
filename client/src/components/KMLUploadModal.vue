<template>
  <div class="modal fade" :id="modalId" tabindex="-1" :aria-labelledby="`${modalId}Label`" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" :id="`${modalId}Label`">
            <i class="bi bi-geo-alt-fill me-2"></i>Загрузка KML файлов
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <p class="text-muted small">
            Выберите один или несколько KML-файлов для обновления данных существующих на карте точек.
          </p>
          <form @submit.prevent="submitForm">
            <div class="mb-3">
              <label for="kmlFileInput" class="form-label">KML файл(ы):</label>
              <input
                type="file"
                class="form-control"
                id="kmlFileInput"
                ref="fileInput"
                @change="onFileSelected"
                accept=".kml"
                required
                multiple 
              />
              <div v-if="selectedFiles.length > 0" class="form-text small mt-1">
                Выбрано файлов: {{ selectedFiles.length }}
              </div>
            </div>

            <!-- ===== ИЗМЕНЕНИЕ: Добавляем поле для радиуса ===== -->
            <div class="mb-3">
              <label for="kmlSearchRadius" class="form-label">Радиус поиска (в метрах):</label>
              <input
                type="number"
                class="form-control"
                id="kmlSearchRadius"
                v-model.number="searchRadius"
                min="1"
                max="100"
                required
              />
              <div class="form-text small mt-1">
                Радиус, в котором будет искаться существующая точка RINEX для сопоставления с точкой из KML.
              </div>
            </div>
            <!-- ===== КОНЕЦ ИЗМЕНЕНИЯ ===== -->

             <div class="d-grid">
                <button 
                  type="submit" 
                  class="btn btn-primary" 
                  :disabled="selectedFiles.length === 0"
                  data-bs-dismiss="modal"
                >
                    <i class="bi bi-cloud-arrow-up-fill me-2"></i>Загрузить и обновить ({{ selectedFiles.length }})
                </button>
             </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  modalId: { type: String, required: true }
});

const emit = defineEmits(['upload-kml']);

const selectedFiles = ref([]);
const fileInput = ref(null);
// ===== ИЗМЕНЕНИЕ: Создаем ref для хранения значения радиуса =====
const searchRadius = ref(3);

const onFileSelected = (event) => {
  selectedFiles.value = Array.from(event.target.files);
};

const submitForm = () => {
  if (selectedFiles.value.length === 0) {
    return;
  }
  const formData = new FormData();
  selectedFiles.value.forEach(file => {
      formData.append('kml_files', file);
  });
  
  // ===== ИЗМЕНЕНИЕ: Добавляем значение радиуса в FormData =====
  formData.append('radius', searchRadius.value);

  // Отправляем событие с данными, как и раньше
  emit('upload-kml', { formData });

  // Очищаем форму для следующего открытия
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  selectedFiles.value = [];
  // Значение радиуса не сбрасываем, чтобы пользователь мог использовать его повторно
};
</script>

<style scoped>
.modal-title i {
    color: var(--bs-info);
}
</style>