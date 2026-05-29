<template>
  <div 
    class="bg-background border border-border rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer hover:border-primary/50"
    @click="$emit('view', pedido)"
  >
    <!-- Header compacto -->
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="font-bold text-foreground">#{{ pedido.numero }}</span>
        <span :class="[
          'px-1.5 py-0.5 text-xs font-medium rounded-full',
          getStatusColor(pedido.status)
        ]">
          {{ getStatusLabel(pedido.status) }}
        </span>
      </div>
      <div class="flex items-center gap-1">
        <button
          @click.stop="$emit('print', pedido)"
          class="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
          title="Imprimir pedido"
        >
          <Icon icon="print" class-name="w-3 h-3" fallback="" />
        </button>
      </div>
    </div>

    <!-- Informações essenciais -->
    <div class="mb-2">
      <p class="font-medium text-foreground text-sm">{{ pedido.cliente }}</p>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1">
          <span :class="[
            'px-1.5 py-0.5 text-xs rounded-full',
            pedido.tipoEntrega === 'entrega' 
              ? 'bg-blue-100 text-blue-700' 
              : 'bg-gray-100 text-gray-700'
          ]">
            {{ pedido.tipoEntrega === 'entrega' ? 'Entrega' : 'Retirada' }}
          </span>
          <span :class="[
            'px-1.5 py-0.5 text-xs rounded-full',
            getPaymentColor(pedido.formaPagamento)
          ]">
            {{ getPaymentLabel(pedido.formaPagamento) }}
          </span>
        </div>
        <span class="text-xs text-muted-foreground">{{ getTimeAgo(pedido.dataHora) }}</span>
      </div>
    </div>

    <!-- Resumo dos itens (apenas quantidade) -->
    <div class="mb-2">
      <div class="text-xs text-muted-foreground">
        {{ pedido.items.length }} {{ pedido.items.length === 1 ? 'item' : 'itens' }}
        • R$ {{ pedido.total.toFixed(2) }}
      </div>
    </div>

    <!-- Ações baseadas no status -->
    <div class="flex gap-1.5">
      <template v-if="pedido.status === 'novo'">
        <button
          @click.stop="$emit('accept', pedido.id)"
          class="flex-1 bg-green-600 hover:bg-green-700 text-white px-2 py-1.5 rounded text-xs font-medium transition-colors"
        >
          <Icon icon="check" class-name="w-3 h-3 mr-1" fallback="" />
          Aceitar
        </button>
      </template>
      
      <template v-else-if="pedido.status === 'cozinha'">
        <button
          @click.stop="$emit('ready', pedido.id)"
          class="flex-1 bg-orange-600 hover:bg-orange-700 text-white px-2 py-1.5 rounded text-xs font-medium transition-colors"
        >
          <Icon icon="utensils" class-name="w-3 h-3 mr-1" fallback="" />
          Pronto
        </button>
      </template>
      
      <template v-else-if="pedido.status === 'entrega'">
        <button
          @click.stop="$emit('complete', pedido.id)"
          class="flex-1 bg-purple-600 hover:bg-purple-700 text-white px-2 py-1.5 rounded text-xs font-medium transition-colors"
        >
          <Icon icon="check-circle" class-name="w-3 h-3 mr-1" fallback="" />
          Concluir
        </button>
      </template>

      <template v-else-if="pedido.status === 'concluido'">
        <div class="flex-1 bg-green-100 text-green-700 px-2 py-1.5 rounded text-xs font-medium text-center">
          <Icon icon="check-circle" class-name="w-3 h-3 mr-1" fallback="" />
          Concluído
        </div>
      </template>
    </div>

    <!-- Observação importante se houver -->
    <div v-if="pedido.observacao" class="mt-2 p-1.5 bg-yellow-50 border-l-2 border-yellow-400 rounded text-xs">
      <span class="font-medium text-yellow-800">Obs:</span> 
      <span class="text-yellow-700">{{ pedido.observacao.length > 40 ? pedido.observacao.substring(0, 40) + '...' : pedido.observacao }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface PedidoItem {
  nome: string
  quantidade: number
  preco: number
  observacao?: string
}

interface Pedido {
  id: string
  numero: number
  cliente: string
  telefone: string
  endereco?: string
  items: PedidoItem[]
  total: number
  formaPagamento: 'dinheiro' | 'cartao' | 'pix'
  tipoEntrega: 'retirada' | 'entrega'
  status: 'novo' | 'cozinha' | 'entrega' | 'concluido'
  observacao?: string
  troco?: number
  dataHora: Date
  tempoEstimado?: number
}

interface Props {
  pedido: Pedido
}

defineProps<Props>()

defineEmits<{
  view: [pedido: Pedido]
  accept: [pedidoId: string]
  ready: [pedidoId: string]
  complete: [pedidoId: string]
  print: [pedido: Pedido]
}>()

const getStatusLabel = (status: string) => {
  const labels = {
    novo: 'Novo',
    cozinha: 'Cozinha',
    entrega: 'Entrega',
    concluido: 'Concluído'
  }
  return labels[status as keyof typeof labels] || status
}

const getStatusColor = (status: string) => {
  const colors = {
    novo: 'bg-blue-100 text-blue-700',
    cozinha: 'bg-orange-100 text-orange-700',
    entrega: 'bg-purple-100 text-purple-700',
    concluido: 'bg-green-100 text-green-700'
  }
  return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-700'
}

const getPaymentLabel = (payment: string) => {
  const labels = {
    dinheiro: 'Dinheiro',
    cartao: 'Cartão',
    pix: 'PIX'
  }
  return labels[payment as keyof typeof labels] || payment
}

const getPaymentColor = (payment: string) => {
  const colors = {
    dinheiro: 'bg-green-100 text-green-700',
    cartao: 'bg-purple-100 text-purple-700',
    pix: 'bg-orange-100 text-orange-700'
  }
  return colors[payment as keyof typeof colors] || 'bg-gray-100 text-gray-700'
}

const getTimeAgo = (date: Date) => {
  const now = new Date()
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
  
  if (diffInMinutes < 1) return 'Agora'
  if (diffInMinutes < 60) return `${diffInMinutes}min atrás`
  
  const diffInHours = Math.floor(diffInMinutes / 60)
  return `${diffInHours}h atrás`
}
</script>

