import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import { flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, type Ref } from 'vue'
import { baseEnI18n } from '../mocks/i18n'
import { mockApplication } from '../mocks/mockedData'
import { applicationPageStubs } from './helpers/renewal-test-utils'
import Application from '~/pages/application.vue'

const replaceMock = vi.fn().mockResolvedValue(undefined)
const mockRoute = {
  path: '/application',
  query: { renew: 'true' } as Record<string, string>,
  meta: {} as Record<string, unknown>
}

const {
  renewalRegId,
  registrationRef,
  applicationRef,
  isRegistrationRenewalRef
} = vi.hoisted(() => {
  return {
    renewalRegId: { value: '12345', __v_isRef: true } as unknown as Ref<string>,
    registrationRef: { value: { id: 12345 }, __v_isRef: true } as unknown as Ref<{ id: number } | undefined>,
    applicationRef: { value: undefined, __v_isRef: true } as unknown as Ref<unknown>,
    isRegistrationRenewalRef: { value: true, __v_isRef: true } as unknown as Ref<boolean>
  }
})

const {
  submitApplicationMock,
  openAppSubmitErrorMock,
  openConfirmProceedToPayAndRunMock,
  validValidationStep
} = vi.hoisted(() => {
  const validStep = [{ formId: 'test', success: true, errors: [] }]
  return {
    validValidationStep: validStep,
    submitApplicationMock: vi.fn(),
    openAppSubmitErrorMock: vi.fn(),
    openConfirmProceedToPayAndRunMock: vi.fn(
      async (onConfirm: () => Promise<void>, onError: (e: unknown) => void) => {
        try {
          await onConfirm()
        } catch (e) {
          onError(e)
        }
        return true
      }
    )
  }
})
let lastButtonControl: {
  leftButtons: { action: () => void | Promise<void> }[]
  rightButtons: { action: () => void | Promise<void> }[]
} | null = null

const duplicateRenewalError = {
  statusCode: 409,
  data: {
    message: 'A renewal application is already in progress for this registration.',
    errorCode: 'RENEWAL_ALREADY_IN_PROGRESS'
  }
}

mockNuxtImport('useRouter', () => () => ({ replace: replaceMock }))
mockNuxtImport('useRoute', () => () => mockRoute)

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => mockRoute),
  useRouter: () => ({ replace: replaceMock }),
  onBeforeRouteLeave: vi.fn()
}))

vi.mock('#baseWeb/utils/todoItems', () => ({
  getTodoRegistration: vi.fn().mockResolvedValue({
    hasRenewalTodo: false,
    hasRenewalDraft: false,
    hasRenewalPaymentPending: false,
    renewalDraftId: null,
    renewalPaymentPendingId: null
  })
}))

vi.mock('@/stores/hostPermit', () => ({
  useHostPermitStore: () => ({
    loadHostRegistrationData: vi.fn(() => {
      registrationRef.value = { id: 7 }
    }),
    loadHostData: vi.fn(),
    renewalRegId,
    effectiveRegistrationId: renewalRegId,
    registration: registrationRef,
    application: applicationRef,
    isRegistrationRenewal: isRegistrationRenewalRef,
    persistSelectedRegistrationId: vi.fn(),
    $reset: vi.fn()
  })
}))

vi.mock('@/stores/hostProperty', () => ({
  useHostPropertyStore: () => ({
    unitAddress: { address: mockApplication.registration.unitAddress },
    unitDetails: ref(mockApplication.registration.unitDetails),
    blInfo: ref({ businessLicense: '', businessLicenseExpiryDate: '' }),
    validateUnitAddress: () => validValidationStep,
    validateUnitDetails: () => validValidationStep,
    validateBusinessLicense: () => validValidationStep,
    $reset: vi.fn()
  })
}))

vi.mock('@/stores/propertyRequirements', () => ({
  usePropertyReqStore: () => ({
    showUnitDetailsForm: ref(true),
    prRequirements: ref({ isPropertyPrExempt: false, prExemptionReason: undefined }),
    propertyReqs: ref({}),
    validateBlExemption: () => validValidationStep,
    validatePrRequirements: () => validValidationStep,
    $reset: vi.fn()
  })
}))

vi.mock('@/stores/hostOwner', () => ({
  useHostOwnerStore: () => ({ validateOwners: () => validValidationStep, $reset: vi.fn() })
}))

vi.mock('@/stores/document', () => ({
  useDocumentStore: () => ({
    validateRequiredDocuments: () => [],
    storedDocuments: ref([]),
    removeDocumentsByType: vi.fn(),
    $reset: vi.fn()
  })
}))

vi.mock('@/stores/hostApplication', () => ({
  useHostApplicationStore: () => ({
    submitApplication: submitApplicationMock,
    validateUserConfirmation: (returnBool = false) =>
      returnBool ? true : validValidationStep,
    $reset: vi.fn()
  })
}))

mockNuxtImport('useButtonControl', () => () => ({
  setButtonControl: (c: typeof lastButtonControl) => { lastButtonControl = c },
  handleButtonLoading: vi.fn()
}))

