// GET /api/publico/conectar/:token/status — SEM autenticação.
// Status atual (o que já está gravado no banco) da instância dona deste
// link — usado ao abrir a página, antes de decidir se já mostra "conectado"
// ou parte pro fluxo de QR Code.
export default defineEventHandler(async (event) => {
  const token = getRouterParam(event, 'token')
  if (!token) throw createError({ statusCode: 400, statusMessage: 'token obrigatório' })

  const rows = await supabasePublicRpc('instancia_status_publica', { p_token: token })
  const row = Array.isArray(rows) ? rows[0] : rows
  if (!row) throw createError({ statusCode: 404, statusMessage: 'Link inválido ou revogado' })

  return { nome_instancia: row.nome_instancia, status: row.status, phone: row.phone }
})
