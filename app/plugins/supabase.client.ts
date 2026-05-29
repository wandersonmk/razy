import { createClient } from '@supabase/supabase-js'

export default defineNuxtPlugin(() => {
  console.log('[Supabase Plugin] Executando plugin no cliente...')
  
  const config = useRuntimeConfig()
  
  console.log('[Supabase Plugin] Config disponível:', {
    hasPublicUrl: !!config.public?.supabaseUrl,
    hasPublicKey: !!config.public?.supabaseAnonKey
  })

  const url = config.public?.supabaseUrl as string
  const anonKey = config.public?.supabaseAnonKey as string

  if (!url || !anonKey) {
    console.error('[Supabase] Variáveis de ambiente ausentes.')
    return
  }

  console.log('[Supabase Plugin] Criando cliente...')
  const supabase = createClient(url, anonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      storage: window.localStorage,
      storageKey: 'agzap-auth-token',
      flowType: 'pkce'
    }
  })

  console.log('[Supabase Plugin] Cliente criado com sucesso')

  return {
    provide: {
      supabase
    }
  }
})


