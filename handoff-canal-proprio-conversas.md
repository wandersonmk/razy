# Handoff — Canal próprio (QR Code UAZAPI) + Página de Conversas + Pipeline de Mensagens

> Documento de referência extraído do código real do Agzap (Nuxt + Supabase + ai-service
> Python/FastAPI com LangChain/LangGraph) para replicar, em OUTRO aplicativo, três coisas:
> 1. Canal próprio via UAZAPI (QR Code, conexão, ciclo de vida da instância);
> 2. Página de Conversas (cards, layout, abertura/pausa/fechamento de atendimento);
> 3. Pipeline de recebimento de mensagem — em especial a distinção entre **mensagem do
>    cliente** e **mensagem que o colaborador manda pelo PRÓPRIO CELULAR** (sem usar o app),
>    que é o requisito central do novo app: os atendentes não respondem pela ferramenta,
>    respondem pelo WhatsApp do celular deles, e o painel só INTERCEPTA/EXIBE isso.
>
> Este NÃO é um guia de "copiar e colar" — é a arquitetura real, generalizada, com as
> decisões de design que já foram testadas em produção (e os bugs que elas resolveram).
> Onde o novo app precisa de algo que o Agzap não tem hoje (ex.: vincular explicitamente
> 1 instância a 1 profissional), está marcado como **[NOVO]**.

---

## 0. Visão geral da arquitetura

```
WhatsApp do CLIENTE  ─┐
                       │  mensagem (texto/áudio/imagem/doc/vídeo)
WhatsApp do COLABORADOR┘  (colaborador respondendo pelo PRÓPRIO celular)
        │
        ▼
   UAZAPI (SaaS que fala com o WhatsApp; 1 "instância" = 1 número conectado)
        │  webhook HTTP (POST, JSON, header "token" identifica a instância)
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ ai-service (Python/FastAPI)                                           │
│  POST /uazapi/webhook                                                 │
│   1. find_instancia_by_token(token) -> empresa_id, instancia_id       │
│   2. normalize_uazapi(body) -> dict canônico (from_me, telefone,      │
│      kind, texto, media_url, chatlid, message_id...)                  │
│   3. INSERT langchain.inbound_queue (fila em Postgres) + NOTIFY       │
└───────────────────────────────────────────────────────────────────────┘
        │  (worker faz polling / LISTEN da fila)
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ WorkerLoop -> dispatch(job)                                           │
│   from_me == True  -> handle_from_me()   (colaborador via CELULAR)    │
│   from_me == False -> fluxo normal       (cliente -> IA, se tiver)    │
│   Em ambos: mídia é baixada e movida para o R2 ANTES do INSERT;       │
│   mensagem é gravada na tabela `mensagens` (direção SENT/RECEIVED)    │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
   Supabase Postgres: tabelas `conversas` / `mensagens`
        │  trigger AFTER INSERT/UPDATE -> realtime.send() (Broadcast do banco)
        ▼
   Canal privado `empresa:{empresa_id}` (tópicos 'mensagem' / 'conversa')
        │
        ▼
   Frontend (página de Conversas) — assina o canal, atualiza a lista e o
   chat aberto em tempo real, sem depender de refresh.
```

Duas peças de "banco" diferentes, propositalmente separadas:

- **Supabase Postgres** — fonte de verdade do negócio: `conversas`, `mensagens`,
  `instancias_uazapi`, `midias_conversas`, etc. É nele que o Realtime/Broadcast roda.
- **Postgres do ai-service** (self-hosted, ex.: EasyPanel) — schema `langchain`:
  fila `inbound_queue` (mensagens chegando, para desacoplar o webhook HTTP do
  processamento) + tabelas de checkpoint do LangGraph (`langchain.checkpoints`,
  criadas automaticamente pelo `PostgresSaver`). Pode ser o MESMO Postgres do
  Supabase (schema separado) ou uma instância própria — o Agzap usa uma instância
  própria porque o worker precisa de conexão direta (`asyncpg`) com `LISTEN/NOTIFY`
  e `FOR UPDATE SKIP LOCKED`, o que o pooler do Supabase (PgBouncer transaction mode)
  não suporta bem.

---

## 1. Canal próprio — UAZAPI (criação de instância + QR Code)

Base URL: `UAZAPI_BASE_URL` (ex.: `https://<subdominio>.uazapi.com`). Toda chamada
autenticada usa o header `token` (token da instância) ou `admintoken` (token de admin,
só para criar instância nova).

### 1.1 Criar a instância

```
POST {UAZAPI_BASE_URL}/instance/init
Headers: Content-Type: application/json, admintoken: <ADMIN_TOKEN>
Body: { "name": "<slug-sem-acento-e-espaco>", "systemName": "<NomeDoSeuApp>" }
Resposta: { "token": "...", "name": "..." }
```

Passos no backend (Nuxt aqui, mas é framework-agnóstico):
1. Resolver `empresa_id` do usuário autenticado.
2. Checar limite de instâncias da empresa (`empresas.max_instancias` vs
   `COUNT(instancias_uazapi WHERE empresa_id=... AND status != 'deleted')`).
3. Gerar um slug do nome (lowercase, sem acento, sem espaço) — vira o `name` da UAZAPI.
4. Checar duplicidade de slug **dentro da mesma empresa**.
5. Chamar `/instance/init` com `admintoken`.
6. **Proteção crítica**: antes de gravar, checar se `payload.token` já está vinculado
   a QUALQUER empresa no seu banco (`UNIQUE (uazapi_token)` + lookup) — evita que uma
   resposta duplicada/replay da UAZAPI vincule o mesmo número a duas empresas.
7. Gravar em `instancias_uazapi` com `status = 'disconnected'`.
8. (Se você assina o evento `messages_update` da UAZAPI para tiques de entregue/lido,
   é o momento de garantir essa assinatura — best-effort, idempotente.)

### 1.2 Conectar / gerar QR Code

```
POST {UAZAPI_BASE_URL}/instance/connect
Headers: token: <TOKEN_DA_INSTANCIA>
Body: {}                      # sem "phone" = fluxo por QR Code (escanear)
Resposta: { "instance": { "status": "...", "qrcode": "data:image/png;base64,...",
                            "paircode": "ABCD-1234", "profileName": "..." },
            "connected": false }
```

- `qrcode` já vem pronto para `<img :src="qrCode">` (é um data URL base64).
- `paircode` é a alternativa "digitar código no celular" em vez de escanear.
- **Não grave `status` no banco aqui** — deixe o polling de status (1.3) decidir,
  porque a resposta deste endpoint é só "conexão iniciada", não o estado real.
- Trate `429` (limite de conexões simultâneas da UAZAPI) como erro amigável — não é
  bug seu, é rate limit deles.

### 1.3 Poll de status (chamar a cada poucos segundos enquanto a tela do QR está aberta)

