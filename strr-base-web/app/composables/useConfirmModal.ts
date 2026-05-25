import { ModalBase } from '#components'

export type OpenConfirmOptions = {
  title: string
  content: string
  confirmLabel: string
  cancelLabel: string
  confirmVariant?: string
  cancelVariant?: string
  /** Render confirm before cancel (e.g. unsaved-changes layout). */
  confirmFirst?: boolean
  hideCancel?: boolean
}

export type OpenConfirmAndRunOptions = OpenConfirmOptions & {
  onConfirm: () => Promise<void>
  onError?: (error: unknown) => void
}

type ConfirmAction = {
  label: string
  handler: () => void
  variant?: string
}

/**
 * Programmatic confirm modals for Nuxt UI's single modal slot.
 * Always resolves or runs follow-up work after the modal has fully left.
 */
export function useConfirmModal () {
  const modal = useModal()

  function close () {
    modal.close()
  }

  function buildActions (options: OpenConfirmOptions, requestClose: (confirmed: boolean) => void): ConfirmAction[] {
    const confirmAction: ConfirmAction = {
      label: options.confirmLabel,
      handler: () => requestClose(true),
      variant: options.confirmVariant
    }
    const cancelAction: ConfirmAction = {
      label: options.cancelLabel,
      handler: () => requestClose(false),
      variant: options.cancelVariant ?? 'outline'
    }

    if (options.hideCancel) {
      return [confirmAction]
    }

    return options.confirmFirst
      ? [confirmAction, cancelAction]
      : [cancelAction, confirmAction]
  }

  function openConfirmModal (
    options: OpenConfirmOptions,
    onAfterLeave: (confirmed: boolean) => void | Promise<void>
  ): void {
    let pendingConfirmed: boolean | null = null

    const requestClose = (confirmed: boolean) => {
      pendingConfirmed = confirmed
      close()
    }

    modal.open(ModalBase, {
      title: options.title,
      content: options.content,
      closeFn: () => requestClose(false),
      onAfterLeave: async () => {
        if (pendingConfirmed === null) {
          return
        }

        const confirmed = pendingConfirmed
        pendingConfirmed = null
        await onAfterLeave(confirmed)
      },
      actions: buildActions(options, requestClose)
    })
  }

  function openConfirm (options: OpenConfirmOptions): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      let settled = false

      openConfirmModal(options, (confirmed) => {
        if (settled) {
          return
        }
        settled = true
        resolve(confirmed)
      })
    })
  }

  function openConfirmAndRun (options: OpenConfirmAndRunOptions): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      let settled = false

      const settle = (value: boolean) => {
        if (settled) {
          return
        }
        settled = true
        resolve(value)
      }

      openConfirmModal(options, async (confirmed) => {
        if (!confirmed) {
          settle(false)
          return
        }

        try {
          await options.onConfirm()
          settle(true)
        } catch (error) {
          options.onError?.(error)
          settle(true)
        }
      })
    })
  }

  return {
    openConfirm,
    openConfirmAndRun
  }
}
