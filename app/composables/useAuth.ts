import { ref, computed, readonly } from 'vue'
import type { User, Session } from '@supabase/supabase-js'
import { useSupabaseClient } from './useSupabaseClient'

export function useAuth() {
  const user = useState<User | null>('auth_user', () => null)
  const session = useState<Session | null>('auth_session', () => null)
  const isLoading = useState<boolean>('auth_loading', () => process.server ? false : true)
  const errorMessage = ref<string | null>(null)

  const isAuthenticated = computed(() => !!user.value && !!session.value)

  const getSupabase = () => {
    if (process.server) return null
    return useSupabaseClient()
  }

  const translateError = (msg: string): string => {
    const m = msg.toLowerCase()
    if (m.includes('invalid login credentials')) return 'Email ou senha incorretos.'
    if (m.includes('email not confirmed')) return 'Confirme seu email antes de entrar.'
    if (m.includes('user already registered')) return 'Este email já está cadastrado.'
    if (m.includes('password should be at least')) return 'A senha deve ter pelo menos 6 caracteres.'
    if (m.includes('rate limit')) return 'Muitas tentativas. Aguarde alguns instantes.'
    return msg
  }

  const signInWithEmailAndPassword = async (email: string, password: string) => {
    const supabase = getSupabase()
    if (!supabase) return false

    isLoading.value = true
    errorMessage.value = null
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      user.value = data.user
      session.value = data.session
      return data.user
    } catch (err: any) {
      errorMessage.value = translateError(String(err?.message || err))
      return false
    } finally {
      isLoading.value = false
    }
  }

  const signUp = async ({ name, companyName, email, password }: { name: string, companyName: string, email: string, password: string }) => {
    const supabase = getSupabase()
    if (!supabase) return false

    isLoading.value = true
    errorMessage.value = null
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { nome: name, empresa: companyName }
        }
      })
      if (error) throw error
      if (!data.user) {
        errorMessage.value = 'Erro ao criar usuário'
        return false
      }

      const { error: insertError } = await supabase.from('usuarios').insert({
        id: data.user.id,
        nome: name,
        empresa: companyName,
        email,
        perfil: 'admin'
      })
      if (insertError) {
        console.error('[useAuth] Erro ao inserir em usuarios:', insertError)
      }

      if (data.session) {
        user.value = data.user
        session.value = data.session
      }

      return data.user
    } catch (err: any) {
      errorMessage.value = translateError(String(err?.message || err))
      return false
    } finally {
      isLoading.value = false
    }
  }

  const signOut = async () => {
    const supabase = getSupabase()
    if (!supabase) return
    try {
      await supabase.auth.signOut()
    } catch (err) {
      console.error('[useAuth] Erro ao sair:', err)
    } finally {
      user.value = null
      session.value = null
    }
  }

  const reloadSession = async () => {
    const supabase = getSupabase()
    if (!supabase) return
    const { data } = await supabase.auth.getSession()
    user.value = data.session?.user ?? null
    session.value = data.session ?? null
  }

  const clearError = () => { errorMessage.value = null }

  return {
    user: readonly(user),
    session: readonly(session),
    isAuthenticated: readonly(isAuthenticated),
    isLoading: readonly(isLoading),
    errorMessage: readonly(errorMessage),
    signInWithEmailAndPassword,
    signUp,
    signOut,
    reloadSession,
    clearError
  }
}
