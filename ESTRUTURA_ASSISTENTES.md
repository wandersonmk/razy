# Estrutura da Página de Assistentes IA

> Documentação técnica de **como criar novos assistentes** e **como atrelar a
> instância (canal WhatsApp) a cada assistente**, além da **página de
> Informações da Empresa** e da **listagem de assistentes (cards)**.
>
> Escopo (conforme solicitado): apenas a **página de Informações da Empresa** e a
> **página de Assistente** com as abas internas relevantes à criação/vínculo.
> As abas **API / Integrações**, **Logs**, **Construtor de Prompt** e
> **Base de Conhecimento** existem no editor mas **não são detalhadas** aqui —
> só ficam listadas para contexto.

---

## 1. Visão geral / arquitetura

A funcionalidade vive na rota **`/instrucao`** (arquivo
[app/pages/instrucao.vue](app/pages/instrucao.vue)), que funciona como um *shell*
que alterna entre dois modos:

| Modo | Componente | Papel |
|------|-----------|-------|
| `lista` | [AssistentesLista.vue](app/components/AssistentesLista.vue) | Grade de cards + criação de novos assistentes |
| `editor` | [InstrucaoManager.vue](app/components/InstrucaoManager.vue) | Edição completa de um assistente (abas internas) |

A página de **Informações da Empresa** é separada: vive dentro de
**`/configuracoes`** → aba **Empresa**
([app/components/configuracoes/EmpresaConfig.vue](app/components/configuracoes/EmpresaConfig.vue)).

### Fluxo de navegação

```
/instrucao (pages/instrucao.vue)
│
├── modo = 'lista'  → <AssistentesLista>
│      │  @editar(id) → abre editor daquele assistente
│      │  @novo(id)   → criou um novo, abre editor já nele
│      ▼
├── modo = 'editor' → <InstrucaoManager :agente-id="id" @cancelar="voltarParaLista">
│      └── abas internas (Informações Gerais, Assistente IA, ...)
```

Trechos-chave em [instrucao.vue](app/pages/instrucao.vue):

```ts
const modo = ref<'lista' | 'editor'>('lista')
const agenteEditandoId = ref<string | null>(null)
// no template:
<AssistentesLista @editar="(id)=>{agenteEditandoId=id; modo='editor'}"
                  @novo="(id)=>{agenteEditandoId=id; modo='editor'}" />
<InstrucaoManager :agente-id="agenteEditandoId" @cancelar="voltarParaLista" />
```

### Guarda de acesso (`verificarAcesso`, linhas 64-100)

A página exige **assinatura ativa** *e* **pelo menos 1 canal criado** (não
precisa estar conectado, só existir). Se não cumprir, redireciona para `/` e
abre modal explicativo:

- `subscriptionStatus.isBlocked` → modal "Comece agora" (trial) ou "Assinatura pendente".
- `temCanal === false` → modal "Crie um canal primeiro".

---

## 2. Modelo de dados (tabelas envolvidas)

| Tabela | Papel |
|--------|-------|
| **`agente_configuracoes`** | 1 linha por assistente. Guarda nome, tipo, instrução, `instancia_id`, `ativo`, modelo de IA, capacidades, etc. |
| **`empresas`** | Dados da empresa + `max_agentes`, `horario_semanal`, `fuso_horario`. |
| **`instancias_uazapi`** | Canais WhatsApp nativos (UAzAPI). `instancia_id` do assistente aponta pra cá. |
| **`instancias_meta`** | Canais WhatsApp Meta / Cloud API. Também podem ser vinculados. |
| **`usuarios` / `usuarios_empresas`** | Resolvem a empresa do usuário logado (por vínculo, não por `auth_user_id`). |
| **`profissionais`** | Atendentes (usados na transferência / atribuição). |

> **`instancia_id` é polimórfico**: aponta para `instancias_uazapi.id` **ou**
> `instancias_meta.id`. Os endpoints validam nas duas tabelas.

