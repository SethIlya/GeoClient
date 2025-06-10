<template>
  <div ref="mapDiv" class="map-container w-100 h-100"></div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import L from 'leaflet';

const props = defineProps({
  pointsData: { type: Array, required: true, default: () => [] },
  selectedPointIds: { type: Array, default: () => [] } // Массив строковых ID
});
const emit = defineEmits(['point-clicked', 'map-ready']);

const mapDiv = ref(null);
let mapInstance = null;
let markersLayer = null;

// --- Код для pointTypesList, pointTypeToText, createCustomIcon ---
// Вставьте сюда ваш актуальный код для этих функций
const pointTypesList = [
    { value: 'ggs', text: 'Пункты гос. геодезической сети' },
    { value: 'ggs_kurgan', text: 'Пункты ГГС на курганах' },
    { value: 'survey', text: 'Точки съемочной сети' },
    { value: 'survey_kurgan', text: 'Точки съемочной сети на курганах' },
    { value: 'astro', text: 'Астрономические пункты' },
    { value: 'leveling', text: 'Нивелирные марки/реперы' },
    { value: 'default', text: 'Неопределенный тип' },
];
const pointTypeToText = (value) => {
    const found = pointTypesList.find(pt => pt.value === value);
    return found ? found.text : (value || 'N/A');
};
const createCustomIcon = (pointType, isSelected) => {
    let className = 'custom-div-icon';
    let htmlContent = '';
    let iconSizeTuple, iconAnchorTuple;
    const centerDotHtml = '<div class="center-dot"></div>';
    const kurganStarRaysHtml = `<div class="kurgan-star-rays"> <div class="ray n"></div><div class="ray s"></div><div class="ray w"></div><div class="ray e"></div> <div class="ray nw"></div><div class="ray ne"></div><div class="ray sw"></div><div class="ray se"></div> </div>`;
    const baseGgsSize = { width: 28, height: 24.25 }; 
    const baseSurveySize = { width: 20, height: 20 }; 
    const rayOutwardLength = 7;
    const kurganContainerPadding = rayOutwardLength + 2;
    const popupOffsetAboveIcon = 5;
    const astroContentWidth = 59; const astroContentHeight = 20;
    const astroPaddingY = 1; const astroPaddingX = 3;

    switch (pointType) {
        case 'ggs':
            className += ' icon-ggs'; htmlContent = centerDotHtml;
            iconSizeTuple = [baseGgsSize.width, baseGgsSize.height];
            iconAnchorTuple = [baseGgsSize.width / 2, baseGgsSize.height];
            break;
        case 'ggs_kurgan':
            className += ' icon-ggs icon-kurgan'; htmlContent = centerDotHtml + kurganStarRaysHtml;
            iconSizeTuple = [ baseGgsSize.width + 2 * kurganContainerPadding, baseGgsSize.height + 2 * kurganContainerPadding ];
            iconAnchorTuple = [iconSizeTuple[0] / 2, iconSizeTuple[1] / 2];
            break;
        case 'survey':
            className += ' icon-survey'; htmlContent = centerDotHtml;
            iconSizeTuple = [baseSurveySize.width, baseSurveySize.height];
            iconAnchorTuple = [baseSurveySize.width / 2, baseSurveySize.height / 2];
            break;
        case 'survey_kurgan':
            className += ' icon-survey icon-kurgan'; htmlContent = centerDotHtml + kurganStarRaysHtml;
            iconSizeTuple = [ baseSurveySize.width + 2 * kurganContainerPadding, baseSurveySize.height + 2 * kurganContainerPadding ];
            iconAnchorTuple = [iconSizeTuple[0] / 2, iconSizeTuple[1] / 2];
            break;
        case 'astro':
            className += ' icon-astro';
            htmlContent = '<span class="star-symbol">★</span><span class="astro-text">астр.</span>';
            iconSizeTuple = [ astroContentWidth + 2 * astroPaddingX, astroContentHeight + 2 * astroPaddingY ];
            iconAnchorTuple = [ astroPaddingX + (astroContentHeight / 2), astroPaddingY + (astroContentHeight / 2) ];
            break;
        case 'leveling':
            className += ' icon-leveling'; htmlContent = '<div class="diag-line line1"></div><div class="diag-line line2"></div>';
            iconSizeTuple = [20, 20]; iconAnchorTuple = [10, 10];
            break;
        default:
            className += ' icon-default'; htmlContent = '?';
            iconSizeTuple = [20, 20]; iconAnchorTuple = [10, 10];
            break;
    }
    if (isSelected) { className += ' selected'; }
    let popupOffsetY;
    if (pointType === 'ggs') popupOffsetY = -iconAnchorTuple[1] - popupOffsetAboveIcon;
    else if (pointType === 'ggs_kurgan') popupOffsetY = -(baseGgsSize.height / 2) - popupOffsetAboveIcon;
    else if (pointType === 'survey_kurgan' || pointType === 'survey') popupOffsetY = -(baseSurveySize.height / 2) - popupOffsetAboveIcon;
    else popupOffsetY = -(iconSizeTuple[1] / 2) - popupOffsetAboveIcon;
    
    return L.divIcon({
        className: className, html: htmlContent,
        iconSize: L.point(iconSizeTuple[0], iconSizeTuple[1]),
        iconAnchor: L.point(iconAnchorTuple[0], iconAnchorTuple[1]),
        popupAnchor: L.point(0, popupOffsetY)
    });
};
// --- Конец кода для pointTypesList, pointTypeToText, createCustomIcon ---

