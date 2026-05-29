<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header com botões de exportação -->
    <div class="flex items-center justify-between p-6 border-b border-border">
      <div>
        <h2 class="text-xl font-semibold text-foreground">Relatórios</h2>
        <p class="text-sm text-muted-foreground mt-1">Acompanhe todos os registros do sistema</p>
        <p v-if="relatoriosFiltrados && relatoriosFiltrados.length > 0" class="text-xs text-muted-foreground mt-1">
          Total de registros: <span class="font-semibold text-primary">{{ relatoriosFiltrados.length }}</span>
        </p>
      </div>
      <div class="flex items-center space-x-2">
        <button
          @click="exportToPDF"
          class="flex items-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium"
          title="Exportar para PDF"
        >
          <Icon icon="file-pdf" class-name="w-4 h-4" fallback="" />
          <span>PDF</span>
        </button>
        <button
          @click="exportToExcel"
          class="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium"
          title="Exportar para Excel"
        >
          <Icon icon="file-excel" class-name="w-4 h-4" fallback="" />
          <span>Excel</span>
        </button>
      </div>
    </div>

    <!-- Filtros -->
    <div class="p-6 border-b border-border bg-muted/30">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Filtro por Data Inicial -->
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Data Inicial</label>
          <input
            v-model="filtros.dataInicial"
            type="date"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary date-input-white-icon"
          />
        </div>

        <!-- Filtro por Data Final -->
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Data Final</label>
          <input
            v-model="filtros.dataFinal"
            type="date"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary date-input-white-icon"
          />
        </div>

        <!-- Filtro por CNPJ/Nome da Loja -->
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">CNPJ ou Nome da Loja</label>
          <input
            v-model="filtros.lojaOuCnpj"
            type="text"
            placeholder="Digite CNPJ ou nome da loja"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <!-- Filtro por Empresa/Operadora -->
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Empresa</label>
          <select
            v-model="filtros.empresa"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">Todas as empresas</option>
            <option value="Vivo">Vivo</option>
            <option value="Tim">Tim</option>
            <option value="Claro">Claro</option>
            <option value="Oi">Oi</option>
            <option value="Casas Bahia">Casas Bahia</option>
          </select>
        </div>
      </div>

      <!-- Botões de ação dos filtros -->
      <div class="flex items-center justify-end mt-4">
        <button
          @click="limparFiltros"
          class="flex items-center space-x-2 px-4 py-2 border border-border text-foreground hover:bg-muted rounded-lg transition-colors text-sm font-medium"
        >
          <Icon icon="times-circle" class-name="w-4 h-4" fallback="" />
          <span>Limpar Filtros</span>
        </button>
      </div>
    </div>

    <!-- Lista de relatórios -->
    <div class="p-6">
      <!-- Loading state -->
      <div v-if="isLoading" class="text-center py-8">
        <div class="flex flex-col items-center">
          <div class="w-12 h-12 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
            <svg class="w-6 h-6 text-muted-foreground animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </div>
          <h3 class="text-lg font-medium text-foreground mb-2">Carregando relatórios...</h3>
          <p class="text-muted-foreground">Aguarde um momento</p>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="text-center py-8">
        <div class="flex flex-col items-center">
          <Icon icon="exclamation-triangle" class-name="w-12 h-12 text-red-500 mb-4" fallback="" />
          <h3 class="text-lg font-medium text-foreground mb-2">Erro ao carregar relatórios</h3>
          <p class="text-muted-foreground mb-4">{{ error }}</p>
          <button
            @click="recarregarRelatorios"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      </div>

      <!-- Mensagem quando não há relatórios -->
      <div v-else-if="relatoriosFiltrados.length === 0" class="text-center py-8">
        <div class="flex flex-col items-center">
          <Icon icon="file-alt" class-name="w-12 h-12 text-muted-foreground/50 mb-4" fallback="" />
          <h3 class="text-lg font-medium text-foreground mb-2">
            {{ filtrosAplicados ? 'Nenhum relatório encontrado' : 'Nenhum relatório disponível' }}
          </h3>
          <p class="text-muted-foreground">
            {{ filtrosAplicados ? 'Tente ajustar os filtros para encontrar relatórios.' : 'Quando houver relatórios de tickets, eles aparecerão aqui.' }}
          </p>
        </div>
      </div>

      <!-- Tabela de relatórios -->
      <div class="overflow-x-auto">
        <div style="max-height: 400px; overflow-y: auto; position: relative;">
          <table class="w-full">
            <thead>
              <tr class="border-b border-border">
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Nome</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Telefone</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Loja</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">CNPJ</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Data/Hora</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Motivo</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Empresa</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="relatorio in (relatoriosOrdenados ? relatoriosOrdenados.slice(0, relatoriosVisiveis) : [])" 
                :key="relatorio.id"
                class="border-b border-border/50 hover:bg-muted/30 transition-colors"
              >
                <!-- Nome da pessoa -->
                <td class="py-3 px-3">
                  <div class="flex items-center">
                    <div class="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center mr-2">
                      <Icon icon="user" class-name="w-3 h-3 text-primary" fallback="" />
                    </div>
                    <span class="font-medium text-foreground text-sm">{{ relatorio.nome_pessoa }}</span>
                  </div>
                </td>
                
                <!-- Telefone -->
                <td class="py-3 px-3">
                  <span class="text-foreground text-sm">{{ relatorio.telefone }}</span>
                </td>
                
                <!-- Nome da loja -->
                <td class="py-3 px-3">
                  <span class="text-foreground font-medium text-sm">{{ relatorio.nome_loja }}</span>
                </td>
                
                <!-- CNPJ -->
                <td class="py-3 px-3">
                  <span class="text-foreground text-xs font-mono">{{ relatorio.cnpj }}</span>
                </td>
                
                <!-- Data e Hora -->
                <td class="py-3 px-3">
                  <div class="text-xs">
                    <div class="font-medium text-foreground">{{ relatorio.data_abertura_chamado }}</div>
                    <div class="text-muted-foreground">{{ relatorio.hora_abertura_chamado }}</div>
                  </div>
                </td>
                
                <!-- Motivo -->
                <td class="py-3 px-3">
                  <span class="text-foreground text-xs">{{ relatorio.motivo_chamado }}</span>
                </td>
                
                <!-- Empresa -->
                <td class="py-3 px-3">
                  <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                        :class="getEmpresaClass(relatorio.nome_empresa)">
                    {{ relatorio.nome_empresa }}
                  </span>
                </td>
              </tr>
              
              <tr v-if="relatoriosFiltrados && relatoriosVisiveis < relatoriosFiltrados.length">
                <td :colspan="7" style="padding:0; border:none; background:transparent;">
                  <div ref="relatorioSentinel" style="height: 1px; width: 100%;"></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tabela de relatórios -->
      <div class="overflow-x-auto">
        <div style="max-height: 700px; overflow-y: auto;">
          <!-- ...existing code... -->
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
// Interface para relatório
interface Relatorio {
  id: string
  nome_pessoa: string
  telefone: string
  nome_loja: string
  cnpj: string
  nome_empresa: string
  data_abertura_chamado: string
  hora_abertura_chamado: string
  motivo_chamado: string
  created_at: string
}

