<template>
  <div class="file-upload-section card shadow-sm">
    <div class="card-body">
      <h5 class="card-title mb-3">Загрузить RINEX файл(ы)</h5>
      <form @submit.prevent="handleFileUpload">
        <div class="mb-3">
          <label for="rinexFile" class="form-label">Выберите файл(ы) комплектов RINEX:</label>
          <input
            type="file"
            class="form-control form-control-sm"
            id="rinexFile"
            ref="fileInput"
            @change="onFileSelected"
            accept=".rnx,.obs,.nav,.o,.n,.g,.26o,.26n,.26g,.25o,.25n,.25g,.24o,.24n,.24g,.23o,.23n,.23g,.22o,.22n,.22g,.21o,.21n,.21g,.20o,.20n,.20g,.19o,.19n,.19g,.18o,.18n,.18g,.17o,.17n,.17g,.16o,.16n,.16g,.15o,.15n,.15g"
            required
            multiple
          />
          <div class="form-text small mt-2">
          </div>
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
          {{ isUploading ? 'Обработка...' : `Загрузить ${selectedFiles.length} файла(ов)` }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, getCurrentInstance } from 'vue';

const props = defineProps({
    apiUploadUrl: {
        type: String,
        required: true
    }
});

const emit = defineEmits(['upload-complete', 'upload-message']);

const fileInput = ref(null);
const selectedFiles = ref([]);
const isUploading = ref(false);

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

const onFileSelected = (event) => {
  selectedFiles.value = Array.from(event.target.files);
};

const handleFileUpload = async () => {
  if (!selectedFiles.value.length) {
    emit('upload-message', { type: 'warning', text: 'Пожалуйста, выберите хотя бы один файл.' });
    return;
  }
  isUploading.value = true;
  // Обновляем сообщение, предупреждая пользователя о возможном долгом ожидании
  emit('upload-message', { 
    type: 'info', 
    text: `Начинается загрузка и обработка ${selectedFiles.value.length} файла(ов)... Это может занять продолжительное время.`
  });

  const formData = new FormData();
  selectedFiles.value.forEach(file => {
    formData.append('rinex_files', file);
  });

  try {
    // ВАЖНОЕ ИЗМЕНЕНИЕ: timeout: 0 отключает таймаут на клиенте (в браузере).
    // Теперь браузер будет ждать ответа от сервера столько, сколько потребуется, 
    // не обрывая соединение через 30-60 секунд.
    const response = await $axios.post(props.apiUploadUrl, formData, {
        timeout: 0 
    });
    
    emit('upload-complete', response.data);
  } catch (error) {
    console.error('Ошибка загрузки файла(ов):', error.response || error);
    let errorPayload = {
        success: false,
        total_created_count: 0,
        messages: [{type: 'danger', text: 'Произошла непредвиденная ошибка при загрузке.'}],
    };
    if (error.response && error.response.data) {
        if (Array.isArray(error.response.data.messages) && error.response.data.messages.length > 0) {
            errorPayload.messages = error.response.data.messages;
        } else {
            const serverMessage = error.response.data.detail || error.response.data.message || `Ошибка сервера: ${error.response.status}`;
            errorPayload.messages = [{ type: 'danger', text: serverMessage }];
        }
    } else if (error.code === 'ECONNABORTED') {
        errorPayload.messages = [{ type: 'danger', text: 'Превышено время ожидания соединения.' }];
    }
    emit('upload-complete', errorPayload);
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