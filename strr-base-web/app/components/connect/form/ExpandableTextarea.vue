<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'

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
const isOverflowing = ref(false)

const getTextareaEl = (): HTMLTextAreaElement | null =>
  textareaRef.value?.textarea ??
  textareaRef.value?.$el?.querySelector?.('textarea') ??
  null

const checkOverflow = () => {
  const el = getTextareaEl()
  if (el) {
    isOverflowing.value = el.scrollHeight > el.clientHeight + 10
  }
}

const applyHeight = (heightPx: number) => {
  const el = getTextareaEl()
  if (el) {
    el.style.height = `${heightPx}px`
  }
}

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
  isExpanded.value = !isExpanded.value
  emit('toggleExpand', isExpanded.value)

  const el = getTextareaEl()
  if (!el) { return }

  if (isExpanded.value) {
    const targetHeight = Math.max(el.scrollHeight + 32, props.expandedMinHeight)
    applyHeight(targetHeight)
  } else {
    applyHeight(props.initialHeight)
  }
}

const textareaClasses = computed(() => {
  const collapsedHeightClass = props.initialHeight === 290
    ? 'h-[290px]'
    : `h-[${props.initialHeight}px]`

  return [
    !isExpanded.value && collapsedHeightClass,
    'min-h-[80px] resize-y focus:ring-0',
    props.bgClass
  ].filter(Boolean).join(' ')
})

watch(model, () => {
  nextTick(checkOverflow)
})

onMounted(() => {
  applyHeight(props.initialHeight)
  nextTick(checkOverflow)
})
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