const initializeMap = () => {
  if (mapDiv.value && !mapInstance) {
    console.log("[MapComponent] initializeMap: Инициализация новой карты.");
    mapInstance = L.map(mapDiv.value).setView([55.751244, 37.618423], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(mapInstance);
    markersLayer = L.layerGroup().addTo(mapInstance);
    emit('map-ready', mapInstance);
  } else if (mapDiv.value && mapInstance) {
    console.warn("[MapComponent] initializeMap: Попытка повторной инициализации. Пропуск.");
  }
};

const updateMarkersOnMap = (pointsToRender) => {
  if (!mapInstance || !markersLayer) {
    console.warn("[MapComponent] updateMarkersOnMap: Карта или слой маркеров не инициализированы.");
    return; 
  }
  console.log("[MapComponent] updateMarkersOnMap: Обновление маркеров. Точек:", pointsToRender?.length);
  markersLayer.clearLayers();

  if (pointsToRender && pointsToRender.length > 0) {
    pointsToRender.forEach(feature => {
      if (feature && feature.geometry && feature.geometry.type === 'Point' && feature.properties) {
        const [longitude, latitude] = feature.geometry.coordinates;
        const properties = feature.properties;
        const pointId = String(properties.id); // Убедимся, что ID - строка

        if (!pointId) {
            console.warn("[MapComponent] Пропуск точки без ID:", feature);
            return; 
        }

        // props.selectedPointIds уже должен содержать строки
        const isSelected = props.selectedPointIds.includes(pointId); 
        const finalPointType = properties.point_type || 'default';
        const customIcon = createCustomIcon(finalPointType, isSelected);
        
        const marker = L.marker([latitude, longitude], { icon: customIcon, pointId: pointId }); // Сохраняем строковый ID

        let popupHtml = `<div class="leaflet-popup-bootstrap"><h6 class="mb-1 text-primary">${properties.name || properties.station_name || pointId}</h6><small class="text-muted">ID: ${pointId} | Тип: ${pointTypeToText(finalPointType)}</small><hr class="my-1">`;
        popupHtml += `<p class="mb-1"><strong>Координаты:</strong><br><span class="font-monospace">${parseFloat(latitude).toFixed(6)}, ${parseFloat(longitude).toFixed(6)}</span></p>`;
        if (properties.timestamp_display) popupHtml += `<p class="mb-1"><strong>Время:</strong><br>${properties.timestamp_display}</p>`;
        if (properties.receiver_number) popupHtml += `<p class="mb-1"><strong>Приемник №:</strong><br>${properties.receiver_number}</p>`;
        if (properties.antenna_height != null) popupHtml += `<p class="mb-1"><strong>Высота ант. (H):</strong><br>${properties.antenna_height.toFixed(4)} м</p>`;
        if (properties.description) popupHtml += `<p class="mb-0"><strong>Описание:</strong><br>${properties.description}</p>`;
        popupHtml += `</div>`;
        marker.bindPopup(popupHtml, { minWidth: 240 });

        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          emit('point-clicked', feature); 
        });
        markersLayer.addLayer(marker);
      }
    });
  }
};

