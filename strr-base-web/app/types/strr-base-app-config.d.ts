type StrrLoginIdp = 'bcsc' | 'bceid' | 'idir'

declare module 'nuxt/schema' {
  interface AppConfigInput {
    strrBaseLayer: {
      page: {
        login: {
          redirectPath: string,
          options: {
            createAccount: boolean,
            idps: Array<StrrLoginIdp>,
            loginIdpButtonClass?: Partial<Record<StrrLoginIdp, string>>,
            loginIdpButtonContainerClass?: Partial<Record<StrrLoginIdp, string>>,
            /** If set, the JWT must include every listed role in `realm_access.roles`. */
            requiredRealmRoles?: string[],
            bcscSubtext: string | undefined,
            bceidSubtext: string | undefined,
            idirSubtext: string | undefined
          }
        }
      },
      feeWidget?: {
        itemLabelTooltip: Record<string, { i18nkey: string, hrefRtcKey?: keyof PublicRuntimeConfig }> // typeCode
      },
      feeInfo?: {
        hrefRtcKey?: keyof PublicRuntimeConfig
      },
      sbcWebMsg: {
        enable: boolean
      }
    }
  }
}

declare module 'nuxt/schema' {
  interface AppConfig {
    strrBaseLayer: {
      page: {
        login: {
          redirectPath: string,
          options: {
            createAccount: boolean,
            idps: Array<StrrLoginIdp>,
            loginIdpButtonClass?: Partial<Record<StrrLoginIdp, string>>,
            loginIdpButtonContainerClass?: Partial<Record<StrrLoginIdp, string>>,
            /** If set, the JWT must include every listed role in `realm_access.roles`. */
            requiredRealmRoles?: string[],
            bcscSubtext: string | undefined,
            bceidSubtext: string | undefined,
            idirSubtext: string | undefined
          }
        }
      },
      feeWidget?: {
        itemLabelTooltip: Record<string, { i18nkey: string, hrefRtcKey?: keyof PublicRuntimeConfig }> // typeCode
      },
      feeInfo?: {
        hrefRtcKey?: keyof PublicRuntimeConfig
      },
      sbcWebMsg: {
        enable: boolean
      }
    }
  }
}

declare global {
  interface Window {
    _genesysJs: string
    Genesys: {
      q?: any[]
      t?: number
      c?: {
        environment: string
        deploymentId: string
      }
    }
  }
}

export {}
