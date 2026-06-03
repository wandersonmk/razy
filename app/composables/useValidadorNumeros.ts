// Validador de números de WhatsApp a partir de uma planilha.
// Faz o parse no navegador (xlsx), valida em lotes via /api/numeros/validar e
// separa as linhas em válidas (têm WhatsApp) e inválidas (não têm), preservando
// TODAS as colunas/observações originais — só a linha inteira é mantida/removida.
import { ref, computed } from 'vue'

export interface LinhaResultado {
  indice: number            // posição original na planilha (1-based, sem cabeçalho)
  linha: (string | number)[] // a linha original completa (AoA)
  numeroOriginal: string
  numeroNormalizado: string
  temWhatsapp: boolean
  verifiedName?: string
  motivo?: string           // por que foi considerada inválida
}

// A verificação no WhatsApp é lenta (~0,4s por número no pior caso). Mantemos o
// lote pequeno para cada requisição terminar bem dentro do timeout de função da
// Vercel (~10s); a página percorre os lotes em sequência com barra de progresso.
const TAMANHO_LOTE = 12

// Mesmas regras do backend (server/api/whatsapp/send.post.ts / orquestrador).
function normalizarNumero(raw: string | number | null | undefined): string {
  const nums = String(raw ?? '').replace(/\D/g, '')
  if (nums.startsWith('55') && nums.length >= 12) return nums
  if (nums.length === 10 || nums.length === 11) return '55' + nums
  return nums
}

function numeroPlausivel(normalizado: string): boolean {
  // 55 + DDD(2) + 8/9 dígitos → 12 ou 13 dígitos.
  return /^55\d{10,11}$/.test(normalizado)
}

function detectarColunaTelefone(headers: string[]): number {
  const re = /(telefone|celular|whats|whatsapp|fone|n[uú]mero|numero|contato|phone|tel\b|cel\b)/i
  const idx = headers.findIndex((h) => re.test(String(h || '')))
  return idx >= 0 ? idx : (headers.length ? 0 : -1)
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}
}

