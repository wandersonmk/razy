# Instalação de uma nova instância do Razy (outro cliente, do zero)

> **Para quem é este documento:** o técnico — ou o assistente de IA — que vai levantar uma
> cópia completa e independente deste sistema para **outro cliente**, com
> **Supabase novo, Vercel nova, EasyPanel novo (VPS nova ou projeto novo) e chave OpenAI
> nova**. Nenhum recurso é compartilhado com a instalação original.
>
> Leia a seção [1](#1-o-que-é-este-sistema) inteira antes de executar qualquer passo: sem
> entender os quatro pedaços e como eles se acham, é fácil subir tudo e o WhatsApp não
> responder ninguém.
>
> Arquivos que acompanham este guia:
> - [supabase/schema_completo.sql](supabase/schema_completo.sql) — banco inteiro (19 tabelas, 11 funções, 4 triggers, RLS, Storage, Realtime). Gerado por introspecção do banco de produção em 22/09/2026.
> - O **`.env` da instalação atual** — copie esse arquivo (ele está no `.gitignore`, não vem pelo GitHub: pegue direto da máquina onde o projeto roda hoje) e **troque todos os valores** pelos do cliente novo. Ele é o ponto de partida do ambiente; a seção [3.3](#33-o-env-da-nova-instalação) diz exatamente o que substituir e o que acrescentar nele.
> - [DEPLOY_LANGCHAIN_LANGGRAPH_EASYPANEL.md](DEPLOY_LANGCHAIN_LANGGRAPH_EASYPANEL.md) — passo a passo longo de VPS + EasyPanel (comprar, instalar, Postgres, Redis, GitHub, domínio). Este guia aqui referencia aquele nas etapas 5 e 6.
> - [ESTRUTURA_BANCO_DADOS.md](ESTRUTURA_BANCO_DADOS.md) — descrição coluna a coluna (foi escrito em 04/08/2026, antes das tabelas de conversas/profissionais; o SQL acima é a fonte atual).

---

## Índice

| # | Etapa | Onde | Tempo |
|---|---|---|---|
| [1](#1-o-que-é-este-sistema) | Entender a arquitetura | — | 10 min de leitura |
| [2](#2-o-que-provisionar-antes-de-começar) | Contas e credenciais | — | 30 min |
| [3](#3-passo-1--repositório-da-nova-instância) | Repositório, `.env` e o que trocar no código | GitHub | 25 min |
| [4](#4-passo-2--supabase-novo) | Banco, Storage, Realtime, Auth | Supabase | 30 min |
| [5](#5-passo-3--uazapi-whatsapp) | Servidor UAzAPI e webhook | UAzAPI | 20 min |
| [6](#6-passo-4--easypanel-serviço-de-ia) | Postgres, Redis, ai-service | EasyPanel | 45 min |
| [7](#7-passo-5--vercel-painel) | Painel Nuxt | Vercel | 20 min |
| [8](#8-passo-6--openai) | Chave e saldo | OpenAI | 10 min |
| [9](#9-passo-7--amarrar-as-pontas) | Webhook, CORS, URLs cruzadas | todos | 15 min |
| [10](#10-passo-8--primeiro-uso-no-painel) | Criar conta, canal, IA | Painel | 20 min |
| [11](#11-checklist-de-validação-ponta-a-ponta) | Validação | — | 30 min |
| [12](#12-tabela-mestre-de-variáveis-de-ambiente) | Referência de variáveis | — | — |
| [13](#13-mapa-do-código-para-quem-vai-dar-manutenção) | Mapa do código | — | — |
| [14](#14-regras-de-negócio-que-não-estão-no-schema) | Regras que o banco não conta | — | — |
| [15](#15-armadilhas-conhecidas-e-solução-de-problemas) | Troubleshooting | — | — |
| [16](#16-o-que-não-copiar) | O que não copiar | — | — |

---

## 1. O que é este sistema

Um painel de **atendimento e disparo em massa por WhatsApp com IA**. Quatro peças, cada uma
numa plataforma diferente:

```
┌──────────────────────────────┐        ┌───────────────────────────────┐
│  PAINEL (Nuxt 4, SPA)        │        │  SUPABASE                     │
│  Vercel                      │───────▶│  Postgres + Auth + Storage    │
│  app/  server/               │  REST  │  + Realtime (broadcast)       │
│  - SSR desligado (ssr:false) │  RLS   │  19 tabelas, tudo isolado por │
│  - server/api/* = "porteiro" │        │    usuario_id = auth.uid()    │
└──────────┬───────────────────┘        └───────────────▲───────────────┘
           │ X-Internal-Token                           │ SQL direto (asyncpg)
           │                                            │ + Storage (service role)
           ▼                                            │
┌──────────────────────────────┐                        │
│  AI-SERVICE (FastAPI)        │────────────────────────┘
│  EasyPanel (Docker)          │
│  ai-service/app/             │        ┌───────────────────────────────┐
│  - webhook da UAzAPI         │◀──────▶│  UAzAPI (WhatsApp)            │
│  - disparo das campanhas     │        │  instâncias = números         │
│  - follow-up e agendamentos  │        └───────────────────────────────┘
│  - LangChain/LangGraph       │
│  + Postgres dedicado         │        ┌───────────────────────────────┐
│  + Redis dedicado            │───────▶│  OpenAI (gpt-6-luna,          │
└──────────────────────────────┘        │          whisper-1)           │
                                        └───────────────────────────────┘
```

### 1.1 Quem fala com quem (isto é o que quebra quando falta configuração)

| Origem | Destino | Como | Se faltar |
|---|---|---|---|
| Navegador | Supabase | `@supabase/supabase-js` com a **anon key** + JWT do usuário (RLS) | Painel abre em branco / erro de login |
| Navegador | `server/api/*` (Nuxt) | `$fetch` com o JWT no header | — |
| `server/api/*` | ai-service | `POST/GET` com header `X-Internal-Token` | Disparo, Analista e pausa não funcionam |
| `server/api/*` | UAzAPI | `admintoken` (criar instância) e `token` da instância (enviar) | Não cria/conecta canal |
| UAzAPI | ai-service | `POST https://<ai-service>/webhook/uazapi` | **A IA nunca responde ninguém** |
| ai-service | Supabase | Postgres direto (session pooler) + REST do Storage (service role) | Serviço sobe mas não dispara nem grava conversa |
| ai-service | OpenAI | chave lida de `integracoes.openai_api_key` (do painel), com fallback para `OPENAI_API_KEY` do ambiente | IA não gera resposta |

### 1.2 Os dois fluxos que precisam funcionar no final

**Fluxo A — Atendimento (o mais importante):**
1. Cliente manda mensagem no WhatsApp → UAzAPI chama `POST /webhook/uazapi` no ai-service.
2. O webhook responde `200` na hora e processa em segundo plano (`_processar_evento`).
3. Resolve a instância pelo `token` do payload → `usuario_id`, `instancia_id`, profissional.
4. Converte mídia em texto: **áudio sempre** (whisper-1), **imagem** só se `assistentes.ler_imagem`, **documento** só se `ler_documento`.
5. Agrupa mensagens em rajada por **8 segundos** (`IA_JANELA_RAJADA_S`) para responder uma vez só.
6. Gera a resposta (gpt-6-luna, LangGraph com checkpointer no Postgres do EasyPanel + contexto no Redis), envia pela UAzAPI e grava tudo em `conversas`/`mensagens`/`midias_conversas`.
7. Os triggers `broadcast_*` publicam no canal Realtime `usuario:{uuid}` e a tela de Conversas atualiza sozinha.

**Fluxo B — Disparo em massa:**
1. Painel cria `campanhas` + `disparos` no Supabase.
2. `POST /api/campanhas/{id}/iniciar` (Nuxt) valida a posse e repassa ao ai-service com o `INTERNAL_TOKEN`.
3. O ai-service (`services/orquestrador.py`) percorre os contatos, **revalida o status do canal ao vivo na UAzAPI**, respeita `intervalo_segundos`, roteia entre canais (`usar_roteamento`/`alternar_canais`/`canais_ids`) e grava `campanha_logs`.
4. Campanhas agendadas e follow-ups rodam em dois loops de 60s dentro do próprio ai-service, protegidos por *advisory lock* do Postgres (o container sobe com 2 workers).

---

## 2. O que provisionar antes de começar

Junte tudo isto **antes**, porque metade dos passos seguintes precisa de um valor gerado no outro:

| # | Item | Onde consegue | Observação |
|---|---|---|---|
| 1 | Conta **Supabase** do cliente | supabase.com | Região `sa-east-1` (São Paulo) |
| 2 | Conta **Vercel** do cliente | vercel.com | Plano Hobby serve |
| 3 | **VPS + EasyPanel** | Hostinger/Contabo/etc. | 2 vCPU / 8 GB — ver [DEPLOY_LANGCHAIN_LANGGRAPH_EASYPANEL.md](DEPLOY_LANGCHAIN_LANGGRAPH_EASYPANEL.md) §1–3 |
| 4 | **Chave OpenAI** do cliente | platform.openai.com | Precisa de **saldo** (billing), senão o painel mostra o banner "sem saldo" |
| 5 | **Servidor UAzAPI** + `admintoken` | uazapi.com | Um servidor por cliente (ex.: `https://clientex.uazapi.com`) |
| 6 | **Repositório GitHub** com este código | — | Privado; o EasyPanel e a Vercel puxam dele |
| 7 | Domínio (opcional) | — | Um subdomínio para o ai-service (`ia.cliente.com.br`) facilita a vida |
| 8 | Dois segredos gerados por você | `openssl rand -hex 32` | `INTERNAL_TOKEN` e a senha do Postgres do EasyPanel |

> **Regra de ouro:** nenhuma credencial da instalação antiga entra na nova. Nem chave OpenAI,
> nem token da UAzAPI, nem URL do Supabase. Se aparecer um `xdpjhvqfuhjylxaishks` ou um
> `razycorretora.uazapi.com` no ambiente novo, é sobra — corrija.

---

## 3. Passo 1 — Repositório da nova instância

### 3.1 Copiar o código

```bash
git clone <repo-original> razy-cliente-x
cd razy-cliente-x
rm -rf .git
git init && git add -A && git commit -m "chore: base do Razy para o cliente X"
git remote add origin git@github.com:CLIENTE/razy-cliente-x.git
git push -u origin main
```

Não versione: `.env`, `.output/`, `.nuxt/`, `node_modules/`, `ai-service/**/__pycache__/`.
O `.gitignore` já cobre todos eles.

O `.env`, por não ir para o GitHub, é copiado **à parte**, na mão, da máquina onde o projeto
roda hoje — ver [3.3](#33-o-env-da-nova-instalação).

### 3.2 Hardcodes que **precisam** ser trocados no código

Estes valores não vêm de variável de ambiente. Se não forem trocados, a instalação nova
continua apontando para a infraestrutura antiga:

| Arquivo | Linha | Valor atual | Trocar por |
|---|---|---|---|
| [app/pages/recuperar-senha.vue](app/pages/recuperar-senha.vue#L84) | 84 | `https://kxvraxkisrgyhntifxrc.supabase.co/auth/v1/recover` | URL do Supabase novo — **ou**, melhor, `useRuntimeConfig().public.supabaseUrl` |
| [app/components/RedefinirSenhaForm.vue](app/components/RedefinirSenhaForm.vue#L73) | 73 | `https://kxvraxkisrgyhntifxrc.supabase.co/auth/v1/user` | idem |
| [ai-service/app/main.py](ai-service/app/main.py#L107) | 105-108 | `ALLOWED_ORIGINS = ["https://razy.vercel.app", "http://localhost:3000"]` | domínio da Vercel nova |
| [nuxt.config.ts](nuxt.config.ts#L17) | 17 | default `https://razy.uazapi.com` | default do servidor UAzAPI novo (ou deixe e sempre defina `UAZAPI_URL`) |
| [ai-service/app/config.py](ai-service/app/config.py#L43) | 43 | default `https://razycorretora.uazapi.com` | idem, para `UAZAPI_URL` |

> Os dois primeiros são um **bug de vazamento entre projetos**: o "recuperar senha" chama um
> projeto Supabase de outra aplicação. Enquanto não trocar, a recuperação de senha do cliente
> novo não funciona (e vaza requisição para um projeto de terceiro).

### 3.3 O `.env` da nova instalação

A base é o **`.env` que já existe na instalação atual** — não há `.env.example` a seguir. Copie
esse arquivo para a pasta do projeto novo e **substitua todos os valores**. O `.env` serve os
dois lados em desenvolvimento: o painel Nuxt e o ai-service ([ai-service/app/config.py](ai-service/app/config.py)
lê este mesmo arquivo da raiz). Em produção ele **não** vai para o container nem para a Vercel —
lá as variáveis são cadastradas no painel de cada plataforma (passos 6 e 7).

```bash
# na máquina onde o projeto roda hoje
cp /caminho/do/projeto-atual/.env  /caminho/do/razy-cliente-x/.env
# depois edite e troque TODOS os valores
```

**O que trocar, linha por linha:**

| Variável do `.env` atual | Substituir por |
|---|---|
| `NUXT_PUBLIC_SUPABASE_URL` | URL do Supabase novo (passo 4.6) |
| `NUXT_PUBLIC_SUPABASE_ANON_KEY` | anon key do Supabase novo |
| `UAZAPI_URL` | servidor UAzAPI do cliente |
| `UAZAPI_ADMIN_TOKEN` | admintoken do servidor UAzAPI novo |
| `UAZAPI_DELAY_MS` | pode manter `2000` |
| `OPENAI_API_KEY` | chave da conta OpenAI do cliente |
| `POSTGRES_URL` | URL **interna** do Postgres do EasyPanel novo |
| `REDIS_URL` | URL **interna** do Redis do EasyPanel novo |
| `INTERNAL_TOKEN` | segredo novo (`openssl rand -hex 32`) |
| `SUPABASE_DB_URL` | session pooler do Supabase novo |
| `AI_SERVICE_URL` | domínio do ai-service novo |

**O que acrescentar** — estas três não existem no `.env` atual (hoje só estão cadastradas no
EasyPanel), e sem elas o ambiente local fica incompleto:

```env
# REST/Storage do Supabase — upload da mídia das conversas
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_SERVICE_ROLE_KEY=

# Janela (s) de agrupamento de mensagens em rajada — 8 é o valor de produção; 0 desliga
IA_JANELA_RAJADA_S=8
```

> Sem `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`, rodando local, a conversa é gravada mas a
> mídia (áudio, imagem, PDF, foto de perfil) não sobe para o bucket — e o anexo não aparece no
> painel. É o tipo de falha que passa despercebida porque nada quebra.
>
> `UAZAPI_TOKEN` aparece no `.env` atual e é **legado** (só as rotas antigas
> `server/api/whatsapp/*` olham para ela). Pode deixar vazia.

Depois de preencher, confira que **nenhum valor da instalação antiga sobrou**:

```bash
grep -nE "xdpjhvqfuhjylxaishks|razycorretora|razy\.vercel\.app|aplicativo-razy" .env
# não deve devolver nada
```

### 3.4 Opcional, mas recomendado antes de entregar

- `app/plugins/supabase.client.ts`: `storageKey: 'agzap-auth-token'` — troque para algo do
  cliente (`'clientex-auth-token'`) se as duas instalações forem usadas no mesmo navegador,
  senão as sessões se atropelam. Se trocar, ajuste também a leitura em
  [app/components/AppSidebar.vue](app/components/AppSidebar.vue) (`localStorage.getItem('agzap-auth-token')`).
- `package.json` → `"name"`, e os textos de marca em `app/layouts/` e `public/`.

---

## 4. Passo 2 — Supabase novo

### 4.1 Criar o projeto

1. supabase.com → **New project**.
2. Região **South America (São Paulo) `sa-east-1`** — mesma região da VPS reduz a latência do disparo.
3. Guarde a **Database password** que você definir (ela entra na `SUPABASE_DB_URL`).
4. Espere o provisionamento terminar (~2 min).

### 4.2 Rodar o schema

1. Studio → **SQL Editor** → **New query**.
2. Cole o conteúdo inteiro de [supabase/schema_completo.sql](supabase/schema_completo.sql) → **Run**.
3. Confira o resultado com:

```sql
select count(*) from information_schema.tables where table_schema='public';  -- 19
select count(*) from pg_policies where schemaname='public';                  -- 62
select count(*) from pg_trigger where not tgisinternal;                      -- 4
select id from storage.buckets;                                              -- conversas-midia
select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and proname not like '%trgm%' and proname not like '%similarity%'
    and proname not like 'unaccent%' and proname not like '%limit%';         -- 11 funções
```

O script cria, nesta ordem: extensões → 19 tabelas → PK/UNIQUE/CHECK/FK → 32 índices →
11 funções → 4 triggers → RLS em todas as tabelas → 62 policies → grants → bucket de Storage
com policies → policy de Realtime.

**As 19 tabelas e para que servem:**

| Tabela | Papel |
|---|---|
| `usuarios` | Perfil, espelha `auth.users` (mesmo `id`) |
| `instancias` | Canais WhatsApp (1 = 1 número); token da UAzAPI, cooldown, `share_token` do link público, vínculo com profissional |
| `profissionais` | Atendentes humanos |
| `assistentes` | IA por instância (1↔1, índice único parcial) — modelo de disparo |
| `assistentes_profissionais` | IA do canal por profissional (1 por profissional) — nasce **desligada** |
| `integracoes` | Chave OpenAI do cliente + flag `openai_sem_saldo` |
| `publicos` / `contatos` | Listas e leads do disparo |
| `campanhas` / `disparos` / `campanha_logs` | Disparo em massa, envio por contato, trilha de eventos |
| `followup_configs` / `followup_etapas` / `followup_disparos` | Sequências de follow-up e sua fila |
| `conversas` / `mensagens` / `midias_conversas` | Timeline do atendimento (página Conversas) |
| `conversa_atendentes_historico` | Quem assumiu/fechou cada atendimento |
| `validacoes_numeros` | Histórico do validador de números em massa |

### 4.3 Storage

O script já cria o bucket **privado** `conversas-midia` e as duas policies. Confira em
**Storage → Buckets**: precisa existir e estar **Private**. O caminho dos arquivos é
`{usuario_id}/{audio|imagem|pdf|video|foto_perfil}/{arquivo}` — o `usuario_id` como primeiro
segmento é o que a policy usa para isolar o dono; não invente outro layout.

### 4.4 Realtime

A policy `broadcast_usuario_receber` em `realtime.messages` também vem no script. Ela autoriza
o painel a entrar no canal privado `usuario:{uuid}`. **Sem ela a página de Conversas não
atualiza em tempo real** e o console mostra `CHANNEL_ERROR` — é o erro mais fácil de não notar
na hora da migração.

Não é preciso habilitar "Realtime" nas tabelas: o sistema usa **Broadcast** (via `realtime.send()`
nos triggers), não replicação de tabela.

### 4.5 Autenticação

Em **Authentication → Providers → Email**: deixe **Email** habilitado (é o único usado).

Em **Authentication → URL Configuration**:
- **Site URL:** `https://<projeto>.vercel.app` (ou o domínio final do painel).
- **Redirect URLs:** acrescente `https://<projeto>.vercel.app/**` e `http://localhost:3000/**`.

Decida com o cliente se **Confirm email** fica ligado:
- Ligado (padrão): o usuário só entra depois de clicar no link do e-mail. O painel já trata
  esse estado (`EmailConfirmationModal.vue`, mensagem "Confirme seu email antes de entrar").
- Desligado: cadastro entra direto. Mais simples para uma conta única de cliente.

> O cadastro (`useAuth.signUp`) cria a linha em `public.usuarios` **pelo navegador**, logo após
> o `signUp`. Não existe trigger de `auth.users` fazendo isso. Se o e-mail exigir confirmação e
> a sessão não vier na hora, a inserção em `usuarios` pode falhar silenciosamente — confira
> depois do primeiro login que existe 1 linha em `public.usuarios` com o mesmo `id` de
> `auth.users`, senão insira manualmente:
> ```sql
> insert into public.usuarios (id, nome, empresa, email, perfil)
> select id, coalesce(raw_user_meta_data->>'nome','Admin'),
>        raw_user_meta_data->>'empresa', email, 'admin'
> from auth.users
> on conflict (id) do nothing;
> ```

### 4.6 Anotar as credenciais

**Settings → API:**
- `Project URL` → `NUXT_PUBLIC_SUPABASE_URL` e `SUPABASE_URL`
- `anon public` → `NUXT_PUBLIC_SUPABASE_ANON_KEY`
- `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (**só no ai-service**, nunca na Vercel pública, nunca no navegador)

**Settings → Database → Connection string → Session pooler (porta 5432, IPv4):**
```
postgresql://postgres.<ref>:<senha>@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
```
→ `SUPABASE_DB_URL`. Use **o pooler**, não a conexão direta: a VPS normalmente não tem IPv6, e
o `asyncpg` do ai-service já sobe com `statement_cache_size=0` por causa do Supavisor.

---

## 5. Passo 3 — UAzAPI (WhatsApp)

1. Contrate/provisione o servidor UAzAPI do cliente (ex.: `https://clientex.uazapi.com`).
2. Pegue o **admintoken** do servidor → `UAZAPI_ADMIN_TOKEN` (fica **só no lado servidor** da Vercel).
3. **Não crie instâncias pelo painel da UAzAPI.** Quem cria é o app: `POST /api/instancias/create`
   chama `POST /instance/create` com o `admintoken`, guarda o token retornado em
   `instancias.uazapi_token` e já cria o assistente correspondente. Instância criada por fora
   não tem token no banco e **não entra no roteamento de disparo**.
4. O **webhook** é o que liga o WhatsApp à IA. Configure para cada instância (ou como padrão do
   servidor, se a sua UAzAPI permitir), depois que o ai-service estiver no ar (passo 6):
   - **URL:** `https://<dominio-do-ai-service>/webhook/uazapi`
   - **Evento:** `messages` (o handler ignora qualquer outro `EventType`)
   - **Incluir mensagens próprias (`fromMe`)**: **sim** — o serviço usa o eco das mensagens
     enviadas pelo celular do atendente para pausar a IA e transcrever o áudio do vendedor.
   - **Grupos:** o handler já descarta (`isGroup`).
   - O payload precisa trazer o campo `token` da instância — é assim que o serviço descobre de
     qual usuário é a mensagem.

> Se a sua UAzAPI configura webhook por API em vez de painel, confira o contrato atual em
> <https://docs.uazapi.com> (o spec real fica em `https://docs.uazapi.com/openapi-bundled.json`).

---

## 6. Passo 4 — EasyPanel (serviço de IA)

Siga [DEPLOY_LANGCHAIN_LANGGRAPH_EASYPANEL.md](DEPLOY_LANGCHAIN_LANGGRAPH_EASYPANEL.md) — ele
cobre VPS, instalação do EasyPanel, Postgres, Redis, GitHub e domínio em detalhe. O resumo do
que precisa existir no projeto novo:

### 6.1 Três serviços no mesmo projeto do EasyPanel

| Serviço | Tipo | Observações |
|---|---|---|
| `postgres` | Template Postgres | Banco **dedicado ao LangGraph** (checkpointer) — *não* é o Supabase. Anote a **URL de conexão interna**. |
| `redis` | Template Redis | Contexto de conversa, travas de rajada/idempotência e cache de pausa. Anote a **URL interna**. |
| `ai-service` | App (Dockerfile) | Source = repositório novo, **Build path / Dockerfile path = `ai-service`**, porta **8000** |

As URLs internas usam o hostname do Docker (`projeto_postgres:5432`), nunca `localhost` nem o IP
público.

### 6.2 Build

- **Build method:** Dockerfile
- **Dockerfile path:** `ai-service/Dockerfile`
- **Build context:** `ai-service`
- O `Dockerfile` já traz healthcheck em `/healthz` e `uvicorn --workers 2`.

### 6.3 Variáveis de ambiente do ai-service

```env
OPENAI_API_KEY=sk-...                      # fallback; a chave que vale é a do painel
POSTGRES_URL=postgres://postgres:SENHA@projeto_postgres:5432/razy_ai?sslmode=disable
REDIS_URL=redis://default:SENHA@projeto_redis:6379
SUPABASE_DB_URL=postgresql://postgres.<ref>:<senha>@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
UAZAPI_URL=https://clientex.uazapi.com
INTERNAL_TOKEN=<mesmo valor que vai na Vercel>
IA_JANELA_RAJADA_S=8
```

`POSTGRES_URL`, `REDIS_URL` e `INTERNAL_TOKEN` são **obrigatórios** — sem eles o container nem
sobe. `SUPABASE_DB_URL` é opcional para subir, mas sem ela o serviço loga
`SUPABASE_DB_URL não definido — disparo/IA indisponível` e não faz nada de útil.

### 6.4 Domínio e HTTPS

Aponte um subdomínio (`ia.cliente.com.br`) para o serviço, porta 8000, e ligue o Let's Encrypt.
A UAzAPI e a Vercel precisam alcançar essa URL **por HTTPS**.

### 6.5 Validar

```bash
curl https://ia.cliente.com.br/healthz          # {"status":"ok"}
```

Nos logs de startup tem que aparecer `Conectado ao Postgres do Supabase (dados de negócio).`
e nenhuma exceção do checkpointer.

### 6.6 A pilha LangChain / LangGraph — o que é instalado e onde ela mora

**Você não instala LangChain nem LangGraph à mão em lugar nenhum.** Eles são dependências
Python declaradas em [ai-service/pyproject.toml](ai-service/pyproject.toml) e instaladas
dentro da imagem, no build do EasyPanel, pelo [ai-service/Dockerfile](ai-service/Dockerfile):

```dockerfile
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv   # instalador rápido
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml                    # <- LangChain/LangGraph entram aqui
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

As dependências relevantes do `pyproject.toml`:

| Pacote | Para que serve aqui |
|---|---|
| `langchain`, `langchain-openai` | `ChatOpenAI` (gpt-6-luna) e as mensagens (`SystemMessage`/`HumanMessage`/`AIMessage`) |
| `langgraph` | O `StateGraph` que gera a mensagem ([graph/build.py](ai-service/app/graph/build.py)) |
| `langgraph-checkpoint-postgres` + `psycopg[binary]` | Checkpointer: persiste o histórico por `thread_id` no Postgres do EasyPanel |
| `fastapi`, `uvicorn[standard]` | O servidor HTTP |
| `asyncpg` | Pools diretos: Postgres do EasyPanel e Postgres do Supabase |
| `redis` | Contexto curto, travas e pausas |
| `openai` | Whisper (`whisper-1`) e visão, chamados fora do LangChain |
| `pypdf`, `python-docx` | Capacidade "ler documentos" |

Nenhuma versão está pinada: o build instala sempre a mais recente compatível com Python 3.13.
Se o cliente precisar de build reprodutível, gere um lock (`uv pip compile`) antes de entregar.

**O que sobe no startup** (`lifespan` em [ai-service/app/main.py](ai-service/app/main.py)), nesta ordem:

1. Pool `asyncpg` no **Postgres do EasyPanel** (`POSTGRES_URL`).
2. Cliente **Redis** (`REDIS_URL`) — faz `PING`; se falhar, o container não sobe.
3. Pool `asyncpg` no **Postgres do Supabase** (`SUPABASE_DB_URL`) — este é opcional no boot.
4. `AsyncPostgresSaver.from_conn_string(POSTGRES_URL)` + `await checkpointer.setup()` —
   **cria sozinho** as tabelas `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` e
   `checkpoint_migrations`. É idempotente; você não roda SQL nenhum aqui.
5. `build_graph(checkpointer)` — compila o grafo (hoje um nó só, `llm`).
6. Os dois loops de 60s (campanhas agendadas e follow-up), cada um sob advisory lock.

**Divisão de memória — as três camadas não se misturam:**

| Onde | O que guarda | Some se apagar? |
|---|---|---|
| Postgres do **EasyPanel** (checkpointer) | Histórico da thread por `thread_id` (telefone + instância). É o que dá contexto ao follow-up e à resposta | A IA perde o histórico das conversas, mas o painel continua íntegro |
| **Redis** | `pausa:{tid}`, `pausa_manual:{tid}`, `buf:{tid}`/`bufgen:{tid}` (rajada de 8s), `echo:{tid}` (eco do envio), `loopmsg_*` (anti-loop), cooldowns | Volátil por natureza: o sistema se recupera sozinho |
| **Supabase** | Tudo que o painel mostra: conversas, mensagens, campanhas, contatos | É o dado de verdade — faça backup |

Por isso o Postgres do EasyPanel **precisa de volume persistente** (`/var/lib/postgresql/data`)
e o Redis **não precisa**.

**Replicas = 1.** O container já roda 2 workers uvicorn, e os loops de background se protegem
com advisory lock **no Postgres do EasyPanel** (chaves `920101` e `920102`). Subir réplicas em
máquinas diferentes que apontem para o mesmo Postgres continua seguro para os loops, mas o
dreno de webhooks no shutdown vale por container — mantenha 1 réplica salvo necessidade real.

**Conferir que o checkpointer funcionou** — serviço `postgres` → Console:

```sql
\dt
-- checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations
select count(*) from checkpoints;   -- passa de 0 depois da primeira resposta da IA
```

Se as tabelas não existirem, o `setup()` falhou no startup: leia os logs do `ai-service` —
quase sempre é `POSTGRES_URL` errada (hostname, senha com caractere especial não codificado, ou
falta de `?sslmode=disable` em Postgres interno sem TLS).

---

## 7. Passo 5 — Vercel (painel)

1. Vercel → **Add New → Project** → importe o repositório novo.
2. Framework: **Nuxt** (detectado sozinho). Build `npm run build`, output `.output` — não mexa.
3. **Environment Variables** (Production **e** Preview):

```env
NUXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NUXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
UAZAPI_URL=https://clientex.uazapi.com
UAZAPI_ADMIN_TOKEN=<admintoken da UAzAPI>
UAZAPI_DELAY_MS=2000
AI_SERVICE_URL=https://ia.cliente.com.br
INTERNAL_TOKEN=<mesmo valor do ai-service>
```

> **Nunca** coloque `SUPABASE_SERVICE_ROLE_KEY` na Vercel. O painel opera sempre com a anon key
> + JWT do usuário, e é a RLS que isola os dados.
>
> `UAZAPI_TOKEN` é legado: só as rotas `server/api/whatsapp/*` (antigas, que ainda consultam
> uma tabela `canais` que não existe mais) olham para ela. Pode deixar vazia.

4. **Deploy**. Depois do primeiro deploy, volte ao Supabase e confirme que a URL final está em
   **Site URL / Redirect URLs** (passo 4.5), e ao `ai-service/app/main.py` para conferir se o
   domínio está em `ALLOWED_ORIGINS` (passo 3.2).

---

## 8. Passo 6 — OpenAI

1. platform.openai.com → **API keys** → *Create new secret key* (na conta **do cliente**).
2. **Billing:** adicione saldo. Sem saldo, a OpenAI devolve `429 insufficient_quota`, o
   ai-service grava `integracoes.openai_sem_saldo = true` e o painel mostra o banner vermelho
   no topo ([app/components/AlertaSaldoOpenAI.vue](app/components/AlertaSaldoOpenAI.vue)).
3. A chave que o sistema realmente usa é a cadastrada **no painel** (Configurações →
   Integrações → OpenAI), que fica em `integracoes.openai_api_key` por usuário. A
   `OPENAI_API_KEY` do ambiente do ai-service é só fallback.
4. Modelos usados (se for trocar, é aqui):
   - `gpt-6-luna` — resposta do assistente, disparo/follow-up, visão e Analista. Fica numa
     constante só, `MODELO_OPENAI` em [config.py](ai-service/app/config.py#L27). É modelo de
     raciocínio, usado com `reasoning_effort="none"` e sem `temperature` — o comentário ao lado
     da constante diz o que conferir antes de trocar. Substituiu o `gpt-4.1-mini`, que a OpenAI
     desliga em 14/01/2027.
   - `whisper-1` — transcrição de áudio ([services/assistente.py](ai-service/app/services/assistente.py#L487)).

---

## 9. Passo 7 — Amarrar as pontas

Ordem certa (cada item depende do anterior estar no ar):

1. **ai-service no ar** com domínio HTTPS → `curl /healthz` responde.
2. **Vercel** com `AI_SERVICE_URL` apontando para esse domínio e o **mesmo** `INTERNAL_TOKEN`
   dos dois lados. Token diferente = `401 unauthorized` em tudo que depende de IA.
3. **UAzAPI** com o webhook `https://<ai-service>/webhook/uazapi`, evento `messages`, `fromMe` incluso.
4. **CORS** do ai-service (`ALLOWED_ORIGINS`) com o domínio da Vercel — necessário se algum dia
   o navegador chamar o serviço direto; hoje as chamadas passam pelo servidor do Nuxt, mas
   deixe correto para não caçar esse problema depois.
5. **Supabase → Site URL / Redirect URLs** com o domínio final.

---

## 10. Passo 8 — Primeiro uso no painel

1. Abra `https://<projeto>.vercel.app` → **Criar conta** (nome, empresa, e-mail, senha).
   Confirme o e-mail se a confirmação estiver ligada.
2. Confirme no Supabase que nasceu a linha em `public.usuarios` (ver 4.5).
3. **Configurações → Integrações** → cole a chave da OpenAI → salvar.
4. **Profissionais & Canais**:
   - Cadastre os atendentes (profissionais).
   - Crie o canal: com `profissional_id` → canal de atendimento (a IA dele é configurada em
     "IA dos Profissionais" e **nasce desligada**); sem profissional → canal de disparo, que já
     nasce com um assistente ativo.
   - **Conectar** → leia o QR Code no WhatsApp do número. Ou use **Compartilhar link**, que gera
     `instancias.share_token` e abre `/conectar/{token}` — página pública, o atendente conecta o
     próprio número sem ter login no painel.
5. **Assistente** (ou **IA dos Profissionais**): preencha empresa, informações, horário e a
   instrução. Ligue `ler_imagem`/`ler_documento` se o cliente precisar (custam tokens a mais;
   áudio é nativo e sempre ligado).
6. **Públicos** → importe a planilha de contatos → **Campanhas** → crie e dispare uma campanha
   de teste com 1 contato só.

---

## 11. Checklist de validação ponta a ponta

Marque um por um; cada linha falha por um motivo diferente.

| # | Teste | Esperado | Se falhar, veja |
|---|---|---|---|
| 1 | `curl https://<ai-service>/healthz` | `{"status":"ok"}` | Logs do EasyPanel; `POSTGRES_URL`/`REDIS_URL` |
| 2 | Logs de startup do ai-service | `Conectado ao Postgres do Supabase` | `SUPABASE_DB_URL` (use o **pooler**) |
| 3 | Criar conta e entrar no painel | Dashboard abre | `NUXT_PUBLIC_*`, Redirect URLs |
| 4 | `select count(*) from public.usuarios` | 1 | Seção 4.5 |
| 5 | Salvar a chave OpenAI em Configurações | Salva sem erro | RLS de `integracoes` |
| 6 | Criar um canal | Linha em `instancias` com `uazapi_token` | `UAZAPI_ADMIN_TOKEN` |
| 7 | Conectar o número (QR) | `status = connected` | UAzAPI |
| 8 | Mandar mensagem de um celular qualquer para o número conectado | Aparece em **Conversas** em segundos, **sem recarregar a página** | Webhook da UAzAPI; policy de Realtime (4.4) |
| 9 | A IA responde no WhatsApp | Resposta em ~10-15s | Assistente `ativo`; chave OpenAI com saldo; logs do webhook |
| 10 | Mandar um **áudio** | Transcrição aparece na conversa e a IA responde | `whisper-1`, saldo OpenAI |
| 11 | Mandar uma **imagem** com `ler_imagem` ligado | IA comenta a imagem | Flag no assistente |
| 12 | Abrir a mídia no painel | Abre via signed URL | Bucket `conversas-midia` + `SUPABASE_SERVICE_ROLE_KEY` no ai-service |
| 13 | Responder pelo **celular** do atendente | IA pausa (badge "IA pausada" na conversa) | `pausa_ativa`, webhook com `fromMe` |
| 14 | Enviar mensagem pelo painel (composer, texto/áudio/arquivo) | Chega no WhatsApp | `server/utils/uazapi.ts`, token da instância |
| 15 | Campanha de teste com 1 contato | `disparos.status = enviado` e log em `campanha_logs` | `AI_SERVICE_URL` + `INTERNAL_TOKEN` |
| 16 | Responder ao disparo | `disparos.respondido_em` preenchido; contador de respostas sobe | Webhook; RPC `contar_respostas_campanhas` |
| 17 | Follow-up com etapa de 1 minuto | Dispara sozinho em ~1 min | Loop de follow-up (60s) nos logs |
| 18 | Campanha agendada para daqui 2 min | Inicia sozinha | Loop de scheduler (60s) |
| 19 | **Relatórios** e **Analista de Atendimento** | Números e resposta do Analista | RPCs `get_metricas_*`; `INTERNAL_TOKEN` |
| 20 | Link público `/conectar/{token}` numa aba anônima | Mostra QR e conecta | RPCs `instancia_*_publica` (grant para `anon`) |

---

## 12. Tabela mestre de variáveis de ambiente

| Variável | Vercel | ai-service | Local (.env) | O que é |
|---|:--:|:--:|:--:|---|
| `NUXT_PUBLIC_SUPABASE_URL` | ✅ | — | ✅ | URL do projeto Supabase (vai ao navegador) |
| `NUXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | — | ✅ | anon key (vai ao navegador; protegida por RLS) |
| `UAZAPI_URL` | ✅ | ✅ | ✅ | Base do servidor UAzAPI |
| `UAZAPI_ADMIN_TOKEN` | ✅ | — | ✅ | Cria instâncias na UAzAPI (**só servidor**) |
| `UAZAPI_DELAY_MS` | ✅ | — | ✅ | Espaçamento padrão entre envios (2000) |
| `UAZAPI_TOKEN` | opcional | — | opcional | Legado (`server/api/whatsapp/*`) |
| `AI_SERVICE_URL` | ✅ | — | ✅ | URL pública do ai-service |
| `INTERNAL_TOKEN` | ✅ | ✅ | ✅ | Segredo compartilhado Nuxt ↔ ai-service (**igual nos dois**) |
| `OPENAI_API_KEY` | — | ✅ (fallback) | ✅ | A chave que vale é a do painel (`integracoes`) |
| `POSTGRES_URL` | — | ✅ | ✅ | Postgres do EasyPanel (checkpointer do LangGraph) |
| `REDIS_URL` | — | ✅ | ✅ | Redis do EasyPanel (contexto, travas, pausas) |
| `SUPABASE_DB_URL` | — | ✅ | ✅ | Postgres do Supabase via **session pooler** (dados de negócio) |
| `SUPABASE_URL` | — | ✅ | ✅ | REST/Storage do Supabase (upload de mídia) |
| `SUPABASE_SERVICE_ROLE_KEY` | ❌ **nunca** | ✅ | ✅ | Bypassa RLS — só no serviço de backend |
| `IA_JANELA_RAJADA_S` | — | opcional | opcional | Janela de agrupamento de rajada (padrão 8s; 0 desliga) |

A base do arquivo local é o **`.env` da instalação atual**, com todos os valores trocados — ver
[3.3](#33-o-env-da-nova-instalação). Em produção, nada de `.env`: as variáveis são cadastradas
no painel da Vercel (passo 7) e do EasyPanel (passo 6.3).

---

## 13. Mapa do código (para quem vai dar manutenção)

### Painel (Nuxt 4, `ssr: false`)

| Caminho | O que tem |
|---|---|
| [app/pages/](app/pages/) | 12 páginas do menu + `/conectar/[token]` (pública) + login/recuperar/redefinir senha |
| [app/composables/](app/composables/) | Toda a conversa com o Supabase e com `server/api` (`useConversas`, `useCampanhas`, `useCanais`, `useRealtimeConversas`, …) |
| [app/plugins/supabase.client.ts](app/plugins/supabase.client.ts) | Cliente Supabase (PKCE, `storageKey`) |
| [app/middleware/](app/middleware/) | `auth` (exige sessão) e `guest` |
| [server/api/](server/api/) | 56 rotas: "porteiro" que valida o JWT (`requireUser`) e fala com UAzAPI / ai-service com segredos que nunca vão ao navegador |
| [server/utils/](server/utils/) | `auth.ts` (valida JWT), `supabase.ts` (REST com o JWT do usuário + RPC pública com anon), `uazapi.ts` (composer: texto/mídia/`ptt`), `instancias.ts` |

### Serviço de IA (FastAPI)

| Caminho | O que tem |
|---|---|
| [ai-service/app/main.py](ai-service/app/main.py) | Lifespan (pools, checkpointer, grafo), CORS, os dois loops de 60s com advisory lock, dreno de webhooks no shutdown |
| [ai-service/app/api/webhook.py](ai-service/app/api/webhook.py) | `POST /webhook/uazapi` — coração do atendimento |
| [ai-service/app/api/campanhas.py](ai-service/app/api/campanhas.py) | `POST /campanhas/{id}/iniciar`, `GET /campanhas/{id}/logs` |
| [ai-service/app/api/assistente.py](ai-service/app/api/assistente.py) | Pausas da IA (listar/remover, pausar/despausar conversa) |
| [ai-service/app/api/analista.py](ai-service/app/api/analista.py) | Analista de Atendimento (resumo + perguntas em linguagem natural) |
| [ai-service/app/services/orquestrador.py](ai-service/app/services/orquestrador.py) | Disparo: rotação de canais, intervalo, revalidação de status, logs |
| [ai-service/app/services/assistente.py](ai-service/app/services/assistente.py) | Resposta da IA, rajada, pausa, transcrição, notificação do atendente |
| [ai-service/app/services/conversas.py](ai-service/app/services/conversas.py) | Timeline (`conversas`/`mensagens`), foto de perfil, atribuição ao profissional |
| [ai-service/app/services/followup.py](ai-service/app/services/followup.py) | Fila de follow-up |
| [ai-service/app/services/midia.py](ai-service/app/services/midia.py) | Visão (imagem) e extração de PDF/Word/txt |
| [ai-service/app/services/storage.py](ai-service/app/services/storage.py) | Upload no bucket `conversas-midia` |
| [ai-service/app/services/repo.py](ai-service/app/services/repo.py) | SQL direto no Supabase (service role, ignora RLS) |

### Endpoints do ai-service (todos exigem `X-Internal-Token`, menos `/healthz` e o webhook)

```
GET  /healthz
POST /webhook/uazapi
POST /campanhas/{id}/iniciar        GET /campanhas/{id}/logs
GET  /assistente/pausas             POST /assistente/pausas/remover
POST /conversas/pausar              POST /conversas/despausar    POST /conversas/pausar-automatica
GET  /analista/resumo               POST /analista/perguntar
```

---

## 14. Regras de negócio que não estão no schema

Copiar o banco não copia estas decisões — elas vivem no código e explicam comportamentos que
parecem bug:

1. **1 instância ↔ 1 assistente** (índice único parcial `assistentes_instancia_uniq`). Ao criar
   uma instância sem profissional, o app já cria o assistente herdando a configuração de um
   assistente existente. Ao excluir a instância, o assistente fica **órfão** (`instancia_id`
   vira NULL) — não some.
2. **Canal por profissional usa outra tabela de IA** (`assistentes_profissionais`, 1 por
   profissional, nasce desligada). Nunca os dois modelos no mesmo canal.
3. **Roteamento de disparo**: o status do canal é revalidado **ao vivo na UAzAPI** na hora do
   envio — o `status` do banco é só cache. Instância que não existe no banco (criada direto na
   UAzAPI) não entra na rotação. `canais_ids` vazio/NULL = todos os canais elegíveis.
4. **Cooldown do erro 463** (restrição do WhatsApp): o canal recebe `bloqueado_ate` +
   `bloqueio_motivo` e sai da rotação até a data passar.
5. **`uso_notificacao = true`**: canal reservado para avisar o atendente — o webhook ignora
   mensagens dele, não faz atendimento.
6. **Pausa da IA**: quando o humano responde (pelo celular ou pelo painel), a IA pausa por
   `pausa_minutos` (padrão 30). Controlado por `pausa_ativa` e guardado no Redis.
7. **Janela de rajada de 8s**: mensagens seguidas do mesmo contato viram **uma** resposta. O
   valor saiu de medição real (máximo observado entre duas mensagens: 7,3s). Cada segundo aqui
   é latência somada a toda resposta — não mexa sem dado novo.
8. **PostgREST corta em 1000 linhas**: contagens que somam muitas linhas precisam de RPC no
   banco. É por isso que existe `contar_respostas_campanhas` — agregar no navegador truncava em
   silêncio e o contador de respostas ficava errado.
9. **Campanha `arquivada`** é soft-delete: sai da lista de Campanhas mas continua nos Relatórios
   e no Dashboard. A limpeza definitiva é o botão "Apagar métricas".
10. **`contatos.followup_excluido`**: lead que deu negativa sai de **todas** as sequências de
    follow-up, atuais e futuras.
11. **Conversa só nasce quando o contato responde** (ou quando o dono manda mensagem manual). O
    disparo em massa sozinho não cria conversa — o eco `fromMe` do envio é consumido em
    `marcar_saida`/`consumir_eco`.
12. **Dois workers, um loop**: scheduler e follow-up rodam sob advisory lock (`920101`/`920102`).
    Se um dia o serviço for escalado para mais réplicas, os locks continuam garantindo execução
    única — mas o dreno de webhook do shutdown vale por container.

---

## 15. Armadilhas conhecidas e solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| Conversas não atualizam em tempo real (precisa recarregar) | Falta a policy `broadcast_usuario_receber` em `realtime.messages` | Rode a seção 10 do `schema_completo.sql` |
| A IA nunca responde | Webhook da UAzAPI não aponta para `/webhook/uazapi`, ou evento diferente de `messages` | Reconfigure o webhook (passo 5.4) |
| A IA responde uma vez por mensagem em rajada | `IA_JANELA_RAJADA_S=0` | Volte para 8 |
| `401 unauthorized` ao iniciar disparo / Analista mudo | `INTERNAL_TOKEN` diferente entre Vercel e ai-service | Iguale os dois e redeploy dos dois lados |
| Banner "sem saldo OpenAI" | `429 insufficient_quota` gravou `integracoes.openai_sem_saldo` | Adicione saldo; a flag limpa sozinha quando a IA volta a responder |
| Mídia não aparece no painel | Falta `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` no ai-service, ou o bucket | A mensagem é gravada mesmo assim, só sem anexo — corrija o env e o bucket |
| ai-service não sobe | `POSTGRES_URL`/`REDIS_URL` errados, ou hostname interno errado | Use o hostname do Docker (`projeto_postgres`), não `localhost` |
| ai-service sobe mas "disparo indisponível" | `SUPABASE_DB_URL` ausente | Use a string do **session pooler** (IPv4, porta 5432) |
| Erro de prepared statement no asyncpg | Conexão direta em vez do pooler | Troque para o pooler (o código já usa `statement_cache_size=0`) |
| Recuperar senha não funciona | Hardcode do projeto Supabase antigo | Passo 3.2 |
| Canal criado na UAzAPI não dispara | Instância sem linha (com token) no banco do app | Crie sempre pelo painel |
| Excluir instância dá erro | Trava: instância em campanha, ou follow-ups agendados apontando para ela | Arquive/conclua a campanha, ou cancele os follow-ups |
| Excluir público dá erro | `campanhas.publico_id` é FK sem `ON DELETE` | Apague/arquive as campanhas do público antes |
| Login some ao abrir a outra instalação no mesmo navegador | Mesmo `storageKey` do Supabase nos dois apps | Passo 3.4 |

---

## 16. O que **não** copiar

- **Dados** (`contatos`, `conversas`, `mensagens`, `disparos`, `campanhas`, `validacoes_numeros`):
  são do cliente antigo. O cliente novo começa vazio. Se um dia for preciso migrar dados, a
  ordem por causa das FKs é: `usuarios` → `profissionais` → `instancias` → `assistentes`/
  `assistentes_profissionais` → `publicos` → `contatos` → `campanhas` → `disparos` →
  `campanha_logs` → `followup_*` → `conversas` → `mensagens` → `midias_conversas`. E os `id` de
  `usuarios` precisam existir antes em `auth.users`.
- **Credenciais** de qualquer tipo (OpenAI, UAzAPI, Supabase, `INTERNAL_TOKEN`).
- **Instâncias da UAzAPI** — números são do cliente antigo.

### Código legado que você vai encontrar (não é bug novo, não "conserte" sem pedir)

- `server/api/whatsapp/*` — rotas antigas que consultam uma tabela `canais` que **não existe
  mais** (substituída por `instancias`). O composer novo vive em `server/utils/uazapi.ts`.
- `app/composables/useEmpresa.ts` — consulta uma tabela `empresas` que **não existe** neste
  banco; sempre erra em silêncio.
- `app/pages/cardapio.vue` e `app/pages/pedidos.vue` (+ componentes de cardápio/pedidos) —
  protótipo **100% em memória** (`useState`), sem tabela no banco, e **fora do menu**.
- `campanhas.canal_id`, `campanhas.instancia_token`, `campanhas.instancia_url` — colunas legadas;
  o canal atual é `campanhas.instancia_id`.
- `create_produtos_table.sql`, `create_table.js`, `temp_list_tables.js`, `test-*.js` na raiz —
  arquivos vazios.
- Os `.md` da raiz que falam de `empresas`, n8n ou Meta Cloud API (`chat.md`,
  `foto-nome-contato-e-badges-conversas.md`, `handoff-canal-proprio-conversas.md`) descrevem
  **outro** aplicativo usado como referência de design — não descrevem este sistema.