### Colunas de `agente_configuracoes` lidas/gravadas

`id, empresa_id, usuario_id, auth_user_id, instancia_id, nome, tipo,
is_principal, ativo, reativar_em, desativado_em, modelo_ia, personalidade,
instrucao_principal, informacoes_empresa, horario_funcionamento,
horario_semanal, fuso_horario, delivery_ativo, delivery_horario_semanal,
feriados_ativo, feriados, pausa_segundos, rotatividade_ativa,
permitir_notificar_offline, enviar_mensagem_ausencia, mensagem_ausencia,
informar_cliente_sem_profissionais, nao_notificar_fora_horario, ler_imagens,
instrucao_imagens, ler_documentos, instrucao_documentos, numero_teste,
atendente_comercial, atendente_fora_horario, created_at, updated_at`

---

## 3. Página de Informações da Empresa (`EmpresaConfig.vue`)

Rota: **`/configuracoes?aba=empresa`**. Componente lê/grava na tabela
**`empresas`**. Acesso restrito: papel `admin` **não** vê (`podeVerEmpresa=false`).

### Seções e campos

| Seção | Campo (UI) | Coluna no banco | Observações |
|-------|-----------|-----------------|-------------|
| **Identidade** | Nome da Empresa `*` | `nome` | Obrigatório |
| | CNPJ | `cnpj` (fallback `cpf` se for CNPJ de 14 díg.) | Máscara `##.###.###/####-##` |
| | WhatsApp | `whatsapp` | Salvo com DDI `55`; exibido sem `55` |
| **Funcionamento** (agenda) | Fuso horário | `fuso_horario` | Default `America/Sao_Paulo`; lista de fusos BR |
| | Horário por dia (0-6) | `horario_semanal` (jsonb) | `{aberto, abertura, fechamento}` por dia |
| **Conta** | E-mail | `email` (só leitura) | Vinculado à conta, não editável |

> ⚠️ **Importante:** o horário desta página é o da **agenda de agendamentos**
> (calendário + lembretes). O **horário de funcionamento que a IA usa**
> (saudação, "fora do horário") é configurado **por assistente**, na aba
> *Assistente IA → Informações Gerais* — assim cada número/loja tem o seu.

### Carregar / salvar

- `onMounted`: resolve empresa por **vínculo** (`fetchContext`, não por
  `auth_user_id`) e faz `select` em `empresas`. Compat: empresa antiga sem
  `horario_semanal` deriva das colunas legadas `dias_funcionamento` +
  `horario_abertura`/`horario_fechamento`.
- `salvarDados`: valida cada dia aberto (fechamento > abertura), monta o jsonb
  `horario_semanal` e **sincroniza colunas legadas** (`horario_abertura` = min,
  `horario_fechamento` = max, `dias_funcionamento` = dias abertos). Faz
  `update` em `empresas`.
- Estado *dirty*: `dadosOriginais` (snapshot JSON) vs `formData`. Barra sticky
  no rodapé mostra "alterações não salvas" e habilita o botão Salvar.

---

## 4. Página de Assistentes — Lista e Cards (`AssistentesLista.vue`)

### 4.1 Carregamento

`carregar()` (linhas 131-162):

1. `fetchContext()` → `empresaId`.
2. `fetchInstancias()` → popula `instanciasAtivas` (via `useInstancias`).
3. Em paralelo:
   - `empresas.select('max_agentes')`
   - `agente_configuracoes.select(...)` de **todos** (ativos + desligados),
     ordenados por `ativo desc, is_principal desc, nome`.

Interface do assistente na lista:

```ts
interface Assistente {
  id, nome, tipo, descricao, is_principal,
  instancia_id, ativo, reativar_em, created_at, updated_at
}
```

### 4.2 Limite de assistentes

