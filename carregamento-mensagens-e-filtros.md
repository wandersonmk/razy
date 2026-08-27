# Carregamento de mensagens, conversas, clientes e filtros

> Documento de referência pra replicar (com correções) esse comportamento em
> outro app. Descreve como as páginas **Conversas** e **Clientes** carregam
> dados do Supabase/PostgREST e como os filtros funcionam — em especial o que
> acontece quando a base passa de 1.000 linhas.

---

## 0. O problema raiz: o corte de 1.000 linhas do PostgREST

O PostgREST (motor de API do Supabase) tem um limite padrão de **1.000 linhas
por resposta** (`max-rows`). Isso vale pra **qualquer** `.select()` que não
tenha `.range()`/`.limit()` explícito — e o pulo do gato é que **não dá erro
nenhum**: a query volta com sucesso (200), só que cortada nas primeiras 1.000
linhas (por ordem, geralmente a ordem natural da tabela, não a que você
espera). Em teste, com poucos registros, tudo parece perfeito. Em produção,
meses depois, uma empresa cresce, passa de 1.000 conversas/clientes/leads, e:

- a lista "esquece" os registros mais antigos;
- um filtro (etiqueta, atendente, período) que rode só sobre esse recorte
  "some" com resultados que existem, mas ficaram fora do corte;
- os contadores (badges de aba, "Selecionar todos") não batem com a tela.

Foi exatamente esse bug, em variações diferentes, que apareceu em Conversas
(atendente com 238 conversas via só 4), em Clientes (filtro de etiqueta
mostrando 1 de 63) e no Kanban do CRM. **Este documento existe pra esse bug
nunca mais precisar ser redescoberto.**

Duas estratégias diferentes são usadas neste app pra lidar com isso — a
escolha depende do tamanho esperado da tabela:

| Estratégia | Quando usar | Onde é usada aqui |
|---|---|---|
| **A. Paginar tudo pra memória** — loop de `.range()` até a página vir incompleta, guarda a base inteira no client | Tabela com volume limitado por natureza (centenas, não dezenas de milhares, por empresa) | Página **Clientes** |
| **B. Janela recente + busca/filtro sob demanda no servidor** — só as N linhas mais recentes ficam em memória; qualquer filtro/busca que possa alcançar fora dessa janela vai direto no banco (RPC) e mescla o resultado | Tabela que cresce sem teto (uma linha por mensagem trocada) | Página **Conversas** (lista) e mensagens de uma conversa |

---

## 1. Página de Conversas (`app/pages/conversas.vue`)

### 1.1 Lista de conversas (sidebar) — janela recente + scroll infinito

- **Carga inicial**: `fetchConversas()` monta a query (`montarQueryConversas`,
  linha ~8100) com os joins de `clientes`/`crm_leads`/`profissionais`,
  filtrada por `empresa_id` + instâncias permitidas, ordenada por
  `ultimo_horario desc`, e aplica `.limit(CONVERSAS_CARGA_INICIAL)` — **500**
  conversas (`app/pages/conversas.vue:8187`). A página abre rápido
  independente do tamanho da base, porque nunca carrega tudo de uma vez.
- **Contador real da aba "Todas"**: como a lista só tem as 500 mais recentes,
  o número da aba não pode vir de `conversas.value.length`. Uma query
  separada com `count: 'exact', head: true` (sem baixar linha nenhuma) traz o
  total real do servidor (`conversas.vue:8167-8183`).
- **Scroll infinito de DADOS** (não confundir com o de renderização, item
  1.6): `carregarMaisConversasServidor()` (`conversas.vue:8654`) busca o
  próximo lote por **cursor** — `ultimo_horario < últimoCarregado`,
  `.limit(CONVERSAS_POR_PAGINA_SERVIDOR)` (500) — nunca por `offset`. Cursor
  evita duplicar/pular linha quando chega mensagem nova no topo enquanto o
  usuário rola pra baixo. Disparado quando o scroll físico chega perto do fim
  do que **já foi carregado do banco** (não só do que está renderizado —
  pré-carregamento, ver 1.6).

### 1.2 Busca por texto — acha conversas fora da janela carregada

