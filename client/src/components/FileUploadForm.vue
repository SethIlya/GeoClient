<!-- client/src/components/FileUploadForm.vue -->
<template>
  <div class="file-upload-section card shadow-sm">
    <div class="card-body">
      <h5 class="card-title mb-3">Загрузить RINEX файл(ы)</h5>
      <form @submit.prevent="handleFileUpload">
        <div class="mb-3">
          <label for="rinexFile" class="form-label">Выберите файл(ы) (.o):</label>
          <input
            type="file"
            class="form-control"
            id="rinexFile"
            ref="fileInput"
            @change="onFileSelected"
            accept=".25o,.25g,.25n.o,.g,.n,.rnx"
            required
            multiple  повадки 
          />
        </div>
        <button type="submit" :disabled="isUploading || !selectedFiles.length" class="btn btn-primary w-100">
          <span v-if="isUploading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          {{ isUploading ? ' Загрузка...' : (selectedFiles.length > 1 ? `Загрузить ${selectedFiles.length} файла(ов)` : 'Загрузить и обработать') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, getCurrentInstance, defineEmits } from 'vue';

const fileInput = ref(null);
const selectedFiles = ref([]); // Изменено на массив
const isUploading = ref(false);

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const emit = defineEmits(['upload-complete', 'upload-message']);

const onFileSelected = (event) => {
  selectedFiles.value = Array.from(event.target.files); // Преобразуем FileList в массив
};

const handleFileUpload = async () => {
  if (!selectedFiles.value.length) {
    emit('upload-message', { type: 'warning', text: 'Пожалуйста, выберите хотя бы один файл.' });
    return;
  }
  isUploading.value = true;
  const formData = new FormData();
  selectedFiles.value.forEach(file => {
    formData.append('rinex_files', file); // Используем 'rinex_files' (plural) как ключ
  });

  try {
    const response = await $axios.post($djangoSettings.apiUploadUrl, formData);
    emit('upload-complete', response.data);
  } catch (error) {
    console.error('Ошибка загрузки файла(ов):', error);
    let errorMessage = 'Произошла ошибка при загрузке файла(ов).';
    if (error.response && error.response.data) {
        errorMessage = error.response.data.message ||
                       (error.response.data.detail) ||
                       (typeof error.response.data.errors === 'object' ? Object.values(error.response.data.errors).flat().join(' ') : errorMessage);
    }
    emit('upload-complete', { success: false, message: errorMessage, messages: [{type: 'danger', text: errorMessage}] });
  } finally {
    isUploading.value = false;
    if (fileInput.value) fileInput.value.value = ''; // Очищаем input
    selectedFiles.value = []; // Очищаем массив выбранных файлов
  }
};
</script>

<style scoped>
/* Стили остаются прежними */
</style>