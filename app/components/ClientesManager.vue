<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header com título e botões de exportação -->
    <div class="flex items-center justify-between p-6 border-b border-border">
      <div>
        <h2 class="text-xl font-semibold text-foreground">Clientes</h2>
        <p class="text-sm text-muted-foreground mt-1">Contatos que responderam aos seus disparos</p>
        <p v-if="clientes && clientes.length > 0" class="text-xs text-muted-foreground mt-1">
          Total de clientes: <span class="font-semibold text-primary">{{ clientes.length }}</span>
        </p>
      </div>
      
      <!-- Botões de exportação -->
      <div class="flex items-center space-x-2">
        <button
          @click="atualizar"
          :disabled="isLoading"
          class="flex items-center space-x-2 px-4 py-2 border border-border hover:bg-muted disabled:opacity-50 text-foreground rounded-lg transition-colors text-sm font-medium"
          title="Atualizar lista e pausas"
        >
          <svg :class="['w-4 h-4', isLoading ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          <span>Atualizar</span>
        </button>
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
    <div class="px-6 py-4 border-b border-border bg-muted/30">
      <div class="flex flex-wrap items-end gap-3">
        <!-- Filtro por campanha -->
        <div class="flex flex-col gap-1 min-w-[200px]">
          <label class="text-xs font-medium text-muted-foreground">Campanha</label>
          <select
            v-model="filtroCampanha"
            class="text-sm border border-border rounded-lg px-3 py-1.5 bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            <option value="">Todas as campanhas</option>
            <option v-for="c in campanhas" :key="c.id" :value="c.id">{{ c.nome }}</option>
          </select>
        </div>

        <!-- Filtro por data início -->
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-muted-foreground">De</label>
          <input
            v-model="filtroDataInicio"
            type="date"
            class="text-sm border border-border rounded-lg px-3 py-1.5 bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        <!-- Filtro por data fim -->
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-muted-foreground">Até</label>
          <input
            v-model="filtroDataFim"
            type="date"
            class="text-sm border border-border rounded-lg px-3 py-1.5 bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        <!-- Botões -->
        <div class="flex items-end gap-2">
          <button
            @click="aplicarFiltros"
            class="px-4 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
          >
            Filtrar
          </button>
          <button
            v-if="temFiltroAtivo"
            @click="limparFiltros"
            class="px-4 py-1.5 text-sm font-medium border border-border rounded-lg text-foreground hover:bg-muted transition"
          >
            Limpar
          </button>
        </div>
      </div>
    </div>

      <!-- Lista de clientes -->
    <div class="p-6">
      <!-- Loading state -->
      <div v-if="isLoading" class="text-center py-8">
        <div class="flex flex-col items-center">
          <div class="w-12 h-12 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
            <svg class="w-6 h-6 text-muted-foreground animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </div>
          <h3 class="text-lg font-medium text-foreground mb-2">Carregando clientes...</h3>
          <p class="text-muted-foreground">Aguarde um momento</p>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="text-center py-8">
        <div class="flex flex-col items-center">
          <Icon icon="exclamation-triangle" class-name="w-12 h-12 text-red-500 mb-4" fallback="" />
          <h3 class="text-lg font-medium text-foreground mb-2">Erro ao carregar clientes</h3>
          <p class="text-muted-foreground mb-4">{{ error }}</p>
          <button
            @click="recarregarClientes"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      </div>

      <!-- Mensagem quando não há clientes -->
      <div v-else-if="clientes.length === 0" class="text-center py-8">
        <div class="flex flex-col items-center">
          <Icon icon="users" class-name="w-12 h-12 text-muted-foreground/50 mb-4" fallback="" />
          <h3 class="text-lg font-medium text-foreground mb-2">Nenhum cliente ainda</h3>
          <p class="text-muted-foreground">Quando um contato responder a um disparo, ele aparece aqui.</p>
        </div>
      </div>

      <!-- Tabela de clientes -->
      <div v-else class="overflow-x-auto">
  <div style="max-height: 600px; overflow-y: auto;">
          <table class="w-full">
            <thead>
              <tr class="border-b border-border">
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Nome</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Telefone</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Resposta</th>
                <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Campanha</th>
                <th class="text-right py-2 px-3 font-medium text-muted-foreground text-xs">Ações</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="cliente in (clientesOrdenados ? clientesOrdenados.slice(0, clientesVisiveis) : [])" 
                :key="cliente.id"
                class="border-b border-border/50 hover:bg-muted/30 transition-colors"
              >
                <!-- Nome do cliente -->
                <td class="py-3 px-3">
                  <div class="flex items-center gap-2">
                    <div class="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                      <Icon icon="user" class-name="w-3 h-3 text-primary" fallback="" />
                    </div>
                    <span class="font-medium text-foreground text-sm">{{ cliente.nome }}</span>
                    <span
                      v-if="cliente.pausado_segundos"
                      class="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 whitespace-nowrap"
                      title="Atendimento da IA pausado — você assumiu a conversa"
                    >
                      <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M5 4h3v12H5V4zm7 0h3v12h-3V4z"/></svg>
                      Pausado · {{ formatarPausa(cliente.pausado_segundos) }}
                    </span>
                  </div>
                </td>
                
                <!-- Telefone do cliente -->
                <td class="py-3 px-3">
                  <span class="text-foreground text-sm">{{ cliente.telefone }}</span>
                </td>
                
                <!-- Resposta do cliente -->
                <td class="py-3 px-3 max-w-xs">
                  <span
                    v-if="cliente.resposta_texto"
                    class="text-foreground text-sm italic truncate block"
                    :title="cliente.resposta_texto"
                  >
                    "{{ cliente.resposta_texto }}"
                  </span>
                  <span v-else class="text-muted-foreground text-sm">—</span>
                </td>

                <!-- Campanha -->
                <td class="py-3 px-3">
                  <span class="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary font-medium whitespace-nowrap">
                    {{ cliente.campanha_nome || '—' }}
                  </span>
                </td>

                <!-- Botões de ação -->
                <td class="py-3 px-3 text-right">
                  <div class="flex items-center justify-end space-x-2">
                    <!-- Botão WhatsApp -->
                    <button
                      @click="abrirWhatsApp(cliente)"
                      class="p-2 text-green-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-all duration-200 group"
                      title="Conversar no WhatsApp"
                    >
                      <Icon icon="comments" class-name="w-4 h-4 group-hover:scale-110 transition-transform duration-200" fallback="" />
                    </button>
                    
                    <!-- Botão de excluir -->
                    <button
                      @click="confirmarExclusao(cliente)"
                      class="p-2 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200 group"
                      title="Excluir cliente"
                    >
                      <Icon icon="trash" class-name="w-4 h-4 group-hover:scale-110 transition-transform duration-200" fallback="" />
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Sentinel para infinite scroll -->
              <tr v-if="clientes && clientesVisiveis < clientes.length">
                <td :colspan="5">
                  <div ref="sentinel" style="height: 1px;"></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Modal de confirmação de exclusão -->
    <div 
      v-if="clienteParaExcluir"
      class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
    >
      <div class="bg-card rounded-lg shadow-xl max-w-md w-full p-6 border border-border">
        <div class="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 dark:bg-red-900/20 rounded-full">
          <Icon icon="exclamation-triangle" class-name="w-6 h-6 text-red-600" fallback="" />
        </div>
        
        <h3 class="text-lg font-semibold text-foreground text-center mb-2">
          Confirmar exclusão
        </h3>
        
        <p class="text-muted-foreground text-center mb-6">
          Tem certeza que deseja excluir o cliente 
          <strong class="text-foreground">{{ clienteParaExcluir.nome }}</strong>?
          <br>
          Esta ação não pode ser desfeita.
        </p>
        
        <div class="flex space-x-3">
          <button
            @click="cancelarExclusao"
            class="flex-1 px-4 py-2 border border-border rounded-lg text-foreground hover:bg-muted transition-colors"
          >
            Cancelar
          </button>
          <button
            @click="excluirCliente"
            class="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Excluir
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useCampanhas } from '~/composables/useCampanhas'

