// GET /api/assistentes
// Lista os assistentes do usuário, cada um com os dados da instância vinculada
// (nome/phone/status) via embed do PostgREST. Assistentes órfãos vêm com
// instancia = null.
export default defineEventHandler(async (event) => {
  await requireUser(event)

  const assistentes = await supabaseFetch(
    event,
    `/assistentes?select=*,instancia:instancias(id,nome_instancia,phone,status)&order=instancia_id.asc.nullslast,created_at.asc`
  )

  return assistentes
})
