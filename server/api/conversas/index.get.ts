// GET /api/conversas
// Lista as conversas do usuário (página de Conversas) — de qualquer canal que
// tenha timeline gravada: canal por profissional e canal de disparo (a IA
// service grava em `mensagens`/`conversas` pra qualquer instância desde que o
// contato responda, ver ai-service/app/api/webhook.py). Não filtra por
// profissional_id da instância; quem restringe é só o `instancia_id` da query.
// Query: aba=todas|nao_atribuidas|resolvidas|arquivadas, instancia_id=<uuid>,
//        busca=<texto>, limit=<n>
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const query = getQuery(event)

  const aba = String(query.aba || 'todas')
  const instanciaId = query.instancia_id ? String(query.instancia_id) : null
  const busca = query.busca ? String(query.busca).trim() : null
  const limit = Math.min(Math.max(parseInt(String(query.limit || '80'), 10) || 80, 1), 200)

  const filtros: string[] = [`usuario_id=eq.${user.id}`, `deleted_at=is.null`]

  if (aba === 'arquivadas') {
    filtros.push('arquivada=eq.true')
  } else {
    filtros.push('arquivada=eq.false')
    if (aba === 'resolvidas') {
      filtros.push('resolved_at=not.is.null')
    } else {
      // 'todas' e 'nao_atribuidas' só mostram o que ainda está em aberto
      filtros.push('resolved_at=is.null')
      if (aba === 'nao_atribuidas') {
        filtros.push('assigned_to_professional_id=is.null')
      }
    }
  }

  if (instanciaId) filtros.push(`instancia_id=eq.${instanciaId}`)
  if (busca) {
    const termo = busca.replace(/[,()]/g, ' ')
    filtros.push(`or=(nome_contato.ilike.*${termo}*,numero.ilike.*${termo}*)`)
  }

  const select = 'select=*,instancia:instancias(id,nome_instancia,phone,status,profissional_id),profissional:profissionais!conversas_assigned_to_professional_id_fkey(id,nome)'
  const order = 'order=ultimo_horario.desc.nullslast,created_at.desc'

  const conversas = await supabaseFetch(
    event,
    `/conversas?${filtros.join('&')}&${select}&${order}&limit=${limit}`
  )

  return conversas
})
