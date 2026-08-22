// GET /api/profissionais
// Lista os profissionais do usuário, cada um com a instância vinculada (se houver)
// e o estado da IA própria (se já foi configurada).
export default defineEventHandler(async (event) => {
  await requireUser(event)

  const profissionais = await supabaseFetch(
    event,
    `/profissionais?select=*,instancia:instancias(id,nome_instancia,phone,status),assistente_ia:assistentes_profissionais(id,ativo)&order=created_at.desc`
  )

  return profissionais
})
