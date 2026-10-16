import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, it, expect } from 'vitest'
import { nextTick } from 'vue'
import { enI18n } from '../mocks/i18n'
import ExpandableTextarea from '~/components/ExpandableTextarea.vue'

describe('ExpandableTextarea Component', () => {
  it('should render with initial compact height and enable resize by default', async () => {
    const wrapper = await mountSuspended(ExpandableTextarea, {
      props: {
        modelValue: '',
        placeholder: 'Enter details...',
        dataTestid: 'custom-area'
      },
      global: { plugins: [enI18n] }
    })

    const textarea = wrapper.find('[data-testid="custom-area"]')
    expect(textarea.exists()).toBe(true)
    expect(textarea.classes()).toContain('h-[290px]')
    expect(textarea.classes()).toContain('min-h-[290px]')
    expect(textarea.classes()).not.toContain('resize-none')
  })

  it('should not display the expand button when text is empty', async () => {
    const wrapper = await mountSuspended(ExpandableTextarea, {
      props: {
        modelValue: '',
        dataTestid: 'custom-area'
      },
      global: { plugins: [enI18n] }
    })

    expect(wrapper.find('[data-testid="custom-area-toggle-expand"]').exists()).toBe(false)
  })

  it('should display the expand button when text exceeds line threshold', async () => {
    const longText = Array(12).fill('Line of text in editor').join('\n')
    const wrapper = await mountSuspended(ExpandableTextarea, {
      props: {
        modelValue: longText,
        dataTestid: 'custom-area'
      },
      global: { plugins: [enI18n] }
    })

    const toggleBtn = wrapper.find('[data-testid="custom-area-toggle-expand"]')
    expect(toggleBtn.exists()).toBe(true)
    expect(toggleBtn.text()).toContain('Expand')
  })

  it('should toggle between expand and collapse while preserving content', async () => {
    const longText = Array(15).fill('Decision condition item').join('\n')
    const wrapper = await mountSuspended(ExpandableTextarea, {
      props: {
        modelValue: longText,
        dataTestid: 'custom-area',
        toggleTestid: 'toggle-btn'
      },
      global: { plugins: [enI18n] }
    })

    const toggleBtn = wrapper.find('[data-testid="toggle-btn"]')
    expect(toggleBtn.exists()).toBe(true)
    expect(toggleBtn.text()).toContain('Expand')

    const textarea = wrapper.find('[data-testid="custom-area"]')
    expect(textarea.classes()).toContain('h-[290px]')

    // Expand
    await toggleBtn.trigger('click')
    expect(toggleBtn.text()).toContain('Collapse')
    expect(textarea.classes()).toContain('min-h-[560px]')
    expect(textarea.classes()).toContain('max-h-[80vh]')
    expect((textarea.element as HTMLTextAreaElement).value).toBe(longText)
    expect(wrapper.emitted('toggleExpand')?.[0]).toEqual([true])

    // Collapse
    await toggleBtn.trigger('click')
    expect(toggleBtn.text()).toContain('Expand')
    expect(textarea.classes()).toContain('h-[290px]')
    expect((textarea.element as HTMLTextAreaElement).value).toBe(longText)
    expect(wrapper.emitted('toggleExpand')?.[1]).toEqual([false])
  })

  it('should emit update:modelValue and change events on input', async () => {
    const wrapper = await mountSuspended(ExpandableTextarea, {
      props: {
        modelValue: 'Initial',
        dataTestid: 'custom-area'
      },
      global: { plugins: [enI18n] }
    })

    const textarea = wrapper.find('[data-testid="custom-area"]')
    await textarea.setValue('Updated text')
    await nextTick()

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('change')).toBeTruthy()
  })

  it('should respect disabled prop', async () => {
    const wrapper = await mountSuspended(ExpandableTextarea, {
      props: {
        modelValue: 'Disabled text',
        disabled: true,
        dataTestid: 'custom-area'
      },
      global: { plugins: [enI18n] }
    })

    const textarea = wrapper.find('[data-testid="custom-area"]')
    expect(textarea.attributes('disabled')).toBeDefined()
  })
})
