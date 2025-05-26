<template>
  <div class="message-display">
    <div 
      v-for="msg in messages" 
      :key="msg.id" 
      :class="['alert', `alert-${msg.type || 'secondary'}`, 'alert-dismissible', 'fade', 'show']" 
      role="alert"
    >
      {{ msg.text }}
      <button 
        type="button" 
        class="btn-close" 
        @click="emit('clear-message', msg.id)" 
        aria-label="Close"
      ></button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  messages: {
    type: Array,
    default: () => []
  }
});
const emit = defineEmits(['clear-message']);
</script>

<style scoped>
/* Стили для alert уже есть в Bootstrap */
</style>