import { randomBytes } from 'node:crypto'
import { getRequestURL } from 'h3'

// POST /api/instancias/:id/link
// Gera (ou reaproveita, se já existir) o token do link compartilhável de
// conexão — a página pública /conectar/:token deixa o vendedor/atendente
// escanear o próprio QR Code sem precisar logar no painel.
// supabaseFetch preserva RLS: só o dono da instância consegue gerar o link.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=id,share_token`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })

  let token = inst.share_token as string | null
  if (!token) {
    token = randomBytes(24).toString('base64url')
    await supabaseFetch(event, `/instancias?id=eq.${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ share_token: token })
    })
  }

  const origin = getRequestURL(event).origin
  return { token, url: `${origin}/conectar/${token}` }
})
