// Tipos para o sistema de cardápio

export interface Categoria {
  id: string
  nome: string
  descricao?: string
  ordem: number
  ativa: boolean
  icone?: string
}

export interface Complemento {
  id: string
  nome: string
  preco: number
  descricao?: string
  obrigatorio: boolean
  categoria: string // categoria do complemento (ex: "Adicionais", "Bebidas", etc.)
  disponivel: boolean
}

export interface SaborPizza {
  nome: string
  preco: number
  ingredientes: string[]
}

export interface Produto {
  id: string
  nome: string
  preco: number
  descricao: string
  foto?: string
  categoriaId: string
  ativo: boolean
  complementos?: string[] // IDs dos complementos disponíveis
  tipo: 'comum' | 'pizza'
  // Para pizzas
  sabores?: SaborPizza[]
  tamanhos?: {
    nome: string
    multiplicador: number // 1.0 para pequena, 1.2 para média, 1.5 para grande
  }[]
}

export interface ItemCarrinho {
  produtoId: string
  produto: Produto
  quantidade: number
  complementosSelecionados: {
    complementoId: string
    complemento: Complemento
    quantidade: number
  }[]
  // Para pizzas
  saboresSelecionados?: SaborPizza[]
  tamanhoSelecionado?: string
  precoCalculado: number
  observacoes?: string
}

export interface CardapioState {
  categorias: Categoria[]
  produtos: Produto[]
  complementos: Complemento[]
  carrinho: ItemCarrinho[]
}
