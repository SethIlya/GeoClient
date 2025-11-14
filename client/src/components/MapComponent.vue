<template>
  <div ref="mapDiv" class="map-container w-100 h-100">
    <div class="leaflet-top leaflet-right">
      <div class="leaflet-control leaflet-bar">
        <a
          href="#"
          title="Выделить область"
          role="button"
          aria-label="Выделить область"
          :class="{'active-selection-mode': isSelecting}"
          @click.prevent="toggleSelectionMode"
        >
          <i class="bi bi-bounding-box-circles"></i>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const props = defineProps({
  pointsData: { type: Array, required: true, default: () => [] },
  selectedPointIds: { type: Array, default: () => [] },
  activePointId: { type: String, default: null }
});
const emit = defineEmits(['point-clicked', 'map-ready', 'points-selected-by-area']);

const mapDiv = ref(null);
let mapInstance = null;
let markersLayer = null;
const isSelecting = ref(false);
let startPos = null;
let tempRect = null;
const renderedMarkers = new Map();

const pointTypeToText = (value) => {
    const types = {
        'ggs': 'Пункты гос. геодезической сети',
        'ggs_kurgan': 'Пункты ГГС на курганах',
        'survey': 'Точки съемочной сети',
        'survey_kurgan': 'Точки съемочной сети на курганах',
        'astro': 'Астрономический пункт/Высокоточная сеть',
        'leveling': 'Нивелирная марка/ГНСС',
        'default': 'Неопределенный тип',
    };
    return types[value] || 'N/A';
};

const createCustomIcon = (pointType, isSelected, isActive) => {
    const strokeColor = isSelected ? '#0d6efd' : 'black';
    const activeStrokeColor = '#d63384';
    const finalStrokeColor = isActive ? activeStrokeColor : strokeColor;
    const strokeWidth = isActive ? 2.5 : 1.5;
    
    let svgHtml = '', divHtml = '', iconSize, iconAnchor, popupAnchor;
    const ggsPolygon = `<polygon points="14,0 28,24.25 0,24.25" />`;
    const ggsCenterDot = `<circle cx="14" cy="16" r="2" fill="black" />`;
    const surveyRect = `<rect x="0" y="0" width="20" height="20" rx="1" />`;
    const surveyCenterDot = `<circle cx="10" cy="10" r="2" fill="black" />`;
    const kurganRaysDiv = `<div class="kurgan-star-rays"><div></div></div>`;

    switch (pointType) {
        case 'ggs': case 'ggs_kurgan':
            iconSize = [28, 25]; iconAnchor = [14, 25];
            svgHtml = `<svg width="28" height="25">${ggsPolygon}${ggsCenterDot}</svg>`;
            if(pointType.includes('kurgan')) divHtml = kurganRaysDiv;
            break;
        case 'survey': case 'survey_kurgan':
            iconSize = [20, 20]; iconAnchor = [10, 10];
            svgHtml = `<svg width="20" height="20">${surveyRect}${surveyCenterDot}</svg>`;
            if(pointType.includes('kurgan')) divHtml = kurganRaysDiv;
            break;
        case 'astro': // ЗВЕЗДОЧКА для ФАГС, ВГС, СГС-1
             iconSize = [24, 24]; iconAnchor = [12, 12];
             svgHtml = `<svg width="24" height="24"><text x="12" y="12" font-size="22" text-anchor="middle" dominant-baseline="central" fill="black">★</text></svg>`;
             break;
        case 'leveling': // КРУГ для ГНСС и нивелирных марок
             iconSize = [20, 20]; iconAnchor = [10, 10];
             svgHtml = `<svg width="20" height="20"><circle cx="10" cy="10" r="9" /><path d="M5,5 L15,15 M15,5 L5,15" stroke-width="1.5" /></svg>`;
             break;
        default:
             iconSize = [22, 22]; iconAnchor = [11, 11];
             svgHtml = `<svg width="22" height="22"><circle cx="11" cy="11" r="10" /><text x="11" y="11" text-anchor="middle" dominant-baseline="central" font-size="14" font-weight="bold" fill="#555">?</text></svg>`;
             break;
    }
    
    popupAnchor = [0, -iconAnchor[1]];
    const finalHtml = `<div class="icon-wrapper" style="--stroke-color:${finalStrokeColor}; --stroke-width:${strokeWidth};">${svgHtml}${divHtml}</div>`;
    return L.divIcon({ className: 'custom-leaflet-icon-container', html: finalHtml, iconSize, iconAnchor, popupAnchor });
};