```
GET {UAZAPI_BASE_URL}/instance/status
Headers: token: <TOKEN_DA_INSTANCIA>
Resposta: { "instance": { "status": "...", "qrcode": "...", "profileName": "...",
                            "profilePicUrl": "...", "isBusiness": false },
            "status": { "loggedIn": true|false, "jid": "5511999999999:35@s.whatsapp.net",
                          "connected": true|false } }
```

**Armadilha real (já causou incidente em produção) — leia com atenção:**

- `instance.status` é o estado do PROCESSO da UAZAPI, não da sessão do WhatsApp. Fica
  em `"connecting"` a maior parte do tempo mesmo com a sessão perfeita.
- `status.connected` é o socket do instante — oscila o tempo todo, não é confiável.
- **O único sinal confiável de "número pareado e funcional" é `status.loggedIn === true`
  (ou a presença de `status.jid`)**. É esse campo que decide se dá para enviar/receber.
- O telefone conectado sai de `status.jid` (formato `"5511999999999:35@s.whatsapp.net"`)
  — remova o sufixo `:35` (device id) e o domínio antes de gravar.

Lógica recomendada de status:

```
pareado  = status.loggedIn === true || !!status.jid
pareando = !!qrcode || !!paircode
status_final = pareado ? 'connected' : pareando ? 'connecting' : 'disconnected'
```

**Anti-oscilação ao rebaixar**: quando a UAZAPI tem um soluço passageiro, o payload de
uma instância saudável fica IDÊNTICO ao de quem realmente deslogou (`loggedIn:false`,
`jid:null`) — não dá para distinguir pelo conteúdo, só pela repetição. Por isso:
- **Subir** para `connected` é imediato (não tem falso positivo).
- **Descer** de `connected`/`connecting` exige **duas leituras ruins seguidas**
  (contador `status_falhas`, zera a cada leitura boa). Uma leitura ruim isolada só
  incrementa o contador; o card continua mostrando o status anterior.
- Isso vale também para "connecting → disconnected": entre um QR expirar e o próximo
  ser gerado a UAZAPI responde sem `qrcode` e sem `loggedIn`, payload idêntico ao de
  quem deslogou — rebaixar aqui derruba pareamentos em andamento.

### 1.4 Outras chamadas do ciclo de vida

- `POST /instance/disconnect` (header `token`) — desconecta sem apagar a instância.
- Renomear/apagar são operações só no SEU banco (a UAZAPI não precisa saber do nome
  amigável que você dá à instância).
- Ao **excluir de verdade**, chame o endpoint de delete da UAZAPI e marque
  `status = 'deleted'` no seu banco (não faça hard delete — mantém histórico e evita
  reuso acidental do slug).

### 1.5 Enviar mensagem (a instância como remetente automático — IA ou API)

```
POST {UAZAPI_BASE_URL}/send/text     body: { "number": "<telefone>", "text": "..." }
POST {UAZAPI_BASE_URL}/send/media    body: { "number": "...", "type": "audio|image|document|video",
                                              "file": "<url pública>", "text"?, "docName"? }
Headers sempre: token: <TOKEN_DA_INSTANCIA>
```
`number` aceita telefone puro; se você resolve por `@lid` (endereçamento cruzado do
WhatsApp), a UAZAPI aceita endereçar pelo `chatlid` também — mantenha essa opção se for
lidar com contatos que trocam de `@lid` (grupos, multi-dispositivo).

### 1.6 Variáveis de ambiente necessárias

| Variável | Uso |
|---|---|
| `UAZAPI_BASE_URL` | base da API (`https://<seu-subdominio>.uazapi.com`) |
| `UAZAPI_ADMIN_TOKEN` | só para criar instância nova (`/instance/init`) |
| (token por instância) | gravado em `instancias_uazapi.uazapi_token`, um por número |

---

## 2. Banco de dados — schema de referência

Todas as tabelas abaixo são as REAIS do Agzap (via introspecção do Postgres, não do
código legado). Adapte nomes ao seu domínio, mas mantenha as relações e os campos
marcados como críticos.

### 2.1 `instancias_uazapi` — 1 linha por número conectado

```sql
id                    uuid PK default gen_random_uuid()
empresa_id            uuid NOT NULL  -> empresas(id) ON DELETE CASCADE
usuario_id            uuid NOT NULL  -> usuarios(id) ON DELETE CASCADE   -- quem CRIOU a instância
nome_instancia        text NOT NULL                                      -- nome amigável (ex.: "João - Vendas")
uazapi_instance_name  text                                               -- slug devolvido pela UAZAPI
uazapi_token          text NOT NULL UNIQUE                               -- token da instância (1:1)
status                text NOT NULL default 'disconnected'               -- disconnected|connecting|connected|deleted
status_falhas         smallint NOT NULL default 0                        -- anti-oscilação (ver 1.3)
phone                 text                                               -- telefone pareado (só some quando loggedIn)
data_criacao          timestamptz NOT NULL default now()
created_at            timestamptz NOT NULL default now()
```

**[NOVO]** — no Agzap, `instancias_uazapi` NÃO tem `profissional_id`: o vínculo
"este número é do fulano" é só convenção de nome. Para o seu app, onde **cada
profissional tem exatamente 1 número conectado e os atendentes respondem só pelo
celular**, isso deveria ser explícito:

```sql
ALTER TABLE instancias_uazapi ADD COLUMN profissional_id uuid REFERENCES profissionais(id);
-- 1 profissional = no máximo 1 instância ativa (ajuste a regra ao seu caso):
CREATE UNIQUE INDEX ux_instancia_por_profissional
  ON instancias_uazapi (profissional_id) WHERE status != 'deleted';
```
Isso permite: (a) a aba "por número" da página de Conversas já nascer com o nome do
profissional; (b) `handle_from_me` (seção 3) resolver o profissional dono da instância
sem heurística; (c) as métricas por atendente (seção 6) fazerem `JOIN` direto.

### 2.2 `conversas` — 1 linha por (contato × instância)

```sql
id                          uuid PK
conversa_id                 text NOT NULL         -- id externo/lid, usado como chave alternativa
numero                      text NOT NULL          -- telefone do CONTATO (cliente), dígitos puros
nome_contato                text
nome_editado                boolean default false  -- trava contra sobrescrever nome editado manualmente
photo                       text
ultima_mensagem             text
ultimo_horario              timestamptz
ultima_msg_cliente_em       timestamptz            -- só atualiza em mensagens RECEIVED (usado no TMPR, seção 6)
nao_lidas                   integer default 0
importante                  boolean default false
status                      text                   -- 'ativo' | 'aberta' | 'fechada' ...
chatlid                     text                   -- @lid do WhatsApp (endereçamento cruzado)
empresa_id                  uuid NOT NULL
cliente_id                  uuid                   -- FK para o cadastro de cliente/CRM
instancia_id                uuid                   -- FK para instancias_uazapi = QUAL NÚMERO recebeu

-- Atribuição (quem está atendendo esta conversa agora)
assigned_to_professional_id uuid
assigned_at                 timestamptz
assigned_by                 uuid                   -- usuário que fez a atribuição

-- Ciclo de vida do atendimento (abrir/pausar/fechar)
opened_at                   timestamptz            -- quando o atendimento foi ABERTO
closed_at                   timestamptz            -- quando foi FECHADO (tempo = closed_at - opened_at)
resolved_at                 timestamptz            -- marca "foi para a aba Resolvidas" (ver 4.6)
tempo_pausa                 integer                -- segundos de pausa automática/manual (badge)
tempo_pausa_inicio          timestamptz            -- início da contagem regressiva da pausa

arquivada                   boolean NOT NULL default false
deleted_at                  timestamptz
created_at / updated_at     timestamptz
```

