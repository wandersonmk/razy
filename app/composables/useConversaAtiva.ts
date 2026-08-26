// Conversa aberta na tela agora — estado compartilhado entre a página de
// Conversas e o Analista de Atendimento (que vive no layout e não enxerga o
// componente da lista).
//
// Existe porque a pergunta quase sempre nasce olhando uma conversa: o dono abre
// o atendimento da Karyne e clica no analista querendo saber daquele cliente,
// não de um telefone genérico. Sem isto, o painel abria sugerindo um número que
// não tinha nada a ver com o que estava na tela.
//
// `useState` com a mesma chave devolve a MESMA ref em qualquer componente,
// mesmo padrão do useSidebar.

export interface ConversaAtiva {
  id: string
  numero: string
  nome: string | null
  vendedor: string | null
}

export function useConversaAtiva() {
  const conversaAtiva = useState<ConversaAtiva | null>('conversa_ativa', () => null)

  function definir(c: ConversaAtiva | null) {
    conversaAtiva.value = c
  }

  function limpar() {
    conversaAtiva.value = null
  }

  return { conversaAtiva, definir, limpar }
}

/** Telefone em formato legível: 5511989444136 → +55 11 98944-4136 */
export function formatarTelefoneBR(numero: string | null | undefined): string {
  const d = (numero || '').replace(/\D/g, '')
  if (!d) return ''
  const nac = d.startsWith('55') && d.length >= 12 ? d.slice(2) : d
  const ddd = nac.slice(0, 2)
  const resto = nac.slice(2)
  if (resto.length === 9) return `+55 ${ddd} ${resto.slice(0, 5)}-${resto.slice(5)}`
  if (resto.length === 8) return `+55 ${ddd} ${resto.slice(0, 4)}-${resto.slice(4)}`
  return `+55 ${ddd} ${resto}`
}
