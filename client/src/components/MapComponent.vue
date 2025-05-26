<template>
  <div ref="mapDiv" class="map-container w-100 h-100"></div>
</template>

<script setup>
// ... (остальной JS код MapComponent.vue остается таким же, как в предыдущем ответе)
// Он отвечает за логику Leaflet, а не за стилизацию Bootstrap.
import { ref, onMounted, watch, onBeforeUnmount, defineProps, defineEmits } from 'vue';
import L from 'leaflet';

import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: iconRetinaUrl,
  iconUrl: iconUrl,
  shadowUrl: shadowUrl,
});

const props = defineProps({
  pointsData: {
    type: Array,
    required: true,
    default: () => []
  }
});
const emit = defineEmits(['point-selected']);

const mapDiv = ref(null);
let mapInstance = null;
let markersLayer = null;

const initializeMap = () => {
  if (mapDiv.value && !mapInstance) {
    mapInstance = L.map(mapDiv.value).setView([55.751244, 37.618423], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(mapInstance);
    markersLayer = L.layerGroup().addTo(mapInstance);
  }
};

const updateMarkersOnMap = (newPoints) => {
  if (!mapInstance || !markersLayer) return;
  markersLayer.clearLayers();
  if (newPoints && newPoints.length > 0) {
    const leafletMarkers = [];
    newPoints.forEach(feature => {
      if (feature.geometry && feature.geometry.type === 'Point') {
        const [longitude, latitude] = feature.geometry.coordinates;
        const properties = feature.properties || {};
        const marker = L.marker([latitude, longitude]);
        
        let popupHtml = `<h6 class="mb-1">${properties.name || 'Без имени'}</h6>`; // Bootstrap класс для заголовка
        popupHtml += `<small class="text-muted">ID: ${properties.id}</small><br>`; // Bootstrap классы
        popupHtml += `Координаты: ${parseFloat(properties.latitude || latitude).toFixed(6)}, ${parseFloat(properties.longitude || longitude).toFixed(6)}<br>`;
        if (properties.timestamp_display) {
          popupHtml += `Время: ${properties.timestamp_display}<br>`;
        }
        if (properties.description) {
          popupHtml += `Описание: ${properties.description}<br>`;
        }
        // Можно обернуть содержимое попапа в div с классами Bootstrap для лучшего вида, если стандартный не устраивает
        marker.bindPopup(popupHtml);

        marker.on('click', () => emit('point-selected', feature));
        leafletMarkers.push(marker);
      }
    });
    if (leafletMarkers.length > 0) {
      leafletMarkers.forEach(m => markersLayer.addLayer(m));
    }
  }
};

onMounted(() => {
  initializeMap();
  updateMarkersOnMap(props.pointsData);
});

watch(() => props.pointsData, (newVal) => {
  updateMarkersOnMap(newVal);
}, { deep: true });

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
});
</script>

<style scoped>
/* .map-container стили могут быть минимальными, т.к. w-100 h-100 уже заданы */
.map-container {
  background-color: #e9ecef; /* Фоновый цвет для карты, пока тайлы не загрузились */
}
/* Стили для Leaflet попапов можно кастомизировать здесь, если стандартные Bootstrap не подходят */
:global(.leaflet-popup-content h6) { /* Пример глобального стиля для заголовка в попапе Leaflet */
  margin-top: 0;
}
</style>