// Usar o composable de clientes
const {
  clientes,
  isLoading,
  error,
  fetchClientes,
  deleteCliente,
  clearError
} = useClientes()

// Campanhas disponíveis para o filtro
const { campanhas, fetchCampanhas } = useCampanhas()

// Filtros
const filtroCampanha = ref('')
const filtroDataInicio = ref('')
const filtroDataFim = ref('')

function aplicarFiltros() {
  fetchClientes({
    campanha_id: filtroCampanha.value || undefined,
    data_inicio: filtroDataInicio.value || undefined,
    data_fim: filtroDataFim.value || undefined,
  })
}

function limparFiltros() {
  filtroCampanha.value = ''
  filtroDataInicio.value = ''
  filtroDataFim.value = ''
  fetchClientes()
}

const temFiltroAtivo = computed(() =>
  !!(filtroCampanha.value || filtroDataInicio.value || filtroDataFim.value)
)

// Estado para modal de confirmação de exclusão
const clienteParaExcluir = ref<any>(null)

// Infinite scroll
const clientesVisiveis = ref(10)
const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

onMounted(() => {
  fetchClientes()
  fetchCampanhas()
})

watch(
  () => clientes.value?.length,
  () => {
    if (sentinel.value && clientes.value && clientes.value.length > 10) {
      if (!observer) {
        observer = new IntersectionObserver((entries) => {
          const entry = entries[0]
          if (entry && entry.isIntersecting) {
            if (clientesVisiveis.value < clientes.value.length) {
              clientesVisiveis.value += 10
            }
          }
        })
        observer.observe(sentinel.value)
      }
    }
  }
)