const createOrUpdateMarker = (feature) => {
    const pointId = String(feature.properties.id);
    const properties = feature.properties;
    const [longitude, latitude] = feature.geometry.coordinates;

    const isSelected = props.selectedPointIds.includes(pointId);
    const isActive = props.activePointId === pointId;
    const icon = createCustomIcon(properties.point_type, isSelected, isActive);
    
    let popupHtml = `<div class="leaflet-popup-bootstrap"><h6 class="mb-1 text-primary">${properties.station_name || properties.id}</h6><small class="text-muted">ID: ${properties.id} | Тип: ${pointTypeToText(properties.point_type)}</small>`;
    const observationCount = properties.observations?.length || 0;
    popupHtml += `<p class="mb-0 mt-1 small"><strong>Кол-во наблюдений:</strong> ${observationCount}</p>`;
    popupHtml += `<hr class="my-1">`;
    const kml_data = {"Класс": properties.network_class, "Индекс": properties.index_name, "Тип центра": properties.center_type, "Номер марки": properties.mark_number, "Статус": properties.status,};
    for (const [key, value] of Object.entries(kml_data)) {
        popupHtml += `<p class="mb-1 small"><strong>${key}:</strong> ${value || '<span class="text-muted">Нет данных</span>'}</p>`;
    }
    popupHtml += `<p class="mb-1"><strong>Координаты:</strong><br><span class="font-monospace">${latitude.toFixed(6)}, ${longitude.toFixed(6)}</span></p>`;
    if (properties.latest_observation_data?.timestamp_display) {
      popupHtml += `<p class="mb-1"><strong>Последнее наблюдение:</strong><br>${properties.latest_observation_data.timestamp_display}</p>`;
    }
    popupHtml += `</div>`;

    if (renderedMarkers.has(pointId)) {
        const marker = renderedMarkers.get(pointId);
        marker.setIcon(icon);
        marker.setPopupContent(popupHtml);
        const currentLatLng = marker.getLatLng();
        if (currentLatLng.lat !== latitude || currentLatLng.lng !== longitude) {
            marker.setLatLng([latitude, longitude]);
        }
    } else {
        const marker = L.marker([latitude, longitude], { icon, pointId });
        marker.bindPopup(popupHtml, { minWidth: 240 });
        marker.on('click', (e) => {
            marker.openPopup();
            emit('point-clicked', feature, e);
        });
        renderedMarkers.set(pointId, marker);
        markersLayer.addLayer(marker);
    }
};

watch(() => props.pointsData, (newPoints) => {
    if (!markersLayer) return;
    const newPointIds = new Set(newPoints.map(p => String(p.properties.id)));
    
    renderedMarkers.forEach((marker, id) => {
        if (!newPointIds.has(id)) {
            markersLayer.removeLayer(marker);
            renderedMarkers.delete(id);
        }
    });

    newPoints.forEach(feature => {
        createOrUpdateMarker(feature);
    });
}, { deep: true });

watch([() => props.selectedPointIds, () => props.activePointId], () => {
    props.pointsData.forEach(feature => {
        if (renderedMarkers.has(String(feature.properties.id))) {
            createOrUpdateMarker(feature);
        }
    });
}, { deep: true });

const toggleSelectionMode = () => {
    isSelecting.value = !isSelecting.value;
    const mapContainer = mapInstance.getContainer();
    if (isSelecting.value) {
        L.DomUtil.addClass(mapContainer, 'selection-cursor');
        mapInstance.dragging.disable();
    } else {
        L.DomUtil.removeClass(mapContainer, 'selection-cursor');
        mapInstance.dragging.enable();
        if (tempRect) { mapInstance.removeLayer(tempRect); tempRect = null; }
        startPos = null;
    }
};

const onMapMouseDown = (e) => {
    if (isSelecting.value) {
        startPos = e.latlng;
    }
};