watch(() => props.pointsData, (newPoints) => {
  console.log("[MapComponent] watch props.pointsData: Данные точек изменились.");
  updateMarkersOnMap(newPoints); 
}, { deep: true });

watch(() => props.selectedPointIds, (newSelectedIds, oldSelectedIds) => {
  if (!markersLayer) return;
  console.log("[MapComponent] watch props.selectedPointIds: Выбранные ID изменились. Новые:", newSelectedIds);
  
  const idsToUpdate = new Set();
  (oldSelectedIds || []).map(String).forEach(id => idsToUpdate.add(id));
  (newSelectedIds || []).map(String).forEach(id => idsToUpdate.add(id));

  idsToUpdate.forEach(pointIdStr => {
    markersLayer.eachLayer(marker => {
      if (String(marker.options.pointId) === pointIdStr) {
        const pointFeature = props.pointsData.find(p => p.properties && String(p.properties.id) === pointIdStr);
        if (pointFeature && pointFeature.properties) {
          const pointType = pointFeature.properties.point_type || 'default';
          const isCurrentlySelected = (newSelectedIds || []).includes(pointIdStr);
          marker.setIcon(createCustomIcon(pointType, isCurrentlySelected));
        }
        return false; 
      }
    });
  });
}, { deep: true });

onMounted(() => {
  console.log("[MapComponent] onMounted: Начало монтирования.");
  initializeMap();
  if (props.pointsData && props.pointsData.length > 0 && mapInstance && markersLayer) {
      console.log("[MapComponent] onMounted: Первоначальная отрисовка маркеров.");
      updateMarkersOnMap(props.pointsData);
  } else {
      console.log("[MapComponent] onMounted: Нет начальных данных или карта не готова для маркеров.");
  }
});

onBeforeUnmount(() => {
  console.log("[MapComponent] onBeforeUnmount: Очистка карты...");
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
    markersLayer = null;
    console.log("[MapComponent] Карта и слой маркеров удалены.");
  }
});
</script>