`UNIQUE (numero, empresa_id, instancia_id) WHERE deleted_at IS NULL` (via lógica de
aplicação/trigger) é o que garante **1 conversa por contato POR NÚMERO CONECTADO** —
se o mesmo cliente falar com dois profissionais diferentes (dois números diferentes da
empresa), nascem DUAS linhas de `conversas`, uma por instância. É assim que a aba "por
número" (seção 4.2) funciona: filtrar por `instancia_id`.

### 2.3 `mensagens` — 1 linha por mensagem, em qualquer direção

```sql
id                        uuid PK
numero                    text NOT NULL           -- telefone do CONTATO (mesmo em SENT ou RECEIVED)
mensagem                  text                    -- texto, OU url de mídia (imagem/doc/vídeo)
direcao                   text NOT NULL           -- 'RECEIVED' (cliente->empresa) | 'SENT' (empresa->cliente)
enviado_por               text default 'user'     -- 'user' (cliente) | 'assistant' (IA) | 'humano' (app) | 'celular' (ATENDENTE PELO CELULAR)
enviado_por_profissional_id uuid                  -- quem (humano) mandou, quando aplicável
nome_contato               text
chatlid                    text
empresa_id                 uuid NOT NULL
instancia_id               uuid                   -- QUAL número trafegou essa mensagem
conversa_id                uuid                   -- FK conversas(id), preenchido por trigger no INSERT
data_hora                  timestamptz
kind                       text                   -- 'text'|'audio'|'image'|'document'|'video'|'sticker'|'reaction'|'unknown'
audio_url                  text                   -- só quando kind='audio'
photo                      text
arquivo_nome               text                   -- nome original do documento (a URL no R2 usa UUID)
wa_message_id               text                   -- id da mensagem NA UAZAPI (para citar/responder)
reply_to_wa_id / reply_to_text / reply_to_from_me   -- citação (responder mensagem)
wa_status / wa_lida_em      -- tiques de entregue/lido
editada                    boolean default false
origem_api                 boolean default false   -- mandada pela API pública (não pelo painel)
created_at / updated_at
```

Semântica de `enviado_por` — **é o campo que separa os 4 tipos de remetente**:

| `direcao` | `enviado_por` | Significado |
|---|---|---|
| `RECEIVED` | `user` | Mensagem do **cliente** |
| `SENT` | `assistant` | Resposta da **IA** |
| `SENT` | `humano` | Atendente respondeu **pelo app/painel** (se seu app tiver essa opção) |
| `SENT` | `celular` | **Atendente respondeu pelo PRÓPRIO CELULAR** — é o caso central do seu app |

### 2.4 `conversa_atendentes_historico` — auditoria de abrir/atribuir/fechar (alimenta métricas)

```sql
id                          uuid PK
empresa_id                  uuid NOT NULL
conversa_id                 uuid NOT NULL
cliente_id                  uuid
crm_lead_id                 uuid
profissional_id             uuid
profissional_nome_snapshot  text        -- nome no momento do evento (sobrevive a rename/exclusão)
acao                        text NOT NULL   -- 'atribuido' | 'desatribuido' | 'fechado'
created_by                  uuid            -- usuário que disparou a ação (null se automático)
created_at                  timestamptz default now()
```
1 linha por evento. É a fonte para "quanto tempo o atendente ficou com a conversa",
"quantas conversas cada atendente fechou no dia", etc.

### 2.5 `midias_conversas` — rastreio de mídia no R2 (para expirar depois)

```sql
id             uuid PK
mensagem_id    uuid NOT NULL      -- FK mensagens(id)
empresa_id     uuid NOT NULL
instancia_id   uuid
storage_path   text NOT NULL      -- key dentro do bucket
tipo           text NOT NULL      -- CHECK IN ('audio','imagem','pdf','documento')  -- video/sticker mapeiam pra estes
url_original   text               -- URL temporária de origem (UAZAPI)
url_storage    text NOT NULL      -- URL pública definitiva (R2/CDN)
criado_em      timestamptz default now()
expira_em      timestamptz default now() + interval '60 days'   -- job de limpeza usa isso
```

### 2.6 `profissionais` (colaboradores/atendentes)

Campos relevantes para este handoff: `id`, `empresa_id`, `nome`, `telefone`,
`avatar_url`, `status` ('ativo'), `disponibilidade` ('online'/'offline', setado pelo
frontend via `sendBeacon` ao fechar aba), `usuario_id` (se o profissional também loga
no painel — no seu caso pode nem existir usuário/login, já que ele não usa o app).

---

## 3. Pipeline de recebimento — LangGraph/LangChain (ai-service)

Esta seção é a mais importante para o seu caso de uso: **como o sistema recebe
mensagem via UAZAPI e diferencia "o cliente escreveu" de "o atendente respondeu pelo
próprio celular"**, incluindo texto, áudio, imagem, documento e vídeo, nos dois
sentidos.

### 3.1 Entrada: webhook único da UAZAPI

Você registra **uma única URL de webhook** na UAZAPI (global, para todas as
instâncias — o `token` no corpo do payload é que identifica QUAL instância mandou).
Endpoint FastAPI:

```python
@router.post("/uazapi/webhook")
async def uazapi_webhook(request: Request):
    body = await request.json()
    token = body.get("token")
    instancia = find_instancia_by_token(token)        # -> empresa_id, instancia_id
    if not instancia:
        return {"ok": True, "skipped": "instancia_nao_encontrada"}

    event_type = (body.get("EventType") or "").lower()
    if event_type == "messages_update":
        # tiques de entregue/lido — payload de ATUALIZAÇÃO, não mensagem nova.
        # NUNCA passar isso pelo normalize_uazapi (viraria balão novo/reprocessaria IA).
        ...
        return {"ok": True}
    if event_type and event_type not in {"messages", "message"}:
        return {"ok": True, "skipped": f"evento_{event_type}"}

    normalized = normalize_uazapi(body)   # ver 3.2 — aqui mora a lógica crítica

    # enfileira (desacopla o HTTP do processamento; sobrevive a pico de tráfego)
    await pool.execute(
        "INSERT INTO langchain.inbound_queue (empresa_id, instancia_id, source, payload) "
        "VALUES ($1, $2, 'uazapi', $3::jsonb)",
        empresa_id, instancia_id, json.dumps(normalized),
    )
    await pool.execute("NOTIFY langchain_inbound_queue, 'new'")
    return {"ok": True}
```

