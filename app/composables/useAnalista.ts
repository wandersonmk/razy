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

/** Série de um gráfico. `cores` só é usada em rosca (uma cor por fatia). */
export interface SerieGrafico {
  nome: string
  dados: number[]
  cor?: string
  cores?: string[]
}

/**
 * Especificação de gráfico montada no backend a partir do retorno REAL da
 * consulta — o modelo de linguagem não escolhe número nem rótulo aqui.
 */
export interface GraficoSpec {
  tipo: 'barras' | 'barras_h' | 'rosca'
  titulo: string
  labels: string[]
  series: SerieGrafico[]
  sufixo?: string
}

export interface RespostaAnalista {
  resposta: string
  rastro: PassoRastro[]
  cobertura: Cobertura | null
  graficos: GraficoSpec[]
  titulo: string
}

export interface TurnoAnalista {
  id: string
  papel: 'user' | 'assistant'
  texto: string
  rastro?: PassoRastro[]
  cobertura?: Cobertura | null
  graficos?: GraficoSpec[]
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
        graficos: r.graficos || [],
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
/**
 * Desenha um gráfico num canvas fora da tela e devolve o PNG.
 *
 * Renderiza à parte em vez de fotografar o gráfico da tela por dois motivos: o
 * da tela está no tema do usuário (fundo escuro fica horrível impresso) e pode
 * nem estar visível quando o PDF é gerado. Aqui a moldura é sempre clara.
 */
async function graficoParaPNG(spec: GraficoSpec): Promise<{ png: string; proporcao: number } | null> {
  try {
    const { Chart, registerables } = await import('chart.js')
    Chart.register(...registerables)

    const CORES: Record<string, string> = {
      azul: '#3B82F6', verde: '#10B981', ambar: '#F59E0B', rosa: '#F43F5E', violeta: '#8B5CF6'
    }
    const cor = (n?: string) => CORES[n || 'azul'] || CORES.azul!

    const horizontal = spec.tipo === 'barras_h'
    const rosca = spec.tipo === 'rosca'
    const largura = 900
    const altura = horizontal ? Math.max(260, spec.labels.length * 42 + 80) : 380

    const canvas = document.createElement('canvas')
    canvas.width = largura
    canvas.height = altura
    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    // Fundo branco: o PDF é impresso, e canvas transparente vira preto no jsPDF.
    ctx.fillStyle = '#FFFFFF'
    ctx.fillRect(0, 0, largura, altura)

    const serie = spec.series[0]!
    const eixo = { color: '#4B5563', font: { size: 18 } }
    const grade = { color: 'rgba(17,24,39,0.10)' }

    const chart = new Chart(ctx, rosca
      ? {
          type: 'doughnut',
          data: {
            labels: spec.labels,
            datasets: [{
              data: serie.dados,
              backgroundColor: (serie.cores || spec.labels.map((_, i) => ['azul', 'verde', 'violeta'][i]!)).map(cor),
              borderWidth: 0
            }]
          },
          options: {
            responsive: false, animation: false, cutout: '58%',
            plugins: {
              legend: {
                position: 'right',
                labels: { color: '#374151', font: { size: 18 }, usePointStyle: true, pointStyle: 'circle', boxWidth: 12, padding: 16 }
              }
            }
          }
        }
      : {
          type: 'bar',
          data: {
            labels: spec.labels,
            datasets: [{
              data: serie.dados,
              backgroundColor: cor(serie.cor),
              borderRadius: 6,
              maxBarThickness: horizontal ? 26 : 56
            }]
          },
          options: {
            indexAxis: horizontal ? 'y' : 'x',
            responsive: false, animation: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { beginAtZero: horizontal, ticks: eixo, grid: horizontal ? grade : { display: false }, border: { display: false } },
              y: { beginAtZero: !horizontal, ticks: eixo, grid: horizontal ? { display: false } : grade, border: { display: false } }
            }
          }
        }
    )

    const png = canvas.toDataURL('image/png', 1)
    chart.destroy()
    return { png, proporcao: altura / largura }
  } catch (e) {
    console.warn('[analista] falha ao rasterizar gráfico:', e)
    return null
  }
}

/**
 * Números de destaque para o topo do relatório.
 *
 * Sai das séries dos gráficos — que já vieram do banco — em vez de tentar
 * extrair número do texto do modelo. Assim o destaque nunca diverge do gráfico
 * logo abaixo dele.
 */
