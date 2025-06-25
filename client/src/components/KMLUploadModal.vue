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
            Выберите один или несколько KML-файлов, экспортированных из GeoEye, чтобы обновить данные для существующих на карте точек.
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
             <div class="d-grid">
                <!-- 
                  --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ ---
                  Добавляем атрибут data-bs-dismiss="modal".
                  Теперь Bootstrap сам закроет окно при клике на эту кнопку.
                -->
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
  
  // Отправляем событие с данными, как и раньше
  emit('upload-kml', { formData });

  // Очищаем форму для следующего открытия
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  selectedFiles.value = [];
};
</script>

<style scoped>
.modal-title i {
    color: var(--bs-info);
}
</style>