// Interface para filtros
interface Filtros {
  dataInicial: string
  dataFinal: string
  lojaOuCnpj: string
  empresa: string
}

// Usar o composable de relatórios
const { 
  relatorios: relatoriosData, 
  isLoading, 
  error, 
  fetchRelatorios, 
  clearError 
} = useRelatorios()

// Estados reativos
const filtros = ref<Filtros>({
  dataInicial: '',
  dataFinal: '',
  lojaOuCnpj: '',
  empresa: ''
})

// Computed para detectar se há filtros ativos automaticamente
const filtrosAplicados = computed(() => {
  return filtros.value.dataInicial !== '' || 
         filtros.value.dataFinal !== '' || 
         filtros.value.lojaOuCnpj !== '' || 
         filtros.value.empresa !== ''
})

// Computed para relatórios filtrados
const relatoriosFiltrados = computed(() => {
  let resultado = relatoriosData.value

  if (filtros.value.dataInicial) {
    resultado = resultado.filter(r => {
      // Converter data do formato DD/MM/YYYY para comparação
      const dataRelatorio = new Date(r.data_abertura_chamado.split('/').reverse().join('-'))
      const dataFiltro = new Date(filtros.value.dataInicial)
      return dataRelatorio >= dataFiltro
    })
  }

  if (filtros.value.dataFinal) {
    resultado = resultado.filter(r => {
      const dataRelatorio = new Date(r.data_abertura_chamado.split('/').reverse().join('-'))
      const dataFiltro = new Date(filtros.value.dataFinal)
      return dataRelatorio <= dataFiltro
    })
  }

  if (filtros.value.lojaOuCnpj) {
    const termo = filtros.value.lojaOuCnpj.toLowerCase()
    resultado = resultado.filter(r => 
      r.nome_loja.toLowerCase().includes(termo) || 
      r.cnpj.toLowerCase().includes(termo)
    )
  }

  if (filtros.value.empresa) {
    resultado = resultado.filter(r =>
      r.nome_empresa && filtros.value.empresa &&
      r.nome_empresa.toLowerCase() === filtros.value.empresa.toLowerCase()
    )
  }

  return resultado
})