**Por que fila em vez de processar inline no handler HTTP**: um webhook que demora
(download de mídia, chamada de IA, R2) atrasa a resposta 200 para a UAZAPI, que
reenvia se não vir 2xx rápido — reentrega vira mensagem duplicada / IA respondendo
2x. Gravar na fila e responder 200 imediatamente resolve isso. Some com dedupe por
`wa_message_id` (idempotência — mesma mensagem chegando de novo não duplica linha).

### 3.2 `normalize_uazapi` — a parte que resolve "cliente vs. atendente pelo celular"

O payload cru da UAZAPI tem dois blocos: `chat` (descreve a conversa/contato) e
`message` (descreve a mensagem específica). O campo que decide tudo é
**`message.fromMe`**:

- `fromMe = false` → mensagem **do cliente** chegando.
- `fromMe = true`  → mensagem que **SAIU** por aquele número. No seu caso, como o
  atendente não usa o app, **toda mensagem `fromMe=true` que não foi você mesmo que
  mandou via API é o atendente respondendo pelo próprio celular.**

**Armadilha nº 1 — telefone**: em `fromMe=true`, `message.sender_pn` aponta para o
DONO da instância (a empresa), não para o cliente. O telefone do CLIENTE (que é quem
identifica a conversa) precisa vir de `chat.wa_chatid` (o chat individual = o outro
lado da conversa):

```python
from_me = bool(message.get("fromMe"))
if from_me:
    telefone = digits(chat.get("wa_chatid") or message.get("sender_pn"))
else:
    telefone = digits(message.get("sender_pn") or chat.get("wa_chatid"))
```

**Armadilha nº 2 — mesma regra vale para o `@lid`** (endereçamento alternativo do
WhatsApp): em `fromMe=true`, `message.chatlid` pode apontar para OUTRO contato (o
último chat do aparelho), não para o destinatário. Use sempre `chat.wa_chatlid`
quando `from_me=true`; só caia para `message.chatlid` como fallback quando
`from_me=false`. (Bug real de produção: uma resposta pelo celular endereçou para o
`@lid` errado e a mensagem foi para outra pessoa.)

**Armadilha nº 3 — nome do contato**: os campos `senderName`/`pushName` em `message.*`
descrevem quem MANDOU a mensagem — em `fromMe=true` isso é o nome da PRÓPRIA empresa,
não do cliente. Só leia esses campos quando `from_me=false`; em `fromMe=true` use
apenas os campos de `chat.*` (que descrevem o contato, nos dois sentidos).

**Tipo de conteúdo (`kind`)** — mapeado do `message.messageType` da UAZAPI:

```python
_UAZAPI_TYPE_MAP = {
    "Conversation": "text", "ExtendedTextMessage": "text",
    "AudioMessage": "audio", "ImageMessage": "image",
    "DocumentMessage": "document", "VideoMessage": "video",
    "ReactionMessage": "reaction", "StickerMessage": "sticker",
}
```
Para mídia, a URL pode vir em campos diferentes conforme a versão da UAZAPI
(`mediaUrl`, `downloadUrl`, `url`, `audioUrl`...) — teste todos em ordem. Se a URL
vier vazia (mídia criptografada), chame
`POST {UAZAPI_BASE_URL}/message/download` com `{"id": message_id, "generate_mp3": true}`
e o header `token` — a UAZAPI devolve a URL já descriptografada.

**Citação/reply**: se o cliente OU o atendente (pelo celular) responderam citando uma
mensagem anterior, o campo `message.quoted` traz `{ id, fromMe, messageType, ... }` —
extraia `reply_to_wa_id` (o `id` citado), `reply_to_text` (resumo/rótulo do que foi
citado) e `reply_to_from_me`, para o front desenhar o "balão citado" igual ao
WhatsApp. Best-effort: nunca deixe essa extração quebrar o recebimento da mensagem.

Saída canônica de `normalize_uazapi` (isso é o que vai para a fila):
```json
{
  "source": "uazapi",
  "from_me": true,
  "telefone": "5511999999999",
  "chatlid": "158214230417410",
  "nome": "Nome do contato",
  "kind": "audio",
  "text": "",
  "media_url": "https://.../files/xxxx.ogg",
  "message_id": "3EB0...",
  "reply_to_wa_id": null, "reply_to_text": null, "reply_to_from_me": null,
  "raw": { "...payload bruto original..." }
}
```

### 3.3 `dispatch()` — o que acontece depois de tirar da fila

```python
async def dispatch(job):
    payload = job["payload"]
    if payload.get("from_me"):
        await handle_from_me(empresa_id=..., instancia_id=..., payload=payload)
    else:
        await handle_cliente(empresa_id=..., instancia_id=..., payload=payload)  # -> IA, se houver
```

#### `handle_from_me` — atendente respondeu PELO CELULAR (o caso central do seu app)

```python
async def handle_from_me(*, empresa_id, instancia_id, payload):
    kind, telefone = payload["kind"], payload["telefone"]

    # 1) Mídia: resolve URL descriptografada (se preciso) e MOVE pro storage
    #    permanente (R2) ANTES do insert — ver seção 5.
    if kind in {"audio","image","document","video","sticker"} and not payload.get("media_url"):
        payload["media_url"] = await resolver_url_uazapi(payload)
    if kind in KIND_TO_TIPO_STORAGE and payload.get("media_url"):
        payload = await persistir_midia_em_r2(empresa_id, instancia_id, payload)

    # 2) Grava na timeline: direcao=SENT, enviado_por='celular'
    insert_mensagem_celular(empresa_id, instancia_id, payload)

    # 3) Pausa automática da IA (ou, no seu caso, simplesmente marca
    #    "atendente está no controle" para o painel exibir)
    pausa_segundos = get_pausa_configurada(empresa_id, instancia_id)
    if pausa_segundos > 0:
        session_id = build_session_id(telefone, empresa_id, instancia_id)
        if not await tem_pausa_manual_ativa(session_id):     # pausa manual > automática
            await set_block(session_id, pausa_segundos)        # Redis (seção 4.6 / 5)
            atualizar_conversa(tempo_pausa=pausa_segundos, tempo_pausa_inicio=agora)
```

Do lado do CLIENTE (`from_me=False`), o fluxo espelha: grava `direcao=RECEIVED,
enviado_por='user'`, e SÓ ENTÃO — se seu app tiver IA — checa o bloqueio Redis; se
não estiver bloqueado, roda a IA e grava a resposta como `SENT/assistant`. No seu
caso (sem IA nas conversas dos atendentes, já que eles não usam o app), esse ramo
pode ser só "grava a mensagem e deixa aparecer no painel" — sem chamar LLM nenhum.