// Função para recarregar clientes
const recarregarClientes = () => {
  clearError()
  fetchClientes()
}

// Botão atualizar (recarrega lista + pausas respeitando filtros ativos)
function atualizar() {
  fetchClientes({
    campanha_id: filtroCampanha.value || undefined,
    data_inicio: filtroDataInicio.value || undefined,
    data_fim: filtroDataFim.value || undefined,
  })
}

// Formata o tempo de pausa restante (segundos → "Xmin" ou "Xh Ymin")
function formatarPausa(seg: number): string {
  const min = Math.ceil(seg / 60)
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h}h ${m}min` : `${h}h`
}

// Função para confirmar exclusão
const confirmarExclusao = (cliente: any) => {
  clienteParaExcluir.value = cliente
}

// Função para cancelar exclusão
const cancelarExclusao = () => {
  clienteParaExcluir.value = null
}

// Função para excluir cliente
const excluirCliente = async () => {
  if (clienteParaExcluir.value) {
    await deleteCliente(clienteParaExcluir.value.id)
    clienteParaExcluir.value = null
    await fetchClientes() // Recarregar lista
  }
}

// Função para abrir WhatsApp
const abrirWhatsApp = (cliente: any) => {
  const numeroLimpo = cliente.telefone.replace(/\D/g, '')
  const url = `https://wa.me/55${numeroLimpo}`
  window.open(url, '_blank')
}

// Função para exportar para PDF
const exportToPDF = async () => {
  try {
    const { jsPDF } = await import('jspdf')
    const doc = new jsPDF({ orientation: 'landscape' })

    // Header com fundo roxo — largura landscape = 297mm
    doc.setFillColor(102, 90, 228)
    doc.rect(0, 0, 297, 45, 'F')

    // Título principal
    doc.setTextColor(255, 255, 255) // Texto branco
    doc.setFontSize(24)
    doc.setFont('helvetica', 'bold')
    doc.text('Razy', 20, 20)

    // Subtítulo
    doc.setFontSize(14)
    doc.setFont('helvetica', 'normal')
    doc.text('Sistema de disparo', 20, 35)

    // Resetar cor do texto para preto
    doc.setTextColor(0, 0, 0)

    // Título da seção
    doc.setFontSize(18)
    doc.setFont('helvetica', 'bold')
    doc.text('Lista de Clientes', 20, 65)

    // Informações de geração
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    const agora = new Date()
    const dataFormatada = agora.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
    const horaFormatada = agora.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    })
    doc.text(`Gerado em: ${dataFormatada}, ${horaFormatada}`, 20, 75)
    doc.text(`Total de clientes: ${clientes.value.length}`, 20, 85)

    // Cabeçalho da tabela com fundo roxo — landscape: margem 20, largura útil 257mm
    // Colunas: # (20), Nome (35), Telefone (105), Resposta (165)
    let yPosition = 100
    doc.setFillColor(102, 90, 228)
    doc.rect(20, yPosition - 10, 257, 15, 'F')

    doc.setTextColor(255, 255, 255)
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('#', 25, yPosition - 2)
    doc.text('Nome', 40, yPosition - 2)
    doc.text('Telefone', 105, yPosition - 2)
    doc.text('Resposta', 165, yPosition - 2)

    doc.setTextColor(0, 0, 0)
    yPosition += 10

    // Dados dos clientes — landscape altura útil ~190mm
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    clientes.value.forEach((cliente, index) => {
      if (yPosition > 185) {
        doc.addPage()
        yPosition = 20

        doc.setFillColor(102, 90, 228)
        doc.rect(20, yPosition - 10, 257, 15, 'F')
        doc.setTextColor(255, 255, 255)
        doc.setFontSize(12)
        doc.setFont('helvetica', 'bold')
        doc.text('#', 25, yPosition - 2)
        doc.text('Nome', 40, yPosition - 2)
        doc.text('Telefone', 105, yPosition - 2)
        doc.text('Resposta', 165, yPosition - 2)
        doc.setTextColor(0, 0, 0)
        doc.setFontSize(10)
        doc.setFont('helvetica', 'normal')
        yPosition += 10
      }

      if (index % 2 === 0) {
        doc.setFillColor(249, 250, 251)
        doc.rect(20, yPosition - 8, 257, 12, 'F')
      }

      // Resposta pode ser longa — trunca em 80 chars para caber na coluna
      const respostaTruncada = (cliente.resposta_texto || '—').substring(0, 80)
      doc.text((index + 1).toString(), 25, yPosition)
      doc.text(cliente.nome, 40, yPosition)
      doc.text(cliente.telefone, 105, yPosition)
      doc.text(respostaTruncada, 165, yPosition)
      
      yPosition += 12
    })

    // Salvar o PDF
    doc.save('lista-clientes.pdf')
  } catch (error) {
    console.error('Erro ao exportar PDF:', error)
    alert('Erro ao exportar PDF. Tente novamente.')
  }
}