<style>
/* --- Стили для иконок (custom-div-icon, icon-ggs, icon-survey, etc.) --- */
/* Эти стили должны быть здесь, как вы их предоставляли ранее */
.custom-div-icon { display: flex; justify-content: center; align-items: center; position: relative; box-sizing: border-box; }
.custom-div-icon .center-dot { width: 4px; height: 4px; background-color: black; border-radius: 50%; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 3; }
/* ... и так далее для всех ваших стилей иконок ... */
.custom-div-icon.icon-ggs { width: 28px; height: 24.25px; }
.custom-div-icon.icon-ggs::before { content: ''; position: absolute; width: 0; height: 0; border-left: 14px solid transparent; border-right: 14px solid transparent; border-bottom: 24.25px solid white; top: 0; left: 0; z-index: 1; }
.custom-div-icon.icon-ggs::after { content: ''; position: absolute; width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-bottom: 26px solid black; top: -0.87px; left: -1px; z-index: 0; }
.custom-div-icon.icon-ggs .center-dot { top: 15px; left: 14px; }
.custom-div-icon.icon-survey { width: 20px; height: 20px; background-color: white; border: 1.5px solid black; box-sizing: border-box; z-index: 1; }
.custom-div-icon.icon-kurgan .kurgan-star-rays { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: -1; }
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray { position: absolute; background-color: black; transform-origin: center; width: 1.5px; height: 7px; }
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.n { top: 0; left: 50%; transform: translate(-50%, -100%);}
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.s { bottom: 0; left: 50%; transform: translate(-50%, 100%);}
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.w { left: 0; top: 50%; transform: translate(-100%, -50%); height: 1.5px; width: 7px;}
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.e { right: 0; top: 50%; transform: translate(100%, -50%); height: 1.5px; width: 7px;}
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.nw { top: 0; left: 0; transform: translate(-70.7%, -70.7%) rotate(-45deg); transform-origin: bottom right; }
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.ne { top: 0; right: 0; transform: translate(70.7%, -70.7%) rotate(45deg); transform-origin: bottom left; }
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.sw { bottom: 0; left: 0; transform: translate(-70.7%, 70.7%) rotate(45deg); transform-origin: top right; }
.custom-div-icon.icon-kurgan .kurgan-star-rays .ray.se { bottom: 0; right: 0; transform: translate(70.7%, 70.7%) rotate(-45deg); transform-origin: top left; }
.custom-div-icon.icon-ggs.icon-kurgan::before, .custom-div-icon.icon-ggs.icon-kurgan::after { top: 50%; left: 50%; }
.custom-div-icon.icon-ggs.icon-kurgan::before { transform: translate(-14px, calc(-24.25px / 2 - 5px)); z-index: 1; }
.custom-div-icon.icon-ggs.icon-kurgan::after { transform: translate(calc(-14px - 1px), calc(-24.25px / 2 - 5px - 0.87px)); z-index: 0; }
.custom-div-icon.icon-ggs.icon-kurgan .center-dot { transform: translate(175%, calc(0px)); z-index: 2; }
.custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays { width: 28px; height: 24.25px; }
.custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.n { top: -1px; }
.custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.w { width: 5px; }
.custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.e { width: 5px; }
.custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.nw, .custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.ne, .custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.sw, .custom-div-icon.icon-ggs.icon-kurgan .kurgan-star-rays .ray.se { height: 6px; }
.custom-div-icon.icon-survey.icon-kurgan { background-color: transparent !important; border: none !important; }
.custom-div-icon.icon-survey.icon-kurgan::before { content: ''; position: absolute; top: 50%; left: 50%; width: 20px; height: 20px; background-color: white; border: 1.5px solid black; transform: translate(-50%, -50%); box-sizing: border-box; z-index: 1; }
.custom-div-icon.icon-survey.icon-kurgan .center-dot { z-index: 2; }
.custom-div-icon.icon-survey.icon-kurgan .kurgan-star-rays { width: 20px; height: 20px; }
.custom-div-icon.icon-astro { padding: 1px 3px; background-color: white; }
.custom-div-icon.icon-astro .star-symbol { font-size: 20px; color: black; line-height: 1; margin-right: 4px; }
.custom-div-icon.icon-astro .astro-text { font-size: 14px; color: black; font-family: Arial, sans-serif; white-space: nowrap; line-height: 1.1; }
.custom-div-icon.icon-leveling { width: 20px; height: 20px; background-color: white; border: 1.5px solid black; border-radius: 50%; box-sizing: border-box; }
.custom-div-icon.icon-leveling .diag-line { position: absolute; background-color: black; width: 14px; height: 1.5px; top: 50%; left: 50%; }
.custom-div-icon.icon-leveling .line1 { transform: translate(-50%, -50%) rotate(45deg); }
.custom-div-icon.icon-leveling .line2 { transform: translate(-50%, -50%) rotate(-45deg); }
.custom-div-icon.icon-default { width: 20px; height: 20px; background-color: white; border: 1.5px solid black; border-radius: 50%; font-size: 13px; color: #555; line-height: 17px; text-align: center; box-sizing: border-box; }
.custom-div-icon.selected { box-shadow: 0 0 0 2px white, 0 0 0 3.5px #0d6efd; /* Синяя рамка для выделения (Bootstrap primary) */ }
.custom-div-icon.icon-ggs.selected::after { border-bottom-color: #0d6efd; }
.custom-div-icon.icon-survey.selected { border-color: #0d6efd; }
.custom-div-icon.icon-survey.icon-kurgan.selected::before { border-color: #0d6efd; }
.custom-div-icon.icon-leveling.selected, .custom-div-icon.icon-default.selected { border-color: #0d6efd; }
/* Стили для попапов */
.leaflet-popup-bootstrap h6 { margin-bottom: 0.25rem; color: #0d6efd; }
.leaflet-popup-bootstrap hr { margin-top: 0.25rem; margin-bottom: 0.25rem; opacity: 0.25; }
.leaflet-popup-bootstrap p { font-size: 0.875rem; line-height: 1.5; margin-bottom: 0.25rem; }
.leaflet-popup-bootstrap p:last-child { margin-bottom: 0; }
.leaflet-popup-content-wrapper { border-radius: 0.375rem !important; box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1); }
.leaflet-popup-content { margin: 1rem !important; padding: 0 !important; min-width: 220px; }
.leaflet-popup-close-button { padding: 0.5rem 0.5rem !important; font-size: 1.25rem !important; color: #6c757d !important; }
.leaflet-popup-close-button:hover { color: #212529 !important; background-color: #e9ecef !important; }
/* --- Конец стилей для иконок --- */
.map-container { 
  height: 100%;
  width: 100%;
}
</style>