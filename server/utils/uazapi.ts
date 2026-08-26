// Cliente da UAzAPI para o composer (mensagem mandada pelo dono, pela tela).
//
// Contrato de /send/media extraído do openapi-bundled.json publicado pela
// própria UAzAPI (a doc em docs.uazapi.com é uma SPA e não dá pra ler direto —
// o spec real está em https://docs.uazapi.com/openapi-bundled.json). Campos:
// { number, type, file, text?, docName? }, type ∈ image|video|document|ptt|...
// 'ptt' é a nota de voz nativa (bolha com onda, toca inline) — é o que o
// composer grava, não um arquivo de áudio anexado ('audio'/'myaudio').
//
// O envio de TEXTO já existia (server/api/whatsapp/send.post.ts, usado pelo
// disparo em massa) — mas aquele endpoint resolve o token via a tabela
// `canais`, que não existe mais neste banco (legado — ver `instancias`, que é
// a tabela real hoje). Por isso este arquivo tem seu próprio envio de texto,
// já resolvendo o token pela tabela certa.

export function formatarTelefoneUazapi(telefone: string): string {
  const numeros = String(telefone || '').replace(/\D/g, '')
  if (numeros.startsWith('55') && numeros.length >= 12) return numeros
  if (numeros.length === 10 || numeros.length === 11) return `55${numeros}`
  return numeros
}

interface RespostaUazapi {
  sucesso: boolean
  messageid: string | null
  erro: string | null
}

async function chamarUazapi(path: string, token: string, body: Record<string, unknown>): Promise<RespostaUazapi> {
  const config = useRuntimeConfig()
  const url = `${String(config.uazapiUrl).replace(/\/$/, '')}${path}`

  let resp: Response
  try {
    resp = await fetch(url, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', token },
      body: JSON.stringify(body)
    })
  } catch {
    return { sucesso: false, messageid: null, erro: 'Falha de rede ao chamar a UAzAPI.' }
  }

  const data = await resp.json().catch(() => ({} as any))
  const bloco = (data as any)?.response
  // A UAzAPI às vezes devolve 200 com um erro dentro de `response.status`.
  const sucesso = resp.ok && bloco?.status !== 'error'
  const erro = sucesso ? null : (bloco?.error || (data as any)?.error || (data as any)?.message || `HTTP ${resp.status}`)
  const messageid = (data as any)?.messageid || (data as any)?.id || null

  return { sucesso, messageid, erro }
}

export async function enviarTextoUazapi(opts: { token: string; numero: string; texto: string }): Promise<RespostaUazapi> {
  return chamarUazapi('/send/text', opts.token, { number: opts.numero, text: opts.texto })
}

/** tipo: o mesmo `kind` de `mensagens` ('audio'|'image'|'document'|'video'). */
export async function enviarMidiaUazapi(opts: {
  token: string
  numero: string
  tipo: 'audio' | 'image' | 'document' | 'video'
  arquivoUrl: string
  legenda?: string
  nomeDocumento?: string
}): Promise<RespostaUazapi> {
  const MAPA_TIPO: Record<string, string> = { audio: 'ptt', image: 'image', document: 'document', video: 'video' }
  const body: Record<string, unknown> = {
    number: opts.numero,
    type: MAPA_TIPO[opts.tipo] || opts.tipo,
    file: opts.arquivoUrl
  }
  if (opts.legenda) body.text = opts.legenda
  if (opts.tipo === 'document' && opts.nomeDocumento) body.docName = opts.nomeDocumento
  return chamarUazapi('/send/media', opts.token, body)
}
