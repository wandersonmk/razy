// POST /api/profissionais
// Cadastra um profissional (sem login — é só o dono do número, pra dar nome ao
// canal e servir de base pra IA independente e pro histórico de atendimento).
// Body: { nome: string, telefone?: string }
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const body = await readBody<{ nome?: string; telefone?: string }>(event)

  const nome = body?.nome?.trim()
  if (!nome) {
    throw createError({ statusCode: 400, statusMessage: 'nome é obrigatório' })
  }

  const [profissional] = await supabaseFetch(event, '/profissionais', {
    method: 'POST',
    body: JSON.stringify({
      usuario_id: user.id,
      nome,
      telefone: body?.telefone?.trim() || null,
      ativo: true
    })
  })

  return profissional
})