const onMapMouseMove = (e) => {
    if (!startPos) return;
    if (tempRect) {
        mapInstance.removeLayer(tempRect);
    }
    const bounds = L.latLngBounds(startPos, e.latlng);
    tempRect = L.rectangle(bounds, { color: '#0d6efd', weight: 1, opacity: 1, fillOpacity: 0.2, interactive: false }).addTo(mapInstance);
};

const onMapMouseUp = (e) => {
    if (!startPos) return;
    const bounds = L.latLngBounds(startPos, e.latlng);
    const selectedIds = props.pointsData
        .filter(feature => {
            if (!feature?.geometry) return false;
            const pointLatLng = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
            return bounds.contains(pointLatLng);
        })
        .map(feature => String(feature.properties.id));
    
    emit('points-selected-by-area', selectedIds);

    startPos = null;
    if (tempRect) {
        mapInstance.removeLayer(tempRect);
        tempRect = null;
    }
    if (isSelecting.value) {
        toggleSelectionMode();
    }
};

onMounted(() => {
  if (mapDiv.value && !mapInstance) {
    mapInstance = L.map(mapDiv.value, { zoomControl: true }).setView([53.5, 108.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(mapInstance);
    markersLayer = L.layerGroup().addTo(mapInstance);
    
    mapInstance.on('mousedown', onMapMouseDown);
    mapInstance.on('mousemove', onMapMouseMove);
    mapInstance.on('mouseup', onMapMouseUp);
    
    emit('map-ready', mapInstance);
  }
  props.pointsData.forEach(feature => createOrUpdateMarker(feature));
});

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
    markersLayer = null;
    renderedMarkers.clear();
  }
});
</script>

<style>
.custom-leaflet-icon-container { background-color: transparent !important; border: none !important; }
.icon-wrapper { position: relative; stroke: var(--stroke-color, black); stroke-width: var(--stroke-width, 1.5); fill: white; }
.icon-wrapper svg { overflow: visible; z-index: 1; position: relative; }
.kurgan-star-rays { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: -1; }
.kurgan-star-rays::before, .kurgan-star-rays::after { content: ''; position: absolute; background-color: var(--stroke-color, black); transform-origin: center; }
.icon-wrapper:has(svg) .kurgan-star-rays::before { top: 50%; left: 50%; width: 1.5px; height: 32px; margin-top: -16px; margin-left: -0.75px; }
.icon-wrapper:has(svg) .kurgan-star-rays::after { top: 50%; left: 50%; width: 32px; height: 1.5px; margin-top: -0.75px; margin-left: -16px; }
.kurgan-star-rays div { position: absolute; width: 100%; height: 100%; transform: rotate(45deg); }
.kurgan-star-rays div::before, .kurgan-star-rays div::after { content: ''; position: absolute; background-color: var(--stroke-color, black); transform-origin: center; }
.kurgan-star-rays div::before { top: 50%; left: 50%; width: 1.5px; height: 32px; margin-top: -16px; margin-left: -0.75px; }
.kurgan-star-rays div::after { top: 50%; left: 50%; width: 32px; height: 1.5px; margin-top: -0.75px; margin-left: -16px; }
.icon-wrapper:has(svg rect) .kurgan-star-rays { top: 0; left: 0; }
.icon-wrapper:has(svg polygon) .kurgan-star-rays { top: 2px; left: 0px; }
.selection-cursor { cursor: crosshair !important; }
.leaflet-control a.active-selection-mode { background-color: #d1e7fd; color: #0d6efd; }
.leaflet-control i.bi { font-size: 1.2rem; }
.leaflet-control.leaflet-bar a { width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; }
.leaflet-popup-bootstrap h6 { margin-bottom: 0.25rem; color: #0d6efd; }
.leaflet-popup-bootstrap hr { margin-top: 0.25rem; margin-bottom: 0.25rem; opacity: 0.25; }
.leaflet-popup-bootstrap p { font-size: 0.875rem; line-height: 1.5; margin-bottom: 0.25rem; }
.leaflet-popup-bootstrap p.small { font-size: 0.8rem; line-height: 1.4; }
.leaflet-popup-content-wrapper { border-radius: 0.375rem !important; box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1); }
.leaflet-popup-content { margin: 1rem !important; padding: 0 !important; min-width: 220px; }
.leaflet-popup-close-button { padding: 0.5rem 0.5rem !important; font-size: 1.25rem !important; color: #6c757d !important; }
</style>