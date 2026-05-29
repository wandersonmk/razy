// Helper para chamar Supabase REST API usando o JWT do usuário (preserva RLS).
import { getHeader, type H3Event, createError } from 'h3'

export async function supabaseFetch(event: H3Event, path: string, init: RequestInit = {}) {
  const config = useRuntimeConfig()
  const supabaseUrl = config.public.supabaseUrl as string
  const anonKey = config.public.supabaseAnonKey as string
  const userJwt = getHeader(event, 'authorization')

  if (!userJwt) {
    throw createError({ statusCode: 401, statusMessage: 'Não autenticado' })
  }

  const url = `${supabaseUrl.replace(/\/$/, '')}/rest/v1${path}`
  const headers: Record<string, string> = {
    'apikey': anonKey,
    'Authorization': userJwt,
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
    ...(init.headers as Record<string, string> || {})
  }

  const res = await fetch(url, { ...init, headers })
  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw createError({
      statusCode: res.status,
      statusMessage: (data as any)?.message || `Supabase error ${res.status}`
    })
  }

  return data
}
