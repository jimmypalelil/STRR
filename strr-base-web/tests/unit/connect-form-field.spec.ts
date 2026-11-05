import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import ConnectFormField from '../../app/components/connect/form/field/Index.vue'
import { optionalOrEmptyString, getRequiredNonEmptyString } from '../../app/utils/connect-validation'
import { formatAddress } from '../../app/utils/formattingHelpers'

const stubs = {
  UInput: {
    inheritAttrs: false,
    props: ['modelValue', 'modelModifiers', 'id', 'placeholder', 'size', 'color', 'disabled', 'maxlength', 'min', 'max', 'type'],
    emits: ['update:modelValue', 'blur'],
    template: `
      <input
        :id="id"
        v-bind="$attrs"
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
        @blur="$emit('blur', $event)"
      />
    `
  }
}

describe('ConnectFormField & Validation', () => {
  it('allows entering space characters without trimming during user typing', async () => {
    const HostComponent = defineComponent({
      components: { ConnectFormField },
      setup () {
        const text = ref('')
        return { text }
      },
      template: '<ConnectFormField id="rental-unit-address-nickname" v-model="text" />'
    })

    const wrapper = mount(HostComponent, {
      global: {
        stubs,
        directives: {
          maska: () => {}
        }
      }
    })

    const input = wrapper.find('input')

    // Simulate user typing a word followed by space: must NOT trim during input
    await input.setValue('asfdasfsafd ')
    expect(wrapper.vm.text).toBe('asfdasfsafd ')

    // Simulate continuing to type
    await input.setValue('asfdasfsafd next')
    expect(wrapper.vm.text).toBe('asfdasfsafd next')
  })

  it('trims leading and trailing whitespace on blur', async () => {
    const HostComponent = defineComponent({
      components: { ConnectFormField },
      setup () {
        const text = ref('  accidental spacing  ')
        return { text }
      },
      template: '<ConnectFormField id="rental-unit-address-nickname" v-model="text" />'
    })

    const wrapper = mount(HostComponent, {
      global: {
        stubs,
        directives: {
          maska: () => {}
        }
      }
    })

    const input = wrapper.find('input')
    await input.trigger('blur')
    expect(wrapper.vm.text).toBe('accidental spacing')
  })

  it('trims leading and trailing whitespace during schema evaluation and transforms empty strings', () => {
    expect(optionalOrEmptyString.parse('  My Rental Property  ')).toBe('My Rental Property')
    expect(optionalOrEmptyString.parse('   ')).toBeUndefined()
    expect(optionalOrEmptyString.parse('')).toBeUndefined()
    expect(optionalOrEmptyString.parse(undefined)).toBeUndefined()

    expect(getRequiredNonEmptyString('Required').parse('  Main Street  ')).toBe('Main Street')
    expect(() => getRequiredNonEmptyString('Required').parse('   ')).toThrow()
  })

  it('formatAddress sanitizes and trims address properties', () => {
    const formatted = formatAddress({
      country: '  CA  ',
      street: '  123 Main St  ',
      streetAdditional: '  Suite 4  ',
      city: '  Victoria  ',
      region: '  BC  ',
      postalCode: '  V8W 1W4  ',
      locationDescription: '  Near the park  '
    })

    expect(formatted).toEqual({
      country: 'CA',
      address: '123 Main St',
      addressLineTwo: 'Suite 4',
      city: 'Victoria',
      province: 'BC',
      postalCode: 'V8W 1W4',
      locationDescription: 'Near the park'
    })
  })
})
