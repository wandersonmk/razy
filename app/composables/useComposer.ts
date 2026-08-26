// Composer da página de Conversas: dono/atendente manda mensagem (texto, áudio,
// imagem, documento) por qualquer conversa, mesmo com a IA ligada. Este arquivo
// só cuida de REDE (upload + envio) — o estado de interação (gravando, prévia de
// imagem pendente, câmera aberta) fica no componente, que é quem desenha isso.
//
// Upload de mídia vai DIRETO pro Supabase Storage via signed upload URL — nunca
// pela function do Vercel. Documento chega a 50MB e função serverless tem teto
// de payload; rotear os bytes por ali quebraria justo no arquivo grande.
import type { Mensagem } from '~/composables/useConversas'

export const LIMITES_MIDIA = {
  audio: 16 * 1024 * 1024,
  video: 16 * 1024 * 1024,
  image: 5 * 1024 * 1024,
  document: 50 * 1024 * 1024
} as const

const PASTA_POR_KIND: Record<string, string> = {
  audio: 'audio', image: 'imagem', video: 'video', document: 'pdf'
}

async function usuarioIdAtual(): Promise<string> {
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getUser()
  const id = data?.user?.id
  if (!id) throw new Error('Sessão expirada — recarregue a página')
  return id
}

async function authHeader(): Promise<Record<string, string>> {
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}
}

/**
 * Sobe um arquivo pro bucket `conversas-midia` via signed upload URL (RLS
 * restringe a escrita à pasta `{usuario_id}/...` do próprio dono — ver policy
 * `conversas_midia_insert_own`) e devolve o `storage_path` gravado.
 */
export async function uploadMidiaComposer(
  arquivo: Blob | File,
  kind: 'audio' | 'image' | 'video' | 'document',
  extensao: string
): Promise<string> {
  const supabase = useSupabaseClient()
  const usuarioId = await usuarioIdAtual()
  const pasta = PASTA_POR_KIND[kind] || 'pdf'
  const ext = (extensao || 'bin').replace(/^\./, '') || 'bin'
  const path = `${usuarioId}/${pasta}/${crypto.randomUUID()}.${ext}`

  const { data: assinado, error: erroAssinar } = await supabase.storage
    .from('conversas-midia')
    .createSignedUploadUrl(path)
  if (erroAssinar || !assinado) throw new Error('Não consegui preparar o envio do arquivo')

  const { error: erroUpload } = await supabase.storage
    .from('conversas-midia')
    .uploadToSignedUrl(path, assinado.token, arquivo)
  if (erroUpload) throw new Error('Falha ao enviar o arquivo — tente de novo')

  return path
}

interface EnvioBody {
  kind: 'text' | 'audio' | 'image' | 'document' | 'video'
  texto?: string
  storage_path?: string
  nome_arquivo?: string
}

async function postarMensagem(conversaId: string, body: EnvioBody): Promise<Mensagem> {
  const headers = await authHeader()
  const res = await fetch(`/api/conversas/${conversaId}/mensagens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body)
  })
  const data = await res.json().catch(() => ({} as any))
  if (!res.ok) {
    throw new Error(data?.statusMessage || data?.message || 'Não consegui enviar a mensagem')
  }
  return data as Mensagem
}

export function useComposer(conversaId: () => string) {
  async function enviarTexto(texto: string): Promise<Mensagem> {
    return postarMensagem(conversaId(), { kind: 'text', texto })
  }

  async function enviarAudio(blob: Blob, extensao: string): Promise<Mensagem> {
    if (blob.size > LIMITES_MIDIA.audio) throw new Error('Áudio muito grande (máx. 16 MB)')
    const path = await uploadMidiaComposer(blob, 'audio', extensao)
    return postarMensagem(conversaId(), { kind: 'audio', storage_path: path })
  }

  async function enviarImagemOuVideo(file: File, legenda?: string): Promise<Mensagem> {
    const kind = file.type.startsWith('video/') ? 'video' : 'image'
    const limite = kind === 'video' ? LIMITES_MIDIA.video : LIMITES_MIDIA.image
    if (file.size > limite) {
      throw new Error(kind === 'video' ? 'Vídeo muito grande (máx. 16 MB)' : 'Imagem muito grande (máx. 5 MB)')
    }
    const ext = (file.name.split('.').pop() || (kind === 'video' ? 'mp4' : 'jpg'))
    const path = await uploadMidiaComposer(file, kind, ext)
    return postarMensagem(conversaId(), { kind, storage_path: path, texto: legenda })
  }

  async function enviarDocumento(file: File): Promise<Mensagem> {
    if (file.size > LIMITES_MIDIA.document) throw new Error('Arquivo muito grande (máx. 50 MB)')
    const ext = file.name.split('.').pop() || 'bin'
    const path = await uploadMidiaComposer(file, 'document', ext)
    return postarMensagem(conversaId(), { kind: 'document', storage_path: path, nome_arquivo: file.name })
  }

  return { enviarTexto, enviarAudio, enviarImagemOuVideo, enviarDocumento }
}