// Computed para ordenar relatórios por data de criação (mais novos no topo)
const relatoriosOrdenados = computed(() => {
  return relatoriosFiltrados.value ? [...relatoriosFiltrados.value].sort((a, b) => {
    if (!a.created_at || !b.created_at) return 0
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  }) : []
})

// Função para recarregar relatórios
const recarregarRelatorios = () => {
  clearError()
  fetchRelatorios()
}

// Função para limpar filtros
function limparFiltros() {
  filtros.value = {
    dataInicial: '',
    dataFinal: '',
    lojaOuCnpj: '',
    empresa: ''
  }
  console.log('Filtros limpos - os filtros agora são automáticos!')
}

// Função para obter classes CSS da empresa
function getEmpresaClass(empresa: string) {
  const classes = {
    'VIVO': 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
    'TIM': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
    'CLARO': 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
    'OI': 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
  }
  return classes[empresa as keyof typeof classes] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
}

// Função auxiliar para converter data sem problemas de fuso horário
function formatarDataFiltro(dataString: string): string {
  // Separar a data em partes (YYYY-MM-DD)
  const partes = dataString.split('-')
  if (partes.length !== 3 || !partes[0] || !partes[1] || !partes[2]) {
    return dataString // Retorna original se formato inválido
  }
  
  const ano = parseInt(partes[0], 10)
  const mes = parseInt(partes[1], 10) - 1 // Mês é 0-indexado no JS
  const dia = parseInt(partes[2], 10)
  
  // Criar data especificando ano, mês e dia para evitar problemas de UTC
  const data = new Date(ano, mes, dia)
  
  return data.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

// Função para exportar para PDF
async function exportToPDF() {
  // Verificar se estamos no cliente
  if (typeof window === 'undefined') {
    console.warn('Exportação PDF só funciona no cliente')
    return
  }

  try {
    // Importação dinâmica para evitar problemas com SSR
    const [{ default: jsPDF }, { default: autoTable }] = await Promise.all([
      import('jspdf'),
      import('jspdf-autotable')
    ])
    
    // Criar documento PDF em formato A4 paisagem
    const doc = new jsPDF('landscape', 'mm', 'a4')
    
    // Configurar fonte para suporte UTF-8
    doc.setFont('helvetica', 'normal')
    
    // Cores do tema
    const primaryColor: [number, number, number] = [79, 70, 229] // Indigo-600
    const textColor: [number, number, number] = [17, 24, 39] // Gray-900
    const lightGray: [number, number, number] = [243, 244, 246] // Gray-100
    
    // Header do documento
    doc.setFillColor(primaryColor[0], primaryColor[1], primaryColor[2])
    doc.rect(0, 0, 297, 40, 'F')
    
    // Logo/Título
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(24)
    doc.setFont('helvetica', 'bold')
    doc.text('Razy', 20, 20)
    
    doc.setFontSize(14)
    doc.setFont('helvetica', 'normal')
    doc.text('Sistema de disparo', 20, 30)
    
    // Informações do relatório
    doc.setTextColor(textColor[0], textColor[1], textColor[2])
    doc.setFontSize(18)
    doc.setFont('helvetica', 'bold')
    doc.text('Relatórios de Tickets', 20, 55)
    
    // Data de geração
    const agora = new Date()
    const dataFormatada = agora.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
    
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(107, 114, 128)
    doc.text(`Gerado em: ${dataFormatada}`, 20, 65)
    doc.text(`Total de registros: ${relatoriosFiltrados.value.length}`, 20, 72)
    
    // Mostrar filtros aplicados se houver
    let yPosicaoAtual = 72
    if (filtrosAplicados.value) {
      yPosicaoAtual += 10
      doc.setFontSize(10)
      doc.setFont('helvetica', 'bold')
      doc.setTextColor(79, 70, 229) // Cor primária
      doc.text('Filtros Aplicados:', 20, yPosicaoAtual)
      
      doc.setFont('helvetica', 'normal')
      doc.setTextColor(107, 114, 128)
      yPosicaoAtual += 7
      
      if (filtros.value.dataInicial && filtros.value.dataFinal) {
        const dataIni = formatarDataFiltro(filtros.value.dataInicial)
        const dataFim = formatarDataFiltro(filtros.value.dataFinal)
        doc.text(`• Período: ${dataIni} até ${dataFim}`, 20, yPosicaoAtual)
        yPosicaoAtual += 7
      } else if (filtros.value.dataInicial) {
        const dataIni = formatarDataFiltro(filtros.value.dataInicial)
        doc.text(`• Data inicial: ${dataIni}`, 20, yPosicaoAtual)
        yPosicaoAtual += 7
      } else if (filtros.value.dataFinal) {
        const dataFim = formatarDataFiltro(filtros.value.dataFinal)
        doc.text(`• Data final: ${dataFim}`, 20, yPosicaoAtual)
        yPosicaoAtual += 7
      }
      
      if (filtros.value.empresa) {
        doc.text(`• Empresa: ${filtros.value.empresa}`, 20, yPosicaoAtual)
        yPosicaoAtual += 7
      }
      
      if (filtros.value.lojaOuCnpj) {
        doc.text(`• Loja/CNPJ: ${filtros.value.lojaOuCnpj}`, 20, yPosicaoAtual)
        yPosicaoAtual += 7
      }
    }
    
    // Ajustar posição Y da tabela baseado nos filtros
    const startYTabela = yPosicaoAtual + 15
    
    // Preparar dados para a tabela
    const tableData = relatoriosFiltrados.value.map((relatorio, index) => [
      (index + 1).toString(),
      relatorio.nome_pessoa,
      relatorio.telefone,
      relatorio.nome_loja,
      relatorio.cnpj,
      `${relatorio.data_abertura_chamado} ${relatorio.hora_abertura_chamado}`,
      relatorio.motivo_chamado,
      relatorio.nome_empresa
    ])
    
    // Configurar tabela
    autoTable(doc, {
      head: [['#', 'Nome', 'Telefone', 'Loja', 'CNPJ', 'Data/Hora', 'Motivo', 'Empresa']],
      body: tableData,
      startY: startYTabela,
      theme: 'grid',
      styles: {
        font: 'helvetica',
        fontSize: 8,
        cellPadding: 3,
        textColor: textColor,
        lineColor: [209, 213, 219],
        lineWidth: 0.5
      },
      headStyles: {
        fillColor: primaryColor,
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        fontSize: 9
      },
      alternateRowStyles: {
        fillColor: lightGray
      },
      columnStyles: {
        0: { cellWidth: 10, halign: 'center' }, // #
        1: { cellWidth: 35 }, // Nome
        2: { cellWidth: 30 }, // Telefone
        3: { cellWidth: 35 }, // Loja
        4: { cellWidth: 35 }, // CNPJ
        5: { cellWidth: 35 }, // Data/Hora
        6: { cellWidth: 60 }, // Motivo
        7: { cellWidth: 20 } // Empresa
      },
      margin: { left: 15, right: 15 }
    })
    
    // Footer
    const pageCount = doc.getNumberOfPages()
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i)
      
      // Linha do footer
      doc.setDrawColor(209, 213, 219)
      doc.line(15, 200, 282, 200)
      
      // Texto do footer
      doc.setFontSize(8)
      doc.setTextColor(107, 114, 128)
      doc.text('Razy - Sistema de disparo', 15, 208)
      doc.text(`Página ${i} de ${pageCount}`, 282, 208, { align: 'right' })
    }
    
    // Salvar o arquivo
    const nomeArquivo = `relatorios_tickets_${agora.toISOString().split('T')[0]}.pdf`
    doc.save(nomeArquivo)
    
    console.log('PDF de relatórios exportado com sucesso!')
    
  } catch (error) {
    console.error('Erro ao exportar PDF:', error)
    alert('Erro ao gerar o PDF. Tente novamente.')
  }
}

