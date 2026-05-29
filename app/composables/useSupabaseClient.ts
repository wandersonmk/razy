import type { SupabaseClient } from '@supabase/supabase-js'

export function useSupabaseClient(): SupabaseClient {
  // Só funciona no cliente
  if (process.server) {
    throw new Error('useSupabaseClient só pode ser usado no cliente')
  }

  const nuxtApp = useNuxtApp()
  
  if (!nuxtApp.$supabase) {
    console.error('[useSupabaseClient] Cliente não encontrado. Verifique se:')
    console.error('1. As variáveis de ambiente estão configuradas no arquivo .env')
    console.error('2. O plugin supabase.client.ts está sendo carregado')
    console.error('3. As URLs e chaves do Supabase estão corretas')
    throw new Error('Supabase client não foi inicializado. Verifique as variáveis de ambiente.')
  }

  return nuxtApp.$supabase as SupabaseClient
}