`buscarConversasNoServidor(termo)` (`conversas.vue:8737`): com 3+ caracteres
digitados (debounce 400ms), chama a RPC `buscar_conversas_ids` — que resolve
nome (tolerante a acento/caixa via `unaccent`) ou sufixo de telefone (8
últimos dígitos, casa com/sem 9º dígito e DDI) **direto no banco**, devolvendo
só os `id` (até 200, por recência). Os detalhes das que ainda não estão na
lista são buscados em **lotes de 100** via `.in()` (um `.in()` com centenas de
UUIDs estoura o tamanho da URL do PostgREST e vira 400) e mesclados em
`conversas.value` com dedup por id.

Sem isso, o filtro de busca só acharia contatos dentro da janela de 500
recentes — um cliente antigo, sem mensagem recente, "não existiria" pra
busca.

### 1.3 Filtro por atendente ("Minhas" + filtro avançado)

`carregarConversasDoProfissional(profId)` (`conversas.vue:8907`): fatia por
`.range()` em passos de 500 até o teto `CONVERSAS_PROF_TETO = 3000`
(`conversas.vue:8904,8926`), buscando **todas** as conversas atribuídas àquele
profissional, não só as recentes, e mescla na lista. Cacheado por
`profId` (`Set`, `conversas.vue:8905`) — roda uma vez só por profissional até
a lista ser recarregada do zero. Disparado tanto ao trocar o filtro quanto
`immediate: true` no watch do profissional logado (pra o contador da aba
"Minhas" já nascer certo).

### 1.4 Filtro por etiqueta e período — RPC dedicada

`carregarConversasPorFiltroServidor()` (`conversas.vue:8980`): a RPC
`buscar_conversas_ids_filtro` resolve `conversas → clientes.crm_lead_id →
crm_lead_tags` **no banco** (um join que via PostgREST viraria vários lotes de
`.in()`), aplicando etiqueta (semântica **E**, não OU — a conversa precisa ter
TODAS as etiquetas marcadas) e intervalo de data juntos, com
`limit = CONVERSAS_FILTRO_TETO = 1000` (`conversas.vue:8970`, capado em 2000
dentro da própria função SQL). Debounce de 300ms; cache por chave
`JSON.stringify([tagIds, inicioIso, fimIso])` pra não repetir a mesma consulta
ao alternar entre os mesmos filtros.

**Este é exatamente o cenário que você descreveu**: antes dessa RPC existir,
filtrar por etiqueta/período rodava só sobre o que já estava carregado em
memória — e escondia silenciosamente qualquer conversa fora da janela. O
bug documentado que motivou o fix: filtro por atendente mostrando 4
conversas de 238 reais.

> ⚠️ Mesmo essa RPC tem um teto (2000, hardcoded em SQL). Pra a maioria das
> empresas isso nunca é alcançado num filtro combinado de etiqueta+período,
> mas é um limite que existe — se uma base crescer o bastante pra bater nele,
> o sintoma volta (filtro corta nos primeiros 2000 por recência).

### 1.5 Reconciliação após recarregar a lista inteira

Toda vez que `fetchConversas()` substitui `conversas.value` por completo
(carga inicial, refresh manual), os merges dos itens 1.2–1.4 são apagados
junto. `recarregarComplementosDaLista()` (`conversas.vue:9050`) limpa os
caches (`_profissionaisCarregados`, `_filtrosCarregados`) e refaz os merges
de atendente e de etiqueta/período. É chamada sempre depois de
`fetchConversas`.

### 1.6 Filtragem final — client-side, só sobre o que está em memória

`conversasFiltradas` (computed, `conversas.vue:8600`) aplica, nessa ordem:
aba (todas/minhas/não-atribuídas/resolvido/arquivadas) → roteamento (some
lead atribuído a outra empresa) → permissão de instância → instância
selecionada (pill) → `aplicarFiltrosBusca` (busca textual local + atendente +
etiqueta E + período) → conversas fixadas no topo.

`contagemAbas` (computed, `conversas.vue:8595`) aplica **a mesma cadeia**
(menos o filtro de aba em si), pra o número do badge nunca divergir do que a
lista mostra — foi fonte de bug quando essas duas funções tinham lógica
duplicada e discordavam.

**Ponto-chave**: essa camada só enxerga o que já está em `conversas.value`.
Ela funciona corretamente **porque** as seções 1.2–1.4 garantem que qualquer
coisa que um filtro/busca possa precisar encontrar já foi mesclada nesse
array antes dela rodar — não porque ela mesma vá buscar mais dados.

