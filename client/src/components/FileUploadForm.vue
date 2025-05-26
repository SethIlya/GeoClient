<template>
  <div class="file-upload-section card shadow-sm">
    <div class="card-body">
      <h5 class="card-title mb-3">Загрузить RINEX файл</h5>
      <form @submit.prevent="handleFileUpload">
        <div class="mb-3">
          <label for="rinexFile" class="form-label">Выберите файл (.o, .n, .g, .rnx):</label>
          <input 
            type="file" 
            class="form-control"
            id="rinexFile"
            ref="fileInput" 
            @change="onFileSelected" 
            accept=".25o,.25g,.25n,.o,.g,.n,.rnx"
            required 
          />
        </div>
        <button type="submit" :disabled="isUploading" class="btn btn-primary w-100">
          <span v-if="isUploading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          {{ isUploading ? ' Загрузка...' : 'Загрузить и обработать' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, getCurrentInstance, defineEmits } from 'vue';

const fileInput = ref(null);
const selectedFile = ref(null);
const isUploading = ref(false);

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;
const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const emit = defineEmits(['upload-complete', 'upload-message']);

const onFileSelected = (event) => {
  selectedFile.value = event.target.files[0];
};

const handleFileUpload = async () => {
  if (!selectedFile.value) {
    emit('upload-message', { type: 'warning', text: 'Пожалуйста, выберите файл.' });
    return;
  }
  isUploading.value = true;
  const formData = new FormData();
  formData.append('rinex_file', selectedFile.value);

  try {
    const response = await $axios.post($djangoSettings.apiUploadUrl, formData);
    emit('upload-complete', response.data);
  } catch (error) {
    console.error('Ошибка загрузки файла:', error);
    let errorMessage = 'Произошла ошибка при загрузке файла.';
    if (error.response && error.response.data) {
        errorMessage = error.response.data.message || 
                       (typeof error.response.data.errors === 'object' ? Object.values(error.response.data.errors).flat().join(' ') : errorMessage);
    }
    emit('upload-complete', { success: false, message: errorMessage, messages: [{type: 'danger', text: errorMessage}] });
  } finally {
    isUploading.value = false;
    if (fileInput.value) fileInput.value.value = '';
    selectedFile.value = null;
  }
};
</script>

<style scoped>
/* Минимальные кастомные стили, если Bootstrap не покрывает все */
</style>