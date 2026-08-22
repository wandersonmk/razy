// Estado global (compartilhado entre AppSidebar e o layout) do menu lateral
// colapsado/expandido. useState com a mesma chave devolve a MESMA ref em
// qualquer componente — não precisa passar por prop.
const CHAVE_STORAGE = 'razy_sidebar_colapsado'

export function useSidebar() {
  const colapsado = useState<boolean>('sidebar_colapsado', () => false)

  function persistir() {
    if (!process.client) return
    try {
      localStorage.setItem(CHAVE_STORAGE, colapsado.value ? '1' : '0')
    } catch {
      // best-effort — não trava a navegação por causa disso
    }
  }

  function restaurar() {
    if (!process.client) return
    try {
      const salvo = localStorage.getItem(CHAVE_STORAGE)
      if (salvo !== null) colapsado.value = salvo === '1'
    } catch {
      // ignora
    }
  }

  function alternar() {
    colapsado.value = !colapsado.value
    persistir()
  }

  function colapsar() {
    if (colapsado.value) return
    colapsado.value = true
    persistir()
  }

  function expandir() {
    if (!colapsado.value) return
    colapsado.value = false
    persistir()
  }

  return { colapsado, alternar, colapsar, expandir, restaurar }
}
