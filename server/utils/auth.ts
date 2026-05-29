import type { H3Event } from 'h3'
import { createError, getHeader } from 'h3'

// Valida o token JWT do Supabase enviado pelo cliente.
// Retorna o usuário ou lança 401.
export async function requireUser(event: H3Event) {
  const authHeader = getHeader(event, 'authorization')
  if (!authHeader) {
    throw createError({ statusCode: 401, statusMessage: 'Token de autenticação ausente' })
  }

  const config = useRuntimeConfig()
  const supabaseUrl = config.public.supabaseUrl as string
  const anonKey = config.public.supabaseAnonKey as string

  if (!supabaseUrl || !anonKey) {
    throw createError({ statusCode: 500, statusMessage: 'Supabase não configurado' })
  }

  const response = await fetch(`${supabaseUrl}/auth/v1/user`, {
    headers: {
      'apikey': anonKey,
      'Authorization': authHeader
    }
  })

  if (!response.ok) {
    throw createError({ statusCode: 401, statusMessage: 'Sessão inválida' })
  }

  return await response.json()
}