**Ordem de operações importa** (mantenha esta ordem, ela evita bugs reais já vistos
em produção):
1. Resolver mídia (URL descriptografada) **antes** de qualquer insert.
2. Mover a mídia para o storage permanente **antes** do insert na tabela de
   mensagens — assim a URL gravada já nasce definitiva (nunca fica um período com
   URL temporária da UAZAPI, que expira em poucos dias).
3. Inserir a mensagem (SEMPRE, mesmo que a pausa automática falhe depois — a
   pessoa que está olhando o painel precisa ver a mensagem, aconteça o que
   acontecer com o resto do pipeline).
4. Só depois, tratar pausa/bloqueio/notificação — tudo isso é "efeito colateral",
   nunca pode impedir a mensagem de aparecer.
5. Idempotência por `wa_message_id`: antes de inserir, cheque se aquele
   `wa_message_id` já existe na tabela — a UAZAPI reentrega webhooks que não
   respondem 2xx rápido, e sem essa trava a mesma mensagem vira 2+ balões.

### 3.4 Fila (`langchain.inbound_queue`) — schema mínimo

```sql
CREATE SCHEMA IF NOT EXISTS langchain;
CREATE TABLE langchain.inbound_queue (
    id           BIGSERIAL PRIMARY KEY,
    empresa_id   UUID NOT NULL,
    instancia_id UUID NOT NULL,
    source       TEXT NOT NULL CHECK (source IN ('uazapi','meta')),
    payload      JSONB NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','done','error')),
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_inbound_queue_pending ON langchain.inbound_queue (created_at)
  WHERE status IN ('pending','processing');
```

Worker: `SELECT ... WHERE status='pending' ORDER BY created_at FOR UPDATE SKIP LOCKED
LIMIT 1` dentro de uma transação, marca `processing`, processa, marca `done`/`error`
(com retry até N tentativas). Rode **N jobs concorrentes**, mas **serialize por
conversa** (lock em memória por `empresa:instancia:telefone`) — sem isso, duas
mensagens seguidas do mesmo contato podem gravar fora de ordem. Tenha *sempre* um
timeout por job (ex.: 180s): um job pendurado (download que não responde) não pode
travar a fila inteira — é fila compartilhada entre todos os contatos/empresas.

---

## 4. Página de Conversas — estrutura da UI

Layout de 2 (ou 3) colunas, mobile-first (lista some quando uma conversa é
selecionada em telas < 600px):

```
┌─────────────────────────┬───────────────────────────────┬──────────────────┐
│ COLUNA 1 — Lista         │ COLUNA 2 — Chat aberto         │ COLUNA 3 (flutua)│
│ - topo: título + status  │ - header: nome/foto/telefone   │ Detalhes do      │
│   de conexão realtime    │   + badges (pausada/aberta/    │ contato/conversa │
│ - seletor de instância   │   fechada)                     │ (abre por cima,  │
│   (pills horizontais)    │ - histórico de mensagens       │ position fixed)  │
│ - abas (Todas/Minhas/    │   (scroll, bolha por           │                  │
│   Não atribuídas/        │   direção+tipo)                │                  │
│   Resolvidas/Arquivadas) │ - rodapé: campo de envio       │                  │
│ - lista de cards         │   (só se o seu app permitir     │                  │
│   (scroll infinito)      │   responder pelo painel)        │                  │
└─────────────────────────┴───────────────────────────────┴──────────────────┘
```

### 4.1 Seletor de instância/número (o requisito "1 aba por número conectado")

Pills horizontais no topo da lista, uma por instância ativa da empresa + "Todos":

```html
<button @click="instanciaSelecionada = null">Todos ({{ total }})</button>
<button v-for="inst in instanciasAtivas" @click="instanciaSelecionada = inst.id"
        :title="inst.status === 'connected' ? `${inst.nome} — Online` : `${inst.nome} — Offline`">
  <span class="dot" :class="inst.status === 'connected' ? 'verde' : 'cinza'" />
  {{ inst.nome }}
</button>
```
Clicar num número filtra `conversas` por `instancia_id === inst.id`. Isso só aparece
quando há mais de 1 instância ativa (empresa com 1 número só não precisa do
seletor). No SEU app — com `instancias_uazapi.profissional_id` **[NOVO]** — o nome de
cada pill já é o nome do profissional dono daquele número.

### 4.2 Abas

| Aba | Filtro |
|---|---|
| Todas | conversas não resolvidas (`resolved_at IS NULL`) e não arquivadas |
| Minhas | + `assigned_to_professional_id = eu` |
| Não atribuídas | + `assigned_to_professional_id IS NULL` |
| Resolvidas | `resolved_at IS NOT NULL` |
| Arquivadas | `arquivada = true` (fora da contagem das outras abas) |

Contadores calculados client-side sobre a lista já carregada (evita 1 query por
badge). Reabrir uma conversa resolvida (cliente manda mensagem de novo) deve **zerar
`resolved_at`/`closed_at` via trigger** no INSERT de `mensagens` — a conversa "volta"
sozinha para Todas/Não atribuídas sem ação manual.

### 4.3 Card da conversa (coluna 1)

Campos exibidos, da esquerda pra direita / cima pra baixo:
- **Avatar**: foto do contato (se válida) ou iniciais sobre gradiente; ponto verde
  sobreposto se `status === 'online'`.
- **Nome** do contato (trunca com `truncate`) + badge de roteamento (se aplicável).
- **Prévia da última mensagem** (`ultima_mensagem` — já formatada como "🎵 Áudio",
  "📷 Imagem", "🎥 Vídeo", "📎 Arquivo" ou o texto puro).
- **Horário** da última mensagem (formatado relativo: "12:34", "Ontem", "Seg").
- **📌** se a conversa está fixada.
- **Badge de não lidas** (verde, `nao_lidas > 0`).
- **Badge de atribuição**: "Atribuído para mim" (verde) ou "Atribuído para {nome}"
  (roxo) quando `assigned_to_professional_id` está preenchido.
- **Menu de 3 pontos**: atribuir para mim / atribuir para outro profissional (lista
  buscável, com filtro online/offline) / remover atribuição.

### 4.4 Painel de detalhes (coluna 3, flutuante)

Header (fundo com gradiente da cor primária):
- botão fechar (X)
- avatar grande (clicável → amplia foto)
- nome (editável inline) + telefone
- **badge "IA/atendimento pausado"** se `tempo_pausa` ainda não expirou (contagem
  regressiva ao vivo; texto especial "Pausado Permanente" se o valor for o teto usado
  para permanente, ex.: 31536000s = 1 ano)