// Função para exportar para Excel
async function exportToExcel() {
  // Verificar se estamos no cliente
  if (typeof window === 'undefined') {
    console.warn('Exportação Excel só funciona no cliente')
    return
  }

  try {
    // Importação dinâmica para evitar problemas com SSR
    const XLSX = await import('xlsx')
    
    // Data de geração
    const agora = new Date()
    const dataFormatada = agora.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
    
    // Preparar dados completos para o Excel
    const dadosCompletos = [
      // Informações do cabeçalho
      ['Razy - Sistema de disparo'],
      ['Relatórios de Tickets'],
      [`Gerado em: ${dataFormatada}`],
      [`Total de registros: ${relatoriosFiltrados.value.length}`]
    ]
    
    // Adicionar filtros aplicados se houver
    if (filtrosAplicados.value) {
      dadosCompletos.push([]) // Linha vazia
      dadosCompletos.push(['Filtros Aplicados:'])
      
      if (filtros.value.dataInicial && filtros.value.dataFinal) {
        const dataIni = formatarDataFiltro(filtros.value.dataInicial)
        const dataFim = formatarDataFiltro(filtros.value.dataFinal)
        dadosCompletos.push([`Período: ${dataIni} até ${dataFim}`])
      } else if (filtros.value.dataInicial) {
        const dataIni = formatarDataFiltro(filtros.value.dataInicial)
        dadosCompletos.push([`Data inicial: ${dataIni}`])
      } else if (filtros.value.dataFinal) {
        const dataFim = formatarDataFiltro(filtros.value.dataFinal)
        dadosCompletos.push([`Data final: ${dataFim}`])
      }
      
      if (filtros.value.empresa) {
        dadosCompletos.push([`Empresa: ${filtros.value.empresa}`])
      }
      
      if (filtros.value.lojaOuCnpj) {
        dadosCompletos.push([`Loja/CNPJ: ${filtros.value.lojaOuCnpj}`])
      }
    }
    
    // Linha vazia e cabeçalho da tabela
    dadosCompletos.push([])
    dadosCompletos.push(['#', 'Nome', 'Telefone', 'Loja', 'CNPJ', 'Data Abertura', 'Hora Abertura', 'Motivo', 'Empresa'])
    
    // Adicionar dados dos relatórios
    relatoriosFiltrados.value.forEach((relatorio, index) => {
      dadosCompletos.push([
        (index + 1).toString(),
        relatorio.nome_pessoa,
        relatorio.telefone,
        relatorio.nome_loja,
        relatorio.cnpj,
        relatorio.data_abertura_chamado,
        relatorio.hora_abertura_chamado,
        relatorio.motivo_chamado,
        relatorio.nome_empresa
      ])
    })
    
    // Criar workbook e worksheet
    const workbook = XLSX.utils.book_new()
    const worksheet = XLSX.utils.aoa_to_sheet(dadosCompletos)
    
    // Configurar largura das colunas
    const columnWidths = [
      { wch: 5 },  // #
      { wch: 25 }, // Nome
      { wch: 18 }, // Telefone
      { wch: 25 }, // Loja
      { wch: 20 }, // CNPJ
      { wch: 15 }, // Data
      { wch: 10 }, // Hora
      { wch: 40 }, // Motivo
      { wch: 12 }  // Empresa
    ]
    worksheet['!cols'] = columnWidths
    
    // Mesclar células do cabeçalho (dinâmico baseado nos filtros)
    const merges = [
      { s: { r: 0, c: 0 }, e: { r: 0, c: 8 } }, // Título principal
      { s: { r: 1, c: 0 }, e: { r: 1, c: 8 } }, // Subtítulo
      { s: { r: 2, c: 0 }, e: { r: 2, c: 8 } }, // Data
      { s: { r: 3, c: 0 }, e: { r: 3, c: 8 } }, // Total
    ]
    
    // Se há filtros, adicionar mesclagens para as linhas de filtros
    if (filtrosAplicados.value) {
      let linhaMerge = 5 // Linha "Filtros Aplicados:"
      merges.push({ s: { r: linhaMerge, c: 0 }, e: { r: linhaMerge, c: 8 } })
      
      // Contar quantas linhas de filtro foram adicionadas
      let linhasExtras = 1 // "Filtros Aplicados:"
      if (filtros.value.dataInicial || filtros.value.dataFinal) linhasExtras++
      if (filtros.value.empresa) linhasExtras++
      if (filtros.value.lojaOuCnpj) linhasExtras++
      
      // Mesclar cada linha de filtro
      for (let i = 1; i < linhasExtras; i++) {
        merges.push({ s: { r: linhaMerge + i, c: 0 }, e: { r: linhaMerge + i, c: 8 } })
      }
    }
    
    worksheet['!merges'] = merges
    
    // Estilizar células específicas
    if (worksheet['A1']) {
      worksheet['A1'].s = {
        font: { bold: true, size: 14, color: { rgb: "4F46E5" } },
        alignment: { horizontal: "center" }
      }
    }
    
    if (worksheet['A2']) {
      worksheet['A2'].s = {
        font: { bold: true, size: 12 },
        alignment: { horizontal: "center" }
      }
    }
    
    // Estilizar cabeçalho da tabela (linha 6)
    for (let col = 0; col < 9; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: 5, c: col })
      if (worksheet[cellAddress]) {
        worksheet[cellAddress].s = {
          font: { bold: true, color: { rgb: "FFFFFF" } },
          fill: { fgColor: { rgb: "4F46E5" } },
          alignment: { horizontal: "center" },
          border: {
            top: { style: "thin", color: { rgb: "000000" } },
            bottom: { style: "thin", color: { rgb: "000000" } },
            left: { style: "thin", color: { rgb: "000000" } },
            right: { style: "thin", color: { rgb: "000000" } }
          }
        }
      }
    }
    
    // Adicionar worksheet ao workbook
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Relatórios')
    
    // Salvar o arquivo
    const nomeArquivo = `relatorios_tickets_${agora.toISOString().split('T')[0]}.xlsx`
    XLSX.writeFile(workbook, nomeArquivo)
    
    console.log('Excel de relatórios exportado com sucesso!')
    
  } catch (error) {
    console.error('Erro ao exportar Excel:', error)
    alert('Erro ao gerar o arquivo Excel. Tente novamente.')
  }
}

