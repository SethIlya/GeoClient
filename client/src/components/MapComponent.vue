<template>
  <div ref="mapDiv" class="map-container w-100 h-100"></div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'; // defineProps, defineEmits не нужны для импорта в <script setup>
import L from 'leaflet';

const props = defineProps({
  pointsData: {
    type: Array,
    required: true,
    default: () => []
  },
  selectedPointIds: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['point-clicked', 'map-ready']);

const mapDiv = ref(null);
let mapInstance = null;
let markersLayer = null;

// --- Начало: Код для pointTypesList, pointTypeToText, createCustomIcon ---
// (Этот код должен быть вашим актуальным рабочим кодом для создания иконок)
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
            iconAnchorTuple = [ astroPaddingX + (astroContentHeight / 2), astroPaddingY + (astroContentHeight / 2) ]; // Уточнено якорение для астро
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
    if (pointType === 'ggs') {
        popupOffsetY = -iconAnchorTuple[1] - popupOffsetAboveIcon;
    } else if (pointType === 'ggs_kurgan') {
        // Центр треугольника находится примерно на 2/3 высоты от вершины
        // Якорь иконки ggs_kurgan - центр всего divIcon.
        // popupOffsetY должен быть от якоря до верхнего края внутреннего треугольника + смещение
        popupOffsetY = -(baseGgsSize.height / 2 + kurganContainerPadding - (baseGgsSize.height - iconAnchorTuple[1])) - popupOffsetAboveIcon; // Это неверно, упростим
        popupOffsetY = -(baseGgsSize.height / 2) - popupOffsetAboveIcon; // По центру внутреннего символа
    } else if (pointType === 'survey_kurgan' || pointType === 'survey') {
        popupOffsetY = -(baseSurveySize.height / 2) - popupOffsetAboveIcon; // По центру внутреннего символа
    } else { // astro, leveling, default
        popupOffsetY = -(iconSizeTuple[1] / 2) - popupOffsetAboveIcon; // По центру иконки
    }
    
    return L.divIcon({
        className: className, html: htmlContent,
        iconSize: L.point(iconSizeTuple[0], iconSizeTuple[1]),
        iconAnchor: L.point(iconAnchorTuple[0], iconAnchorTuple[1]),
        popupAnchor: L.point(0, popupOffsetY)
    });
};
// --- Конец: Код для pointTypesList, pointTypeToText, createCustomIcon ---

const initializeMap = () => {
  // Проверяем, что mapDiv.value существует и карта еще не создана
  if (mapDiv.value && !mapInstance) {
    console.log("[MapComponent] initializeMap: Инициализация новой карты.");
    mapInstance = L.map(mapDiv.value, {
        // preferCanvas: true // Можно раскомментировать для лучшей производительности с большим кол-вом маркеров
    }).setView([55.751244, 37.618423], 5); // Центральная точка и зум по умолчанию

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(mapInstance);

    markersLayer = L.layerGroup().addTo(mapInstance); // Создаем слой для маркеров
    emit('map-ready', mapInstance);
  } else if (mapDiv.value && mapInstance) {
    console.warn("[MapComponent] initializeMap: Попытка повторной инициализации уже существующей карты. Пропуск.");
  } else if (!mapDiv.value) {
    console.error("[MapComponent] initializeMap: mapDiv не найден. Карта не может быть инициализирована.");
  }
};

const updateMarkersOnMap = (pointsToRender) => {
  // Важно: выполняем действия только если карта и слой маркеров готовы
  if (!mapInstance || !markersLayer) {
    console.warn("[MapComponent] updateMarkersOnMap: Карта или слой маркеров не инициализированы. Обновление маркеров отложено.");
    return; 
  }
  console.log("[MapComponent] updateMarkersOnMap: Обновление маркеров. Количество точек для рендера:", pointsToRender?.length);
  markersLayer.clearLayers(); // Очищаем предыдущие маркеры

  if (pointsToRender && pointsToRender.length > 0) {
    pointsToRender.forEach(feature => {
      if (feature && feature.geometry && feature.geometry.type === 'Point' && feature.properties) {
        const [longitude, latitude] = feature.geometry.coordinates;
        const properties = feature.properties;
        const pointId = properties.id;

        if (pointId == null) { // Пропускаем точки без ID
            console.warn("[MapComponent] updateMarkersOnMap: Пропуск точки без ID в properties:", feature);
            return; 
        }

        const isSelected = props.selectedPointIds.includes(pointId); // Проверяем, выбран ли маркер
        const finalPointType = properties.point_type || 'default';
        const customIcon = createCustomIcon(finalPointType, isSelected);
        
        const marker = L.marker([latitude, longitude], { 
            icon: customIcon, 
            pointId: pointId // Сохраняем ID точки в опциях маркера для легкого доступа
        });

        // Формирование HTML для попапа
        let popupHtml = `<div class="leaflet-popup-bootstrap">
                           <h6 class="mb-1 text-primary">${properties.name || 'Без имени'}</h6>
                           <small class="text-muted">ID: ${pointId} | Тип: ${pointTypeToText(finalPointType)}</small><hr class="my-1">
                           <p class="mb-1"><strong>Координаты:</strong><br><span class="font-monospace">${parseFloat(latitude).toFixed(6)}, ${parseFloat(longitude).toFixed(6)}</span></p>`;
        if (properties.timestamp_display) {
          popupHtml += `<p class="mb-1"><strong>Время:</strong><br>${properties.timestamp_display}</p>`;
        }
        if (properties.description) {
          popupHtml += `<p class="mb-0"><strong>Описание:</strong><br>${properties.description}</p>`;
        }
        popupHtml += `</div>`;
        marker.bindPopup(popupHtml, { minWidth: 220 });

        // Обработчик клика по маркеру
        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e); // Остановка всплытия события, чтобы не срабатывал клик по карте
          emit('point-clicked', feature); // Эмитим весь объект feature точки
        });
        markersLayer.addLayer(marker);
      }
    });
  }
};

