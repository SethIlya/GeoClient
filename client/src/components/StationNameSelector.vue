<template>
  <div class="mb-3 station-name-selector-wrapper">
    <label :for="selectId" class="form-label mb-1 small">
      <strong>{{ label }}:</strong>
    </label>
    
    <div class="input-group input-group-sm">
      <select 
        :id="selectId" 
        class="form-select form-select-sm" 
        :value="modelValue" 
        @change="handleSelect($event.target.value)"
      >
        <option value="">-- {{ placeholder }} --</option>
        <option v-if="showCustomOptionInSelect" :value="customOptionValue" disabled>
          {{ customOptionValue }} (новое)
        </option>
        <option v-for="name in sortedAvailableNames" :key="name" :value="name">
          {{ name }}
        </option>
        <option :value="customInputOptionValue">-- Ввести свое имя... --</option>
      </select>
      <button 
        v-if="modelValue && !isModelValueInOfficialList && !isShowingCustomInput"
        class="btn btn-outline-success" 
        type="button" 
        @click.prevent="openManageNamesModalToPrefillCurrent"
        title="Добавить это новое имя в общий справочник..."
      >
        <i class="bi bi-bookmark-plus"></i>
      </button>
    </div>

    <input
      v-if="isShowingCustomInput"
      :id="customInputId"
      type="text"
      class="form-control form-control-sm mt-2"
      v-model="customInputValue"
      @input="handleCustomInput"
      @blur="applyCustomInput"
      placeholder="Введите новое имя станции"
      ref="customInputRef"
    />
    <div class="form-text small mt-1" v-if="modelValue && !isModelValueInOfficialList && !isShowingCustomInput">
        <i class="bi bi-lightbulb me-1 text-info"></i>Новое имя. Вы можете <a href="#" @click.prevent="openManageNamesModalToPrefillCurrent">добавить его в справочник</a>.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { Modal } from 'bootstrap';

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Имя точки (присвоенное)' },
  placeholder: { type: String, default: 'Выберите или введите имя' },
  availableNames: { type: Array, default: () => [] } // Список строк имен
});

const emit = defineEmits(['update:modelValue']);

const MANAGE_NAMES_MODAL_ID = 'manageStationNamesModalInstance'; // Должен совпадать с ID в App.vue

const instanceId = Math.random().toString(36).substring(2, 9);
const selectId = `stationNameSelect-${instanceId}`;
const customInputId = `stationNameCustomInput-${instanceId}`;
const customInputOptionValue = `__custom_input__${instanceId}`; // Уникальное значение для опции "Ввести свое"

const isShowingCustomInput = ref(false);
const customInputValue = ref('');
const customInputRef = ref(null); // ref для DOM-элемента кастомного инпута

// Если modelValue нет в официальном списке, но оно не пустое,
// это "новое" имя, которое нужно показать в select как выбранное (но disabled)
const customOptionValue = ref(''); 

watch(() => props.modelValue, (newValue) => {
    if (newValue && !props.availableNames.map(n=>n.toLowerCase()).includes(newValue.toLowerCase())) {
        customOptionValue.value = newValue; // Показываем текущее кастомное имя
    } else {
        customOptionValue.value = ''; // Сбрасываем, если имя из списка или пустое
    }
    // Если новое значение не соответствует опции "Ввести свое", скрываем поле ввода
    if (newValue !== customInputOptionValue) {
        isShowingCustomInput.value = false;
        customInputValue.value = ''; // Очищаем, если выбрали из списка
    }
}, { immediate: true });

const showCustomOptionInSelect = computed(() => {
    return !!(customOptionValue.value && !props.availableNames.map(n=>n.toLowerCase()).includes(customOptionValue.value.toLowerCase()));
});


const sortedAvailableNames = computed(() => {
    return [...props.availableNames].sort((a,b) => a.localeCompare(b, undefined, {sensitivity: 'base'}));
});

const isModelValueInOfficialList = computed(() => {
    if (!props.modelValue || !props.modelValue.trim()) return true;
    return props.availableNames.map(n => n.toLowerCase()).includes(props.modelValue.trim().toLowerCase());
});

const handleSelect = (selectedValue) => {
  if (selectedValue === customInputOptionValue) {
    isShowingCustomInput.value = true;
    customInputValue.value = props.modelValue || ''; // Предзаполняем, если уже есть кастомное значение
    nextTick(() => {
      customInputRef.value?.focus();
    });
    // Не эмитим событие сразу, ждем ввода в customInput
  } else {
    isShowingCustomInput.value = false;
    customInputValue.value = '';
    emit('update:modelValue', selectedValue);
  }
};

const handleCustomInput = (event) => {
  // Не эмитим здесь, чтобы не было слишком частых обновлений, пока пользователь печатает
  // emit('update:modelValue', event.target.value.trim());
};

const applyCustomInput = () => {
    const finalValue = customInputValue.value.trim();
    // if (isShowingCustomInput.value) { // Только если поле ввода было активно
        emit('update:modelValue', finalValue);
        // isShowingCustomInput.value = false; // Можно скрыть после ввода, или оставить
    // }
};

const openManageNamesModalToPrefillCurrent = () => {
    const modalElement = document.getElementById(MANAGE_NAMES_MODAL_ID);Ё
    if (modalElement) {
        const bsModal = Modal.getInstance(modalElement) || new Modal(modalElement);
        if (props.modelValue && !isModelValueInOfficialList.value) {
            localStorage.setItem('prefillStationNameModal', props.modelValue.trim());
        } else {
            localStorage.removeItem('prefillStationNameModal');
        }
        bsModal.show();
    } else {
        console.warn(`Модальное окно с ID '${MANAGE_NAMES_MODAL_ID}' не найдено.`);
    }
};
</script>

<style scoped>
.station-name-selector-wrapper .form-text a {
    cursor: pointer;
    text-decoration: underline;
    color: var(--bs-link-color);
}
.station-name-selector-wrapper .form-text a:hover {
    color: var(--bs-link-hover-color);
}
</style>