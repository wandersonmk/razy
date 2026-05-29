export async function useToastSafe() {
  if (process.client) {
    const nuxtApp = useNuxtApp()
    if ((nuxtApp as any).$toast) {
      return (nuxtApp as any).$toast
    }

    try {
      const mod: any = await import('vue-toastification')
      const useToast = mod.useToast || (mod.default && mod.default.useToast)
      if (typeof useToast === 'function') {
        return useToast()
      }
    } catch (e) {
      // silencioso: retornará undefined e os componentes usam fallback
    }
  }

  return undefined
}