```ts
// Cada instância dá direito a 1 Principal; admin libera mais via max_agentes.
maxAgentes = Math.max(1, max_agentes_configurado, totalInstancias)
assistentesAtivos = assistentes.filter(a => a.ativo)   // desligados NÃO ocupam slot
podeAdicionar = assistentesAtivos.length < maxAgentes
```

A CTA **"Novo Assistente"** some (`noLimite`) quando:
- empresa com direito a **1 só** e já tem o seu (o Principal nasce com o canal), **ou**
- limite de ativos atingido.

Quando no limite, aparece o botão **"Contratar mais"** (link `wa.me`).

### 4.3 Cards (`AssistenteCard.vue`)

Cada card é um "robozinho" animado (cabeça flutuante + corpo em barril). Recebe:

```ts
:assistente, :instancia (nome/phone/status), :tipo-meta (label/icon/cor), :reativacao
```

Emite: **`editar`**, **`excluir`**, **`religar`**, **`desligar`**.

Estados visuais:
- **ONLINE/OFFLINE** (chip por `assistente.ativo`); offline → robô "dorme" (Zzz),
  hover mostra balão "Me acorde!" que chama `religar`.
- Badge de tipo (Principal usa `fa-shield-alt`; demais usam o ícone do tipo).
- Detalhes colapsáveis: instância (nome + telefone + bolinha de conexão) e
  data de criação/reativação.

Tipos disponíveis (`TIPOS`, `AssistentesLista.vue` linhas 51-58):
`principal`, `comercial`, `financeiro`, `suporte`, `pos_venda`, `outro`.
(`principal` **não** é escolhível ao criar — é derivado.)

### 4.4 Ações do card

| Ação | Efeito |
|------|--------|
| `editar` | `emit('editar', id)` → abre `InstrucaoManager` |
| `religar` | `update agente_configuracoes set ativo=true` + log |
| `desligar` | Abre `DesativarAssistenteModal` → grava `ativo=false`, `reativar_em`, `desativado_em` |
| `excluir` | **HARD DELETE** (`delete`). Bloqueado para Principal se houver outros na mesma instância |

---

## 5. Criar um novo assistente

### 5.1 Modal "Novo Assistente" (na lista)

`abrirModalNovo()` valida `podeAdicionar` e pré-seleciona a 1ª instância. O modal
coleta **3 campos**:

| Campo | Ref | Regras |
|-------|-----|--------|
| **Nome** | `novoNome` | Obrigatório, `maxlength=40` |
| **Tipo** | `novoTipo` (default `comercial`) | Botões: todos os tipos **exceto** `principal` |
| **Instância** | `novoInstanciaId` | Se **1 instância** → atribuída automática (sem dropdown); se **várias** → `<select>` |

### 5.2 `criar()` → chama o backend

