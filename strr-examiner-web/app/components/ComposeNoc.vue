<script setup lang="ts">
const { sendNocSchema, sendEmailSchema } = useExaminerStore()
const {
  emailFormRef,
  showComposeEmail,
  emailContent,
  showComposeNocEmail,
  isAssignedToUser,
  activeHeader,
  hasRegistrationNumber,
  isApplication,
  activeReg
} = storeToRefs(useExaminerStore())
const { t } = useNuxtApp().$i18n

const isStrataHotelRenewalApplication = computed(() => {
  const header = activeHeader.value as { applicationType?: string } | undefined
  return isApplication.value &&
    hasRegistrationNumber.value &&
    activeReg.value?.registrationType === ApplicationType.STRATA_HOTEL &&
    header?.applicationType === 'renewal'
})

const canShowComposeEmail = computed(() =>
  (!!showComposeEmail?.value || !!showComposeNocEmail?.value) &&
  !!isAssignedToUser?.value &&
  (!hasRegistrationNumber?.value || isStrataHotelRenewalApplication.value)
)
const formSchema = computed(
  () =>
    [
      ApplicationStatus.PROVISIONAL_REVIEW_NOC_PENDING,
      ApplicationStatus.PROVISIONAL_REVIEW_NOC_EXPIRED
    ].includes(activeHeader.value?.status)
      ? sendEmailSchema.value
      : sendNocSchema.value
)

const handleInput = () => {
  if (emailContent.value.content.length > 1 && emailFormRef.value) {
    emailFormRef.value.clear()
  }
}

const isEmailExpanded = ref(false)
const toggleEmailExpanded = () => {
  isEmailExpanded.value = !isEmailExpanded.value
  const textareaEl = emailFormRef.value?.$el?.querySelector('textarea')
  if (textareaEl) {
    textareaEl.style.height = ''
  }
}

// Reset the email a completing party content so that it does not carry to other applications
onMounted(() => {
  emailContent.value.content = ''
})
</script>

<template>
  <div
    v-if="canShowComposeEmail"
    class="app-inner-container"
  >
    <div class="mb-8 rounded bg-white py-6">
      <UForm
        ref="emailFormRef"
        :schema="formSchema"
        :state="emailContent"
        :validate-on="['submit']"
        data-testid="compose-email"
      >
        <div class="flex">
          <div class="flex w-1/5 flex-col items-center justify-between">
            <span class="pl-5 font-bold">{{ t('modal.noc.title') }}</span>
            <UButton
              :icon="isEmailExpanded ? 'i-mdi-arrow-collapse-vertical' : 'i-mdi-arrow-expand-vertical'"
              :label="isEmailExpanded ? t('btn.collapse') : t('btn.expand')"
              size="xs"
              color="primary"
              variant="ghost"
              data-testid="toggle-expand-noc-email"
              :aria-label="isEmailExpanded ? t('decision.collapseEmail') : t('decision.expandEmail')"
              @click="toggleEmailExpanded"
            />
          </div>
          <div class="flex-auto pr-10">
            <UFormGroup name="content">
              <UTextarea
                v-model="emailContent.content"
                :placeholder="t('modal.noc.placeholder')"
                :aria-label="t('modal.noc.placeholder')"
                :color="'gray'"
                class="text-bcGovColor-midGray focus:ring-0"
                auto-resize
                resize
                :rows="isEmailExpanded ? 12 : 3"
                @update:model-value="handleInput"
              />
            </UFormGroup>
          </div>
        </div>
      </UForm>
    </div>
  </div>
</template>