Renderização no DOM é uma **terceira janela**, além da carregada e da
filtrada: `conversasRenderizadas` (`conversas.vue:8633`) corta
`conversasFiltradas` em fatias de `CONVERSAS_POR_LOTE = 20`
(`conversas.vue:5851`), crescendo 20 em 20 conforme o usuário rola
(`handleConversasScroll`, `conversas.vue:9072`) — pra não jogar milhares de
`<div>` no DOM de uma vez. Reseta pra 20 sempre que qualquer filtro muda
(`conversas.vue:8638`).

### 1.7 Mensagens dentro da conversa aberta

- **`MENSAGENS_POR_PAGINA = 30`** (`conversas.vue:6811`).
- `fetchMensagens(conversaId)` (`conversas.vue:9770`): zera offset/flag,
  busca as **30 mais recentes** (`order data_hora desc, limit 30`), inverte
  pra ordem cronológica, faz `scrollToBottom()`. Mensagens que chegaram via
  Realtime mas que essa query ainda não retornou (corrida: o fetch roda antes
  do commit no banco) são preservadas e mescladas por data.
- `carregarMaisMensagens()` (`conversas.vue:9818`), disparada por
  `handleScroll` quando `scrollTop < 50` (perto do topo,
  `conversas.vue:9705`): pagina por `.range(offset, offset+29)` **desc**,
  inverte, filtra duplicata por id e **insere no topo**. A posição de scroll
  é preservada calculando a diferença de `scrollHeight` antes/depois de
  inserir (`conversas.vue:9850-9867`) — sem isso a tela "pula" quando
  mensagens antigas entram acima do que o usuário está vendo.
- **Fim do histórico**: decidido pelo **tamanho da página recebida** — se a
  página veio com menos que `MENSAGENS_POR_PAGINA`, `todasMensagensCarregadas
  = true`. Não depende de um `count()` separado.

---

## 2. Página de Clientes

### 2.1 Carga da lista — pagina tudo pra memória (`app/composables/useClientes.ts:fetchClientes`)

Loop de `.range()`, página de **1000**, `order(created_at desc).order(id
desc)` (desempate por id pra não pular/duplicar linha quando dois registros
empatam no `created_at` entre páginas), até uma página vir com menos que 1000
(`useClientes.ts:63-87`). Resultado: `clientes.value` guarda a **empresa
inteira**, não uma janela — diferente de Conversas, decisão deliberada porque
`clientes` é uma tabela de volume limitado (não cresce uma linha por
mensagem).

Depois, os `instancia_ids` de cada cliente (via `conversas.instancia_id`) são
resolvidos em **lotes de 150** (`TAM_LOTE`, `useClientes.ts:98`) pelo mesmo
motivo do `.in()` de Conversas: um único `.in()` com milhares de UUIDs estoura
a URL.

### 2.2 Filtros — 100% client-side sobre a lista inteira

`clientesFiltrados` (computed, `ClientesManager.vue:3077`) roda sobre
`clientes.value` completo (já que ele tem a base inteira, não há "janela" a
se preocupar aqui): permissão de instância, instância selecionada, nome
(substring), telefone (`matchTelefoneFiltro` — ciente de DDD vs. número
completo), mês de aniversário, etiquetas (E lógico), roteamento
(matriz/franquia), período (`created_at`), atendente atribuído.

### 2.3 Filtro por etiqueta — resolvido direto no banco, NÃO via `crmLeads`

`carregarLeadsPorEtiquetas()` (`ClientesManager.vue:3034`) consulta
`crm_lead_tags` **diretamente** (não usa o `crmLeads` do `useCrm.ts` — ver a
seção 3), com loop de `.range()` (página 1000) até esgotar, monta um mapa
lead→tags e calcula o conjunto de leads que têm **todas** as etiquetas
selecionadas.

O comentário no próprio código explica o motivo
(`ClientesManager.vue:3024-3031`): `crmLeads` (de `useCrm.ts`) é buscado
**sem** `.range()`, então sofre o corte de 1000. Uma empresa com 5.206 leads
tinha só 2 dos 69 marcados com a etiqueta "Cliente Sanderson" dentro desse
corte — a tela mostrava 1 cliente onde existiam 63. A consulta paginada direta
em `crm_lead_tags` evita cair no mesmo buraco.

### 2.4 Renderização: progressiva sem filtro, completa com filtro ativo