- **badge "atendimento em andamento"** (verde) se `opened_at && !closed_at` — mostra
  cronômetro rodando (`agora - opened_at`, recalculado por um `ref` de "tempo atual"
  atualizado a cada segundo)
- **badge "atendimento encerrado"** (cinza) se `closed_at` preenchido — mostra
  duração final fixa ("Resolvida em 3m 12s" / "Resolvida em 1h 5m")

Corpo (seções abaixo do header, scroll):
- edição de nome/etiquetas/observações do contato
- histórico de atendentes (`conversa_atendentes_historico`, últimos N eventos:
  atribuído/desatribuído/fechado, com nome + timestamp)
- mídias/links/documentos trocados nesta conversa (galeria)
- ações: **Abrir atendimento**, **Pausar (bloquear)**, **Fechar/Resolver**,
  **Atribuir/Transferir**, **Arquivar**

### 4.5 Abrir atendimento (registra início do tempo de atendimento)

Disparado automaticamente quando alguém interage com a conversa (ex.: manda uma
mensagem pelo painel) OU manualmente por um botão "Assumir atendimento":

```ts
async function abrirAtendimento(conversaId: string) {
  const atual = await db.conversas.select('opened_at, closed_at, resolved_at, assigned_to_professional_id').eq('id', conversaId).single()

  if (!atual.opened_at || atual.closed_at || atual.resolved_at) {
    // nunca aberta, OU estava fechada/resolvida -> abre agora
    await db.conversas.update({
      opened_at: now(), closed_at: null, resolved_at: null, status: 'aberta',
      ...(euSouOutroProfissional && { assigned_to_professional_id: eu, assigned_at: now(), assigned_by: meuUsuarioId }),
    }).eq('id', conversaId)
  } else if (atendidaPorOutroProfissional) {
    // já aberta, mas com outro dono -> reatribui pra quem está agindo agora
    await db.conversas.update({ assigned_to_professional_id: eu, assigned_at: now(), assigned_by: meuUsuarioId }).eq('id', conversaId)
  }
}
```
No SEU app — sem atendimento pelo painel — "abrir atendimento" pode ser disparado
automaticamente **pelo próprio `handle_from_me`** (seção 3.3): quando chega a
primeira mensagem `fromMe=true` de uma conversa sem `opened_at`, já marca
`opened_at = agora` e `assigned_to_professional_id = <profissional dono da
instância>` — sem precisar de clique nenhum, porque o "abrir" É o atendente ter
respondido pelo celular.

### 4.6 Pausar (bloquear a IA / marcar "humano no controle")

Dois tipos de pausa, coexistindo pelo MESMO campo (`tempo_pausa`/`tempo_pausa_inicio`
na tabela + chave Redis, seção 5), mas com prioridade diferente:

- **Automática**: disparada por `handle_from_me` toda vez que chega uma mensagem
  `fromMe=true` (o atendente respondeu pelo celular) — dura `pausa_segundos`
  (config, ex.: 24h padrão), e **renova a cada nova mensagem do atendente**.
- **Manual**: o dono/atendente escolhe explicitamente no painel (ex.: modal
  "Pausar por 1h / 10 dias / Permanente"). Uma pausa manual **nunca é rebaixada**
  por uma automática — se o atendente mandou uma mensagem pelo celular enquanto
  havia uma pausa manual de "10 dias" ativa, a automática (que seria menor) É
  IGNORADA. Isso evita que o próprio atendente encurte sem querer uma pausa que o
  dono configurou deliberadamente.

No seu app (sem IA para pausar), o mesmo mecanismo serve para **"marcar que um
humano está no controle daquela conversa"** — útil para o dashboard/relatório saber
que o atendente está ativo ali, mesmo sem IA nenhuma envolvida.

### 4.7 Fechar / Resolver atendimento (registra o tempo total)

```ts
async function fecharAtendimento(conversa) {
  await db.conversas.update({
    closed_at: now(),
    resolved_at: now(),      // vai para a aba "Resolvidas"
    status: 'fechada',
    assigned_to_professional_id: null, assigned_at: null, assigned_by: null,  // libera a conversa
  }).eq('id', conversa.id)

  await registrarHistorico({ conversa, acao: 'fechado', profissionalId: donoAntesDeFechar })

  const tempoMs = new Date(closed_at) - new Date(conversa.opened_at)
  // tempoMs / 60000 = minutos de atendimento -> é ISSO que alimenta o relatório
}
```
`closed_at - opened_at` é a métrica "tempo de atendimento" por conversa. Guarde
sempre os dois timestamps (nunca calcule e descarte) — o relatório (seção 6) precisa
agregar isso depois, por atendente/dia/semana/mês.

**Importante**: se o cliente mandar mensagem de novo depois de fechada, um trigger
`AFTER INSERT ON mensagens` (na direção `RECEIVED`) deve **reabrir** a conversa
(`resolved_at = null`, `closed_at = null`, `status = 'aberta'`) automaticamente — sem
isso a conversa fica presa em "Resolvidas" mesmo com mensagem nova chegando.

### 4.8 Renderização das mensagens no chat

Alinhamento da bolha: `direcao = 'RECEIVED'` → esquerda (cliente); `direcao = 'SENT'`
→ direita (empresa, qualquer que seja `enviado_por`).

Rótulo/ícone do remetente (dentro do balão ou no rodapé, útil pra auditoria):
| `enviado_por` | Rótulo sugerido |
|---|---|
| `user` | (nada — é o cliente, já fica à esquerda) |
| `assistant` | "🤖 Assistente" |
| `humano` | nome do profissional (`enviado_por_profissional_id` → `profissionais.nome`) |
| `celular` | "📱 {nome do profissional dono da instância}" — **este é o selo que avisa "respondido fora do app"** |

Conteúdo por `kind`:
- `text` → `mensagem` (texto puro).
- `audio` → player de áudio lendo `audio_url`.
- `image` → `<img>` lendo `mensagem` (a URL da imagem já fica nesse campo — o
  trigger/parser detecta pela extensão).
- `document` → card de arquivo com ícone + `arquivo_nome` (nome original — a URL usa
  UUID e perde o nome, por isso salvar `arquivo_nome` à parte é necessário).
- `video` → player de vídeo lendo `mensagem`.
- `sticker` → imagem pequena (96×96), tratamento visual diferente de `image` normal.
- Se houver `reply_to_wa_id`/`reply_to_text` → desenha o bloco "citando: ...” acima
  do conteúdo, igual ao WhatsApp nativo.

---

## 5. Armazenamento de mídia — Cloudflare R2

**Por quê**: a UAZAPI hospeda mídia em URLs temporárias
(`https://.../files/<hash>.<ext>`) que **expiram em poucos dias**. Se você gravar
essa URL direto na tabela de mensagens, a imagem/áudio quebra depois de um tempo.
Solução: baixar e re-hospedar num bucket próprio (permanente) ANTES do INSERT.

### 5.1 Fluxo

