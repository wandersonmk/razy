import type { Ref } from 'vue'

interface WaitForAuthReadyOptions {
  pollMs?: number
  maxWaitMs?: number
  minDelayMs?: number
}

export async function waitForAuthReady(
  authLoading: Ref<boolean>,
  options: WaitForAuthReadyOptions = {}
) {
  if (process.server) return

  const pollMs = options.pollMs ?? 50
  const maxWaitMs = options.maxWaitMs ?? 3000
  const minDelayMs = options.minDelayMs ?? 200
  const startedAt = Date.now()

  while (authLoading.value && Date.now() - startedAt < maxWaitMs) {
    await new Promise(resolve => setTimeout(resolve, pollMs))
  }

  if (minDelayMs > 0) {
    await new Promise(resolve => setTimeout(resolve, minDelayMs))
  }
}
