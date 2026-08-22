import type { RealtimeChannel } from '@supabase/supabase-js'

// Tempo real da página de Conversas — 1 canal privado por usuário
// (`usuario:{id}`), Broadcast autenticado via trigger no banco (ver migração
// `canal_por_profissional_realtime`). Singleton com refcount: várias partes da
// tela (lista + chat aberto) podem "assinar" sem abrir socket duplicado — o
// Realtime só permite 1 join por tópico por conexão.

type EventoPayload = { type: 'INSERT' | 'UPDATE' | 'DELETE'; record: any }
type Handler = (payload: EventoPayload) => void

let channel: RealtimeChannel | null = null
let usuarioAtual: string | null = null
let refCount = 0

const mensagemHandlers = new Set<Handler>()
const conversaHandlers = new Set<Handler>()

async function autenticarCanal() {
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  if (data?.session?.access_token) {
    // Precisa terminar ANTES do subscribe — sem isso o join sai sem token e a
    // RLS recusa o canal (cai em CHANNEL_ERROR silenciosamente).
    await supabase.realtime.setAuth(data.session.access_token)
  }
}

async function conectar(usuarioId: string) {
  if (channel && usuarioAtual === usuarioId) return
  if (channel) await desligarCanal()

  const supabase = useSupabaseClient()
  usuarioAtual = usuarioId
  const ch = supabase.channel(`usuario:${usuarioId}`, { config: { private: true } })

  ch.on('broadcast', { event: 'mensagem' }, ({ payload }: any) => {
    mensagemHandlers.forEach((h) => h(payload))
  })
  ch.on('broadcast', { event: 'conversa' }, ({ payload }: any) => {
    conversaHandlers.forEach((h) => h(payload))
  })

  channel = ch
  await autenticarCanal()
  ch.subscribe(async (status) => {
    if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
      // Token pode ter expirado (~1h) — reautentica e deixa o rejoin automático
      // do Phoenix tentar de novo com o token novo.
      await autenticarCanal()
    }
  })
}

async function desligarCanal() {
  if (!channel) return
  const supabase = useSupabaseClient()
  try {
    await supabase.removeChannel(channel)
  } catch {
    // best-effort
  }
  channel = null
  usuarioAtual = null
}

export function useRealtimeConversas() {
  const subscribe = async (usuarioId: string) => {
    refCount++
    await conectar(usuarioId)
  }

  const unsubscribe = async () => {
    refCount = Math.max(0, refCount - 1)
    if (refCount === 0) await desligarCanal()
  }

  const onMensagem = (handler: Handler) => {
    mensagemHandlers.add(handler)
    return () => mensagemHandlers.delete(handler)
  }

  const onConversa = (handler: Handler) => {
    conversaHandlers.add(handler)
    return () => conversaHandlers.delete(handler)
  }

  return { subscribe, unsubscribe, onMensagem, onConversa }
}
