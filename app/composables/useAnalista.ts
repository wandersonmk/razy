import { ref } from 'vue'

export interface PassoRastro {
  fn: string
  args: string
  resultado: string
}

export interface Cobertura {
  total: number
  lidas: number
  sem_conteudo: number
}

export interface RespostaAnalista {
  resposta: string
  rastro: PassoRastro[]
  cobertura: Cobertura | null
  titulo: string
}

export interface TurnoAnalista {
  id: string
  papel: 'user' | 'assistant'
  texto: string
  rastro?: PassoRastro[]
  cobertura?: Cobertura | null
  titulo?: string
  erro?: boolean
}

export interface ResumoOperacao {
  ativas: number | null
  movimento_24h: number | null
  paradas_3d: number | null
  canais_on: number | null
  canais_total: number | null
  vendedores: number | null
  total_msgs: number | null
  msgs_sem_texto: number | null
  cobertura_pct: number | null
  resposta_media_min: number | null
  historico_desde: string | null
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

export function useAnalista() {
  const turnos = ref<TurnoAnalista[]>([])
  const resumo = ref<ResumoOperacao | null>(null)
  const pensando = ref(false)

  const carregarResumo = async () => {
    try {
      const headers = await authHeader()
      const res = await fetch('/api/analista/resumo', { headers })
      if (res.ok) resumo.value = await res.json()
    } catch {
      // Resumo é informação de apoio — o painel funciona sem ele.
    }
  }

  const perguntar = async (pergunta: string) => {
    const texto = pergunta.trim()
    if (!texto || pensando.value) return

    turnos.value.push({ id: `u${Date.now()}`, papel: 'user', texto })
    pensando.value = true

    // Só os turnos ANTERIORES viram contexto (o atual já vai em `pergunta`).
    const historico = turnos.value
      .slice(0, -1)
      .slice(-8)
      .map((t) => ({ papel: t.papel, texto: t.texto }))

    try {
      const headers = await authHeader()
      const res = await fetch('/api/analista/perguntar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify({ pergunta: texto, historico })
      })
      const data = await res.json().catch(() => ({} as any))

      if (!res.ok) {
        turnos.value.push({
          id: `a${Date.now()}`,
          papel: 'assistant',
          texto: data?.statusMessage || data?.message || 'Não consegui responder agora.',
          erro: true
        })
        return
      }

      const r = data as RespostaAnalista
      turnos.value.push({
        id: `a${Date.now()}`,
        papel: 'assistant',
        texto: r.resposta,
        rastro: r.rastro || [],
        cobertura: r.cobertura ?? null,
        titulo: r.titulo
      })
    } catch {
      turnos.value.push({
        id: `a${Date.now()}`,
        papel: 'assistant',
        texto: 'Falha de conexão com o analista. Tente de novo.',
        erro: true
      })
    } finally {
      pensando.value = false
    }
  }

  const limpar = () => { turnos.value = [] }

  return { turnos, resumo, pensando, carregarResumo, perguntar, limpar }
}

// ── Exportação em PDF ────────────────────────────────────────────────────────

// Remove emojis/símbolos que a fonte Latin-1 do jsPDF não renderiza (mantém
// acentos). Mesmo helper usado nos outros relatórios do painel.
function pdfSafe(s: string | null | undefined): string {
  return (s || '')
    .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{2190}-\u{21FF}\u{2300}-\u{23FF}]/gu, '')
    .replace(/[^\x00-\xFF]/g, '')
    .trim()
}

/** Blocos que o markdown da resposta vira no PDF. */
type Bloco =
  | { tipo: 'titulo'; texto: string }
  | { tipo: 'paragrafo'; texto: string }
  | { tipo: 'item'; texto: string }
  | { tipo: 'tabela'; head: string[]; body: string[][] }

