<template>
  <div class="file-upload-section card shadow-sm">
    <div class="card-body">
      <h5 class="card-title mb-3">Загрузить RINEX файл(ы)</h5>
      <!-- Мы используем @submit.prevent, чтобы форма не перезагружала страницу -->
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
          <!-- Эта часть теперь будет корректно отображать информацию о файлах -->
          <div class="form-text small mt-2" v-if="selectedFiles.length > 0">
            Выбрано файлов: {{ selectedFiles.length }}
            <ul class="mb-0 mt-1">
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
import { ref, getCurrentInstance } from 'vue';

// --- Props, которые компонент принимает от родителя ---
const props = defineProps({
    apiUploadUrl: {
        type: String,
        required: true
    }
});

// --- События, которые компонент может отправлять родителю ---
const emit = defineEmits(['upload-complete', 'upload-message']);

// --- Внутреннее состояние компонента ---
const fileInput = ref(null);
const selectedFiles = ref([]); // Эта переменная должна обновляться
const isUploading = ref(false);

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

// --- Обработчик выбора файлов ---
const onFileSelected = (event) => {
  // --- ДИАГНОСТИКА: Эта строка появится в консоли браузера (F12) ---
  console.log('onFileSelected сработал!', event.target.files);
  // -------------------------------------------------------------------

  // Обновляем нашу реактивную переменную
  selectedFiles.value = Array.from(event.target.files);
};

// --- Обработчик отправки формы ---
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
    const response = await $axios.post(props.apiUploadUrl, formData);
    emit('upload-complete', response.data);
  } catch (error) {
    console.error('Ошибка загрузки файла(ов):', error.response || error);
    let errorMessage = 'Произошла ошибка при загрузке файла(ов).';
    if (error.response) {
      errorMessage = error.response.data?.detail || `Ошибка сервера: ${error.response.status}`;
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