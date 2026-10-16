<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useResizeObserver } from '@vueuse/core'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  dataTestid?: string
  toggleTestid?: string
  expandAriaLabel?: string
  collapseAriaLabel?: string
  initialHeight?: number
  expandedMinHeight?: number
  overflowThresholdLines?: number
  overflowThresholdChars?: number
  resize?: boolean
  color?: string
  bgClass?: string
}>(), {
  dataTestid: 'expandable-textarea',
  toggleTestid: '',
  expandAriaLabel: '',
  collapseAriaLabel: '',
  initialHeight: 290,
  expandedMinHeight: 560,
  overflowThresholdLines: 8,
  overflowThresholdChars: 300,
  resize: true,
  color: 'gray',
  bgClass: '!bg-str-bgGray'
})

const emit = defineEmits<{
  change: [value: string]
  toggleExpand: [expanded: boolean]
}>()

const model = defineModel<string>({ default: '' })
const { t } = useI18n()

const textareaRef = ref<{ textarea?: HTMLTextAreaElement, $el?: HTMLElement } | null>(null)
const isExpanded = ref(false)
const scrollHeight = ref(0)
const isOverflowing = ref(false)

const textareaEl = computed<HTMLTextAreaElement | null>(() =>
  textareaRef.value?.textarea ??
  textareaRef.value?.$el?.querySelector?.('textarea') ??
  null
)

const syncMetrics = () => {
  const el = textareaEl.value
  if (!el) { return }
  scrollHeight.value = el.scrollHeight
  isOverflowing.value = el.scrollHeight > el.clientHeight + 10
}

useResizeObserver(textareaEl, syncMetrics)

watch(model, () => {
  nextTick(syncMetrics)
})

const hasExpandableContent = computed(() => {
  const text = (model.value || '').trim()
  if (!text) { return false }
  return text.split('\n').length > props.overflowThresholdLines ||
    text.length > props.overflowThresholdChars
})

const canToggleExpand = computed(() =>
  isExpanded.value || hasExpandableContent.value || isOverflowing.value
)

const toggleExpand = () => {
  syncMetrics()
  isExpanded.value = !isExpanded.value
  emit('toggleExpand', isExpanded.value)
}

const textareaClasses = computed(() => {
  const heightClasses = isExpanded.value
    ? (props.expandedMinHeight === 560
        ? 'min-h-[560px] max-h-[80vh]'
        : `min-h-[${props.expandedMinHeight}px] max-h-[80vh]`)
    : (props.initialHeight === 290
        ? 'min-h-[290px] h-[290px]'
        : `min-h-[${props.initialHeight}px] h-[${props.initialHeight}px]`)

  return [
    heightClasses,
    props.bgClass,
    'focus:ring-0 transition-all duration-200'
  ].join(' ')
})

const textareaStyle = computed(() =>
  isExpanded.value
    ? {
        height: `${Math.max(scrollHeight.value + 32, props.expandedMinHeight)}px`,
        minHeight: `${props.expandedMinHeight}px`,
        maxHeight: '80vh'
      }
    : {
        height: `${props.initialHeight}px`,
        minHeight: `${props.initialHeight}px`
      }
)
</script>

<template>
  <div class="relative w-full">
    <UTextarea
      ref="textareaRef"
      v-model="model"
      v-bind="$attrs"
      :data-testid="dataTestid"
      :color="color as any"
      :resize="resize"
      :style="textareaStyle"
      autoresize
      :ui="{
        base: textareaClasses,
        padding: {
          sm: 'p-4 pr-24'
        }
      }"
      @update:model-value="emit('change', $event)"
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