// Markdown → blocos. O modelo responde em markdown simples (negrito, listas,
// tabelas); não vale trazer um parser inteiro para o bundle por causa disso.
function parseMarkdown(md: string): Bloco[] {
  const blocos: Bloco[] = []
  const linhas = (md || '').split('\n')
  let paragrafo: string[] = []

  const fecharParagrafo = () => {
    if (paragrafo.length) {
      blocos.push({ tipo: 'paragrafo', texto: paragrafo.join(' ').trim() })
      paragrafo = []
    }
  }

  const limpar = (s: string) =>
    s.replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1').replace(/`(.+?)`/g, '$1').trim()

  for (let i = 0; i < linhas.length; i++) {
    const linha = linhas[i] ?? ''
    const t = linha.trim()

    if (!t) { fecharParagrafo(); continue }

    // Tabela: | a | b |  /  |---|---|  /  | 1 | 2 |
    if (t.startsWith('|') && (linhas[i + 1] || '').trim().match(/^\|[\s:|-]+\|$/)) {
      fecharParagrafo()
      const celulas = (l: string) => l.trim().replace(/^\||\|$/g, '').split('|').map((c) => limpar(c))
      const head = celulas(t)
      const body: string[][] = []
      i += 2
      while (i < linhas.length && (linhas[i] || '').trim().startsWith('|')) {
        body.push(celulas(linhas[i] || ''))
        i++
      }
      i--
      blocos.push({ tipo: 'tabela', head, body })
      continue
    }

    if (t.startsWith('#')) {
      fecharParagrafo()
      blocos.push({ tipo: 'titulo', texto: limpar(t.replace(/^#+\s*/, '')) })
      continue
    }

    if (/^[-*+]\s+/.test(t) || /^\d+\.\s+/.test(t)) {
      fecharParagrafo()
      blocos.push({ tipo: 'item', texto: limpar(t.replace(/^([-*+]|\d+\.)\s+/, '')) })
      continue
    }

    paragrafo.push(limpar(t))
  }
  fecharParagrafo()
  return blocos
}

/**
 * Gera o PDF de uma análise. Retrato (é texto corrido, não planilha) e com a
 * mesma marca dos outros relatórios do painel.
 *
 * A faixa de cobertura entra logo abaixo do cabeçalho quando há mensagem
 * ilegível: o PDF circula solto pela empresa, e quem lê precisa saber que o
 * diagnóstico saiu de uma leitura parcial mesmo sem ter visto a tela.
 */
export async function exportarAnalisePDF(turno: TurnoAnalista, pergunta: string): Promise<void> {
  if (typeof window === 'undefined') return

  const { jsPDF } = await import('jspdf')
  const autoTable = (await import('jspdf-autotable')).default
  const doc = new jsPDF({ orientation: 'portrait' })

  const ROXO: [number, number, number] = [102, 90, 228]
  const L = 16                     // margem esquerda
  const LARGURA = 210 - L * 2      // A4 retrato
  const RODAPE = 275               // a partir daqui, quebra a página
  const agora = new Date()

  // ── Cabeçalho ──
  doc.setFillColor(...ROXO)
  doc.rect(0, 0, 210, 30, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFontSize(17)
  doc.setFont('helvetica', 'bold')
  doc.text('Razy', L, 14)
  doc.setFontSize(10)
  doc.setFont('helvetica', 'normal')
  doc.text('Analise de Atendimento', L, 22)

  let y = 40

  doc.setTextColor(30, 30, 30)
  doc.setFontSize(13)
  doc.setFont('helvetica', 'bold')
  const tituloLinhas = doc.splitTextToSize(pdfSafe(pergunta), LARGURA) as string[]
  doc.text(tituloLinhas, L, y)
  y += tituloLinhas.length * 6 + 2

  doc.setTextColor(120, 120, 120)
  doc.setFontSize(8.5)
  doc.setFont('helvetica', 'normal')
  doc.text(`Gerado em ${agora.toLocaleString('pt-BR')}`, L, y)
  y += 9

  // ── Faixa de cobertura ──
  const cob = turno.cobertura
  if (cob && cob.sem_conteudo > 0) {
    const pct = Math.round((cob.lidas / cob.total) * 100)
    doc.setFillColor(255, 248, 230)
    doc.setDrawColor(240, 200, 120)
    doc.roundedRect(L, y, LARGURA, 17, 2, 2, 'FD')
    doc.setTextColor(150, 90, 10)
    doc.setFontSize(9.5)
    doc.setFont('helvetica', 'bold')
    doc.text(`Leitura parcial: ${cob.lidas} de ${cob.total} mensagens (${pct}%)`, L + 4, y + 6.5)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(120, 100, 70)
    doc.text(
      `${cob.sem_conteudo} mensagens sao audio sem transcricao ou imagem sem legenda e nao foram lidas.`,
      L + 4, y + 12.5
    )
    y += 23
  }

  // ── Corpo (markdown convertido) ──
  const quebrarSePreciso = (altura: number) => {
    if (y + altura > RODAPE) { doc.addPage(); y = 20 }
  }

  for (const bloco of parseMarkdown(turno.texto)) {
    if (bloco.tipo === 'tabela') {
      quebrarSePreciso(30)
      autoTable(doc, {
        startY: y,
        head: [bloco.head.map(pdfSafe)],
        body: bloco.body.map((linha) => linha.map(pdfSafe)),
        theme: 'striped',
        styles: { fontSize: 8.5, cellPadding: 2.5 },
        headStyles: { fillColor: ROXO, textColor: 255, fontStyle: 'bold' },
        alternateRowStyles: { fillColor: [249, 250, 251] },
        margin: { left: L, right: L }
      })
      y = (doc as any).lastAutoTable.finalY + 7
      continue
    }

    if (bloco.tipo === 'titulo') {
      quebrarSePreciso(14)
      y += 3
      doc.setTextColor(30, 30, 30)
      doc.setFontSize(11.5)
      doc.setFont('helvetica', 'bold')
      doc.text(pdfSafe(bloco.texto), L, y)
      y += 7
      continue
    }

    const recuo = bloco.tipo === 'item' ? 5 : 0
    const texto = bloco.tipo === 'item' ? `- ${bloco.texto}` : bloco.texto
    const linhas = doc.splitTextToSize(pdfSafe(texto), LARGURA - recuo) as string[]
    quebrarSePreciso(linhas.length * 5 + 4)
    doc.setTextColor(55, 55, 55)
    doc.setFontSize(9.5)
    doc.setFont('helvetica', 'normal')
    doc.text(linhas, L + recuo, y)
    y += linhas.length * 5 + (bloco.tipo === 'item' ? 1.5 : 4)
  }

  // ── Rastro das consultas ──
  // Vai no PDF porque é o que torna o relatório auditável: quem receber o
  // arquivo consegue ver de onde cada número saiu.
  if (turno.rastro?.length) {
    quebrarSePreciso(34)
    y += 4
    doc.setTextColor(30, 30, 30)
    doc.setFontSize(10)
    doc.setFont('helvetica', 'bold')
    doc.text('De onde vieram os dados', L, y)
    y += 3
    autoTable(doc, {
      startY: y,
      head: [['Consulta', 'Parametros', 'Retorno']],
      body: turno.rastro.map((p) => [pdfSafe(p.fn), pdfSafe(p.args), pdfSafe(p.resultado)]),
      theme: 'grid',
      styles: { fontSize: 7.5, cellPadding: 2, textColor: [90, 90, 90] },
      headStyles: { fillColor: [240, 240, 245], textColor: [70, 70, 70], fontStyle: 'bold' },
      margin: { left: L, right: L }
    })
    y = (doc as any).lastAutoTable.finalY + 6
  }

  // ── Rodapé em todas as páginas ──
  const total = doc.getNumberOfPages()
  for (let p = 1; p <= total; p++) {
    doc.setPage(p)
    doc.setFontSize(7.5)
    doc.setTextColor(150, 150, 150)
    doc.setFont('helvetica', 'normal')
    doc.text('Razy - Analise de Atendimento', L, 288)
    doc.text(`${p} de ${total}`, 210 - L, 288, { align: 'right' })
  }

  const slug = pdfSafe(pergunta).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40)
  const data = agora.toISOString().slice(0, 10)
  doc.save(`analise-${slug || 'atendimento'}-${data}.pdf`)
}
