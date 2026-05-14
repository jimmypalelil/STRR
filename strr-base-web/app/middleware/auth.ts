function realmRolesFromToken (): string[] {
  const parsed = useNuxtApp().$keycloak?.tokenParsed as { realm_access?: { roles?: string[] } } | undefined
  return parsed?.realm_access?.roles ?? []
}

export default defineNuxtRouteMiddleware(() => {
  const { isAuthenticated, kcUser, logout } = useKeycloak()
  const loginOptions = useAppConfig().strrBaseLayer.page.login.options
  const allowedIdps = loginOptions.idps
  const requiredRealmRoles = loginOptions.requiredRealmRoles?.filter(Boolean) ?? []

  if (!isAuthenticated.value) { // redirect to login page if user not authenticated
    const localePath = useLocalePath()
    return navigateTo(localePath('/auth/login'))
  }

  const loginSource = kcUser.value.loginSource.toLowerCase()
  const locale = useNuxtApp().$i18n.locale.value

  if (!(allowedIdps as readonly string[]).includes(loginSource)) { // log user out and redirect to login page if user authenticated with invalid login source
    const redirectUrl =
      useRuntimeConfig().public.baseUrl + locale + '/auth/login?invalidIdp=' + kcUser.value.loginSource
    logout(redirectUrl)
    return
  }

  const realmRoles = realmRolesFromToken()
  if (
    requiredRealmRoles.length > 0 &&
    !requiredRealmRoles.every((role: string) => realmRoles.includes(role))
  ) {
    const redirectUrl =
      useRuntimeConfig().public.baseUrl +
      locale +
      '/auth/login?missingRoles=' +
      encodeURIComponent(requiredRealmRoles.join(','))
    logout(redirectUrl)
  }
})
