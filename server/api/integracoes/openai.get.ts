// GET /api/integracoes/openai
// Retorna se a chave OpenAI está configurada e uma versão mascarada para exibição.
// A chave completa NUNCA é enviada ao browser.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)

  const rows = await supabaseFetch(
    event,
    `/integracoes?usuario_id=eq.${user.id}&select=openai_api_key&limit=1`
  )

  const chave: string | null = rows?.[0]?.openai_api_key ?? null

  let chave_mascarada: string | null = null
  if (chave && chave.length > 8) {
    const inicio = chave.slice(0, 12)
    const fim = chave.slice(-4)
    chave_mascarada = `${inicio}...${fim}`
  }

  return {
    configurada: !!chave,
    chave_mascarada
  }
})
