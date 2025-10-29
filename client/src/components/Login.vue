<template>
  <div class="login-modal-overlay">
    <div class="card shadow-lg" style="width: 100%; max-width: 400px;">
      <div class="card-body p-4 p-md-5">
        <h3 class="card-title text-center mb-4">Карта RINEX точек</h3>
        <p class="text-center text-muted mb-4">Вход в систему</p>
        
        <form @submit.prevent="handleLogin">
          <div class="mb-3">
            <label for="username" class="form-label">Имя пользователя</label>
            <input 
              type="text" 
              class="form-control" 
              id="username" 
              v-model="username" 
              required 
              autocomplete="username"
            >
          </div>
          <div class="mb-4">
            <label for="password" class="form-label">Пароль</label>
            <input 
              type="password" 
              class="form-control" 
              id="password" 
              v-model="password" 
              required 
              autocomplete="current-password"
            >
          </div>

          <!-- Сообщение об ошибке -->
          <div v-if="error" class="alert alert-danger small py-2">{{ error }}</div>
          
          <div class="d-grid">
            <button type="submit" class="btn btn-primary btn-lg" :disabled="loading">
              <span v-if="loading" class="spinner-border spinner-border-sm me-1" role="status"></span>
              Войти
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, getCurrentInstance } from 'vue';

const props = defineProps({
    loginUrl: { type: String, required: true }
});
const emit = defineEmits(['login-success']);

const instance = getCurrentInstance();
const $axios = instance.appContext.config.globalProperties.$axios;

const username = ref('');
const password = ref('');
const error = ref(null);
const loading = ref(false);

const handleLogin = async () => {
    loading.value = true;
    error.value = null;
    try {
        const response = await $axios.post(props.loginUrl, {
            username: username.value,
            password: password.value,
        });
        emit('login-success', response.data);
    } catch (err) {
        if (err.response && err.response.data && err.response.data.non_field_errors) {
            error.value = err.response.data.non_field_errors.join(' ');
        } else {
            error.value = 'Произошла ошибка сети или сервера. Попробуйте позже.';
        }
    } finally {
        loading.value = false;
    }
};
</script>

<style scoped>
.login-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(33, 37, 41, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050; 
  -webkit-backdrop-filter: blur(5px);
  backdrop-filter: blur(5px);
}
.card {
  animation: fade-in 0.3s ease-out;
}
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>