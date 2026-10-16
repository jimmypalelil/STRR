<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
interface Props {
  modelValue?: string
  placeholder?: string
  disabled?: boolean
  ariaLabel?: string
  expandAriaLabel?: string
  collapseAriaLabel?: string
  dataTestid?: string
  toggleTestid?: string
  initialHeight?: number
  expandedMinHeight?: number
  maxViewportRatio?: number
  overflowThresholdLines?: number
  overflowThresholdChars?: number
  resize?: boolean
  color?: string
  bgClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '',
  disabled: false,
  ariaLabel: '',
  expandAriaLabel: '',
  collapseAriaLabel: '',
  dataTestid: 'expandable-textarea',
  toggleTestid: '',
  initialHeight: 290,
  expandedMinHeight: 560,
  maxViewportRatio: 0.8,
  overflowThresholdLines: 8,
  overflowThresholdChars: 300,
  resize: true,
  color: 'gray',
  bgClass: '!bg-str-bgGray'
})

const emit = defineEmits(['update:modelValue', 'change', 'blur', 'toggleExpand'])

const { t } = useI18n()

const textareaRef = ref<any>(null)
const isExpanded = ref(false)
const isTextareaOverflowing = ref(false)

const getTextareaEl = (): HTMLTextAreaElement | null => {
  if (!textareaRef.value) { return null }
  if (textareaRef.value.$el) {
    return textareaRef.value.$el.querySelector('textarea') || textareaRef.value.$el
  }
  return textareaRef.value instanceof HTMLTextAreaElement ? textareaRef.value : null
}

const checkOverflow = () => {
  const el = getTextareaEl()
  if (el) {
    isTextareaOverflowing.value = el.scrollHeight > el.clientHeight + 10
  }
}

const hasExpandableContent = computed(() => {
  const text = props.modelValue || ''
  if (!text.trim()) { return false }
  const lineCount = text.split('\n').length
  return lineCount > props.overflowThresholdLines || text.length > props.overflowThresholdChars
})

const canToggleExpand = computed(() =>
  isExpanded.value || hasExpandableContent.value || isTextareaOverflowing.value
)

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
  emit('toggleExpand', isExpanded.value)

  const el = getTextareaEl()
  if (el) {
    el.style.height = ''
    if (isExpanded.value) {
      nextTick(() => {
        const viewportCeiling = typeof window !== 'undefined'
          ? Math.floor(window.innerHeight * props.maxViewportRatio)
          : 800
        const targetHeight = Math.min(
          Math.max(el.scrollHeight + 32, props.expandedMinHeight),
          viewportCeiling
        )
        el.style.height = `${targetHeight}px`
      })
    }
  }
}

const textareaClasses = computed(() => [
  isExpanded.value
    ? `min-h-[${props.expandedMinHeight}px] max-h-[80vh]`
    : `min-h-[${props.initialHeight}px] h-[${props.initialHeight}px]`,
  props.bgClass,
  'focus:ring-0 transition-all duration-200'
].join(' '))

const onInput = (value: string) => {
  emit('update:modelValue', value)
  emit('change', value)
  nextTick(checkOverflow)
}

watch(() => props.modelValue, () => {
  nextTick(checkOverflow)
})

onMounted(() => {
  nextTick(checkOverflow)
})
</script>

<template>
  <div class="relative w-full">
    <UTextarea
      ref="textareaRef"
      :model-value="modelValue"
      :placeholder="placeholder"
      :aria-label="ariaLabel || placeholder"
      :data-testid="dataTestid"
      :color="color as any"
      :disabled="disabled"
      :resize="resize"
      auto-resize
      :ui="{
        base: textareaClasses,
        padding: {
          sm: 'p-4 pr-24'
        }
      }"
      @update:model-value="onInput"
      @blur="emit('blur', $event)"
    >
      <div
        v-if="canToggleExpand"
        class="absolute right-3 top-3 z-10"
      >
        <UButton
          :icon="isExpanded ? 'i-mdi-arrow-collapse-vertical' : 'i-mdi-arrow-expand-vertical'"
          :label="isExpanded ? t('btn.collapse') : t('btn.expand')"
          size="xs"
          color="white"
          variant="solid"
          class="shadow-sm"
          :data-testid="toggleTestid || `${dataTestid}-toggle-expand`"
          :aria-label="isExpanded
            ? (collapseAriaLabel || t('btn.collapse'))
            : (expandAriaLabel || t('btn.expand'))"
          @click="toggleExpand"
        />
      </div>
    </UTextarea>
  </div>
</template>
