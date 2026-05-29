import type { Categoria, Produto, Complemento, SaborPizza, CardapioState } from '../../shared/types/cardapio.types'

export const useCardapio = () => {
  // Estado global do cardápio
  const cardapioState = useState<CardapioState>('cardapio', () => ({
    categorias: [
      {
        id: '1',
        nome: 'Pizzas',
        descricao: 'Nossas deliciosas pizzas artesanais',
        ordem: 1,
        ativa: true,
        icone: 'pizza-slice'
      },
      {
        id: '2',
        nome: 'Lanches',
        descricao: 'Hambúrguers e sanduíches gourmet',
        ordem: 2,
        ativa: true,
        icone: 'hamburger'
      },
      {
        id: '3',
        nome: 'Bebidas',
        descricao: 'Sucos, refrigerantes e bebidas especiais',
        ordem: 3,
        ativa: true,
        icone: 'glass-water'
      },
      {
        id: '4',
        nome: 'Sobremesas',
        descricao: 'Doces e sobremesas irresistíveis',
        ordem: 4,
        ativa: true,
        icone: 'ice-cream'
      }
    ],
    produtos: [
      {
        id: '1',
        nome: 'Pizza Margherita',
        preco: 32.90,
        descricao: 'Pizza clássica com molho de tomate, mussarela e manjericão fresco',
        foto: '/images/pizza-margherita.jpg',
        categoriaId: '1',
        ativo: true,
        tipo: 'pizza',
        complementos: ['1', '2', '3'],
        sabores: [
          {
            nome: 'Margherita',
            preco: 32.90,
            ingredientes: ['Molho de tomate', 'Mussarela', 'Manjericão']
          }
        ],
        tamanhos: [
          { nome: 'Pequena', multiplicador: 1.0 },
          { nome: 'Média', multiplicador: 1.3 },
          { nome: 'Grande', multiplicador: 1.6 }
        ]
      },
      {
        id: '2',
        nome: 'Pizza Calabresa',
        preco: 35.90,
        descricao: 'Pizza tradicional com calabresa, cebola e azeitonas',
        foto: '/images/pizza-calabresa.jpg',
        categoriaId: '1',
        ativo: true,
        tipo: 'pizza',
        complementos: ['1', '2', '3'],
        sabores: [
          {
            nome: 'Calabresa',
            preco: 35.90,
            ingredientes: ['Molho de tomate', 'Mussarela', 'Calabresa', 'Cebola', 'Azeitonas']
          }
        ],
        tamanhos: [
          { nome: 'Pequena', multiplicador: 1.0 },
          { nome: 'Média', multiplicador: 1.3 },
          { nome: 'Grande', multiplicador: 1.6 }
        ]
      },
      {
        id: '3',
        nome: 'Hambúrguer Artesanal',
        preco: 24.50,
        descricao: 'Pão brioche, hambúrguer 180g, queijo, alface, tomate e molho especial',
        foto: '/images/hamburger.jpg',
        categoriaId: '2',
        ativo: true,
        tipo: 'comum',
        complementos: ['4', '5', '6']
      },
      {
        id: '4',
        nome: 'Suco Natural',
        preco: 8.90,
        descricao: 'Suco natural de frutas frescas',
        foto: '/images/suco.jpg',
        categoriaId: '3',
        ativo: true,
        tipo: 'comum',
        complementos: ['7']
      }
    ],
    complementos: [
      {
        id: '1',
        nome: 'Borda Catupiry',
        preco: 5.00,
        descricao: 'Borda recheada com delicioso catupiry',
        obrigatorio: false,
        categoria: 'Bordas',
        disponivel: true
      },
      {
        id: '2',
        nome: 'Borda Cheddar',
        preco: 6.00,
        descricao: 'Borda recheada com queijo cheddar cremoso',
        obrigatorio: false,
        categoria: 'Bordas',
        disponivel: true
      },
      {
        id: '3',
        nome: 'Refrigerante Lata',
        preco: 4.50,
        descricao: 'Coca-Cola, Pepsi, Guaraná ou Fanta 350ml',
        obrigatorio: false,
        categoria: 'Bebidas',
        disponivel: true
      },
      {
        id: '4',
        nome: 'Batata Frita',
        preco: 8.00,
        descricao: 'Porção individual de batata frita crocante',
        obrigatorio: false,
        categoria: 'Acompanhamentos',
        disponivel: true
      },
      {
        id: '5',
        nome: 'Bacon Extra',
        preco: 4.00,
        descricao: 'Porção adicional de bacon crocante',
        obrigatorio: false,
        categoria: 'Adicionais',
        disponivel: true
      },
      {
        id: '6',
        nome: 'Queijo Extra',
        preco: 3.00,
        descricao: 'Porção adicional de queijo mussarela',
        obrigatorio: false,
        categoria: 'Adicionais',
        disponivel: true
      },
      {
        id: '7',
        nome: 'Gelo',
        preco: 0.00,
        obrigatorio: false,
        categoria: 'Opcionais',
        disponivel: true
      }
    ],
    carrinho: []
  }))

  // Getters
  const categorias = computed(() => cardapioState.value.categorias.filter(c => c.ativa).sort((a, b) => a.ordem - b.ordem))
  const produtos = computed(() => cardapioState.value.produtos.filter(p => p.ativo))
  const complementos = computed(() => cardapioState.value.complementos.filter(c => c.disponivel))

  // Funções para categorias
  const adicionarCategoria = (categoria: Omit<Categoria, 'id'>) => {
    const novaCategoria: Categoria = {
      ...categoria,
      id: Date.now().toString()
    }
    cardapioState.value.categorias.push(novaCategoria)
  }

  const editarCategoria = (id: string, dados: Partial<Omit<Categoria, 'id'>>) => {
    const categoria = cardapioState.value.categorias.find(c => c.id === id)
    if (categoria) {
      Object.assign(categoria, dados)
    }
  }

  const removerCategoria = (id: string) => {
    const categoria = cardapioState.value.categorias.find(c => c.id === id)
    if (categoria) {
      categoria.ativa = false
    }
  }

  // Funções para produtos
  const adicionarProduto = (produto: Omit<Produto, 'id'>) => {
    const novoProduto: Produto = {
      ...produto,
      id: Date.now().toString()
    }
    cardapioState.value.produtos.push(novoProduto)
  }

  const editarProduto = (id: string, dados: Partial<Omit<Produto, 'id'>>) => {
    const produto = cardapioState.value.produtos.find(p => p.id === id)
    if (produto) {
      Object.assign(produto, dados)
    }
  }

  const removerProduto = (id: string) => {
    const produto = cardapioState.value.produtos.find(p => p.id === id)
    if (produto) {
      produto.ativo = false
    }
  }

  // Funções para complementos
  const adicionarComplemento = (complemento: Omit<Complemento, 'id'>) => {
    const novoComplemento: Complemento = {
      ...complemento,
      id: Date.now().toString()
    }
    cardapioState.value.complementos.push(novoComplemento)
  }

  const editarComplemento = (id: string, dados: Partial<Omit<Complemento, 'id'>>) => {
    const complemento = cardapioState.value.complementos.find(c => c.id === id)
    if (complemento) {
      Object.assign(complemento, dados)
    }
  }

  const removerComplemento = (id: string) => {
    const complemento = cardapioState.value.complementos.find(c => c.id === id)
    if (complemento) {
      complemento.disponivel = false
    }
  }

  // Funções para busca e filtros
  const produtosPorCategoria = (categoriaId: string) => {
    return produtos.value.filter(p => p.categoriaId === categoriaId)
  }

  const buscarProdutos = (termo: string) => {
    return produtos.value.filter(p => 
      p.nome.toLowerCase().includes(termo.toLowerCase()) ||
      p.descricao.toLowerCase().includes(termo.toLowerCase())
    )
  }

  const complementosPorCategoria = (categoria: string) => {
    return complementos.value.filter(c => c.categoria === categoria)
  }

  const complementosDoProduto = (produtoId: string) => {
    const produto = produtos.value.find(p => p.id === produtoId)
    if (!produto || !produto.complementos) return []
    
    return complementos.value.filter(c => produto.complementos!.includes(c.id))
  }

  // Função especial para calcular preço de pizza
  const calcularPrecoPizza = (sabores: SaborPizza[], tamanho?: string) => {
    if (sabores.length === 0) return 0
    
    // Para pizzas, sempre o maior valor entre os sabores
    const maiorPreco = Math.max(...sabores.map(s => s.preco))
    
    // Aplicar multiplicador do tamanho se especificado
    if (tamanho) {
      const produto = produtos.value.find(p => p.tipo === 'pizza' && p.tamanhos)
      if (produto?.tamanhos) {
        const tamanhoData = produto.tamanhos.find(t => t.nome === tamanho)
        if (tamanhoData) {
          return maiorPreco * tamanhoData.multiplicador
        }
      }
    }
    
    return maiorPreco
  }

  return {
    // Estado
    categorias,
    produtos,
    complementos,
    carrinho: computed(() => cardapioState.value.carrinho),
    
    // Funções de categoria
    adicionarCategoria,
    editarCategoria,
    removerCategoria,
    
    // Funções de produto
    adicionarProduto,
    editarProduto,
    removerProduto,
    
    // Funções de complemento
    adicionarComplemento,
    editarComplemento,
    removerComplemento,
    
    // Funções de busca
    produtosPorCategoria,
    buscarProdutos,
    complementosPorCategoria,
    complementosDoProduto,
    
    // Funções especiais
    calcularPrecoPizza
  }
}