`clientesVisiveis` (computed, `ClientesManager.vue:3180`):

- **Sem filtro ativo**: fatia progressiva de `limiteExibicao` (20, +20 a cada
  scroll perto do fim — `onScrollClientes`, `ClientesManager.vue:3187`).
- **Com filtro ativo** (`temFiltroAtivo`, `ClientesManager.vue:3161`):
  renderiza **todos** os resultados filtrados de uma vez, sem corte de
  scroll. Decisão deliberada — quando o usuário filtra, é justamente pra agir
  sobre o conjunto inteiro (ex.: selecionar todos os clientes de um atendente
  e excluir em massa); um corte de 20 faria "Selecionar todos os N" mentir
  sobre quantos itens realmente seriam selecionados.
- `carregandoFiltro` + `setTimeout` de 350ms (`ClientesManager.vue:3176,3200-3207`):
  dá um frame pro spinner pintar antes do render pesado de centenas/milhares
  de linhas, e de quebra funciona como debounce dos filtros digitados (só o
  último filtro da sequência libera o render).

---

## 3. Gap conhecido, **não corrigido** — não copiar pro outro app sem arrumar

`useCrm.ts` → `fetchLeads()` (`app/composables/useCrm.ts:306`) busca
`crm_leads` **sem** `.range()`. Continua sujeito ao corte de 1.000 do
PostgREST. Qualquer tela que renderize direto de `crmLeads` (o Kanban, por
exemplo) pode esconder leads além do 1.000º silenciosamente numa empresa que
cresça o bastante. O filtro de etiqueta em Clientes (seção 2.3) contorna isso
ignorando `crmLeads` de propósito — mas é um contorno pontual, não um
conserto da fonte.

**No app novo, corrija isso desde o início**: pagine `fetchLeads` do mesmo
jeito que `fetchClientes` pagina `clientes` (loop de `.range()` até a página
vir incompleta).

---

## 4. Checklist — regras gerais pra aplicar no outro app

1. **Nunca** faça um `.select()` sem `.range()`/`.limit()` numa tabela que
   pode passar de 1.000 linhas por empresa/usuário. O PostgREST não erra, ele
   **trunca em silêncio**. É o bug mais perigoso da categoria: passa
   despercebido em teste (poucos registros) e só aparece em produção, meses
   depois, com um cliente grande.
2. **Escolha a estratégia por tabela**, não um padrão único pro app inteiro:
   - Tabela de volume limitado por natureza (centenas por empresa, não
     dezenas de milhares) → pode paginar tudo pra memória com loop de
     `.range()` até a página vir incompleta (modelo Clientes).
   - Tabela que cresce sem teto (conversas, mensagens, eventos) → mantenha só
     uma **janela recente** em memória + scroll infinito por **cursor** (não
     por `offset` — cursor não duplica/pula quando chega linha nova no topo)
     + qualquer filtro/busca que precise alcançar fora da janela vai **direto
     no banco** (RPC ou query dedicada), nunca só filtra o que já foi
     carregado.
3. Todo filtro "avançado" que dependa de um JOIN (etiqueta, atendente,
   período cruzado com outra tabela) só está correto se: (a) roda 100% no
   banco (RPC) e devolve os IDs que faltam na lista local, OU (b) a tabela
   inteira já está em memória (estratégia A do item 2). Filtrar em memória
   uma tabela que só tem uma janela recente carregada **é bug**, mesmo que
   pareça funcionar com poucos dados em teste.
4. O contador de aba/badge precisa rodar **a mesma cadeia de filtros** que a
   lista renderizada. Números que não batem (aba diz 447, tela mostra 3) é
   sintoma de filtro rodando só sobre um pedaço da lista.
5. `.in('id', [...])` ou `.in('coluna', [...])` com centenas/milhares de
   valores: sempre em **lotes** (100–150 por vez). Um `.in()` gigante estoura
   o tamanho da URL do PostgREST e vira 400 — sintoma diferente do corte de
   1.000, mesma categoria de bug ("a base cresceu e a tela quebrou").
6. Busca digitada: debounce (300–400ms) + um contador de sequência que
   descarta resposta velha se o usuário já digitou de novo — sem isso, o
   resultado de uma busca anterior pode "vencer a corrida" e sobrescrever o
   resultado certo.
7. Cache por combinação de filtro (chave `JSON.stringify([...])`) evita
   repetir a mesma consulta cara ao alternar entre as mesmas opções.
