import type { H3Event } from 'h3'

// POST /api/conversas/:id/mensagens
//
// O dono da empresa assume qualquer conversa a qualquer momento — texto, áudio,
// imagem ou documento — mesmo com a IA ligada. Ao mandar algo por aqui, duas
// coisas acontecem: a mensagem é entregue de verdade (UAzAPI) e a IA pausa
// sozinha para aquele contato (mesma config que já rege a pausa quando o
// profissional responde pelo celular — ver ai-service /conversas/pausar-automatica).
//
// Body:
//   kind: 'text' | 'audio' | 'image' | 'document' | 'video'
//   texto?: string          — corpo (kind='text') OU legenda opcional (demais kinds)
//   storage_path?: string   — obrigatório quando kind !== 'text'; path já existente
//                             no bucket `conversas-midia` (upload feito direto do
//                             navegador via signed upload URL — ver useComposer.ts).
//                             Documento chega a 50MB; passar os BYTES por esta
//                             function estouraria o limite de payload do Vercel.
//   nome_arquivo?: string   — nome original (usado em 'document': docName + arquivo_nome)
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const body = await readBody<{
    kind?: string
    texto?: string
    storage_path?: string
    nome_arquivo?: string
  }>(event)

  const kind = body?.kind
  const KINDS_VALIDOS = ['text', 'audio', 'image', 'document', 'video']
  if (!kind || !KINDS_VALIDOS.includes(kind)) {
    throw createError({ statusCode: 400, statusMessage: `kind precisa ser um de: ${KINDS_VALIDOS.join(', ')}` })
  }

  const texto = (body?.texto || '').trim()
  if (kind === 'text' && !texto) {
    throw createError({ statusCode: 400, statusMessage: 'texto é obrigatório para kind=text' })
  }
  if (kind !== 'text' && !body?.storage_path) {
    throw createError({ statusCode: 400, statusMessage: 'storage_path é obrigatório para mídia' })
  }

  // ── Conversa + canal ──
  const conversas = await supabaseFetch(
    event,
    `/conversas?id=eq.${id}&usuario_id=eq.${user.id}&select=` +
      'id,numero,nome_contato,chatlid,instancia_id,assigned_to_professional_id,' +
      'instancia:instancias(id,uazapi_token,status,profissional_id)'
  ) as any[]
  const conversa = conversas[0]
  if (!conversa) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })

  const instancia = conversa.instancia
  if (!instancia) throw createError({ statusCode: 400, statusMessage: 'Conversa sem canal vinculado' })
  if (instancia.status !== 'connected') {
    throw createError({ statusCode: 400, statusMessage: 'Canal desconectado — reconecte antes de enviar' })
  }
  if (!instancia.uazapi_token) {
    throw createError({ statusCode: 400, statusMessage: 'Canal sem token da UAzAPI' })
  }

  // ── Mídia: URL assinada de LEITURA, curta o bastante só para a UAzAPI
  // buscar o arquivo (o upload em si já aconteceu antes, direto pro Storage). ──
  let arquivoUrl: string | null = null
  if (kind !== 'text') {
    arquivoUrl = await gerarUrlAssinadaLeitura(event, body!.storage_path!)
    if (!arquivoUrl) {
      throw createError({ statusCode: 500, statusMessage: 'Não consegui gerar a URL do arquivo para envio' })
    }
  }

  // ── Envio real ──
  const numeroUazapi = formatarTelefoneUazapi(conversa.numero)
  const resultado = kind === 'text'
    ? await enviarTextoUazapi({ token: instancia.uazapi_token, numero: numeroUazapi, texto })
    : await enviarMidiaUazapi({
        token: instancia.uazapi_token,
        numero: numeroUazapi,
        tipo: kind as 'audio' | 'image' | 'document' | 'video',
        arquivoUrl,
        legenda: texto || undefined,
        nomeDocumento: kind === 'document' ? (body?.nome_arquivo || undefined) : undefined
      })

  if (!resultado.sucesso) {
    throw createError({ statusCode: 502, statusMessage: resultado.erro || 'Falha ao enviar pela UAzAPI' })
  }

  // ── Auto-atribuição: canal de profissional sem conversa ainda atribuída vira
  // dele — é o canal DELE, e alguém acabou de atender por ali. Canal SDR
  // (sem profissional_id) não tem a quem atribuir; fica como está. ──
  let profissionalId: string | null = conversa.assigned_to_professional_id || null
  if (!profissionalId && instancia.profissional_id) {
    profissionalId = instancia.profissional_id
    try {
      await supabaseFetch(event, `/conversas?id=eq.${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ assigned_to_professional_id: profissionalId, assigned_at: new Date().toISOString(), assigned_by: user.id })
      })
      await supabaseFetch(event, '/conversa_atendentes_historico', {
        method: 'POST',
        headers: { Prefer: 'return=minimal' },
        body: JSON.stringify({
          usuario_id: user.id, conversa_id: id, profissional_id: profissionalId,
          acao: 'atribuido', created_by: user.id
        })
      })
    } catch (e) {
      // Mensagem já foi entregue de verdade — não vale falhar o envio por causa
      // de um efeito colateral cosmético.
      console.error('[conversas/mensagens] falha na auto-atribuição:', e)
    }
  }

  // ── Grava a mensagem ──
  const arquivoNome = kind === 'document' ? (body?.nome_arquivo || null) : null
  const [mensagemInserida] = await supabaseFetch(event, '/mensagens', {
    method: 'POST',
    body: JSON.stringify({
      usuario_id: user.id,
      instancia_id: conversa.instancia_id,
      conversa_id: id,
      numero: conversa.numero,
      nome_contato: conversa.nome_contato,
      chatlid: conversa.chatlid,
      mensagem: kind === 'text' ? texto : (texto || null),
      direcao: 'SENT',
      enviado_por: 'painel',
      enviado_por_profissional_id: profissionalId,
      kind,
      arquivo_nome: arquivoNome,
      wa_message_id: resultado.messageid,
      data_hora: new Date().toISOString()
    })
  }) as any[]

  // ── Mídia: mesmo registro que o ai-service grava para mensagem recebida
  // (ver repo.inserir_midia_conversa) — é o que MensagemBolha.vue lê para
  // gerar a signed URL de exibição a partir de `storage_path`. ──
  if (kind !== 'text') {
    const TIPO_MIDIA: Record<string, string> = { audio: 'audio', image: 'imagem', document: 'pdf', video: 'video' }
    try {
      await supabaseFetch(event, '/midias_conversas', {
        method: 'POST',
        headers: { Prefer: 'return=minimal' },
        body: JSON.stringify({
          mensagem_id: mensagemInserida.id,
          usuario_id: user.id,
          instancia_id: conversa.instancia_id,
          storage_path: body!.storage_path,
          tipo: TIPO_MIDIA[kind],
          url_original: null,
          url_storage: body!.storage_path
        })
      })
    } catch (e) {
      // A mensagem já existe e já foi entregue; sem isto só a MINIATURA na
      // tela é que falha (o cliente recebeu normalmente).
      console.error('[conversas/mensagens] falha ao registrar mídia:', e)
    }
  }

  // ── Pausa automática da IA. AGUARDADA (não fire-and-forget): em serverless,
  // uma promise disparada e esquecida congela quando a resposta HTTP já foi
  // mandada — a pausa chegaria com atraso, e nesse intervalo a IA responderia
  // por cima de quem acabou de mandar a mensagem. Falha aqui não desfaz o
  // envio, que já aconteceu de verdade; só fica sem pausar. ──
  const config = useRuntimeConfig()
  if (config.aiServiceUrl && config.internalToken) {
    try {
      await fetch(`${String(config.aiServiceUrl).replace(/\/$/, '')}/conversas/pausar-automatica`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Internal-Token': config.internalToken as string },
        body: JSON.stringify({ usuario_id: user.id, instancia_id: conversa.instancia_id, telefone: conversa.numero })
      })
    } catch (e) {
      console.error('[conversas/mensagens] falha ao pausar a IA:', e)
    }
  }

  return mensagemInserida
})

/** Signed URL de LEITURA para a UAzAPI buscar o arquivo recém-enviado ao Storage. */
async function gerarUrlAssinadaLeitura(event: H3Event, storagePath: string): Promise<string | null> {
  const config = useRuntimeConfig()
  const supabaseUrl = String(config.public.supabaseUrl).replace(/\/$/, '')
  const userJwt = getHeader(event, 'authorization')
  // Encoda por SEGMENTO (nunca a string toda) — '/' precisa continuar
  // separando pasta de arquivo, senão o path vira um nome de arquivo só.
  const caminhoCodificado = storagePath.split('/').map(encodeURIComponent).join('/')
  try {
    const res = await fetch(`${supabaseUrl}/storage/v1/object/sign/conversas-midia/${caminhoCodificado}`, {
      method: 'POST',
      headers: {
        apikey: config.public.supabaseAnonKey as string,
        Authorization: userJwt || '',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ expiresIn: 600 })
    })
    if (!res.ok) return null
    const data = await res.json().catch(() => null) as { signedURL?: string } | null
    if (!data?.signedURL) return null
    return `${supabaseUrl}/storage/v1${data.signedURL}`
  } catch {
    return null
  }
}
