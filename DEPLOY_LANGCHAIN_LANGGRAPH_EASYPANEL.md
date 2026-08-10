# Guia Completo — Subir um serviço LangChain + LangGraph em VPS com EasyPanel

> Passo a passo do zero: comprar a VPS → instalar o EasyPanel → subir Postgres e Redis →
> publicar o serviço de IA (FastAPI + LangChain + LangGraph) conectado ao GitHub, com
> **deploy automático a cada push** e botão **Implantar** manual.
>
> Este é exatamente o mesmo arranjo usado no Razy hoje: o painel Nuxt fica na Vercel e o
> `ai-service/` roda em container no EasyPanel, com Redis e Postgres dedicados ao lado.

---

## Índice

| # | Etapa | Tempo |
|---|---|---|
| [1](#1-comprar-a-vps) | Comprar a VPS | ~10 min |
| [2](#2-primeiro-acesso-e-segurança-básica) | Primeiro acesso e segurança básica | ~10 min |
| [3](#3-instalar-o-easypanel) | Instalar o EasyPanel | ~5 min |
| [4](#4-criar-o-projeto-no-easypanel) | Criar o projeto | ~2 min |
| [5](#5-subir-o-postgres) | Subir o Postgres | ~5 min |
| [6](#6-subir-o-redis) | Subir o Redis | ~3 min |
| [7](#7-conectar-o-easypanel-ao-github) | Conectar o EasyPanel ao GitHub | ~5 min |
| [8](#8-criar-o-serviço-de-ia-langchain--langgraph) | Criar o serviço de IA | ~10 min |
| [9](#9-variáveis-de-ambiente) | Variáveis de ambiente | ~10 min |
| [10](#10-domínio-e-https) | Domínio e HTTPS | ~10 min |
| [11](#11-primeiro-deploy-e-validação) | Primeiro deploy e validação | ~5 min |
| [12](#12-deploy-automático-a-cada-push-no-github) | Deploy automático a cada push | ~5 min |
| [13](#13-operação-do-dia-a-dia) | Operação do dia a dia | — |
| [14](#14-solução-de-problemas) | Solução de problemas | — |

**Pré-requisitos:** cartão de crédito, uma conta no GitHub com o repositório do projeto, e (opcional, mas recomendado) um domínio.

---

## 1. Comprar a VPS

> Escrito para a **Hostinger**, que é onde o Razy roda. Em Contabo, Hostgator, DigitalOcean
> ou qualquer outro provedor com Ubuntu, muda só esta seção — do passo 2 em diante é idêntico.

### 1.1 Escolher o plano

1. Acesse **[hostinger.com.br](https://www.hostinger.com.br)** → menu **VPS** → **Hospedagem VPS**.
2. Escolha o plano. Referência de dimensionamento para este serviço:

| Plano | vCPU | RAM | Disco | Serve para |
|---|---:|---:|---:|---|
| KVM 1 | 1 | 4 GB | 50 GB | Testes. Aperta com Postgres + Redis + app juntos |
| **KVM 2** | **2** | **8 GB** | **100 GB** | ✅ **Recomendado** — folga para os 3 containers |
| KVM 4 | 4 | 16 GB | 200 GB | Volume alto de disparos / múltiplos serviços |

> **Por que 8 GB:** o container do app sobe com `--workers 2` (dois processos Python, cada um com LangChain carregado), mais o Postgres e o Redis. Com 4 GB funciona, mas sem margem para picos.

3. Período: quanto maior o contrato, menor o valor mensal. Comece com 12 meses se for produção.
4. Finalize a compra.

### 1.2 Configurar o sistema operacional

Na tela de setup pós-compra:

1. **Localização do servidor:** escolha **São Paulo (Brasil)** — menor latência para usuários e para a API do WhatsApp/UAzAPI.
2. **Sistema operacional:** aqui você tem dois caminhos:

   | Opção | O que fazer | Quando usar |
   |---|---|---|
   | **A — Template pronto** | Em *Aplicativo*, procure **EasyPanel** e selecione | Mais rápido: já vem instalado, **pule o passo 3** |
   | **B — Ubuntu limpo** | Selecione **Ubuntu 24.04 LTS** | Mais controle. Instale o EasyPanel no passo 3 |

   > Se o template EasyPanel não aparecer na sua região/plano, use a **opção B**. É o caminho mais previsível e leva 5 minutos a mais.

3. **Senha do root:** gere uma senha forte e **guarde em um gerenciador de senhas**.
4. **Chave SSH** (recomendado): se você já tem uma, cole a chave pública agora. Para gerar:

   ```bash
   ssh-keygen -t ed25519 -C "seu-email@exemplo.com"
   cat ~/.ssh/id_ed25519.pub    # copie esta saída para o painel da Hostinger
   ```

5. Conclua. A VPS leva de 2 a 5 minutos para provisionar.

### 1.3 Anotar o IP

No painel da VPS, copie o **endereço IPv4** (algo como `191.xxx.xxx.xxx`). Ele será usado em todos os passos seguintes. Neste guia ele aparece como `SEU_IP`.

---

## 2. Primeiro acesso e segurança básica

### 2.1 Conectar por SSH

No terminal do seu computador (PowerShell no Windows, Terminal no Mac/Linux):

```bash
ssh root@SEU_IP
```

Aceite o fingerprint digitando `yes` e informe a senha de root.

### 2.2 Atualizar o sistema

```bash
apt update && apt upgrade -y
```

Se aparecer alguma tela azul perguntando sobre arquivos de configuração, aceite o padrão (*keep the local version*).

### 2.3 Ajustar o firewall

O EasyPanel precisa das portas **80** (HTTP), **443** (HTTPS) e **3000** (painel):

```bash
ufw allow 22/tcp      # SSH — libere ANTES de ativar, ou você se tranca fora
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw --force enable
ufw status
```

> ⚠️ **Nunca** libere as portas 5432 (Postgres) e 6379 (Redis) para a internet. Os containers conversam pela rede interna do Docker — o banco não precisa estar exposto.

### 2.4 Definir o hostname (opcional)

```bash
hostnamectl set-hostname razy-ia
```

---

## 3. Instalar o EasyPanel

> **Pule esta seção** se você escolheu o template EasyPanel no passo 1.2.

### 3.1 Rodar o instalador

Ainda conectado por SSH como root:

```bash
curl -sSL https://get.easypanel.io | sh
```

O script instala o Docker, sobe o EasyPanel em modo swarm e configura o proxy reverso (Traefik). Leva de 3 a 5 minutos. Aguarde a mensagem de conclusão.

### 3.2 Criar a conta de administrador

1. Abra no navegador: **`http://SEU_IP:3000`**
2. Preencha e-mail e senha do administrador. **Essa é a conta que controla o servidor inteiro** — use senha forte.
3. Faça login. Você cai no dashboard do EasyPanel.

### 3.3 Verificar se está tudo de pé

```bash
docker ps
```

Você deve ver os containers `easypanel` e `traefik` rodando.

---

## 4. Criar o projeto no EasyPanel

Um **projeto** é só um agrupador: os serviços dentro dele compartilham a mesma rede interna e se enxergam pelo nome.

1. No dashboard, clique em **+ Create Project** (ou **Criar Projeto**).
2. Nome: **`razy`** (use minúsculas, sem espaços nem acentos — o nome vira parte do hostname interno).
3. Confirme.

> 📌 **Grave esta regra, ela é a chave de todo o guia:** dentro do projeto, cada serviço recebe o hostname interno **`projeto_serviço`**. Um serviço chamado `postgres` no projeto `razy` é acessível pelos outros containers como **`razy_postgres`**. É assim que o app encontra o banco.

---

## 5. Subir o Postgres

Este Postgres tem duas funções: guardar o **estado do LangGraph** (checkpointer) e servir de banco operacional do serviço.

### 5.1 Criar o serviço

1. Dentro do projeto `razy`, clique em **+ Service**.
2. Escolha o tipo **Postgres**.
3. Preencha:

   | Campo | Valor |
   |---|---|
   | **Service Name** | `postgres` |
   | **Image** | `postgres:17` (use a mesma major do seu ambiente) |
   | **Password** | Clique em gerar, ou defina uma senha forte |

4. Clique em **Create**.

### 5.2 Guardar a string de conexão

Abra o serviço `postgres` → aba **Credentials**. O EasyPanel mostra duas URLs:

- **Internal Connection URL** — ✅ **é esta que você vai usar.** Formato:
  ```
  postgres://postgres:SUA_SENHA@razy_postgres:5432/postgres
  ```
- **External Connection URL** — só se você precisar conectar de fora (evite).

Copie a **interna** para um bloco de notas. Ela será a variável `POSTGRES_URL`.

### 5.3 Reservar espaço em disco

Ainda no serviço → aba **Storage**. O EasyPanel já cria um volume persistente para `/var/lib/postgresql/data`. **Confirme que ele existe** — sem volume, você perde o banco a cada redeploy.

### 5.4 Sobre as tabelas do LangGraph

Você **não precisa criar tabela nenhuma manualmente**. Quando o serviço de IA sobe, ele executa:

```python
checkpointer = await AsyncPostgresSaver.from_conn_string(settings.POSTGRES_URL)
await checkpointer.setup()   # cria as tabelas do checkpointer se necessário
```

Esse `setup()` cria automaticamente as tabelas `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` e `checkpoint_migrations`. É idempotente: rodar de novo não quebra nada.

---

## 6. Subir o Redis

O Redis guarda a **memória de curto prazo da conversa** — contexto recente, pausas do assistente, controle de concorrência.

### 6.1 Criar o serviço

1. No projeto `razy` → **+ Service** → tipo **Redis**.
2. Preencha:

   | Campo | Valor |
   |---|---|
   | **Service Name** | `redis` |
   | **Image** | `redis:7` |
   | **Password** | Gere uma senha forte |

3. **Create**.

### 6.2 Guardar a string de conexão

Aba **Credentials** → copie a **Internal Connection URL**:

```
redis://default:SUA_SENHA@razy_redis:6379
```

Ela será a variável `REDIS_URL`.

### 6.3 Persistência (opcional)

Redis aqui é cache/memória volátil — se cair, o sistema se recupera. Mas se quiser sobreviver a reinícios, na aba **Advanced** adicione o comando:

```
redis-server --appendonly yes --requirepass SUA_SENHA
```

E confirme que existe um volume montado em `/data`.

---

## 7. Conectar o EasyPanel ao GitHub

Esta é a etapa que habilita o **botão Implantar** puxando código direto do repositório.

### 7.1 Instalar o GitHub App

1. No EasyPanel, canto superior direito → **Settings** → aba **GitHub**.
2. Clique em **Connect to GitHub** / **Install GitHub App**.
3. Você é levado ao GitHub. Escolha:
   - **Only select repositories** → selecione o repositório do projeto (ex.: `wandersonmk/razy`), **ou**
   - **All repositories**, se preferir liberar geral.
4. Clique em **Install & Authorize**.
5. Você volta ao EasyPanel com a conta vinculada.

### 7.2 Alternativa: repositório privado sem GitHub App

Se preferir não instalar o App, use uma **Deploy Key**:

1. No EasyPanel → **Settings** → **SSH Keys** → gere uma chave e copie a pública.
2. No GitHub → repositório → **Settings** → **Deploy keys** → **Add deploy key** → cole a chave, marque *Allow write access* apenas se necessário.
3. Ao criar o serviço, use o source **Git** com a URL SSH (`git@github.com:usuario/repo.git`).

> O GitHub App é mais simples e já habilita o webhook de auto-deploy sozinho. Prefira ele.

---

## 8. Criar o serviço de IA (LangChain + LangGraph)

### 8.1 Estrutura esperada no repositório

O serviço mora numa subpasta do monorepo:

```
repositório/
├── app/                    ← front-end (Nuxt, vai para a Vercel)
├── server/
└── ai-service/             ← 👈 é ESTA pasta que vira o container
    ├── Dockerfile
    ├── pyproject.toml
    └── app/
        ├── main.py         # FastAPI + lifespan
        ├── config.py       # Settings (variáveis de ambiente)
        ├── api/health.py   # GET /healthz
        ├── db/postgres.py  # pool asyncpg
        ├── db/redis.py     # cliente Redis
        └── graph/build.py  # StateGraph do LangGraph
```

O `Dockerfile` de referência:

```dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# uv (instalador rápido de dependências)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependências primeiro (camada cacheável — acelera muito os redeploys)
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Código da aplicação
COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

E as dependências no `pyproject.toml`:

```toml
[project]
name = "razy-ai-service"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "asyncpg",
    "redis",
    "langchain",
    "langchain-openai",
    "langgraph",
    "langgraph-checkpoint-postgres",
    "psycopg[binary]",
    "openai",
]
```

> ⚠️ **`langgraph-checkpoint-postgres` e `psycopg[binary]` são obrigatórios** para o checkpointer do LangGraph persistir no Postgres. Sem eles o serviço sobe e morre no startup.

### 8.2 Criar o serviço no EasyPanel

1. Projeto `razy` → **+ Service** → tipo **App**.
2. **Service Name:** `ai-service`
3. **Create**.

### 8.3 Configurar a origem (Source)

Abra o serviço `ai-service` → aba **Source**:

| Campo | Valor | Por quê |
|---|---|---|
| **Provider** | GitHub | Habilita o botão Implantar e o auto-deploy |
| **Owner** | seu usuário/organização | — |
| **Repository** | nome do repositório | — |
| **Branch** | `main` | Branch que dispara o deploy |
| **Build Path** | `/ai-service` | 🔑 **Crítico.** O Dockerfile faz `COPY pyproject.toml ./` e `COPY app ./app` — caminhos relativos a esta pasta. Se deixar `/`, o build falha com *file not found* |

Clique em **Save**.

### 8.4 Configurar o build

Aba **Build**:

| Campo | Valor |
|---|---|
| **Build Method** | **Dockerfile** |
| **File** | `Dockerfile` (relativo ao Build Path) |

> Não use Nixpacks nem Buildpacks aqui. O Dockerfile dá controle total sobre a versão do Python e sobre o cache de dependências.

**Save**.

### 8.5 Configurar rede e recursos

Aba **Advanced** (ou **Deploy**):

| Campo | Valor | Observação |
|---|---|---|
| **Replicas** | `1` | ⚠️ Mantenha em 1. O serviço já usa 2 workers internos com *advisory lock* no Postgres para não duplicar disparos. Subir réplicas em máquinas diferentes duplicaria os envios |
| **Memory Limit** | `2048` MB | Suficiente para 2 workers com LangChain |
| **Port** | `8000` | Porta que o uvicorn escuta |

---

## 9. Variáveis de ambiente

Aba **Environment** do serviço `ai-service`. Cole no formato `CHAVE=valor`, uma por linha:

```env
# --- Conexões internas (hostnames do Docker, NÃO use localhost nem IP público) ---
POSTGRES_URL=postgres://postgres:SENHA_DO_POSTGRES@razy_postgres:5432/postgres
REDIS_URL=redis://default:SENHA_DO_REDIS@razy_redis:6379

# --- Banco de negócio (Supabase) ---
SUPABASE_DB_URL=postgresql://postgres.PROJETO:SENHA@aws-1-sa-east-1.pooler.supabase.com:5432/postgres

# --- IA ---
OPENAI_API_KEY=sk-proj-...

# --- Integrações ---
UAZAPI_URL=https://seuservidor.uazapi.com

# --- Segurança interna ---
INTERNAL_TOKEN=gere-um-token-longo-e-aleatorio-aqui
```

### 9.1 O que é cada variável

| Variável | Obrigatória | Descrição |
|---|:---:|---|
| `POSTGRES_URL` | ✅ | Postgres do EasyPanel. Guarda o **checkpointer do LangGraph** (estado das conversas). O serviço **não sobe** sem ela |
| `REDIS_URL` | ✅ | Redis do EasyPanel. Memória de curto prazo. O serviço **não sobe** sem ela |
| `INTERNAL_TOKEN` | ✅ | Autentica chamadas do painel para o serviço. Gere com `openssl rand -hex 32` |
| `SUPABASE_DB_URL` | ⚠️ | Banco de negócio (contatos, campanhas, disparos). O serviço **sobe sem ela**, mas registra um aviso e o disparo/IA fica indisponível |
| `OPENAI_API_KEY` | ⚠️ | Opcional no ambiente: se ausente, cada usuário configura a própria chave pelo painel (Configurações → Integrações) |
| `UAZAPI_URL` | ⚠️ | Base da API do WhatsApp. Tem valor padrão no código |

### 9.2 Regras que evitam 90% dos erros

1. **Use os hostnames internos** (`razy_postgres`, `razy_redis`). `localhost` dentro do container aponta para o próprio container, não para o banco.
2. **Sem aspas** em volta dos valores. O EasyPanel injeta a linha literal — aspas viram parte da senha.
3. **Cuidado com caracteres especiais na senha.** Se a senha tiver `@`, `:`, `/` ou `#`, ela quebra a URL. Ou gere senhas alfanuméricas, ou faça URL-encode (`@` → `%40`).
4. **Estas variáveis são segredo.** Nunca commite no GitHub — o `.env` deve estar no `.gitignore`.

> 💡 Em desenvolvimento local o `config.py` lê o `.env` da raiz do projeto. Em produção esse arquivo não existe no container, e o `pydantic-settings` usa direto as variáveis do painel. Nada a mudar no código.

**Save** ao terminar.

---

## 10. Domínio e HTTPS

### 10.1 Apontar o DNS

No painel do seu provedor de domínio, crie um registro:

| Tipo | Nome | Valor | TTL |
|---|---|---|---|
| `A` | `ia` | `SEU_IP` | 300 |

Isso cria `ia.seudominio.com.br`. A propagação leva de 5 minutos a algumas horas — confira com:

```bash
nslookup ia.seudominio.com.br
```

### 10.2 Configurar no EasyPanel

1. Serviço `ai-service` → aba **Domains** → **Add Domain**.
2. Preencha:

   | Campo | Valor |
   |---|---|
   | **Host** | `ia.seudominio.com.br` |
   | **Port** | `8000` |
   | **HTTPS** | ✅ ligado |
   | **Certificate** | Let's Encrypt (automático) |

3. **Save**. O EasyPanel emite o certificado em 1–2 minutos.

> Sem domínio próprio? O EasyPanel oferece um subdomínio `*.easypanel.host` gratuito. Serve para testar, mas para produção use domínio próprio.

### 10.3 Liberar o CORS para o front-end

O `main.py` traz a lista de origens permitidas:

```python
ALLOWED_ORIGINS = [
    "https://razy.vercel.app",
    "http://localhost:3000",
]
```

**Se o front estiver em outro domínio, adicione-o nessa lista e faça um novo deploy.** Requisição do navegador barrada por CORS é a causa mais comum de "o painel não fala com a IA".

---

## 11. Primeiro deploy e validação

### 11.1 Implantar

Serviço `ai-service` → botão **Deploy** / **Implantar** (canto superior direito).

Acompanhe pela aba **Deployments** → clique no deploy em andamento para ver o log de build ao vivo. O primeiro build baixa a imagem do Python e compila todas as dependências — leva de **3 a 8 minutos**. Os seguintes usam cache e caem para 30–60 segundos.

### 11.2 Checar a saúde do serviço

```bash
curl https://ia.seudominio.com.br/healthz
```

Resposta esperada:

```json
{"status":"ok"}
```

### 11.3 Conferir o log de startup

Aba **Logs**. Um startup saudável mostra:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Conectado ao Postgres do Supabase (dados de negócio).
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Se aparecer `SUPABASE_DB_URL não definido — disparo/IA indisponível até configurar`, o serviço subiu mas falta essa variável.

### 11.4 Confirmar que o LangGraph criou as tabelas

Serviço `postgres` → **Console** (ou via `docker exec`):

```sql
\dt
```

Devem aparecer: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`.
Se estiverem lá, o checkpointer do LangGraph está persistindo corretamente.

---

## 12. Deploy automático a cada push no GitHub

Este é o objetivo final: **subiu para o GitHub → o EasyPanel atualiza sozinho.**

### 12.1 Se você conectou pelo GitHub App (passo 7.1)

O webhook já foi criado automaticamente. Só falta ligar:

1. Serviço `ai-service` → aba **Source**.
2. Ative **Auto Deploy** (ou **Deploy on push**).
3. Confirme que o **Branch** é o mesmo que você usa (`main`).
4. **Save**.

Pronto. Todo `git push origin main` dispara build e deploy.

### 12.2 Se você usou Deploy Key ou quer controle manual do webhook

1. Serviço `ai-service` → aba **Deployments** → copie a **Deploy Webhook URL** (algo como `https://SEU_IP:3000/api/deploy/xxxxxxxx`).
2. No GitHub → repositório → **Settings** → **Webhooks** → **Add webhook**:

   | Campo | Valor |
   |---|---|
   | **Payload URL** | a URL copiada |
   | **Content type** | `application/json` |
   | **Which events** | *Just the push event* |
   | **Active** | ✅ |

3. **Add webhook**.

O GitHub faz um ping de teste na hora. Um ✅ verde na lista de webhooks confirma que está funcionando.

### 12.3 Testar o fluxo completo

```bash
# no seu computador
git add .
git commit -m "test: valida auto-deploy"
git push origin main
```

Em segundos, a aba **Deployments** do EasyPanel deve mostrar um novo build começando. Acompanhe até o verde.

### 12.4 Deploy manual (o "botão Implantar")

Sempre disponível, independente do webhook: **Deploy** no canto superior direito do serviço. Ele puxa o último commit do branch configurado e rebuilda. Use quando:

- Você mudou uma variável de ambiente (mudança de env **exige** redeploy para valer).
- O webhook falhou e você quer forçar.
- Você quer redeployar sem ter feito commit novo.

### 12.5 Voltar para uma versão anterior (rollback)

Aba **Deployments** → localize um deploy antigo que estava bom → **Redeploy**. Volta ao código daquele commit em segundos. Vale conhecer *antes* de precisar.

---

## 13. Operação do dia a dia

### 13.1 Comandos e ações mais usados

| Preciso… | Onde |
|---|---|
| Ver logs em tempo real | Serviço → **Logs** |
| Reiniciar sem rebuildar | Serviço → **Restart** |
| Mudar uma variável | **Environment** → editar → **Save** → **Deploy** |
| Abrir um shell no container | Serviço → **Console** |
| Rodar SQL no Postgres | Serviço `postgres` → **Console** |
| Ver consumo de CPU/RAM | Dashboard → **Monitor** |

### 13.2 Backup do Postgres

O EasyPanel tem backup agendado por serviço: `postgres` → aba **Backups** → configure destino (S3 ou local) e frequência.

Backup manual via SSH:

```bash
docker exec $(docker ps -qf name=razy_postgres) \
  pg_dump -U postgres postgres > backup-$(date +%F).sql
```

> ⚠️ Este Postgres guarda o **estado das conversas do LangGraph**. Perdê-lo significa perder o histórico/contexto dos atendimentos em andamento. O banco de negócio (Supabase) é separado e tem backup próprio.

### 13.3 Manutenção do servidor

```bash
# limpar imagens Docker antigas (recupera disco — rode mensalmente)
docker system prune -af

# atualizar o sistema
apt update && apt upgrade -y

# checar espaço em disco
df -h
```

### 13.4 Atualizar o próprio EasyPanel

Dashboard → **Settings** → **General** → **Check for updates** → **Update**. Os serviços continuam rodando durante a atualização do painel.

---

## 14. Solução de problemas

### Build falha com `COPY failed: file not found`

**Causa:** o **Build Path** está errado. O Dockerfile espera o contexto na pasta `ai-service/`.
**Correção:** aba **Source** → **Build Path** = `/ai-service`.

---

### Serviço sobe e cai em loop (restart contínuo)

Veja os **Logs**. As causas em ordem de frequência:

| Erro no log | Causa | Correção |
|---|---|---|
| `ValidationError: POSTGRES_URL Field required` | Variável ausente | Adicione em **Environment** e redeploy |
| `connection refused` / `could not translate host name` | Hostname interno errado | Use `razy_postgres`, não `localhost`. Confirme na aba **Credentials** do Postgres |
| `password authentication failed` | Senha errada ou com caractere especial não escapado | Recopie a Internal URL; URL-encode caracteres especiais |
| `ModuleNotFoundError: langgraph.checkpoint.postgres` | Falta dependência | Adicione `langgraph-checkpoint-postgres` e `psycopg[binary]` no `pyproject.toml` |

---

### `/healthz` não responde, mas o container está "running"

1. Confirme que a porta no **Domains** é **8000** (a mesma do `EXPOSE`/uvicorn).
2. Teste por dentro: serviço → **Console** → `curl http://127.0.0.1:8000/healthz`.
   - Responde por dentro mas não por fora → problema de domínio/proxy.
   - Não responde por dentro → a aplicação não subiu; volte aos logs.

---

### Certificado HTTPS não é emitido

- O DNS ainda não propagou. Verifique com `nslookup dominio` — precisa retornar `SEU_IP`.
- A porta 80 está fechada. O Let's Encrypt valida por HTTP: `ufw allow 80/tcp`.
- Aguarde e clique em **Save** no domínio de novo para forçar nova tentativa.

---

### Push no GitHub não dispara deploy

1. GitHub → repositório → **Settings** → **Webhooks** → clique no webhook → aba **Recent Deliveries**. Uma entrega com ❌ mostra a resposta do servidor.
2. Confira se o branch do push é o mesmo configurado em **Source** → **Branch**.
3. Confirme que **Auto Deploy** está ativado.

---

### O painel não consegue chamar o serviço (erro de CORS)

No console do navegador aparece *blocked by CORS policy*.
**Correção:** adicione a origem do front em `ALLOWED_ORIGINS` no `main.py`, faça commit e redeploy.

---

### Disparos ou follow-ups saindo duplicados

**Causa:** mais de uma réplica do serviço rodando. Os loops de background usam *advisory lock* no Postgres, que protege entre workers do mesmo container — mas réplicas separadas com pools distintos podem escapar disso.
**Correção:** **Advanced** → **Replicas** = `1`.

---

### Memória estourando / container morto por OOM

```bash
docker stats     # veja quem está consumindo
free -h
```

Opções, em ordem: reduzir `--workers 2` para `1` no `CMD` do Dockerfile → aumentar o **Memory Limit** do serviço → subir o plano da VPS.

---

## Checklist final

Antes de considerar o ambiente pronto:

- [ ] VPS provisionada, com firewall configurado (22, 80, 443, 3000)
- [ ] EasyPanel instalado e conta de administrador criada
- [ ] Projeto `razy` criado
- [ ] Serviço `postgres` rodando, com volume persistente e credenciais salvas
- [ ] Serviço `redis` rodando, com credenciais salvas
- [ ] GitHub conectado ao EasyPanel
- [ ] Serviço `ai-service` com **Build Path** = `/ai-service` e método **Dockerfile**
- [ ] Todas as variáveis de ambiente preenchidas com os **hostnames internos**
- [ ] Domínio apontado, HTTPS ativo
- [ ] `curl https://SEU_DOMINIO/healthz` → `{"status":"ok"}`
- [ ] Tabelas `checkpoints*` criadas no Postgres
- [ ] **Auto Deploy** ligado e testado com um push real
- [ ] Backup do Postgres agendado
- [ ] Origem do front-end presente em `ALLOWED_ORIGINS`

---

## Resumo da arquitetura

```
                    ┌──────────────────────┐
   Usuário ────────>│  Painel (Nuxt)       │
                    │  Vercel              │
                    └──────────┬───────────┘
                               │ HTTPS
                               ▼
┌──────────────────────────────────────────────────────────┐
│  VPS  ·  EasyPanel  ·  Projeto "razy"                    │
│                                                          │
│   ┌────────────────────────────────────────────┐         │
│   │ ai-service  (App)                          │         │
│   │ FastAPI + LangChain + LangGraph            │         │
│   │ uvicorn :8000 · 2 workers                  │         │
│   └───────┬────────────────────┬───────────────┘         │
│           │                    │                         │
│           ▼                    ▼                         │
│   ┌───────────────┐    ┌───────────────┐                 │
│   │ razy_postgres │    │  razy_redis   │                 │
│   │ checkpointer  │    │   memória     │                 │
│   │ do LangGraph  │    │  de conversa  │                 │
│   └───────────────┘    └───────────────┘                 │
└─────────────┬───────────────────────┬────────────────────┘
              │                       │
              ▼                       ▼
      ┌───────────────┐       ┌───────────────┐
      │   Supabase    │       │    UAzAPI     │
      │ dados de      │       │   WhatsApp    │
      │ negócio       │       │               │
      └───────────────┘       └───────────────┘

              ▲
              │ push → webhook → build → deploy
      ┌───────────────┐
      │    GitHub     │
      └───────────────┘
```