```ts
const res = await $fetch('/api/assistentes/criar', {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` },
  body: { nome, tipo: novoTipo.value, instancia_id: novoInstanciaId.value },
})
// sucesso → recarrega lista + emit('novo', res.assistente.id) → abre o editor
```

### 5.3 Endpoint `POST /api/assistentes/criar` ([server](server/api/assistentes/criar.post.ts))

Por que é no servidor: **RLS sozinho não conta linhas** — o limite `max_agentes`
precisa ser validado com service role.

Passo a passo:

1. **Auth**: valida `Bearer` token → `user`.
2. **Resolve empresa** por vínculo (`usuarios` → `usuarios_empresas`), com
   fallback para `empresas.auth_user_id`.
3. **Valida a instância**: procura o `instancia_id` em `instancias_uazapi`
   **e** `instancias_meta`, exigindo `empresa_id` igual. Se não achar → **403**
   "Instancia nao pertence a empresa". Guarda `instProvider` (`uazapi`|`meta`).
4. **Calcula o limite efetivo**:
   ```
   maxAgentes = max(1, empresas.max_agentes, count(instancias_uazapi≠deleted) + count(instancias_meta ativo))
   ```
   Conta os assistentes **ativos** da empresa; se `>= maxAgentes` → **403**
   "Limite atingido".
5. **Decide `is_principal`**: `TRUE` se for o **1º assistente ativo daquela
   instância**, senão `FALSE`. (Garante exatamente 1 Principal por instância.)
6. **Insert** em `agente_configuracoes`:
   ```ts
   {
     empresa_id, usuario_id, auth_user_id, instancia_id, nome, tipo,
     is_principal,
     ativo: true,
     personalidade: 'Profissional, empatico e prestativo',
     pausa_segundos: 86400,   // 24h: IA em silêncio 1 dia após atendente humano
   }
   ```
7. `registrarLog` (ação `criar`, entidade `assistente`) e retorna
   `{ ok: true, assistente: { id, nome, tipo, is_principal, instancia_id } }`.

> **Resumo do vínculo na criação:** a instância é escolhida no modal e enviada
> como `instancia_id`. O servidor confirma que ela é da empresa e grava
> diretamente na coluna `agente_configuracoes.instancia_id`. Não existe tabela
> de junção — o vínculo é essa coluna (1 assistente → 1 instância).

---

## 6. Editor do assistente (`InstrucaoManager.vue`)

Recebe `:agente-id`. Quando presente, abre já na aba **Assistente IA**
(`abaAtiva = props.agenteId ? 'ia' : 'geral'`). Emite `salvo` e `cancelar`.

### 6.1 Abas (`tabsBase`, linhas 177-185)

| id | Rótulo | Detalhado aqui? |
|----|--------|-----------------|
| `geral` | **Informações Gerais** | ✅ Sim (§6.3) |
| `ia` | **Assistente IA** | ✅ Sim (§6.4) |
| `construtor` | Construtor de Prompt | ➖ Fora do escopo |
| `conhecimento` | Base de Conhecimento | ➖ Fora do escopo |
| `api` | API | ➖ Fora do escopo (integrações) |
| `logs` | Logs | ➖ Fora do escopo |
| `avancado` | **Configurações Avançadas** | ✅ Sim (§6.5) |

> (Abas `fluxo-gestante` / `fluxo-nao-gestante` existem só para uma empresa
> especial e estão **dormentes** — `isEmpresaEspecial` sempre `false`.)

### 6.2 Card "Identidade do assistente" (topo, colapsável) — **aqui mora o vínculo**

Card no topo do editor, nasce **colapsado** (`identidadeExpandida=false`). Contém:

| Campo | Ref | UI |
|-------|-----|----|
| **Nome** | `assistenteNome` | input, `maxlength=40` |
| **Tipo** | `assistenteTipo` | select: principal/comercial/financeiro/suporte/pos_venda/outro |
| **Instância vinculada** | `assistenteInstanciaSelecionada` | ver abaixo |
| **Modelo de IA** | `assistenteModeloIa` (default `gpt-4.1-mini`) | cartões: `gpt-4.1-mini` (Padrão), `gpt-5.4-mini` (Raciocínio), `gpt-5.4` (Topo) — só aparece se `podeTrocarModelo` |

**Seleção da instância (vínculo):**
- **1 instância ativa** → mostra visual fixo "Única da empresa" (sem dropdown).
- **Múltiplas** → `<select v-model="assistenteInstanciaSelecionada">` populado
  por `v-for="i in instanciasAtivas"` com `:value="i.id"`.
- Auto-seleção no `onMounted`: prioriza instância `connected`, senão a 1ª ativa.

> **Botão Power (ligar/desligar)** também vive na identidade: `onClickBotaoIA`
> — se ativo abre `DesativarAssistenteModal`; se inativo, religa e salva na hora.

### 6.3 Aba `geral` — Informações Gerais

| Bloco | Campo `config.*` | Coluna |
|-------|------------------|--------|
| Informações da Empresa | `informacoesEmpresa` | `informacoes_empresa` |
| Horário de Funcionamento (da IA) | `fusoHorario` + `horarioSemanal` (por dia) | `fuso_horario`, `horario_semanal` |
| Delivery | `deliveryAtivo` + `deliveryHorarioSemanal` | `delivery_ativo`, `delivery_horario_semanal` |
| Feriados / datas especiais | `feriadosAtivo` + `feriados[]` | `feriados_ativo`, `feriados` |

`FeriadoConfig` = `{data, descricao, fechado, inicio, fim, delivery, repete, mensagem, mostrarMensagem}`.

### 6.4 Aba `ia` — Assistente IA

| Bloco | Campo `config.*` | Coluna |
|-------|------------------|--------|
| **Personalidade** | `personalidade` | `personalidade` |
| **Instrução Principal** | `instrucaoPrincipal` (`maxlength=10000`, contador) | `instrucao_principal` |

Inclui ajudas colapsáveis (mídias, transferência, etiquetas, agenda, kanban) e
modal de tela cheia com busca/substituição. O botão **Testar** abre o playground
(`AssistenteTestChat`) que conversa usando a instrução do editor **sem enviar no
WhatsApp**.

> **Não existe campo "temperatura"** — o comportamento do modelo é escolhido só
> por `modelo_ia`.

### 6.5 Aba `avancado` — Configurações Avançadas (sub-abas)

Sub-abas: `comportamento` | `capacidades` | `avancado`.

**Comportamento:**
- **Pausar IA**: `pausaIA` (`1h`/`24h`/`personalizado`) + `pausaPersonalizada` +
  `pausaUnidade` → convertido em `pausa_segundos` (teto = 1 ano / 31.536.000s).
- **Atribuição de Atendimentos**: `rotatividadeAtiva`, `permitirNotificarOffline`
  (nasce ON), `enviarMensagemAusencia` + `mensagemAusencia`,
  `informarClienteSemProfissionais` (nasce OFF), `naoNotificarForaHorario`.

**Capacidades** (defaults **OFF** — geram custo OpenAI):
- `lerImagens` + `instrucaoImagens`
- `lerDocumentos` + `instrucaoDocumentos`

**Avançado / Zona de perigo:**
- **Modo de teste** (`numerosTeste: string[]` → coluna `numero_teste` em CSV,
  normalizado com DDI 55): a IA responde **somente** a esses números.
- **Limpar memória** e **Resetar rotatividade** (`delete` em `rotatividade_cursor`).

---

## 7. Salvar / atualizar / atrelar instância no editor

Função central `salvarConfiguracoes` (linhas 1746-1927):

1. Resolve empresa/usuário (contexto cacheado ou `empresas`/`usuarios`).
2. Calcula `pausaSegundos` e:
   ```ts
   const instanciaDestino =
     assistenteInstanciaSelecionada.value || instanciaAtiva.value || null
   ```
   → vira `instancia_id` no payload (**é assim que o editor re-atrela a instância**).
3. **Defesa de Principal**: se `tipo === 'principal'` mas a instância destino já
   tem outro Principal ativo (query em `agente_configuracoes`), rebaixa para
   especialista (`is_principal=false`, `tipo='outro'`) — evita violar o índice
   único `agente_configuracoes_instancia_principal_uniq`.
4. Monta `camposAtualizar` (payload completo: identidade + todos os campos de
   `config` + `ativo`/`reativar_em`/`desativado_em` + `numero_teste` CSV).
5. **Criar vs atualizar:**
   - Se `props.agenteId` existe → **UPDATE via `PATCH /api/assistentes/{id}`**
     (Bearer token). **Não** faz update direto no Supabase.
   - Senão, procura registro por `instancia_id` (fluxo legado); se existir faz o
     mesmo PATCH; se não, `insert` direto em `agente_configuracoes`.
6. Limpa `hasUnsavedChanges`, registra log, toast, `emit('salvo')`.

### Endpoint `PATCH /api/assistentes/[id]` ([server](server/api/assistentes/[id].patch.ts))

- Autoriza por JWT: só atualiza assistente da **própria empresa** (senão 403).
- **Allowlist de campos** (`CAMPOS_PERMITIDOS`) — qualquer campo fora dela é
  ignorado. Inclui `instancia_id`, `nome`, `tipo`, `is_principal`, `modelo_ia`,
  `personalidade`, `instrucao_principal`, `pausa_segundos`, `ativo`,
  `reativar_em`, `desativado_em`, capacidades, `numero_teste`, horários,
  delivery, feriados, atendentes, etc.
- **Validação de vínculo cross-company**: se `instancia_id` mudou, confere que a
  nova instância (UAzAPI **ou** Meta) pertence à empresa. Também há o trigger SQL
  `trg_assistente_instancia_mesma_empresa` (defesa em camadas).
- **Defesa de Principal** (mesma regra do front, no servidor).
- Registra log `alterar` e retorna o assistente atualizado.

### Draft vs Publicar

**Não há** fluxo de rascunho persistido. "Rascunho" = estado local não salvo
(`hasUnsavedChanges`, marcado por `watch(config, {deep:true})`). O botão flutuante
de salvar só aparece com mudanças pendentes. O banner "aplicado como rascunho"
(vindo do Construtor ou de Materiais/Modelos) reforça que nada foi gravado até
clicar em **Salvar**.

### Ativar / desativar

- `config.agenteAtivo` ↔ `ativo`; `config.reativarEm` ↔ `reativar_em`.
- `DesativarAssistenteModal` devolve `{ reativarEm }`: `null` (indeterminado) ou
  ISO (volta programada). Grava `ativo=false`, `reativar_em`, `desativado_em`.
- Contador regressivo no front; o cron do backend religa no banco quando vence.

---

## 8. Resumo do vínculo Assistente ↔ Instância

```
                    agente_configuracoes
                    ┌───────────────────────────┐
   instancias_uazapi│ id                        │
   ┌──────────┐     │ instancia_id  ───────────►│ (aponta p/ uazapi OU meta)
   │ id       │◄────┤ empresa_id                │
   └──────────┘     │ is_principal (1 por inst.)│
   instancias_meta  │ nome / tipo / instrução   │
   ┌──────────┐     │ ativo / reativar_em       │
   │ id       │◄────┤ modelo_ia / ...           │
   └──────────┘     └───────────────────────────┘
