// https://nuxt.com/docs/api/configuration/nuxt-config
import { fileURLToPath } from 'node:url'
import { dirname, resolve as resolvePath } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
export default defineNuxtConfig({
  ssr: false,
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  modules: ['@nuxtjs/tailwindcss'],
  tailwindcss: {
    cssPath: resolvePath(__dirname, 'assets/css/tailwind.css')
  },
  css: ['@fortawesome/fontawesome-svg-core/styles.css'],
  runtimeConfig: {
    // Privadas — só ficam no servidor (rotas /api/*)
    uazapiUrl: process.env.UAZAPI_URL || 'https://razy.uazapi.com',
    uazapiToken: process.env.UAZAPI_TOKEN || '',
    uazapiAdminToken: process.env.UAZAPI_ADMIN_TOKEN || '',
    uazapiDelayMs: parseInt(process.env.UAZAPI_DELAY_MS || '2000', 10),

    // Serviço de IA (ai-service) — disparo orquestrado no servidor
    aiServiceUrl: process.env.AI_SERVICE_URL || '',
    internalToken: process.env.INTERNAL_TOKEN || '',

    public: {
      supabaseUrl:
        process.env.NUXT_PUBLIC_SUPABASE_URL ||
        process.env.SUPABASE_URL ||
        process.env.VITE_SUPABASE_URL,
      supabaseAnonKey:
        process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY ||
        process.env.SUPABASE_ANON_KEY ||
        process.env.VITE_SUPABASE_ANON_KEY
    }
  }
})