export function useValidadorNumeros() {
  const etapa = ref<'upload' | 'preview' | 'validando' | 'resultado'>('upload')
  const nomeArquivo = ref('')
  const headers = ref<string[]>([])
  const linhas = ref<(string | number)[][]>([])      // linhas de dados (sem cabeçalho)
  const colunaTelefone = ref<number>(-1)
  const progresso = ref({ feitos: 0, total: 0 })
  const validos = ref<LinhaResultado[]>([])
  const invalidos = ref<LinhaResultado[]>([])
  const canalUsado = ref('')
  const erro = ref<string | null>(null)
  const aviso = ref<string | null>(null)
  const isProcessing = ref(false)

  const colunasDisponiveis = computed(() =>
    headers.value.map((h, i) => ({ label: h || `Coluna ${i + 1}`, value: i }))
  )

  async function parseArquivo(file: File) {
    erro.value = null
    try {
      const XLSX = await import('xlsx')
      const buf = await file.arrayBuffer()
      const wb = XLSX.read(buf, { type: 'array', cellDates: true })
      const ws = wb.Sheets[wb.SheetNames[0]]
      if (!ws) throw new Error('Planilha vazia ou ilegível')

      // raw:true → telefones vêm como número de verdade, e não como o texto
      // formatado "1.15E+12" (notação científica do Excel, que perde dígitos).
      // Depois convertemos com String() para recuperar os dígitos completos.
      const aoa = XLSX.utils.sheet_to_json<(string | number)[]>(ws, {
        header: 1, defval: '', raw: true, blankrows: false
      })
      if (!aoa.length) throw new Error('A planilha não tem dados')

      headers.value = (aoa[0] as any[]).map((c) => String(c ?? ''))
      linhas.value = aoa.slice(1) as (string | number)[][]
      if (!linhas.value.length) throw new Error('A planilha só tem cabeçalho, sem linhas de dados')

      colunaTelefone.value = detectarColunaTelefone(headers.value)
      nomeArquivo.value = file.name.replace(/\.[^.]+$/, '')
      validos.value = []
      invalidos.value = []
      etapa.value = 'preview'
    } catch (e: any) {
      erro.value = e?.message || 'Não foi possível ler o arquivo'
      etapa.value = 'upload'
    }
  }

  function setColunaTelefone(idx: number) {
    colunaTelefone.value = idx
  }

  async function validar() {
    if (colunaTelefone.value < 0) {
      erro.value = 'Selecione a coluna que contém o número de telefone'
      return
    }
    erro.value = null
    aviso.value = null
    isProcessing.value = true
    etapa.value = 'validando'
    validos.value = []
    invalidos.value = []

    try {
      const col = colunaTelefone.value
      // Pré-processa cada linha: número original + normalizado + plausibilidade.
      const preparadas = linhas.value.map((linha, i) => {
        const original = String(linha[col] ?? '').trim()
        const normalizado = normalizarNumero(original)
        return { indice: i + 1, linha, original, normalizado, plausivel: numeroPlausivel(normalizado) }
      })

      // Números únicos e plausíveis para consultar a API (economiza chamadas).
      const unicos = Array.from(
        new Set(preparadas.filter((p) => p.plausivel).map((p) => p.normalizado))
      )
      progresso.value = { feitos: 0, total: unicos.length }

      // Mapa numeroNormalizado -> { tem, nome, naoVerificado }
      const veredito = new Map<string, { tem: boolean; nome?: string; naoVerificado?: boolean }>()
      const headersAuth = await authHeader()
      let naoVerificados = 0

      for (let i = 0; i < unicos.length; i += TAMANHO_LOTE) {
        const lote = unicos.slice(i, i + TAMANHO_LOTE)
        let resultados: any[] | null = null
        let ultimoErro: any = null

        // Uma tentativa + um retry por lote (a verificação pode oscilar).
        for (let tentativa = 0; tentativa < 2 && resultados === null; tentativa++) {
          try {
            const resp = await $fetch<{ canal: string; resultados: any[] }>('/api/numeros/validar', {
              method: 'POST', headers: headersAuth, body: { numbers: lote }, retry: 0,
            })
            canalUsado.value = resp.canal || canalUsado.value
            resultados = resp.resultados || []
          } catch (e: any) {
            ultimoErro = e
          }
        }

        if (resultados === null) {
          // Falha no PRIMEIRO lote → quase sempre é configuração (sem canal conectado,
          // sessão, etc.): aborta com a mensagem clara. Lotes seguintes: tolera e segue.
          if (i === 0) throw ultimoErro
          for (const n of lote) veredito.set(n, { tem: false, naoVerificado: true })
          naoVerificados += lote.length
        } else {
          for (const r of resultados) {
            const q = normalizarNumero(r.query)
            veredito.set(q, { tem: !!r.isInWhatsapp, nome: r.verifiedName || undefined })
          }
          for (const n of lote) if (!veredito.has(n)) veredito.set(n, { tem: false })
        }
        progresso.value = { feitos: Math.min(i + lote.length, unicos.length), total: unicos.length }
      }

      if (naoVerificados > 0) {
        aviso.value = `${naoVerificados} número(s) não puderam ser verificados por instabilidade e estão entre os inválidos com o motivo "Não verificado". Rode novamente para reconferir.`
      }

      // Classifica TODAS as linhas.
      const vOk: LinhaResultado[] = []
      const vNo: LinhaResultado[] = []
      for (const p of preparadas) {
        const base = {
          indice: p.indice, linha: p.linha, numeroOriginal: p.original, numeroNormalizado: p.normalizado,
        }
        if (!p.original) {
          vNo.push({ ...base, temWhatsapp: false, motivo: 'Sem número' })
        } else if (!p.plausivel) {
          vNo.push({ ...base, temWhatsapp: false, motivo: 'Número inválido' })
        } else {
          const res = veredito.get(p.normalizado)
          if (res?.naoVerificado) {
            vNo.push({ ...base, temWhatsapp: false, motivo: 'Não verificado' })
          } else if (res?.tem) {
            vOk.push({ ...base, temWhatsapp: true, verifiedName: res.nome })
          } else {
            vNo.push({ ...base, temWhatsapp: false, motivo: 'Sem WhatsApp' })
          }
        }
      }
      validos.value = vOk
      invalidos.value = vNo
      etapa.value = 'resultado'
    } catch (e: any) {
      erro.value = e?.data?.statusMessage || e?.data?.message || e?.statusMessage || e?.message || 'Erro ao validar os números'
      etapa.value = 'preview'
    } finally {
      isProcessing.value = false
    }
  }

  async function baixar(tipo: 'validos' | 'invalidos') {
    const lista = tipo === 'validos' ? validos.value : invalidos.value
    if (!lista.length) return
    const XLSX = await import('xlsx')
    const col = colunaTelefone.value
    // Reescreve só a célula do telefone como texto limpo (evita a notação
    // científica do Excel no arquivo); as demais colunas seguem idênticas.
    const linhasSaida = lista.map((r) => {
      const linha = r.linha.slice()
      if (col >= 0) linha[col] = r.numeroOriginal
      return linha
    })
    const aoa = [headers.value, ...linhasSaida]
    const ws = XLSX.utils.aoa_to_sheet(aoa)
    const wb = XLSX.utils.book_new()
    const aba = tipo === 'validos' ? 'Validos' : 'Sem WhatsApp'
    XLSX.utils.book_append_sheet(wb, ws, aba)
    XLSX.writeFile(wb, `${nomeArquivo.value || 'contatos'}-${tipo}.xlsx`)
  }

  function reset() {
    etapa.value = 'upload'
    nomeArquivo.value = ''
    headers.value = []
    linhas.value = []
    colunaTelefone.value = -1
    progresso.value = { feitos: 0, total: 0 }
    validos.value = []
    invalidos.value = []
    canalUsado.value = ''
    erro.value = null
    aviso.value = null
  }

  return {
    etapa, nomeArquivo, headers, linhas, colunaTelefone, colunasDisponiveis,
    progresso, validos, invalidos, canalUsado, erro, aviso, isProcessing,
    parseArquivo, setColunaTelefone, validar, baixar, reset,
  }
}