```python
async def mover_para_r2(*, url_original, tipo, empresa_id, instancia_id, mensagem_id, auth_header=None):
    if "SEU_DOMINIO_CDN" in url_original:
        return url_original          # idempotência: já é do seu R2

    resp = await httpx.get(url_original, headers=auth_header, timeout=30)
    body, content_type = resp.content, resp.headers["content-type"]

    ext = MIME_TO_EXT.get(content_type) or extensao_da_url(url_original) or "bin"
    key = f"{pasta_por_tipo[tipo]}/{empresa_id}/{instancia_id or 'sem-instancia'}/{mensagem_id}.{ext}"

    url_r2 = await upload_s3_compatible(bucket=R2_BUCKET, key=key, body=body, content_type=content_type)

    db.midias_conversas.insert({
        "empresa_id": empresa_id, "instancia_id": instancia_id, "mensagem_id": mensagem_id,
        "storage_path": key, "tipo": tipo, "url_original": url_original, "url_storage": url_r2,
    })
    return url_r2
```

- Nunca deixe uma falha de upload quebrar o recebimento da mensagem: se o R2 falhar,
  **grave a URL temporária da UAZAPI mesmo assim** (fallback: melhor mostrar por
  alguns dias do que perder a mídia).
- R2 é S3-compatible: use qualquer SDK S3 (`boto3` em Python, `@aws-sdk/client-s3`
  em Node) apontando `endpoint_url = https://{ACCOUNT_ID}.r2.cloudflarestorage.com`.
- Estrutura de pastas por tipo lógico: `audio/`, `imagens/`, `pdf/`, `documentos/`,
  `video/` (sticker reaproveita `imagens/`, é `.webp`).
- Key: `{pasta}/{empresa_id}/{instancia_id|"sem-instancia"}/{mensagem_id}.{ext}` — dá
  para reconstruir o dono de qualquer arquivo só olhando o path.
- `midias_conversas.expira_em` (ex.: `now() + 60 dias`) alimenta um job de limpeza
  periódico que apaga do bucket + da tabela o que passou da validade — sem isso o
  bucket cresce para sempre.

### 5.2 Variáveis de ambiente

| Variável | Uso |
|---|---|
| `R2_ACCOUNT_ID` | conta Cloudflare |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | credenciais S3-compatible |
| `R2_BUCKET_NAME` | bucket de destino |
| `R2_PUBLIC_URL` | domínio público/CDN na frente do bucket (ex.: `https://files.seudominio.com`) |

---

## 6. Redis — sessão, pausa automática e pausa manual

Compatível com um formato simples de chave, fácil de auditar manualmente:

```
session_id  = "{telefone}_{empresa_id_sem_hifen}_{instancia_id_sem_hifen}"
block_key   = "{session_id}_block"           # TTL = tempo de pausa (segundos)
manual_key  = "{session_id}_block_manual"    # marcador: essa pausa foi definida NA MÃO
```

**Telefone SEM o nono dígito**: a UAZAPI às vezes entrega o telefone sem o nono
dígito do celular (comum em DDDs do interior — 75, 71...), então o MESMO contato
pode aparecer como `5575991198502` (seu banco/front) e `557591198502` (payload
UAZAPI). Ao checar/limpar bloqueio, gere as duas variantes e cheque as duas —
senão um bloqueio setado numa forma não é encontrado/limpo pela outra forma.

```python
def build_session_id(telefone, empresa_id, instancia_id) -> str:
    return f"{telefone}_{empresa_id.replace('-','')}_{instancia_id.replace('-','')}"

def session_ids_for(telefone, empresa_id, instancia_id) -> list[str]:
    variantes = tel_vars(telefone)  # [com_9_digitos, sem_9_digitos] ou equivalente
    return [build_session_id(t, empresa_id, instancia_id) for t in variantes]
```

Operações:
```python
async def set_block(session_id, ttl_seconds):           # pausa AUTOMÁTICA
    await redis.set(block_key(session_id), "true", ex=ttl_seconds)

async def set_block_manual(session_id, ttl_seconds):     # pausa MANUAL
    await redis.set(block_key(session_id), "true", ex=ttl_seconds)
    await redis.set(manual_block_key(session_id), "1", ex=ttl_seconds)  # marcador

async def has_manual_block_any(session_ids) -> bool:     # automática consulta isto ANTES de sobrescrever
    ...
```

Regra de prioridade (repetida da seção 4.6 porque é a parte que mais gera bug se
esquecida): **antes de `set_block` automático, sempre cheque `has_manual_block_any` —
se True, não sobrescreva**. Sem essa checagem, o próprio atendente respondendo pelo
celular encurta uma pausa "Permanente" que o dono tinha configurado.

O Redis aqui é cache/sinalização rápida — **a fonte de verdade do histórico de
conversa continua sendo a tabela `mensagens` no Postgres**; nada crítico deve
depender só do Redis sobreviver (TTL, restart do container, etc. podem limpar).

---

## 7. Tempo real — Broadcast do banco (Supabase Realtime)

**Não use `postgres_changes`** (decodifica o WAL inteiro, caro em banco com volume;
manda payload pra quem não devia ver por padrão até a RLS filtrar). Use **Broadcast
autenticado via trigger** — o banco decide o que mandar, a RLS decide quem recebe.

### 7.1 Trigger (1 por tabela que precisa ser "ao vivo")

```sql
create or replace function public.broadcast_mensagem()
returns trigger language plpgsql security definer set search_path = public as $$
declare rec jsonb; emp uuid;
begin
  -- otimização: ignora UPDATE que só mexeu em updated_at (nada muda na tela)
  if TG_OP = 'UPDATE' and (to_jsonb(OLD) - 'updated_at') is not distinct from (to_jsonb(NEW) - 'updated_at') then
    return null;
  end if;

  if TG_OP = 'DELETE' then rec := to_jsonb(OLD); emp := OLD.empresa_id;
  else rec := to_jsonb(NEW); emp := NEW.empresa_id; end if;
  if emp is null then return null; end if;

  begin
    perform realtime.send(jsonb_build_object('type', TG_OP, 'record', rec), 'mensagem', 'empresa:' || emp::text, true);
  exception when others then null;  -- broadcast NUNCA pode quebrar a escrita
  end;
  return null;
end; $$;

create trigger trg_broadcast_mensagem after insert or delete or update on public.mensagens
  for each row execute function public.broadcast_mensagem();
-- o mesmo padrão para `conversas` (evento 'conversa') e `instancias_uazapi` (evento 'instancia')
```

### 7.2 Autorização — quem pode ouvir o tópico `empresa:{id}`

