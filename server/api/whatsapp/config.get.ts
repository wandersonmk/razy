
// Retorna apenas se a UAzAPI está configurada (NUNCA o token).
export default defineEventHandler(async (event) => {
  await requireUser(event)

  const config = useRuntimeConfig()
  return {
    configurado: !!config.uazapiToken,
    url: config.uazapiUrl as string,
    delay_ms: config.uazapiDelayMs as number
  }
})
