<!-- client/src/components/MessageDisplay.vue -->
<template>
  <div class="message-display">
    <div
      v-for="msg in messages"
      :key="msg.id"
      :class="['alert', `alert-${msg.type || 'secondary'}`, 'alert-dismissible', 'fade', 'show', 'py-2', 'px-3', 'mb-2', 'small']" 
      role="alert"
    >
      <!-- Добавим иконку для наглядности -->
      <i :class="getIconClass(msg.type)" class="me-2"></i>
      {{ msg.text }}
      <button
        type="button"
        class="btn-close btn-sm py-2 px-2" 
        @click="emit('clear-message', msg.id)"
        aria-label="Close"
      ></button>
    </div>
  </div>
</template>

<script setup>
// defineProps и defineEmits не нужно импортировать в <script setup>
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  }
});
const emit = defineEmits(['clear-message']);

const getIconClass = (messageType) => {
  switch (messageType) {
    case 'success': return 'bi bi-check-circle-fill';
    case 'info': return 'bi bi-info-circle-fill';
    case 'warning': return 'bi bi-exclamation-triangle-fill';
    case 'danger': return 'bi bi-x-octagon-fill';
    default: return 'bi bi-bell-fill';
  }
};
</script>

<style scoped>
.alert {
  font-size: 0.875rem; /* Немного уменьшим шрифт для компактности */
}
.alert i.bi {
  font-size: 1rem; /* Размер иконки */
  vertical-align: text-bottom; /* Лучшее выравнивание с текстом */
}
</style>