<template>
  <div class="max-w-7xl mx-auto">
    <!-- Cards de métricas -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <!-- Card Pedidos Hoje -->
      <div class="relative bg-gradient-to-br from-card via-blue-950/10 to-card text-card-foreground rounded-lg border border-blue-800/20 shadow-sm hover:shadow-md hover:shadow-blue-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <!-- Efeito de brilho sutil -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-400 mb-1">Pedidos Hoje</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.pedidosHoje }}</p>
            <p class="text-xs text-green-600 mt-1">+8% desde ontem</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg">
            <Icon icon="shopping-cart" class-name="w-6 h-6 text-white" fallback="" />
          </div>
        </div>
      </div>

      <!-- Card Pedidos Pendentes -->
      <div class="relative bg-gradient-to-br from-card via-amber-950/10 to-card text-card-foreground rounded-lg border border-amber-800/20 shadow-sm hover:shadow-md hover:shadow-amber-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <!-- Efeito de brilho sutil -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-amber-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-400 mb-1">Pedidos Pendentes</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.pedidosPendentes }}</p>
            <p class="text-xs text-yellow-600 mt-1">aguardando processamento</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-amber-600 rounded-lg flex items-center justify-center shadow-lg">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Card Pedidos Concluídos -->
      <div class="relative bg-gradient-to-br from-card via-emerald-950/10 to-card text-card-foreground rounded-lg border border-emerald-800/20 shadow-sm hover:shadow-md hover:shadow-emerald-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <!-- Efeito de brilho sutil -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-emerald-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-400 mb-1">Pedidos Concluídos</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.pedidosConcluidos }}</p>
            <p class="text-xs text-green-600 mt-1">+15% esta semana</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center shadow-lg">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Card Valor Total -->
      <div class="relative bg-gradient-to-br from-card via-purple-950/10 to-card text-card-foreground rounded-lg border border-purple-800/20 shadow-sm hover:shadow-md hover:shadow-purple-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <!-- Efeito de brilho sutil -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-400 mb-1">Valor Total</p>
            <p class="text-2xl font-bold text-foreground">R$ {{ metrics.valorTotal.toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-green-600 mt-1">+22% este mês</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabela de Pedidos Recentes -->
    <div class="bg-card border border-border rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-foreground">Pedidos Recentes</h2>
        <button class="text-sm text-primary hover:text-primary/80 transition-colors">
          Ver todos
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-border">
              <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">ID</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Cliente</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Data</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pedido in pedidosRecentes" :key="pedido.id" class="border-b border-border hover:bg-muted/50 transition-colors">
              <td class="py-3 px-4 text-sm text-foreground">#{{ pedido.id }}</td>
              <td class="py-3 px-4 text-sm text-foreground">{{ pedido.cliente }}</td>
              <td class="py-3 px-4 text-sm text-muted-foreground">{{ pedido.data }}</td>
              <td class="py-3 px-4">
                <span 
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :class="getStatusClass(pedido.status)"
                >
                  {{ pedido.status }}
                </span>
              </td>
              <td class="py-3 px-4 text-sm font-medium text-foreground">R$ {{ pedido.valor.toLocaleString('pt-BR') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Métricas dos pedidos
const metrics = reactive({
  pedidosHoje: 12,
  pedidosPendentes: 8,
  pedidosConcluidos: 156,
  valorTotal: 48750
})

// Dados dos pedidos recentes
const pedidosRecentes = reactive([
  {
    id: '001',
    cliente: 'João Silva',
    data: '27/08/2025',
    status: 'Concluído',
    valor: 1250
  },
  {
    id: '002',
    cliente: 'Maria Santos',
    data: '27/08/2025',
    status: 'Pendente',
    valor: 890
  },
  {
    id: '003',
    cliente: 'Carlos Oliveira',
    data: '26/08/2025',
    status: 'Processando',
    valor: 2150
  },
  {
    id: '004',
    cliente: 'Ana Costa',
    data: '26/08/2025',
    status: 'Concluído',
    valor: 750
  },
  {
    id: '005',
    cliente: 'Pedro Lima',
    data: '25/08/2025',
    status: 'Concluído',
    valor: 1680
  }
])

// Função para retornar as classes CSS baseadas no status
const getStatusClass = (status: string) => {
  switch (status) {
    case 'Concluído':
      return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
    case 'Pendente':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
    case 'Processando':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
  }
}
</script>

