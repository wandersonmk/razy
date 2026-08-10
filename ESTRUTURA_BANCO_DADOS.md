# Estrutura do Banco de Dados — Razy

> Documento gerado a partir da introspecção direta do banco Supabase em **04/08/2026**.
> Projeto: **Aplicativo IA** (`xdpjhvqfuhjylxaishks`) · Região `sa-east-1` · PostgreSQL **17.6.1**
> Host: `db.xdpjhvqfuhjylxaishks.supabase.co`

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Diagrama de relacionamentos](#2-diagrama-de-relacionamentos)
3. [Tabelas](#3-tabelas)
4. [Funções (RPC)](#4-funções-rpc)
5. [Índices](#5-índices)
6. [Políticas RLS](#6-políticas-rls)
7. [Triggers](#7-triggers)
8. [Extensões instaladas](#8-extensões-instaladas)
9. [Migrations aplicadas](#9-migrations-aplicadas)
10. [O que NÃO existe no banco](#10-o-que-não-existe-no-banco)

---

## 1. Visão geral

O schema `public` tem **13 tabelas**, **1 função RPC**, **0 views**, **0 enums**, **0 triggers** e **0 edge functions**.
Todas as tabelas têm **RLS habilitado** e são isoladas por `usuario_id` (que aponta para `auth.users.id`).

| Tabela | Linhas | Tamanho | Papel |
|---|---:|---:|---|
| `usuarios` | 2 | 48 kB | Perfil do usuário, espelho de `auth.users` |
| `instancias` | 26 | 64 kB | Canais WhatsApp (UAzAPI) |
| `assistentes` | 27 | 464 kB | Configuração da IA por instância |
| `integracoes` | 2 | 48 kB | Chave OpenAI + flag de saldo |
| `publicos` | 40 | 32 kB | Listas/segmentos de contatos |
| `contatos` | 15.082 | 20 MB | Leads |
| `campanhas` | 42 | 96 kB | Campanhas de disparo em massa |
| `disparos` | 10.820 | 4.6 MB | Envio individual por contato |
| `campanha_logs` | 497 | 296 kB | Log de eventos da campanha |
| `followup_configs` | 1 | 56 kB | Sequência de follow-up |
| `followup_etapas` | 3 | 32 kB | Etapas da sequência |
| `followup_disparos` | 0 | 520 kB | Agendamento de follow-up |
| `validacoes_numeros` | 56 | 22 MB | Histórico de validação de números |

Schemas presentes: `public`, `auth`, `storage`, `realtime`, `graphql`, `graphql_public`, `extensions`, `vault`, `supabase_migrations`.

---

## 2. Diagrama de relacionamentos

```
auth.users
   │
   ├──> usuarios (id = auth.users.id)          [CASCADE]
   │       └──> instancias (usuario_id)         [CASCADE]
   │               ├──> assistentes (instancia_id)       [SET NULL] · UNIQUE parcial
   │               ├──> campanhas (instancia_id)         [SET NULL]
   │               ├──> disparos (canal_id)              [SET NULL]
   │               ├──> campanha_logs (canal_id)         [SET NULL]
   │               └──> followup_disparos (canal_id)     [sem ação]
   │
   ├──> publicos (usuario_id)                   [CASCADE]
   │       ├──> contatos (publico_id)           [CASCADE]
   │       └──> campanhas (publico_id)          [sem ação — bloqueia exclusão]
   │
   ├──> contatos (usuario_id)                   [CASCADE]
   │       ├──> disparos (contato_id)           [CASCADE]
   │       └──> followup_disparos (contato_id)  [sem ação]
   │
   └──> campanhas (usuario_id)                  [CASCADE]
           ├──> disparos (campanha_id)          [CASCADE]
           ├──> campanha_logs (campanha_id)     [CASCADE]
           ├──> followup_configs (campanha_id)  [CASCADE]
           └──> followup_disparos (campanha_id) [sem ação]

followup_configs
   └──> followup_etapas (config_id)             [CASCADE]
           └──> followup_disparos (etapa_id)    [sem ação]

integracoes        (usuario_id UNIQUE, sem FK)
validacoes_numeros (usuario_id, sem FK)
```

> **Atenção:** `campanhas.canal_id` existe mas **não tem FK** — é coluna legada, substituída por `campanhas.instancia_id`.
> `integracoes.usuario_id` e `validacoes_numeros.usuario_id` também **não têm FK** para `auth.users`.

---

## 3. Tabelas

### 3.1 `usuarios`

Perfil da conta, com `id` espelhando `auth.users.id`.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** · FK → `auth.users(id)` ON DELETE CASCADE |
| `nome` | `text` | não | — | |
| `empresa` | `text` | sim | — | |
| `email` | `text` | não | — | **UNIQUE** |
| `perfil` | `text` | não | `'admin'` | |
| `created_at` | `timestamptz` | não | `now()` | |
| `updated_at` | `timestamptz` | não | `now()` | não há trigger — atualização é feita pela aplicação |

---

### 3.2 `instancias`

Canais WhatsApp conectados via UAzAPI. Uma instância = um número.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `usuario_id` | `uuid` | não | — | FK → `usuarios(id)` ON DELETE CASCADE |
| `nome_instancia` | `text` | não | — | Nome exibido no painel |
| `uazapi_instance_name` | `text` | sim | — | Nome na UAzAPI |
| `uazapi_token` | `text` | não | — | **UNIQUE** · token de autenticação da instância |
| `status` | `text` | não | `'disconnected'` | Status em cache; o disparo revalida **ao vivo** na UAzAPI |
| `phone` | `text` | sim | — | Número conectado |
| `uso_notificacao` | `boolean` | não | `false` | Canal só para notificar atendente — **não faz atendimento de IA** |
| `bloqueado_ate` | `timestamptz` | sim | — | Fora da rotação de disparo até este instante (restrição do WhatsApp). `NULL` = liberado |
| `bloqueio_motivo` | `text` | sim | — | Erro devolvido pela UAzAPI/WhatsApp |
| `data_criacao` | `timestamptz` | não | `now()` | |
| `created_at` | `timestamptz` | não | `now()` | |

> `bloqueado_ate` / `bloqueio_motivo` implementam o cooldown do erro 463 (canal restrito sai da rotação).

---

### 3.3 `assistentes`

Configuração do assistente de IA. Vínculo **1 instância ↔ 1 assistente** garantido por índice único parcial.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `usuario_id` | `uuid` | não | — | Sem FK declarada |
| `instancia_id` | `uuid` | sim | — | FK → `instancias(id)` ON DELETE **SET NULL** · fica órfão ao excluir a instância |
| `nome` | `text` | sim | — | Nome do assistente (**não** é imposto como nome da conversa) |
| `tipo` | `text` | não | `'principal'` | Sem CHECK constraint |
| `ativo` | `boolean` | não | `true` | |
| `empresa_nome` | `text` | sim | — | |
| `empresa_info` | `text` | sim | — | Base de conhecimento |
| `horario_funcionamento` | `text` | sim | — | |
| `instrucao` | `text` | sim | — | Prompt/instrução do sistema |
| `atendente_telefone` | `text` | sim | — | Destino da notificação de transferência |
| `notificar_rotativo` | `boolean` | não | `false` | Rodízio entre canais de notificação |
| `pausa_ativa` | `boolean` | não | `true` | Pausa a IA quando o humano assume |
| `pausa_minutos` | `integer` | não | `30` | Duração da pausa |
| `ler_imagem` | `boolean` | não | `false` | Capacidade: descrever imagens do cliente via visão (custo extra de tokens) |
| `instrucao_imagem` | `text` | sim | — | Instrução só para imagens. Vazio = segue `instrucao` |
| `ler_documento` | `boolean` | não | `false` | Capacidade: extrair texto de PDF/Word/txt (até 8.000 caracteres) |
| `instrucao_documento` | `text` | sim | — | Instrução só para documentos. Vazio = segue `instrucao` |
| `created_at` | `timestamptz` | não | `now()` | |
| `updated_at` | `timestamptz` | não | `now()` | |

**Capacidades de mídia** (aba *Capacidades* no painel): áudio **não tem flag** — é nativo e sempre
ativo (transcrição Whisper). Imagem e documento são opcionais **por assistente**, isto é, por número
conectado. Quando desligados, a mídia chega no WhatsApp mas a IA só enxerga a legenda.

---

### 3.4 `integracoes`

Credenciais de terceiros. **Um registro por usuário** (`usuario_id` UNIQUE).

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `usuario_id` | `uuid` | não | — | **UNIQUE** · sem FK |
| `openai_api_key` | `text` | sim | — | Chave usada pelo painel **e** pelo serviço de IA (não a do `.env`) |
| `openai_sem_saldo` | `boolean` | não | `false` | Gravado pelo serviço de IA ao receber 429/`insufficient_quota`; limpo quando a IA volta a responder. Alimenta o banner do painel |
| `openai_sem_saldo_em` | `timestamptz` | sim | — | Quando a flag foi levantada |
| `updated_at` | `timestamptz` | não | `now()` | |

---

### 3.5 `publicos`

Segmentos/listas de contatos.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `usuario_id` | `uuid` | não | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `nome` | `text` | não | — | |
| `regiao` | `text` | sim | — | |
| `status` | `text` | não | `'frio'` | CHECK: `frio` \| `morno` \| `quente` |
| `created_at` | `timestamptz` | não | `now()` | |

---

### 3.6 `contatos`

Leads. Maior tabela transacional do sistema (15 mil linhas).

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `publico_id` | `uuid` | não | — | FK → `publicos(id)` ON DELETE CASCADE |
| `usuario_id` | `uuid` | não | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `nome` | `text` | sim | — | |
| `telefone` | `text` | não | — | Sem constraint de formato/unicidade |
| `email` | `text` | sim | — | |
| `empresa` | `text` | sim | — | |
| `etapa` | `text` | sim | — | |
| `observacao` | `text` | sim | — | |
| `dados_extras` | `jsonb` | sim | — | Colunas livres da planilha importada |
| `followup_excluido` | `boolean` | não | `false` | `true` = lead deu negativa; sai de **todas** as sequências de follow-up, atuais e futuras |
| `followup_excluido_em` | `timestamptz` | sim | — | |
| `followup_excluido_motivo` | `text` | sim | — | |
| `created_at` | `timestamptz` | não | `now()` | |

> ⚠️ Esta tabela **só tem a PK como índice**. Consultas por `publico_id` ou `usuario_id` fazem seq scan em 20 MB.

---

### 3.7 `campanhas`

Campanha de disparo em massa.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `usuario_id` | `uuid` | não | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `publico_id` | `uuid` | não | — | FK → `publicos(id)` — **sem ON DELETE**, trava exclusão do público |
| `nome` | `text` | não | — | |
| `mensagem` | `text` | sim | — | Texto quando `modo_mensagem = 'manual'` |
| `status` | `text` | não | `'rascunho'` | CHECK: `rascunho` \| `em_andamento` \| `concluida` \| `pausada` \| `falhou` |
| `modo_mensagem` | `text` | não | `'manual'` | CHECK: `manual` \| `ia` |
| `intervalo_segundos` | `integer` | não | `10` | Espaçamento entre envios |
| `agendado_para` | `timestamptz` | sim | — | |
| `usar_roteamento` | `boolean` | não | `false` | Distribui entre múltiplos canais |
| `alternar_canais` | `boolean` | não | `false` | Alterna canal a cada envio |
| `canais_ids` | `uuid[]` | sim | — | Canais escolhidos para o modo multi-canal. **NULL/vazio = todos os elegíveis** (comportamento histórico) |
| `instancia_id` | `uuid` | sim | — | FK → `instancias(id)` ON DELETE SET NULL — **canal atual** |
| `canal_id` | `uuid` | sim | — | ⚠️ **Legado, sem FK** — substituído por `instancia_id` |
| `instancia_token` | `text` | sim | — | ⚠️ Legado — snapshot do token |
| `instancia_url` | `text` | sim | — | ⚠️ Legado — snapshot da URL |
| `total_enviados` | `integer` | não | `0` | Contador denormalizado |
| `total_falhas` | `integer` | não | `0` | Contador denormalizado |
| `total_respostas` | `integer` | não | `0` | Contador denormalizado — a contagem confiável vem da RPC `contar_respostas_campanhas` |
| `arquivada` | `boolean` | não | `false` | Soft-delete: sai da página de Campanhas mas preserva métricas em Relatórios/Dashboard. Limpeza definitiva pelo botão "Apagar métricas" |
| `iniciado_em` | `timestamptz` | sim | — | |
| `concluido_em` | `timestamptz` | sim | — | |
| `created_at` | `timestamptz` | não | `now()` | |

---

### 3.8 `disparos`

Registro de envio individual (uma linha por contato por campanha).

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `campanha_id` | `uuid` | não | — | FK → `campanhas(id)` ON DELETE CASCADE |
| `contato_id` | `uuid` | não | — | FK → `contatos(id)` ON DELETE CASCADE |
| `usuario_id` | `uuid` | não | — | FK → `auth.users(id)` ON DELETE CASCADE |
| `canal_id` | `uuid` | sim | — | FK → `instancias(id)` ON DELETE SET NULL — canal que enviou |
| `status` | `text` | não | `'pendente'` | CHECK: `pendente` \| `enviado` \| `falhou` |
| `mensagem_enviada` | `text` | sim | — | Texto final (após personalização/IA) |
| `erro` | `text` | sim | — | Mensagem de erro da UAzAPI |
| `enviado_em` | `timestamptz` | sim | — | |
| `resposta_texto` | `text` | sim | — | Primeira resposta do lead |
| `respondido_em` | `timestamptz` | sim | — | Preenchido = lead respondeu |
| `created_at` | `timestamptz` | não | `now()` | |

---

### 3.9 `campanha_logs`

Trilha de eventos da campanha (exibida no painel de execução).

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `campanha_id` | `uuid` | não | — | FK → `campanhas(id)` ON DELETE CASCADE |
| `usuario_id` | `uuid` | não | — | Sem FK |
| `canal_id` | `uuid` | sim | — | FK → `instancias(id)` ON DELETE SET NULL |
| `nivel` | `text` | não | `'info'` | CHECK: `info` \| `aviso` \| `erro` |
| `evento` | `text` | não | — | Chave do evento |
| `detalhe` | `text` | sim | — | |
| `created_at` | `timestamptz` | não | `now()` | |

> Só permite `SELECT` e `INSERT` via RLS — não há política de UPDATE nem DELETE (log imutável para o cliente).

---

### 3.10 `followup_configs`

Sequência de follow-up. `campanha_id` nulo = configuração **global** do usuário.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `campanha_id` | `uuid` | sim | — | FK → `campanhas(id)` ON DELETE CASCADE · `NULL` = global |
| `usuario_id` | `uuid` | não | — | Sem FK |
| `ativo` | `boolean` | não | `true` | |
| `criado_em` | `timestamptz` | não | `now()` | |

---

### 3.11 `followup_etapas`

Etapas ordenadas de uma sequência.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `config_id` | `uuid` | não | — | FK → `followup_configs(id)` ON DELETE CASCADE |
| `ordem` | `smallint` | não | — | Sem UNIQUE em `(config_id, ordem)` |
| `delay_minutos` | `integer` | não | — | CHECK: `> 0` — tempo após a etapa anterior |
| `modo_mensagem` | `text` | não | `'ia'` | CHECK: `manual` \| `ia` |
| `mensagem` | `text` | sim | — | Usado quando `modo_mensagem = 'manual'` |
| `criado_em` | `timestamptz` | não | `now()` | |

---

### 3.12 `followup_disparos`

Fila de agendamento de follow-up.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `config_id` | `uuid` | não | — | FK → `followup_configs(id)` ON DELETE CASCADE |
| `etapa_id` | `uuid` | não | — | FK → `followup_etapas(id)` — sem ON DELETE |
| `campanha_id` | `uuid` | não | — | FK → `campanhas(id)` — sem ON DELETE |
| `contato_id` | `uuid` | não | — | FK → `contatos(id)` — sem ON DELETE |
| `usuario_id` | `uuid` | não | — | Sem FK |
| `canal_id` | `uuid` | sim | — | FK → `instancias(id)` — sem ON DELETE |
| `status` | `text` | não | `'pendente'` | CHECK: `pendente` \| `enviado` \| `respondeu` \| `cancelado` |
| `agendado_para` | `timestamptz` | não | — | Momento do envio |
| `enviado_em` | `timestamptz` | sim | — | |
| `mensagem_enviada` | `text` | sim | — | |
| `criado_em` | `timestamptz` | não | `now()` | |

> ⚠️ As FKs sem `ON DELETE` (`etapa_id`, `campanha_id`, `contato_id`, `canal_id`) bloqueiam a exclusão dos registros pai enquanto houver follow-up agendado.

---

### 3.13 `validacoes_numeros`

Histórico das validações de números em massa. Segunda maior tabela (22 MB) por causa do `jsonb`.

| Coluna | Tipo | Nulo | Default | Notas |
|---|---|---|---|---|
| `id` | `uuid` | não | `gen_random_uuid()` | **PK** |
| `usuario_id` | `uuid` | não | `auth.uid()` | Sem FK |
| `nome_arquivo` | `text` | sim | — | Arquivo importado |
| `canal` | `text` | sim | — | Instância usada na validação |
| `total` | `integer` | não | `0` | |
| `validos_count` | `integer` | não | `0` | |
| `invalidos_count` | `integer` | não | `0` | |
| `dados` | `jsonb` | não | `'{}'` | Resultado completo — responsável pelo tamanho da tabela |
| `created_at` | `timestamptz` | não | `now()` | |

> Sem política de `UPDATE` via RLS — só `SELECT`, `INSERT` e `DELETE`.

---

## 4. Funções (RPC)

Existe **uma única** função no schema `public`.

### `contar_respostas_campanhas(ids uuid[])`

```sql
CREATE OR REPLACE FUNCTION public.contar_respostas_campanhas(ids uuid[])
 RETURNS TABLE(campanha_id uuid, total bigint)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  select d.campanha_id, count(distinct d.contato_id)::bigint
  from public.disparos d
  where d.campanha_id = any(ids)
    and d.respondido_em is not null
  group by d.campanha_id
$function$
```

| Propriedade | Valor |
|---|---|
| Retorno | `TABLE(campanha_id uuid, total bigint)` |
| Linguagem | `sql` |
| Volatilidade | `STABLE` |
| `SECURITY DEFINER` | **não** (roda como `INVOKER` — respeita RLS) |
| `search_path` | fixado em `public` |

**Por que existe:** o PostgREST limita respostas a 1.000 linhas. Agregar `disparos` no navegador truncava silenciosamente e o contador de respostas do painel ficava errado. A contagem passou a ser feita no banco.

---

## 5. Índices

| Tabela | Índice | Definição |
|---|---|---|
| `assistentes` | `assistentes_pkey` | `UNIQUE (id)` |
| `assistentes` | `assistentes_instancia_uniq` | `UNIQUE (instancia_id) WHERE instancia_id IS NOT NULL` — garante 1 assistente por instância |
| `assistentes` | `idx_assistentes_instancia_id` | `(instancia_id)` |
| `campanha_logs` | `campanha_logs_pkey` | `UNIQUE (id)` |
| `campanha_logs` | `campanha_logs_campanha_id_idx` | `(campanha_id)` |
| `campanha_logs` | `campanha_logs_created_at_idx` | `(created_at DESC)` |
| `campanhas` | `campanhas_pkey` | `UNIQUE (id)` |
| `campanhas` | `idx_campanhas_usuario_arquivada` | `(usuario_id, arquivada)` |
| `campanhas` | `idx_campanhas_instancia_id` | `(instancia_id)` |
| `campanhas` | `idx_campanhas_canal_id` | `(canal_id)` |
| `contatos` | `contatos_pkey` | `UNIQUE (id)` |
| `disparos` | `disparos_pkey` | `UNIQUE (id)` |
| `disparos` | `disparos_respondidos_idx` | `(campanha_id, contato_id) WHERE respondido_em IS NOT NULL` — serve a RPC de respostas |
| `followup_configs` | `followup_configs_pkey` | `UNIQUE (id)` |
| `followup_configs` | `fu_configs_campanha_idx` | `(campanha_id)` |
| `followup_configs` | `fu_configs_usuario_idx` | `(usuario_id)` |
| `followup_disparos` | `followup_disparos_pkey` | `UNIQUE (id)` |
| `followup_disparos` | `fu_disparos_contato_idx` | `(contato_id, campanha_id)` |
| `followup_disparos` | `fu_disparos_pendentes_idx` | `(agendado_para) WHERE status = 'pendente'` — usado pelo worker da fila |
| `followup_etapas` | `followup_etapas_pkey` | `UNIQUE (id)` |
| `instancias` | `instancias_pkey` | `UNIQUE (id)` |
| `instancias` | `instancias_uazapi_token_key` | `UNIQUE (uazapi_token)` |
| `instancias` | `idx_instancias_usuario_id` | `(usuario_id)` |
| `integracoes` | `integracoes_pkey` | `UNIQUE (id)` |
| `integracoes` | `integracoes_usuario_id_key` | `UNIQUE (usuario_id)` |
| `publicos` | `publicos_pkey` | `UNIQUE (id)` |
| `usuarios` | `usuarios_pkey` | `UNIQUE (id)` |
| `usuarios` | `usuarios_email_key` | `UNIQUE (email)` |
| `validacoes_numeros` | `validacoes_numeros_pkey` | `UNIQUE (id)` |
| `validacoes_numeros` | `idx_validacoes_numeros_usuario_created` | `(usuario_id, created_at DESC)` |

**Lacunas de índice** (tabelas grandes sem índice de FK):

- `contatos` — nada além da PK, com 15 mil linhas / 20 MB. Faltam `(publico_id)` e `(usuario_id)`.
- `disparos` — falta `(campanha_id)` genérico (o parcial só cobre respondidos) e `(contato_id)`.
- `publicos` — falta `(usuario_id)`.
- `followup_etapas` — falta `(config_id)`.

---

## 6. Políticas RLS

**Todas as 13 tabelas têm RLS habilitado.** O padrão é isolamento por dono: `usuario_id = auth.uid()`.

| Tabela | Política | Comando | Role | Condição |
|---|---|---|---|---|
| `usuarios` | `usuarios_select_self` | SELECT | `authenticated` | `auth.uid() = id` |
| `usuarios` | `usuarios_insert_self` | INSERT | `authenticated` | CHECK `auth.uid() = id` |
| `usuarios` | `usuarios_update_self` | UPDATE | `authenticated` | `auth.uid() = id` (USING + CHECK) |
| `instancias` | `instancias_select` / `_insert` / `_update` / `_delete` | 4 comandos | `authenticated` | `auth.uid() = usuario_id` |
| `assistentes` | `assistentes_select` / `_insert` / `_update` / `_delete` | 4 comandos | `public` | `usuario_id = auth.uid()` |
| `integracoes` | `integracoes_select` / `_insert` / `_update` | 3 comandos | `public` | `usuario_id = auth.uid()` |
| `publicos` | `publicos_select` / `_insert` / `_update` / `_delete` | 4 comandos | `authenticated` | `auth.uid() = usuario_id` |
| `contatos` | `contatos_select` / `_insert` / `_update` / `_delete` | 4 comandos | `authenticated` | `auth.uid() = usuario_id` |
| `campanhas` | `campanhas_select` / `_insert` / `_update` / `_delete` | 4 comandos | `authenticated` | `auth.uid() = usuario_id` |
| `disparos` | `disparos_select` / `_insert` / `_update` / `_delete` | 4 comandos | `authenticated` | `auth.uid() = usuario_id` |
| `campanha_logs` | `campanha_logs_select` / `_insert` | 2 comandos | `public` | `usuario_id = auth.uid()` |
| `followup_configs` | `fu_configs_owner` | ALL | `public` | `usuario_id = auth.uid()` (USING + CHECK) |
| `followup_etapas` | `fu_etapas_owner` | ALL | `public` | `EXISTS (select 1 from followup_configs c where c.id = config_id and c.usuario_id = auth.uid())` |
| `followup_disparos` | `fu_disparos_owner` | ALL | `public` | `usuario_id = auth.uid()` |
| `validacoes_numeros` | `validacoes_numeros_select` / `_insert` / `_delete` | 3 comandos | `public` | `auth.uid() = usuario_id` |

**Pontos de atenção:**

- Políticas com role `public` valem também para `anon`; a proteção efetiva vem de `auth.uid()` retornar `NULL` sem sessão. As tabelas com role `authenticated` são mais estritas.
- `followup_configs` e `followup_disparos` são `FOR ALL` com `WITH CHECK` ausente em `followup_disparos` — o Postgres usa `USING` como fallback no INSERT.
- Sem política de UPDATE: `campanha_logs`, `validacoes_numeros`. Sem política de DELETE: `integracoes`, `campanha_logs`.
- O serviço de IA (`ai-service/`) usa a **service role key**, que ignora RLS por completo.

---

## 7. Triggers

**Nenhum trigger no schema `public`.** Colunas `updated_at` são atualizadas pela aplicação, não pelo banco.

Triggers existentes são apenas os internos do Supabase Storage:

| Schema | Tabela | Trigger |
|---|---|---|
| `storage` | `buckets` | `enforce_bucket_name_length_trigger`, `protect_buckets_delete` |
| `storage` | `objects` | `protect_objects_delete`, `update_objects_updated_at` |

---

## 8. Extensões instaladas

Apenas 6 extensões estão de fato instaladas (as demais estão disponíveis no catálogo, mas não habilitadas):

| Extensão | Versão | Schema | Uso |
|---|---|---|---|
| `plpgsql` | 1.0 | `pg_catalog` | Linguagem procedural padrão |
| `pgcrypto` | 1.3 | `extensions` | `gen_random_uuid()` nos defaults |
| `uuid-ossp` | 1.1 | `extensions` | Geração de UUID (legado) |
| `pg_stat_statements` | 1.11 | `extensions` | Estatísticas de query |
| `supabase_vault` | 0.3.1 | `vault` | Cofre de segredos do Supabase |

Não estão habilitados: `pg_cron`, `pg_net`, `vector`, `pg_graphql`, `postgis` — ou seja, **não há agendamento nem HTTP dentro do banco**. Toda automação (fila de follow-up, disparo) roda fora do Postgres.

---

## 9. Migrations aplicadas

23 migrations, em ordem cronológica:

| # | Versão | Nome |
|---:|---|---|
| 1 | `20260525142455` | `create_usuarios_table` |
| 2 | `20260525145148` | `create_disparo_tables` |
| 3 | `20260525151027` | `create_configuracoes_uazapi` |
| 4 | `20260525152910` | `create_canais_table` |
| 5 | `20260525191531` | `replace_canais_with_instancias` |
| 6 | `20260529175603` | `campanhas_modo_ia_intervalo_e_respostas_disparos` |
| 7 | `20260529211226` | `add_roteamento_and_campanha_logs` |
| 8 | `20260529212622` | `add_integracoes_table` |
| 9 | `20260529220225` | `add_followup_tables` |
| 10 | `20260529221351` | `add_alternar_canais` |
| 11 | `20260529222019` | `followup_global_and_disparo_canal` |
| 12 | `20260529223427` | `add_assistentes` |
| 13 | `20260529224951` | `notificacao_canal_e_rotativo` |
| 14 | `20260529231353` | `assistente_pausa` |
| 15 | `20260602174042` | `add_arquivada_to_campanhas` |
| 16 | `20260603002900` | `criar_validacoes_numeros` |
| 17 | `20260609163917` | `contatos_followup_excluido` |
| 18 | `20260722221927` | `contar_respostas_campanhas_rpc` |
| 19 | `20260724145725` | `integracoes_flag_openai_sem_saldo` |
| 20 | `20260724154549` | `assistentes_vinculo_instancia_schema` |
| 21 | `20260724154604` | `assistentes_vinculo_instancia_dados` |
| 22 | `20260724154846` | `assistentes_rls_delete` |
| 23 | `20260728181625` | `instancias_cooldown_restricao_whatsapp` |

---

## 10. O que NÃO existe no banco

Verificado por introspecção — útil para não procurar onde não há:

- **Views / materialized views:** nenhuma.
- **Tipos ENUM:** nenhum — todos os estados são `text` + `CHECK`.
- **Triggers em `public`:** nenhum.
- **Edge Functions:** nenhuma implantada.
- **Buckets de Storage:** nenhum.
- **Tabelas em Realtime:** nenhuma publicação inclui tabelas do `public` — o painel usa polling, não subscriptions.
- **Extensões de agendamento/HTTP:** `pg_cron` e `pg_net` não instalados.
- **Funções `SECURITY DEFINER`:** nenhuma.
- **Tabela `produtos`:** existe um `create_produtos_table.sql` na raiz do projeto, mas a tabela **não foi criada** no banco.
