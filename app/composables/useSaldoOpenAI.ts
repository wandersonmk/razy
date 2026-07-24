// Lê a flag `openai_sem_saldo` da integração do usuário (RLS escopa por conta) e
// mantém atualizada por polling leve. Alimenta o banner de "conta sem saldo".
//
// A flag é gravada pelo serviço de IA: sobe quando a OpenAI retorna
// 429/insufficient_quota e cai sozinha assim que a IA volta a responder — ou
// seja, o banner some ~1 minuto depois de recarregar, sem intervenção.
import { ref, onMounted, onBeforeUnmount } from 'vue'

const INTERVALO_MS = 60_000

export const useSaldoOpenAI = () => {
  const semSaldo = ref(false)
  const carregado = ref(false)
  let supabase: any = null
  let timer: ReturnType<typeof setInterval> | null = null

  const verificar = async () => {
    if (typeof window === 'undefined') return
    if (!supabase) supabase = useSupabaseClient()
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.user) { semSaldo.value = false; return }
      const { data } = await supabase
        .from('integracoes')
        .select('openai_sem_saldo')
        .eq('usuario_id', session.user.id)
        .maybeSingle()
      semSaldo.value = !!data?.openai_sem_saldo
    } catch {
      // Silencioso: o banner nunca deve quebrar a navegação.
    } finally {
      carregado.value = true
    }
  }

  onMounted(() => {
    verificar()
    timer = setInterval(verificar, INTERVALO_MS)
    // Revalida ao voltar o foco na aba (ex.: depois de recarregar na OpenAI).
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisibility)
    }
  })

  const onVisibility = () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'visible') verificar()
  }

  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibility)
  })

  return { semSaldo, carregado, verificar }
}