// Infinite scroll
const relatoriosVisiveis = ref(10)
const relatorioSentinel = ref<HTMLElement | null>(null)
let relatorioObserver: IntersectionObserver | null = null

function setupInfiniteScroll() {
  if (relatorioObserver) {
    relatorioObserver.disconnect()
    relatorioObserver = null
  }
  if (relatorioSentinel.value && relatoriosFiltrados.value.length > 10) {
    relatorioObserver = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) {
        if (relatoriosVisiveis.value < relatoriosFiltrados.value.length) {
          relatoriosVisiveis.value += 10
        }
      }
    })
    relatorioObserver.observe(relatorioSentinel.value)
  }
}

onMounted(() => {
  fetchRelatorios()
  nextTick(() => setupInfiniteScroll())
})

watch(
  () => relatoriosFiltrados.value.length,
  () => nextTick(() => setupInfiniteScroll())
)
</script>

<style scoped>
/* Estilizar o ícone do calendário para ficar branco */
.date-input-white-icon::-webkit-calendar-picker-indicator {
  filter: invert(1);
  cursor: pointer;
}

/* Para Firefox */
.date-input-white-icon::-moz-calendar-picker-indicator {
  filter: invert(1);
  cursor: pointer;
}

/* Para Edge/IE */
.date-input-white-icon::-ms-calendar-picker-indicator {
  filter: invert(1);
  cursor: pointer;
}
</style>

