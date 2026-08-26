// Traduz a falha do ai-service para algo que o dono da empresa consiga agir.
// O FastAPI devolve `{"detail": "Not Found"}` quando o serviço está no ar mas
// SEM a rota — ou seja, rodando um build anterior ao Analista. Repassar esse
// texto cru para a tela deixa a pessoa sem saber o que fazer.
function mensagemDeErro(status: number, detail?: string): string {
  if (status === 404) {
    return 'O Analista ainda não está publicado no servidor de IA. Faça o deploy do ai-service para ativá-lo.'
  }
  if (status === 401 || status === 403) {
    return 'O painel não conseguiu se autenticar no serviço de IA. Confira o INTERNAL_TOKEN nos dois lados.'
  }
  if (status >= 500 && !detail) {
    return 'O serviço de IA falhou ao responder. Tente de novo em instantes.'
  }
  // 400/503 vêm com mensagem escrita por nós (sem chave OpenAI, sem saldo etc.).
  return detail || 'O analista não conseguiu responder.'
}

// POST /api/analista/perguntar — Analista de Atendimento.
// Body: { pergunta: string, historico?: { papel, texto }[] }
//
// O `usuario_id` NUNCA vem do navegador: sai de requireUser(event), que valida o
// JWT do Supabase. É esse ponto que garante que uma empresa não leia os
// atendimentos de outra — o ai-service conecta como `postgres` e bypassa RLS,
// então o isolamento depende de quem chama, não do banco.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()

  if (!config.aiServiceUrl || !config.internalToken) {
    throw createError({
      statusCode: 503,
      statusMessage: 'Analista indisponível: defina AI_SERVICE_URL e INTERNAL_TOKEN no ambiente.'
    })
  }

  const body = await readBody<{ pergunta?: string; historico?: unknown; contexto?: unknown }>(event)
  const pergunta = (body?.pergunta || '').trim()
  if (!pergunta) {
    throw createError({ statusCode: 400, statusMessage: 'Escreva a sua pergunta.' })
  }

  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')

  // A resposta passa por várias consultas + LLM; 90s cobre o pior caso sem
  // deixar a requisição pendurada para sempre se o serviço travar.
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 90_000)

  try {
    const res = await fetch(`${baseUrl}/analista/perguntar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Token': config.internalToken as string
      },
      body: JSON.stringify({
        usuario_id: user.id,
        pergunta,
        historico: Array.isArray(body?.historico) ? body.historico.slice(-8) : [],
        // Só os ids das conversas já identificadas. Não confere nada aqui: o
        // ai-service refaz toda consulta com o usuario_id do JWT, então um id
        // adulterado no navegador não alcança dados de outra empresa.
        contexto: Array.isArray(body?.contexto) ? body.contexto.slice(-6) : []
      }),
      signal: controller.signal
    })

    const data = await res.json().catch(() => ({} as any))
    if (!res.ok) {
      throw createError({
        statusCode: res.status,
        statusMessage: mensagemDeErro(res.status, (data as any)?.detail)
      })
    }
    return data
  } catch (e: any) {
    if (e?.statusCode) throw e
    if (e?.name === 'AbortError') {
      throw createError({
        statusCode: 504,
        statusMessage: 'A análise demorou demais. Tente uma pergunta mais específica.'
      })
    }
    throw createError({ statusCode: 503, statusMessage: 'Analista indisponível no momento.' })
  } finally {
    clearTimeout(timer)
  }
})