```sql
create or replace function public.topicos_empresa_do_usuario()
returns setof text language sql stable security definer set search_path = public as $$
  select 'empresa:' || e.id::text from empresas e where e.auth_user_id = (select auth.uid())
  union
  select 'empresa:' || ue.empresa_id::text from usuarios_empresas ue
  join usuarios u on u.id = ue.usuario_id where u.auth_user_id = (select auth.uid())
$$;

create policy broadcast_empresa_receber on realtime.messages for select to authenticated
  using (extension = 'broadcast' and (select realtime.topic()) in (select public.topicos_empresa_do_usuario()));
```

### 7.3 Frontend — 1 canal privado por empresa, multiplexado por evento

Ponto de atenção real (já causou "painel mudo com o banco intacto" em produção):
canal **privado** (`{config:{private:true}}`) exige `supabase.realtime.setAuth(jwt)`
com `await` **antes** do `.subscribe()` — sem esperar, o join sai sem token, a RLS
recusa e o canal cai silenciosamente em `CHANNEL_ERROR`.

```ts
const channel = supabase.channel(`empresa:${empresaId}`, { config: { private: true } })
// registrar TODOS os eventos conhecidos ANTES do subscribe (exigência do Phoenix)
channel.on('broadcast', { event: 'mensagem' }, ({ payload }) => aplicarEventoMensagem(payload.type, payload.record))
channel.on('broadcast', { event: 'conversa' }, ({ payload }) => aplicarEventoConversa(payload.type, payload.record))

const { data } = await supabase.auth.getSession()
if (data?.session?.access_token) await supabase.realtime.setAuth(data.session.access_token)
channel.subscribe()
```
Reautentique no `CHANNEL_ERROR` (o JWT expira em ~1h e o rejoin automático reusa o
token velho se você não renovar). Use **um único canal compartilhado por empresa**
(um singleton/composable com refcount) se várias partes da tela (lista de conversas +
som de notificação global, por exemplo) precisam do mesmo tópico — o Realtime só
permite 1 join por tópico por socket.

---

## 8. Métricas / Relatórios

### 8.1 Tempo médio de 1ª resposta (TMPR) — já pronto no Agzap, reaproveitável 1:1

```sql
create or replace function get_tmpr_empresa(p_empresa_id uuid, p_inicio timestamptz, p_fim timestamptz)
returns table(tmpr_segundos numeric, total_conversas integer)
language sql security definer set search_path = public as $$
  with primeira_recebida as (
    select distinct on (conversa_id) conversa_id, data_hora as recebida_em
    from mensagens
    where empresa_id = p_empresa_id and direcao = 'RECEIVED'
      and data_hora between p_inicio and p_fim
    order by conversa_id, data_hora asc
  ),
  primeira_resposta as (
    select pr.conversa_id, pr.recebida_em,
      (select m.data_hora from mensagens m
       where m.conversa_id = pr.conversa_id and m.direcao = 'SENT' and m.data_hora > pr.recebida_em
       order by m.data_hora asc limit 1) as respondida_em
    from primeira_recebida pr
  )
  select coalesce(avg(extract(epoch from (respondida_em - recebida_em))), 0)::numeric, count(*)::integer
  from primeira_resposta where respondida_em is not null;
$$;
```
No seu app, a "resposta" que zera o cronômetro do cliente é justamente a mensagem
`SENT/enviado_por='celular'` — ou seja, **o mesmo cálculo funciona sem alteração**,
porque `direcao='SENT'` já cobre qualquer remetente do lado da empresa.

### 8.2 Extensões sugeridas para o seu relatório (por atendente/dia/semana/mês)

```sql
-- Mensagens recebidas por atendente (via instância dele) num período:
select i.profissional_id, date_trunc('day', m.data_hora) as dia, count(*) as recebidas
from mensagens m
join instancias_uazapi i on i.id = m.instancia_id
where m.direcao = 'RECEIVED' and m.empresa_id = :empresa_id
group by 1, 2;

-- Tempo de atendimento por atendente (closed_at - opened_at), a partir de conversas:
select assigned_to_professional_id, avg(closed_at - opened_at) as tempo_medio, count(*) as atendimentos
from conversas
where empresa_id = :empresa_id and closed_at is not null and opened_at between :inicio and :fim
group by 1;

-- 1ª resposta do ATENDENTE especificamente (não IA) — filtra por enviado_por:
-- troque "direcao='SENT'" por "direcao='SENT' and enviado_por='celular'" no CTE
-- `primeira_resposta` acima, se quiser medir só o humano e não contar respostas de IA.
```
`instancias_uazapi.profissional_id` **[NOVO — seção 2.1]** é o que permite o `JOIN`
direto acima; sem ele você precisaria inferir o profissional por
`conversas.assigned_to_professional_id`, que reflete "quem está atendendo agora" e
não necessariamente "dono do número" (pode divergir se houver reatribuição manual).

---

## 9. Checklist de variáveis de ambiente (resumo)

| Variável | Onde | Para quê |
|---|---|---|
| `UAZAPI_BASE_URL` | app + ai-service | base da API do canal WhatsApp |
| `UAZAPI_ADMIN_TOKEN` | app (backend) | criar instância nova |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | app + ai-service | banco principal (conversas/mensagens) |
| `SUPABASE_ANON_KEY` | app (frontend) | auth do usuário + Realtime |
| `POSTGRES_URL` (self-hosted) | ai-service | fila `langchain.inbound_queue` + checkpoints LangGraph |
| `REDIS_URL` | ai-service | pausa automática/manual, sessão |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET_NAME` / `R2_PUBLIC_URL` | ai-service | storage permanente de mídia |

---

## 10. Resumo do que é diferente no seu app vs. Agzap hoje

1. **Sem responder pelo painel** (ou opcional): o campo `enviado_por='humano'`
   (resposta pelo app) pode nem existir no seu fluxo — praticamente tudo do lado
   "empresa" vira `enviado_por='celular'`. Isso simplifica a UI (não precisa de caixa
   de envio funcional, só o histórico).
2. **`instancias_uazapi.profissional_id` [NOVO]** — vínculo direto 1 instância = 1
   profissional, que o Agzap não tem hoje (lá é usuário dono da conta, não o
   atendente operacional). Sem IA no meio, faz sentido isso ser 1:1 explícito desde
   o schema.
3. **Pausa automática vira "indicador de humano ativo"**, não necessariamente pausa
   de IA (a menos que você também tenha IA respondendo quando o atendente NÃO está
   ativo — nesse caso a lógica da seção 4.6/6 se aplica sem alteração nenhuma).
4. **"Abrir atendimento" pode ser 100% automático**: a primeira mensagem
   `fromMe=true` de uma conversa sem `opened_at` já abre e atribui — sem o usuário
   precisar clicar em nada, porque não existe "assumir" pelo painel, só pelo
   celular.
5. Métricas (seção 8) devem ser pensadas desde já com `JOIN` em
   `instancias_uazapi.profissional_id`, já que esse é o eixo principal do relatório
   pedido ("quantas mensagens por atendente/dia/semana/mês", "tempo até a 1ª
   resposta por atendente").