8. Sempre que a lista inteira for **recarregada do zero** (refresh manual,
   reconexão), limpe os caches de merge sob demanda e refaça-os — senão o
   refresh "esquece" o que tinha sido mesclado por filtro/busca.
9. Renderização: nunca jogue milhares de linhas no DOM de uma vez —
   fatiamento progressivo (20 em 20, crescendo no scroll). **Mas** quando um
   filtro está ativo e a intenção é agir sobre o resultado inteiro (seleção
   em massa), renderize o conjunto filtrado **completo**, não a janela — do
   contrário uma ação em massa atinge menos itens do que o usuário pensa que
   selecionou.
10. Mensagens de uma conversa: pagine por `.range()` a partir da mais recente
    pra trás; ao inserir mensagens antigas no topo, preserve a posição de
    scroll calculando a diferença de `scrollHeight` antes/depois — sem isso a
    tela "pula" quando o histórico carrega.
11. Decida "acabaram os registros" pelo **tamanho da página recebida** (veio
    menor que o `limit` pedido), não por um `count()` separado — mais barato
    e não exige uma segunda ida ao banco a cada carga.

---

## 5. Constantes de referência (valores atuais neste app)

| Constante | Valor | Pra que serve | Onde |
|---|---|---|---|
| `CONVERSAS_CARGA_INICIAL` | 500 | Tamanho da 1ª página da lista de conversas | `conversas.vue:8647` |
| `CONVERSAS_POR_PAGINA_SERVIDOR` | 500 | Tamanho de cada página seguinte (scroll infinito por cursor) | `conversas.vue:8648` |
| `CONVERSAS_PROF_TETO` | 3000 | Teto de conversas carregadas por atendente (merge sob demanda) | `conversas.vue:8904` |
| `CONVERSAS_FILTRO_TETO` | 1000 (capado em 2000 na RPC) | Teto pedido no filtro de etiqueta/período server-side | `conversas.vue:8970` |
| `CONVERSAS_POR_LOTE` | 20 | Fatia de renderização no DOM da lista (scroll de UI, não de dados) | `conversas.vue:5851` |
| `MENSAGENS_POR_PAGINA` | 30 | Tamanho de cada página de mensagens do chat | `conversas.vue:6811` |
| `TAM_LOTE` (busca/filtro de conversas) | 100 | Tamanho do lote em `.in()` ao buscar detalhes de IDs | `conversas.vue:8779,9022` |
| RPC `buscar_conversas_ids` — `p_limit` | 200 (capado em 500) | Busca textual de conversas antigas | `20260714_buscar_conversas_ids.sql` |
| `PAGINA` (clientes) | 1000 | Passo do loop de `.range()` que carrega a base inteira de clientes | `useClientes.ts:67` |
| `TAM_LOTE` (instâncias por cliente) | 150 | Lote de `.in()` ao resolver `instancia_ids` | `useClientes.ts:98` |
| `PAGINA` (etiquetas de clientes) | 1000 | Passo do loop que resolve o filtro de etiqueta direto em `crm_lead_tags` | `ClientesManager.vue:3042` |
| `limiteExibicao` inicial | 20 | Fatia de renderização progressiva da lista de clientes (sem filtro ativo) | `ClientesManager.vue:3022` |

---

## Anexo — arquivos-fonte consultados

- `app/pages/conversas.vue` — lista de conversas, filtros, mensagens do chat.
- `app/composables/useClientes.ts` — carga paginada da lista de clientes.
- `app/components/ClientesManager.vue` — filtros e renderização da tela de clientes.
- `app/composables/useCrm.ts` — `fetchLeads` (gap conhecido, seção 3).
- `supabase/migrations/20260714_buscar_conversas_ids.sql` — RPC de busca textual.
- `supabase/migrations/20260805_buscar_conversas_ids_filtro.sql` — RPC de filtro por etiqueta/período.

Memórias relacionadas (contexto histórico dos bugs que motivaram cada fix):
`project_inbox_corte_1000_linhas.md`, `project_crm_kanban_vazio_muitos_leads.md`,
`project_conversas_perf_gargalos.md`, `project_conversas_atendente_filtro_servidor.md`,
`project_filtro_etiqueta_crmleadid_wipe.md`, `project_selecao_massa_ignora_filtro.md`.
