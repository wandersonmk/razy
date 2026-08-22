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

// Chama uma função RPC do Supabase com a anon key, SEM JWT de usuário — usado
// pelas rotas PÚBLICAS do link compartilhável de conexão (o vendedor/atendente
// abre o link sem estar logado no painel). As funções chamadas por aqui são
// SECURITY DEFINER e validam o token de verdade dentro do SQL (ver migração
// instancias_share_token_rpc_seguro) — nunca usar isso pra tabela com RLS
// aberta pra `anon`, só pra essas RPCs específicas.
export async function supabasePublicRpc(fn: string, body: Record<string, unknown>) {
  const config = useRuntimeConfig()
  const supabaseUrl = config.public.supabaseUrl as string
  const anonKey = config.public.supabaseAnonKey as string

  const url = `${supabaseUrl.replace(/\/$/, '')}/rest/v1/rpc/${fn}`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'apikey': anonKey,
      'Authorization': `Bearer ${anonKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
  const data = await res.json().catch(() => null)

  if (!res.ok) {
    throw createError({
      statusCode: res.status,
      statusMessage: (data as any)?.message || `Supabase RPC error ${res.status}`
    })
  }

  return data
}
