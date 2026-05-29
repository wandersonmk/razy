import { ref } from 'vue'

export interface StatusUazapi {
  configurado: boolean
  url: string
  delay_ms: number
}

export function useConfigUazapi() {
  const status = ref<StatusUazapi>({ configurado: false, url: '', delay_ms: 2000 })
  const isLoading = ref(false)

  const fetchStatus = async () => {
    if (process.server) return

    isLoading.value = true
    try {
      const supabase = useSupabaseClient()
      const { data: sessionData } = await supabase.auth.getSession()
      const token = sessionData.session?.access_token
      if (!token) return

      const response = await fetch('/api/whatsapp/config', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!response.ok) return
      status.value = await response.json()
    } finally {
      isLoading.value = false
    }
  }

  const estaConfigurado = () => status.value.configurado

  return { status, isLoading, fetchStatus, estaConfigurado }
}
