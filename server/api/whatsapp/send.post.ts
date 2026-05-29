
function formatarTelefone(telefone: string): string {
  const numeros = String(telefone || '').replace(/\D/g, '')
  if (numeros.startsWith('55') && numeros.length >= 12) return numeros
  if (numeros.length === 10 || numeros.length === 11) return `55${numeros}`
  return numeros
}

// POST body: { number, text, canal_id? }
// Se canal_id for fornecido, usa o token desse canal. Caso contrário, usa UAZAPI_TOKEN do .env.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const config = useRuntimeConfig()
  const body = await readBody<{ number: string; text: string; canal_id?: string }>(event)

  if (!body?.number || !body?.text) {
    throw createError({ statusCode: 400, statusMessage: 'number e text são obrigatórios' })
  }

  // Resolve qual token usar
  let token = config.uazapiToken as string
  if (body.canal_id) {
    const canais = await supabaseFetch(event, `/canais?id=eq.${body.canal_id}&select=instancia_token,status`)
    const canal = canais[0]
    if (!canal) throw createError({ statusCode: 404, statusMessage: 'Canal não encontrado' })
    if (canal.status !== 'conectado') {
      throw createError({ statusCode: 400, statusMessage: 'Canal não está conectado' })
    }
    if (!canal.instancia_token) {
      throw createError({ statusCode: 400, statusMessage: 'Canal sem token de instância' })
    }
    token = canal.instancia_token
  }

  if (!token) {
    throw createError({
      statusCode: 503,
      statusMessage: 'Nenhum token disponível: configure um canal ou UAZAPI_TOKEN no .env'
    })
  }

  const numero = formatarTelefone(body.number)
  if (!numero || numero.length < 10) {
    throw createError({ statusCode: 400, statusMessage: 'Número de telefone inválido' })
  }

  const url = `${String(config.uazapiUrl).replace(/\/$/, '')}/send/text`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'token': token
    },
    body: JSON.stringify({ number: numero, text: body.text })
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    return {
      sucesso: false,
      telefone: numero,
      erro: (data as any)?.message || (data as any)?.error || `HTTP ${response.status}`,
      status: response.status
    }
  }

  return { sucesso: true, telefone: numero, resposta: data }
})
