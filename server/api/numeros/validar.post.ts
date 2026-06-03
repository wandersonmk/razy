// POST /api/numeros/validar
// Valida uma lista de números no WhatsApp via UAzAPI /chat/check, usando um canal
// conectado do usuário. O token da instância nunca vai ao navegador.
// Body: { numbers: string[], canal_id?: string }
// Retorno: { canal, resultados: [{ query, isInWhatsapp, jid, verifiedName, error }] }
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()
  const body = await readBody<{ numbers?: string[]; canal_id?: string }>(event)

  const numbers = Array.isArray(body?.numbers)
    ? body!.numbers.filter((n) => typeof n === 'string' && n.trim()).slice(0, 200)
    : []
  if (!numbers.length) {
    throw createError({ statusCode: 400, statusMessage: 'Informe ao menos um número para validar' })
  }

  // Resolve o token de um canal CONECTADO (o informado, ou o primeiro conectado do usuário).
  // RLS já restringe as instâncias ao próprio usuário; filtramos por usuario_id por garantia.
  let token = ''
  let canalLabel = ''
  if (body?.canal_id) {
    const canais = await supabaseFetch(
      event,
      `/instancias?id=eq.${body.canal_id}&usuario_id=eq.${user.id}&select=uazapi_token,phone,status,uazapi_instance_name`
    )
    const canal = canais[0]
    if (!canal) throw createError({ statusCode: 404, statusMessage: 'Canal não encontrado' })
    if (canal.status !== 'connected') {
      throw createError({ statusCode: 400, statusMessage: 'O canal escolhido não está conectado' })
    }
    token = canal.uazapi_token
    canalLabel = canal.phone || canal.uazapi_instance_name || ''
  } else {
    const conectados = await supabaseFetch(
      event,
      `/instancias?usuario_id=eq.${user.id}&status=eq.connected&select=uazapi_token,phone,uazapi_instance_name&order=created_at.asc&limit=1`
    )
    const canal = conectados[0]
    if (!canal || !canal.uazapi_token) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Nenhum canal conectado disponível. Conecte um WhatsApp antes de validar os números.'
      })
    }
    token = canal.uazapi_token
    canalLabel = canal.phone || canal.uazapi_instance_name || ''
  }

  const url = `${String(config.uazapiUrl).replace(/\/$/, '')}/chat/check`
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', token },
      body: JSON.stringify({ numbers })
    })
  } catch (e: any) {
    throw createError({ statusCode: 502, statusMessage: `Falha ao falar com a UAzAPI: ${e?.message || e}` })
  }

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const msg = (data as any)?.error || (data as any)?.message || `Erro na verificação (HTTP ${response.status})`
    // 401/500 da UAzAPI (sessão/conexão) viram 400 para o front exibir orientação clara.
    throw createError({ statusCode: response.status >= 500 || response.status === 401 ? 400 : response.status, statusMessage: msg })
  }

  return { canal: canalLabel, resultados: Array.isArray(data) ? data : [] }
})
