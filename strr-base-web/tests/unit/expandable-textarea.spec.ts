import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ConnectFormExpandableTextarea from '../../app/components/connect/form/ExpandableTextarea.vue'

vi.stubGlobal('useI18n', () => ({
  t: (key: string) => (key === 'btn.expand' ? 'Expand' : key === 'btn.collapse' ? 'Collapse' : key)
}))

describe('ConnectFormExpandableTextarea Component', () => {
  const globalMocks = {
    mocks: {
      $t: (key: string) => (key === 'btn.expand' ? 'Expand' : key === 'btn.collapse' ? 'Collapse' : key)
    },
    stubs: {
      UTextarea: {
        props: ['modelValue', 'placeholder', 'disabled', 'resize', 'ui'],
        template: `
          <div class="u-textarea-stub" :class="ui?.base">
            <textarea
              :value="modelValue"
              :placeholder="placeholder"
              :disabled="disabled"
              @input="$emit('update:modelValue', $event.target.value)"
              @blur="$emit('blur', $event)"
            />
            <slot />
          </div>
        `
      },
      UButton: {
        props: ['icon', 'label', 'ariaLabel'],
        template: '<button class="u-button-stub" :aria-label="ariaLabel">{{ label }}</button>'
      }
    }
  }

  it('renders with default compact height', () => {
    const wrapper = mount(ConnectFormExpandableTextarea, {
      props: {
        modelValue: '',
        placeholder: 'Enter content...',
        dataTestid: 'custom-textarea'
      },
      global: globalMocks
    })

    expect(wrapper.find('.u-textarea-stub').classes()).toContain('h-[290px]')
    expect(wrapper.find('.u-textarea-stub').classes()).toContain('min-h-[80px]')
    expect(wrapper.find('.u-textarea-stub').classes()).toContain('resize-y')
    expect(wrapper.find('.u-textarea-stub').classes()).not.toContain('transition-all')
  })

  it('hides the toggle button when text is empty', () => {
    const wrapper = mount(ConnectFormExpandableTextarea, {
      props: {
        modelValue: ''
      },
      global: globalMocks
    })

    expect(wrapper.find('.u-button-stub').exists()).toBe(false)
  })

  it('shows the expand toggle button when text exceeds threshold', () => {
    const longText = Array(12).fill('Test line of text').join('\n')
    const wrapper = mount(ConnectFormExpandableTextarea, {
      props: {
        modelValue: longText
      },
      global: globalMocks
    })

    const button = wrapper.find('.u-button-stub')
    expect(button.exists()).toBe(true)
    expect(button.text()).toBe('Expand')
  })

  it('toggles expansion state when button is clicked', async () => {
    const longText = Array(12).fill('Decision reason').join('\n')
    const wrapper = mount(ConnectFormExpandableTextarea, {
      props: {
        modelValue: longText
      },
      global: globalMocks
    })

    const button = wrapper.find('.u-button-stub')
    expect(button.text()).toBe('Expand')

    await button.trigger('click')
    await nextTick()

    expect(wrapper.find('.u-textarea-stub').classes()).not.toContain('max-h-[80vh]')
    expect(wrapper.find('textarea').element.style.height).toBe('560px')
    expect(wrapper.find('.u-button-stub').text()).toBe('Collapse')
    expect(wrapper.emitted('toggleExpand')).toBeTruthy()
    expect(wrapper.emitted('toggleExpand')![0]).toEqual([true])

    // Toggle back
    await wrapper.find('.u-button-stub').trigger('click')
    await nextTick()
    expect(wrapper.find('.u-textarea-stub').classes()).toContain('h-[290px]')
    expect(wrapper.find('textarea').element.style.height).toBe('290px')
    expect(wrapper.find('.u-button-stub').text()).toBe('Expand')
    expect(wrapper.emitted('toggleExpand')![1]).toEqual([false])
  })

  it('emits update:modelValue and change events on input', async () => {
    const wrapper = mount(ConnectFormExpandableTextarea, {
      props: {
        modelValue: 'Initial'
      },
      global: globalMocks
    })

    const textarea = wrapper.find('textarea')
    await textarea.setValue('Updated content')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['Updated content'])
    expect(wrapper.emitted('change')?.[0]).toEqual(['Updated content'])
  })
})
