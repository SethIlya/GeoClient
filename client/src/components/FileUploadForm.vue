<template>
  <div class="file-upload-section card shadow-sm">
    <div class="card-body">
      <h5 class="card-title mb-3">Загрузить RINEX файл(ы)</h5>
      <form @submit.prevent="handleFileUpload">
        <div class="mb-3">
          <label for="rinexFile" class="form-label">Выберите файл(ы) (.o, .n, .g, .rnx):</label>
          <input
            type="file"
            class="form-control form-control-sm" 
            id="rinexFile"
            ref="fileInput"
            @change="onFileSelected"
            accept=".rnx, .obs, .nav, .o, .n, .g, .24o, .23o, .22o, .21o, .20o" 
            required
            multiple
          />
          <div class="form-text small" v-if="selectedFiles.length > 0">
            Выбрано файлов: {{ selectedFiles.length }}
            <ul>
                <li v-for="file in selectedFiles.slice(0, 5)" :key="file.name" class="text-muted" style="font-size: 0.75rem;">
                    {{ file.name }} ({{ (file.size / 1024).toFixed(1) }} KB)
                </li>
                <li v-if="selectedFiles.length > 5" class="text-muted" style="font-size: 0.75rem;">... и еще {{ selectedFiles.length - 5 }}.</li>
            </ul>
          </div>
        </div>
        <button 
          type="submit" 
          :disabled="isUploading || !selectedFiles.length" 
          class="btn btn-primary btn-sm w-100"
        >
          <span v-if="isUploading" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
          {{ isUploading ? 'Загрузка...' : (selectedFiles.length === 1 ? 'Загрузить 1 файл' : `Загрузить ${selectedFiles.length} файла(ов)`) }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, getCurrentInstance, defineProps } from 'vue';

// --- ПРИНИМАЕМ PROP ОТ App.vue ---
const props = defineProps({
    apiUploadUrl: {
        type: String,
        required: true
    }
});

const fileInput = ref(null);
const selectedFiles = ref([]);
const isUploading = ref(false);

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

// --- УДАЛЯЕМ СТАРЫЙ СПОСОБ ПОЛУЧЕНИЯ НАСТРОЕК ---
// const $djangoSettings = instance.appContext.config.globalProperties.$djangoSettings;

const emit = defineEmits(['upload-complete', 'upload-message']);

const onFileSelected = (event) => {
  selectedFiles.value = Array.from(event.target.files);
};

const handleFileUpload = async () => {
  if (!selectedFiles.value.length) {
    emit('upload-message', { type: 'warning', text: 'Пожалуйста, выберите хотя бы один файл.' });
    return;
  }
  isUploading.value = true;
  emit('upload-message', { type: 'info', text: `Начинается загрузка ${selectedFiles.value.length} файла(ов)...`});

  const formData = new FormData();
  selectedFiles.value.forEach(file => {
    formData.append('rinex_files', file);
  });

  try {
    // --- ИСПОЛЬЗУЕМ URL ИЗ PROPS ---
    const response = await $axios.post(props.apiUploadUrl, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
    emit('upload-complete', response.data); 
  } catch (error) {
    console.error('Ошибка загрузки файла(ов):', error);
    let errorMessage = 'Произошла ошибка при загрузке файла(ов).';
    if (error.response) {
        if (error.response.data) {
            if (typeof error.response.data.detail === 'string') {
                errorMessage = error.response.data.detail;
            } else if (typeof error.response.data.message === 'string') {
                errorMessage = error.response.data.message;
            } else if (Array.isArray(error.response.data.errors)) {
                errorMessage = error.response.data.errors.join(' ');
            }
        } else if (error.response.statusText) {
             errorMessage = `Ошибка сервера: ${error.response.status} ${error.response.statusText}`;
        }
    }
    emit('upload-complete', { 
        success: false, 
        message: errorMessage,
        messages: [{type: 'danger', text: errorMessage}],
        total_created_count: 0 
    });
  } finally {
    isUploading.value = false;
    if (fileInput.value) {
      fileInput.value.value = '';
    }
    selectedFiles.value = [];
  }
};
</script>

<style scoped>
.file-upload-section .card-body {
  padding: 1rem;
}
.file-upload-section .card-title {
  font-size: 1.1rem;
  font-weight: 500;
}
.form-text ul {
    padding-left: 1.2rem;
    margin-bottom: 0;
}
</style>