mockNuxtImport('useHostFeatureFlags', () => () => ({
  isSaveDraftEnabled: ref(true),
  isNewDashboardEnabled: ref(false),
  isEnhancedDocumentUploadEnabled: ref(false)
}))

vi.mock('@/composables/useHostApplicationFee', () => ({
  useHostApplicationFee: () => ({
    fetchStrrFees: vi.fn().mockResolvedValue({
      fee1: { amount: 100, feeCode: 'STR_HOST_1', serviceFees: [] },
      fee2: { amount: 450, feeCode: 'STR_HOST_2' },
      fee3: { amount: 100, feeCode: 'STR_HOST_3' }
    }),
    getApplicationFee: vi.fn().mockReturnValue({ amount: 100, feeCode: 'STR_HOST_1' })
  })
}))

mockNuxtImport('useStrrModals', () => () => ({
  openAppSubmitError: openAppSubmitErrorMock
}))

vi.mock('@/composables/useConnectNav', () => ({
  useConnectNav: () => ({ handlePaymentRedirect: vi.fn() })
}))

mockNuxtImport('useHostPmModals', () => () => ({
  openConfirmUnsavedChanges: vi.fn().mockResolvedValue(true),
  openConfirmProceedToPayAndRun: openConfirmProceedToPayAndRunMock
}))

const draftSaveStubs = applicationPageStubs

const mountRenewalApplication = () =>
  mountSuspended(Application, { global: { plugins: [baseEnI18n], stubs: draftSaveStubs } })

async function clickSaveDraft () {
  const saveAction = lastButtonControl?.leftButtons?.[2]?.action
  expect(saveAction).toBeTypeOf('function')
  await saveAction?.()
  await flushPromises()
}

describe('Application page — renewal draft save', () => {
  beforeEach(() => {
    mockRoute.meta = {}
    lastButtonControl = null
    replaceMock.mockClear()
    mockRoute.query = { renew: 'true' }
    renewalRegId.value = '42'
    registrationRef.value = undefined
    isRegistrationRenewalRef.value = false
    submitApplicationMock.mockReset()
    openAppSubmitErrorMock.mockReset()
    openConfirmProceedToPayAndRunMock.mockClear()
    submitApplicationMock.mockResolvedValue({
      paymentToken: '',
      filingId: 'NEW-DRAFT-ID',
      applicationStatus: 'DRAFT',
      applicationType: 'renewal'
    })
  })

  it('first save POSTs without id and syncs applicationId to query', async () => {
    await mountRenewalApplication()
    await flushPromises()
    await clickSaveDraft()
    expect(submitApplicationMock).toHaveBeenCalledWith(true, undefined)
    expect(replaceMock).toHaveBeenCalledWith(
      expect.objectContaining({ query: expect.objectContaining({ applicationId: 'NEW-DRAFT-ID' }) })
    )
  }, 10000)

  it('second save PUTs with filing id from first save', async () => {
    await mountRenewalApplication()
    await flushPromises()
    await clickSaveDraft()
    submitApplicationMock.mockClear()
    await clickSaveDraft()
    expect(submitApplicationMock).toHaveBeenCalledWith(true, 'NEW-DRAFT-ID')
  }, 10000)

  it('session expiry handler reuses effective application number after draft save', async () => {
    await mountRenewalApplication()
    await flushPromises()
    await clickSaveDraft()
    submitApplicationMock.mockClear()
    await (mockRoute.meta.onBeforeSessionExpired as () => Promise<unknown>)()
    expect(submitApplicationMock).toHaveBeenCalledWith(true, 'NEW-DRAFT-ID')
  }, 10000)

  it('opens submit error modal when duplicate renewal POST returns 409', async () => {
    submitApplicationMock.mockRejectedValue(duplicateRenewalError)

    await mountRenewalApplication()
    await flushPromises()

    const saveAction = lastButtonControl?.leftButtons?.[2]?.action
    expect(saveAction).toBeTypeOf('function')
    replaceMock.mockClear()
    await expect(saveAction?.()).rejects.toEqual(duplicateRenewalError)
    await flushPromises()

    expect(submitApplicationMock).toHaveBeenCalledWith(true, undefined)
    expect(openAppSubmitErrorMock).toHaveBeenCalledWith(duplicateRenewalError)
    expect(replaceMock).not.toHaveBeenCalled()
  }, 10000)

  it('routes proceed-to-pay submit 409 through onError callback', async () => {
    submitApplicationMock.mockRejectedValue(duplicateRenewalError)

    await mountRenewalApplication()
    await flushPromises()

    await openConfirmProceedToPayAndRunMock(
      async () => {
        await submitApplicationMock(false, undefined)
      },
      openAppSubmitErrorMock
    )
    await flushPromises()

    expect(submitApplicationMock).toHaveBeenCalledWith(false, undefined)
    expect(openAppSubmitErrorMock).toHaveBeenCalledWith(duplicateRenewalError)
  }, 10000)
})
