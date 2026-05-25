// https://ui.nuxt.com/components/modal#control-programmatically
import {
  ModalBase
} from '#components'
import PlatformRegNumHelp from '~/components/modal/info/PlatformRegNumHelp.vue'
import SupportingDocumentsHelp from '~/components/modal/info/SupportingDocumentsHelp.vue'

export const useHostPmModals = () => {
  const modal = useModal()
  const { openConfirm, openConfirmAndRun } = useConfirmModal()
  const { t } = useNuxtApp().$i18n
  const reqStore = usePropertyReqStore()
  const propStore = useHostPropertyStore()
  const docStore = useDocumentStore()

  function proceedToPayModalOptions () {
    return {
      title: t('modal.proceedToPay.title'),
      content: t('modal.proceedToPay.content'),
      confirmLabel: t('modal.proceedToPay.confirmBtn'),
      cancelLabel: t('modal.proceedToPay.closeBtn')
    }
  }

  function openHelpCreateAccountModal () {
    modal.open(ModalBase, {
      title: t('modal.createAccount.title'),
      content: t('modal.createAccount.content'),
      error: { showContactInfo: true, title: '', description: '', hideIcon: true },
      actions: [{ label: t('btn.close'), handler: () => close() }]
    })
  }

  function openConfirmRestartApplicationModal (edit = true) {
    openConfirmAndRun({
      title: edit ? t('modal.editUnitAddress.title') : t('modal.removeUnitAddress.title'),
      content: edit ? t('modal.editUnitAddress.content') : t('modal.removeUnitAddress.content'),
      confirmLabel: edit ? t('modal.editUnitAddress.confirmBtn') : t('modal.removeUnitAddress.confirmBtn'),
      cancelLabel: t('btn.cancel'),
      onConfirm: async () => {
        reqStore.$reset()
        propStore.$reset()
        await docStore.resetApiDocs()
      }
    }).catch(() => {})
  }

  function openStrataRegNumberHelpModal () {
    modal.open(PlatformRegNumHelp, {
      // @ts-expect-error - actions prop is passed down from PlatformRegNumHelp -> ModalBase
      actions: [{
        label: t('modal.strataPlatformNumHelp.closeBtn'),
        handler: () => close()
      }]
    })
  }

  function openConfirmProceedToPayAndRun (
    onConfirm: () => Promise<void>,
    onError: (error: unknown) => void
  ): Promise<boolean> {
    return openConfirmAndRun({
      ...proceedToPayModalOptions(),
      onConfirm,
      onError
    })
  }

  function openConfirmUnsavedChanges () {
    return openConfirm({
      title: t('modal.unsavedChanges.title'),
      content: t('modal.unsavedChanges.content'),
      confirmLabel: t('modal.unsavedChanges.confirmBtn'),
      cancelLabel: t('modal.unsavedChanges.closeBtn'),
      confirmFirst: true,
      confirmVariant: 'outline',
      cancelVariant: 'solid'
    })
  }

  function openSupportingDocumentsHelpModal () {
    modal.open(SupportingDocumentsHelp, {
      // @ts-expect-error - actions prop is passed down from SupportingDocumentsHelp -> ModalBase
      actions: [{
        label: t('btn.closeBtn'),
        handler: () => close()
      }]
    })
  }

  function close () {
    modal.close()
  }

  return {
    openHelpCreateAccountModal,
    openConfirmRestartApplicationModal,
    openStrataRegNumberHelpModal,
    openConfirmProceedToPayAndRun,
    openConfirmUnsavedChanges,
    openSupportingDocumentsHelpModal,
    close
  }
}