```

- **1 assistente → 1 instância** (coluna `instancia_id`, sem tabela de junção).
- **1 instância → N assistentes**, mas **exatamente 1 Principal ativo** por
  instância (garantido por índice único + defesa no criar e no patch).
- Vínculo definido na **criação** (modal → `POST /criar`) e alterável no
  **editor** (card Identidade → `PATCH /{id}`), sempre validando que a instância
  é da mesma empresa (front, endpoint e trigger SQL).

---

## 9. Arquivos de referência

| Arquivo | Papel |
|---------|-------|
| [app/pages/instrucao.vue](app/pages/instrucao.vue) | Shell lista/editor + guarda de acesso |
| [app/components/AssistentesLista.vue](app/components/AssistentesLista.vue) | Grade de cards + modal "Novo Assistente" |
| [app/components/AssistenteCard.vue](app/components/AssistenteCard.vue) | Card individual (robozinho) |
| [app/components/InstrucaoManager.vue](app/components/InstrucaoManager.vue) | Editor completo com abas |
| [app/components/DesativarAssistenteModal.vue](app/components/DesativarAssistenteModal.vue) | Modal de desligar/programar volta |
| [app/components/configuracoes/EmpresaConfig.vue](app/components/configuracoes/EmpresaConfig.vue) | Página de Informações da Empresa |
| [server/api/assistentes/criar.post.ts](server/api/assistentes/criar.post.ts) | Criação + validação de limite/instância |
| [server/api/assistentes/[id].patch.ts](server/api/assistentes/[id].patch.ts) | Atualização + validação de vínculo |
