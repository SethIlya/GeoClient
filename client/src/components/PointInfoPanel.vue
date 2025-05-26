<template>
  <div class="point-info-card card shadow-sm">
    <div class="card-body">
      <h5 class="card-title">Информация о точке</h5>
      <div v-if="point && point.properties" class="details">
        <ul class="list-unstyled">
          <li><strong>ID:</strong> {{ point.properties.id }}</li>
          <li><strong>Имя:</strong> {{ point.properties.name || 'N/A' }}</li>
          <li>
            <strong>Координаты:</strong> 
            {{ parseFloat(point.properties.latitude).toFixed(6) }}, 
            {{ parseFloat(point.properties.longitude).toFixed(6) }}
          </li>
          <li><strong>Время:</strong> {{ point.properties.timestamp_display || 'N/A' }}</li>
          <li><strong>Описание:</strong> {{ point.properties.description || 'Нет описания' }}</li>
        </ul>
      </div>
      <div v-else class="placeholder text-muted">
        <p class="fst-italic">Выберите точку на карте для просмотра информации.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue';

defineProps({
  point: {
    type: Object,
    default: null
  }
});
</script>

<style scoped>
.details li {
  margin-bottom: 0.3rem;
}
</style>