function destaquesDe(turno: TurnoAnalista): { rotulo: string; valor: string }[] {
  const out: { rotulo: string; valor: string }[] = []

  for (const g of turno.graficos || []) {
    const serie = g.series?.[0]
    if (!serie?.dados?.length) continue
    const sufixo = g.sufixo || ''

    if (g.tipo === 'rosca') {
      // Rosca compara partes de um todo: o destaque é a fatia dominante.
      const total = serie.dados.reduce((s, n) => s + n, 0)
      const i = serie.dados.indexOf(Math.max(...serie.dados))
      if (total > 0 && i >= 0) {
        out.push({ rotulo: `Maior parte: ${g.labels[i]}`, valor: `${Math.round((serie.dados[i]! / total) * 100)}%` })
      }
      continue
    }

    const iMax = serie.dados.indexOf(Math.max(...serie.dados))
    const iMin = serie.dados.indexOf(Math.min(...serie.dados))
    if (iMax >= 0) out.push({ rotulo: `${g.titulo} - maior`, valor: `${g.labels[iMax]}: ${serie.dados[iMax]}${sufixo}` })
    if (iMin >= 0 && iMin !== iMax) out.push({ rotulo: `${g.titulo} - menor`, valor: `${g.labels[iMin]}: ${serie.dados[iMin]}${sufixo}` })
  }

  if (turno.cobertura?.total) {
    const c = turno.cobertura
    out.push({ rotulo: 'Mensagens lidas', valor: `${c.lidas} de ${c.total}` })
  }

  return out.slice(0, 6)
}

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

  const quebrarSePreciso = (altura: number) => {
    if (y + altura > RODAPE) { doc.addPage(); y = 20 }
  }

  // ── Destaques ──
  // Cartões com os números que importam, antes do texto: quem abre o relatório
  // costuma querer o placar primeiro e a explicação depois.
  const destaques = destaquesDe(turno)
  if (destaques.length) {
    const porLinha = 3
    const cardW = (LARGURA - (porLinha - 1) * 4) / porLinha
    const linhas = Math.ceil(destaques.length / porLinha)
    quebrarSePreciso(linhas * 22 + 6)

    destaques.forEach((d, i) => {
      const col = i % porLinha
      const lin = Math.floor(i / porLinha)
      const x = L + col * (cardW + 4)
      const cy = y + lin * 22

      doc.setDrawColor(228, 228, 234)
      doc.setFillColor(250, 250, 252)
      doc.roundedRect(x, cy, cardW, 18, 2, 2, 'FD')

      doc.setTextColor(35, 35, 40)
      doc.setFontSize(10)
      doc.setFont('helvetica', 'bold')
      const valor = doc.splitTextToSize(pdfSafe(d.valor), cardW - 8) as string[]
      doc.text(valor[0] || '', x + 4, cy + 7.5)

      doc.setTextColor(120, 120, 128)
      doc.setFontSize(7)
      doc.setFont('helvetica', 'normal')
      const rotulo = doc.splitTextToSize(pdfSafe(d.rotulo), cardW - 8) as string[]
      doc.text(rotulo[0] || '', x + 4, cy + 13.5)
    })

    y += linhas * 22 + 4
  }

  // ── Corpo (markdown convertido) ──

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

  // ── Gráficos ──
  // Entram depois do texto: o relatório se lê pela conclusão, e o gráfico
  // confirma. Cada um ocupa a largura útil, com a altura pela proporção real.
  for (const spec of turno.graficos || []) {
    const img = await graficoParaPNG(spec)
    if (!img) continue
    const alturaImg = LARGURA * img.proporcao
    quebrarSePreciso(alturaImg + 14)
    y += 3
    doc.setTextColor(30, 30, 30)
    doc.setFontSize(10)
    doc.setFont('helvetica', 'bold')
    doc.text(pdfSafe(spec.titulo), L, y)
    y += 4
    doc.addImage(img.png, 'PNG', L, y, LARGURA, alturaImg)
    y += alturaImg + 8
  }

  // O rastro das consultas NÃO entra no relatório: quem recebe quer a leitura
  // do atendimento, não o encanamento que produziu os números. Ele continua
  // guardado no turno, disponível se um dia for preciso auditar.

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