// Função para exportar para Excel
const exportToExcel = async () => {
  try {
    const XLSX = await import('xlsx')

    // Criar dados do cabeçalho
    const agora = new Date()
    const dataFormatada = agora.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
    const horaFormatada = agora.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    })

    // Preparar dados com todas as colunas conforme a imagem
    const dadosExcel = [
      // Cabeçalho do sistema
      ['Razy - Sistema de disparo'],
      ['Relatórios de Clientes'],
      [`Gerado em: ${dataFormatada}, ${horaFormatada}`],
      [`Total de registros: ${clientes.value.length}`],
      [], // Linha vazia
      // Cabeçalho da tabela
      ['#', 'Nome', 'Telefone', 'Resposta', 'Data da Resposta']
    ]

    // Adicionar dados dos clientes
    clientes.value.forEach((cliente, index) => {
      dadosExcel.push([
        (index + 1).toString(),
        cliente.nome,
        cliente.telefone,
        cliente.resposta_texto || '—',
        new Date(cliente.created_at).toLocaleString('pt-BR')
      ])
    })

    // Criar workbook e worksheet
    const workbook = XLSX.utils.book_new()
    const worksheet = XLSX.utils.aoa_to_sheet(dadosExcel)

    // Definir larguras das colunas
    const columnWidths = [
      { wch: 5 },  // #
      { wch: 20 }, // Nome
      { wch: 15 }, // Telefone
      { wch: 50 }, // Resposta
      { wch: 20 }  // Data da Resposta
    ]
    worksheet['!cols'] = columnWidths

    // Estilizar cabeçalho (se suportado)
    const headerRange = XLSX.utils.decode_range(worksheet['!ref'] || 'A1')
    
    // Mesclar células do título principal
    worksheet['!merges'] = [
      { s: { r: 0, c: 0 }, e: { r: 0, c: 4 } }, // Razy - Sistema de disparo
      { s: { r: 1, c: 0 }, e: { r: 1, c: 4 } }, // Relatórios de Clientes
      { s: { r: 2, c: 0 }, e: { r: 2, c: 4 } }, // Gerado em
      { s: { r: 3, c: 0 }, e: { r: 3, c: 4 } }  // Total de registros
    ]

    // Adicionar worksheet ao workbook
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Relatórios de Clientes')

    // Salvar arquivo
    XLSX.writeFile(workbook, 'relatorios-clientes.xlsx')
  } catch (error) {
    console.error('Erro ao exportar Excel:', error)
    alert('Erro ao exportar Excel. Tente novamente.')
  }
}

// Computed para clientes ordenados por nome (A-Z)
import { computed } from 'vue'
const clientesOrdenados = computed(() => {
  return clientes.value ? [...clientes.value].sort((a, b) => {
    if (!a.nome || !b.nome) return 0
    return a.nome.localeCompare(b.nome, 'pt-BR', { sensitivity: 'base' })
  }) : []
})
</script>