// Следим за изменением props.pointsData (массива точек)
// Этот watch будет срабатывать, когда данные точек загрузятся или изменятся (например, после загрузки файла)
watch(() => props.pointsData, (newPoints) => {
  console.log("[MapComponent] watch props.pointsData: Данные точек изменились. Попытка обновления маркеров.");
  // updateMarkersOnMap сам проверит, готова ли карта
  updateMarkersOnMap(newPoints); 
}, { deep: true }); // immediate: true убран, чтобы не срабатывать до onMounted

// Следим за изменением props.selectedPointIds (массива ID выбранных точек)
// Этот watch обновляет стиль маркеров (выделение/снятие выделения)
watch(() => props.selectedPointIds, (newSelectedIds, oldSelectedIds) => {
  if (!markersLayer) {
      console.warn("[MapComponent] watch props.selectedPointIds: Слой маркеров не готов для обновления выделения.");
      return;
  }
  console.log("[MapComponent] watch props.selectedPointIds: Выбранные ID изменились. Новые:", newSelectedIds, "Старые:", oldSelectedIds);
  
  // Обновляем только те маркеры, чье состояние выделения могло измениться
  const idsToCheck = new Set();
  (oldSelectedIds || []).forEach(id => idsToCheck.add(id)); // Добавляем старые выбранные
  (newSelectedIds || []).forEach(id => idsToCheck.add(id)); // Добавляем новые выбранные

  idsToCheck.forEach(pointId => {
    markersLayer.eachLayer(marker => {
      if (marker.options.pointId === pointId) {
        const pointFeature = props.pointsData.find(p => p.properties && p.properties.id === pointId);
        if (pointFeature && pointFeature.properties) {
          const pointType = pointFeature.properties.point_type || 'default';
          const isCurrentlySelected = (newSelectedIds || []).includes(pointId);
          marker.setIcon(createCustomIcon(pointType, isCurrentlySelected)); // Обновляем иконку
        }
        return false; // Нашли нужный маркер, выходим из eachLayer для этого ID
      }
    });
  });
}, { deep: true });

// Хук жизненного цикла: вызывается после того, как компонент смонтирован в DOM
onMounted(() => {
  console.log("[MapComponent] onMounted: Компонент смонтирован. Инициализация карты...");
  initializeMap(); // Инициализируем карту (создает mapInstance и markersLayer)
  
  // После инициализации карты, если данные точек (props.pointsData) уже доступны,
  // отрисовываем их. Это для случая, когда данные приходят до или одновременно с монтированием.
  if (props.pointsData && props.pointsData.length > 0 && mapInstance && markersLayer) {
      console.log("[MapComponent] onMounted: Карта готова, есть начальные данные. Отрисовка маркеров.");
      updateMarkersOnMap(props.pointsData);
  } else {
      console.log("[MapComponent] onMounted: Карта готова, но нет начальных данных для маркеров или карта/слой еще не созданы.");
  }
});

// Хук жизненного цикла: вызывается перед тем, как компонент будет размонтирован
onBeforeUnmount(() => {
  console.log("[MapComponent] onBeforeUnmount: Компонент будет размонтирован. Очистка карты...");
  if (mapInstance) {
    mapInstance.remove(); // Корректно удаляем инстанс карты Leaflet
    mapInstance = null;
    markersLayer = null; // Также сбрасываем ссылку на слой
    console.log("[MapComponent] Карта и слой маркеров успешно удалены.");
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
.map-container { /* Добавьте, если еще нет, для корректной высоты карты */
  height: 100%;
  width: 100%;
}
</style>