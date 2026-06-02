import type { SupabaseClient } from '@supabase/supabase-js'

// Operações de limpeza de métricas do sistema.
// "Apagar métricas" zera tudo que alimenta o Dashboard e os Relatórios:
//   • disparos          → histórico de envios/respostas (fonte das métricas)
//   • followup_disparos → envios de follow-up
//   • campanhas         → zera os contadores e remove de vez as arquivadas
// Tudo é escopado por usuario_id e protegido por RLS (cada usuário só apaga o seu).
export function useMetricas() {
  const getSupabase = (): SupabaseClient | null => {
    if (process.server) return null
    return useSupabaseClient()
  }

  const apagarTodasMetricas = async () => {
    const supabase = getSupabase()
    if (!supabase) throw new Error('Indisponível no servidor')

    const { data: userData } = await supabase.auth.getUser()
    const uid = userData.user?.id
    if (!uid) throw new Error('Sessão expirada. Faça login novamente.')

    // 1) Histórico de disparos (de onde saem enviados/falhas/respostas)
    const { error: e1 } = await supabase.from('disparos').delete().eq('usuario_id', uid)
    if (e1) throw e1

    // 2) Disparos de follow-up
    const { error: e2 } = await supabase.from('followup_disparos').delete().eq('usuario_id', uid)
    if (e2) throw e2

    // 3) Zera os contadores denormalizados de todas as campanhas
    const { error: e3 } = await supabase
      .from('campanhas')
      .update({ total_enviados: 0, total_falhas: 0, total_respostas: 0 })
      .eq('usuario_id', uid)
    if (e3) throw e3

    // 4) Remove de vez as campanhas arquivadas — só existiam para guardar métricas.
    //    (campanha_logs e followup_configs somem por CASCADE.)
    const { error: e4 } = await supabase
      .from('campanhas')
      .delete()
      .eq('usuario_id', uid)
      .eq('arquivada', true)
    if (e4) throw e4
  }

  return { apagarTodasMetricas }
}
