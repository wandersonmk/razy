-- ============================================================================
-- Razy — schema completo do Supabase (schema public + storage + realtime)
--
-- Gerado por introspeccao do banco de producao em 22/09/2026.
-- Destino: um projeto Supabase NOVO e vazio.
-- Como rodar: Supabase Studio -> SQL Editor -> cole o arquivo inteiro -> Run
--             (ou: psql "<SUPABASE_DB_URL>" -f supabase/schema_completo.sql)
--
-- O script e idempotente: pode rodar de novo sem quebrar (IF NOT EXISTS e
-- DROP ... IF EXISTS antes de policies/triggers).
--
-- NAO cria usuarios: auth.users e do Supabase. A primeira conta nasce pelo
-- cadastro do proprio painel (/login -> Criar conta), que insere a linha
-- correspondente em public.usuarios.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 0. Extensoes
--   pgcrypto  -> gen_random_uuid() nos defaults das PKs
--   pg_trgm   -> indices GIN de busca por nome (conversas, profissionais).
--                No banco de origem ele vive no schema public; mantenha assim,
--                senao os indices "gin_trgm_ops" abaixo nao acham o operador.
--   unaccent  -> busca sem acento
-- ---------------------------------------------------------------------------
create extension if not exists pgcrypto with schema extensions;
create extension if not exists "uuid-ossp" with schema extensions;
create extension if not exists pg_trgm with schema public;
create extension if not exists unaccent with schema public;

-- ---------------------------------------------------------------------------
-- 1. Tabelas (19)
-- ---------------------------------------------------------------------------
-- assistentes
create table if not exists public.assistentes (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  ativo boolean default true not null,
  empresa_nome text,
  empresa_info text,
  horario_funcionamento text,
  instrucao text,
  atendente_telefone text,
  updated_at timestamp with time zone default now() not null,
  notificar_rotativo boolean default false not null,
  pausa_ativa boolean default true not null,
  pausa_minutos integer default 30 not null,
  instancia_id uuid,
  nome text,
  tipo text default 'principal'::text not null,
  created_at timestamp with time zone default now() not null,
  ler_imagem boolean default false not null,
  instrucao_imagem text,
  ler_documento boolean default false not null,
  instrucao_documento text
);

-- assistentes_profissionais
create table if not exists public.assistentes_profissionais (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  profissional_id uuid not null,
  ativo boolean default false not null,
  empresa_nome text,
  empresa_info text,
  horario_funcionamento text,
  instrucao text,
  ler_imagem boolean default false not null,
  instrucao_imagem text,
  ler_documento boolean default false not null,
  instrucao_documento text,
  pausa_ativa boolean default true not null,
  pausa_minutos integer default 30 not null,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null
);

-- campanha_logs
create table if not exists public.campanha_logs (
  id uuid default gen_random_uuid() not null,
  campanha_id uuid not null,
  usuario_id uuid not null,
  nivel text default 'info'::text not null,
  evento text not null,
  detalhe text,
  canal_id uuid,
  created_at timestamp with time zone default now() not null
);

-- campanhas
create table if not exists public.campanhas (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  publico_id uuid not null,
  nome text not null,
  mensagem text,
  status text default 'rascunho'::text not null,
  total_enviados integer default 0 not null,
  total_falhas integer default 0 not null,
  total_respostas integer default 0 not null,
  instancia_token text,
  instancia_url text,
  created_at timestamp with time zone default now() not null,
  iniciado_em timestamp with time zone,
  concluido_em timestamp with time zone,
  canal_id uuid,
  instancia_id uuid,
  modo_mensagem text default 'manual'::text not null,
  intervalo_segundos integer default 10 not null,
  agendado_para timestamp with time zone,
  usar_roteamento boolean default false not null,
  alternar_canais boolean default false not null,
  arquivada boolean default false not null,
  canais_ids uuid[]
);

-- contatos
create table if not exists public.contatos (
  id uuid default gen_random_uuid() not null,
  publico_id uuid not null,
  usuario_id uuid not null,
  nome text,
  telefone text not null,
  email text,
  empresa text,
  etapa text,
  observacao text,
  dados_extras jsonb,
  created_at timestamp with time zone default now() not null,
  followup_excluido boolean default false not null,
  followup_excluido_em timestamp with time zone,
  followup_excluido_motivo text
);

-- conversa_atendentes_historico
create table if not exists public.conversa_atendentes_historico (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  conversa_id uuid not null,
  profissional_id uuid,
  profissional_nome_snapshot text,
  acao text not null,
  created_by uuid,
  created_at timestamp with time zone default now() not null
);

-- conversas
create table if not exists public.conversas (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  instancia_id uuid,
  numero text not null,
  nome_contato text,
  nome_editado boolean default false not null,
  photo text,
  ultima_mensagem text,
  ultimo_horario timestamp with time zone,
  ultima_msg_cliente_em timestamp with time zone,
  nao_lidas integer default 0 not null,
  importante boolean default false not null,
  chatlid text,
  status text default 'ativo'::text not null,
  assigned_to_professional_id uuid,
  assigned_at timestamp with time zone,
  assigned_by uuid,
  opened_at timestamp with time zone,
  closed_at timestamp with time zone,
  resolved_at timestamp with time zone,
  tempo_pausa integer,
  tempo_pausa_inicio timestamp with time zone,
  arquivada boolean default false not null,
  deleted_at timestamp with time zone,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null
);

-- disparos
create table if not exists public.disparos (
  id uuid default gen_random_uuid() not null,
  campanha_id uuid not null,
  contato_id uuid not null,
  usuario_id uuid not null,
  status text default 'pendente'::text not null,
  mensagem_enviada text,
  erro text,
  enviado_em timestamp with time zone,
  created_at timestamp with time zone default now() not null,
  resposta_texto text,
  respondido_em timestamp with time zone,
  canal_id uuid
);

-- followup_configs
create table if not exists public.followup_configs (
  id uuid default gen_random_uuid() not null,
  campanha_id uuid,
  usuario_id uuid not null,
  ativo boolean default true not null,
  criado_em timestamp with time zone default now() not null
);

-- followup_disparos
create table if not exists public.followup_disparos (
  id uuid default gen_random_uuid() not null,
  config_id uuid not null,
  etapa_id uuid not null,
  campanha_id uuid not null,
  contato_id uuid not null,
  usuario_id uuid not null,
  canal_id uuid,
  status text default 'pendente'::text not null,
  agendado_para timestamp with time zone not null,
  enviado_em timestamp with time zone,
  mensagem_enviada text,
  criado_em timestamp with time zone default now() not null
);

-- followup_etapas
create table if not exists public.followup_etapas (
  id uuid default gen_random_uuid() not null,
  config_id uuid not null,
  ordem smallint not null,
  delay_minutos integer not null,
  modo_mensagem text default 'ia'::text not null,
  mensagem text,
  criado_em timestamp with time zone default now() not null
);

-- instancias
create table if not exists public.instancias (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  nome_instancia text not null,
  uazapi_instance_name text,
  uazapi_token text not null,
  status text default 'disconnected'::text not null,
  phone text,
  data_criacao timestamp with time zone default now() not null,
  created_at timestamp with time zone default now() not null,
  uso_notificacao boolean default false not null,
  bloqueado_ate timestamp with time zone,
  bloqueio_motivo text,
  profissional_id uuid,
  share_token text
);

-- integracoes
create table if not exists public.integracoes (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  openai_api_key text,
  updated_at timestamp with time zone default now() not null,
  openai_sem_saldo boolean default false not null,
  openai_sem_saldo_em timestamp with time zone
);

-- mensagens
create table if not exists public.mensagens (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  instancia_id uuid,
  conversa_id uuid,
  numero text not null,
  nome_contato text,
  chatlid text,
  mensagem text,
  direcao text not null,
  enviado_por text default 'user'::text not null,
  enviado_por_profissional_id uuid,
  kind text default 'text'::text not null,
  audio_url text,
  arquivo_nome text,
  wa_message_id text,
  reply_to_wa_id text,
  reply_to_text text,
  reply_to_from_me boolean,
  data_hora timestamp with time zone default now() not null,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null,
  transcricao text,
  transcricao_em timestamp with time zone,
  transcricao_origem text
);

-- midias_conversas
create table if not exists public.midias_conversas (
  id uuid default gen_random_uuid() not null,
  mensagem_id uuid not null,
  usuario_id uuid not null,
  instancia_id uuid,
  storage_path text not null,
  tipo text not null,
  url_original text,
  url_storage text not null,
  criado_em timestamp with time zone default now() not null
);

-- profissionais
create table if not exists public.profissionais (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  nome text not null,
  telefone text,
  avatar_url text,
  ativo boolean default true not null,
  created_at timestamp with time zone default now() not null
);

-- publicos
create table if not exists public.publicos (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid not null,
  nome text not null,
  regiao text,
  status text default 'frio'::text not null,
  created_at timestamp with time zone default now() not null
);

-- usuarios
create table if not exists public.usuarios (
  id uuid default gen_random_uuid() not null,
  nome text not null,
  empresa text,
  email text not null,
  perfil text default 'admin'::text not null,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null
);

-- validacoes_numeros
create table if not exists public.validacoes_numeros (
  id uuid default gen_random_uuid() not null,
  usuario_id uuid default auth.uid() not null,
  nome_arquivo text,
  canal text,
  total integer default 0 not null,
  validos_count integer default 0 not null,
  invalidos_count integer default 0 not null,
  dados jsonb default '{}'::jsonb not null,
  created_at timestamp with time zone default now() not null
);
-- ---------------------------------------------------------------------------
-- 2. Chaves primarias, unicas, CHECKs e foreign keys
-- ---------------------------------------------------------------------------
do $$ begin
  alter table assistentes add constraint assistentes_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table assistentes_profissionais add constraint assistentes_profissionais_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanha_logs add constraint campanha_logs_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanhas add constraint campanhas_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table contatos add constraint contatos_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversa_atendentes_historico add constraint conversa_atendentes_historico_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversas add constraint conversas_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table disparos add constraint disparos_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_configs add constraint followup_configs_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_etapas add constraint followup_etapas_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table instancias add constraint instancias_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table integracoes add constraint integracoes_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table midias_conversas add constraint midias_conversas_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table profissionais add constraint profissionais_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table publicos add constraint publicos_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table usuarios add constraint usuarios_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table validacoes_numeros add constraint validacoes_numeros_pkey PRIMARY KEY (id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table instancias add constraint instancias_share_token_key UNIQUE (share_token);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table instancias add constraint instancias_uazapi_token_key UNIQUE (uazapi_token);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table integracoes add constraint integracoes_usuario_id_key UNIQUE (usuario_id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table usuarios add constraint usuarios_email_key UNIQUE (email);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanha_logs add constraint campanha_logs_nivel_check CHECK ((nivel = ANY (ARRAY['info'::text, 'aviso'::text, 'erro'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanhas add constraint campanhas_status_check CHECK ((status = ANY (ARRAY['rascunho'::text, 'em_andamento'::text, 'concluida'::text, 'pausada'::text, 'falhou'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanhas add constraint campanhas_modo_mensagem_check CHECK ((modo_mensagem = ANY (ARRAY['manual'::text, 'ia'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversa_atendentes_historico add constraint conversa_atendentes_historico_acao_check CHECK ((acao = ANY (ARRAY['atribuido'::text, 'desatribuido'::text, 'fechado'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table disparos add constraint disparos_status_check CHECK ((status = ANY (ARRAY['pendente'::text, 'enviado'::text, 'falhou'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_status_check CHECK ((status = ANY (ARRAY['pendente'::text, 'enviado'::text, 'respondeu'::text, 'cancelado'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_etapas add constraint followup_etapas_delay_minutos_check CHECK ((delay_minutos > 0));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_etapas add constraint followup_etapas_modo_mensagem_check CHECK ((modo_mensagem = ANY (ARRAY['manual'::text, 'ia'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_enviado_por_check CHECK ((enviado_por = ANY (ARRAY['user'::text, 'assistant'::text, 'celular'::text, 'painel'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_direcao_check CHECK ((direcao = ANY (ARRAY['RECEIVED'::text, 'SENT'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table midias_conversas add constraint midias_conversas_tipo_check CHECK ((tipo = ANY (ARRAY['audio'::text, 'imagem'::text, 'pdf'::text, 'documento'::text, 'video'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table publicos add constraint publicos_status_check CHECK ((status = ANY (ARRAY['frio'::text, 'morno'::text, 'quente'::text])));
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table assistentes add constraint assistentes_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES instancias(id) ON DELETE SET NULL;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table assistentes_profissionais add constraint assistentes_profissionais_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table assistentes_profissionais add constraint assistentes_profissionais_profissional_id_fkey FOREIGN KEY (profissional_id) REFERENCES profissionais(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanha_logs add constraint campanha_logs_campanha_id_fkey FOREIGN KEY (campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanha_logs add constraint campanha_logs_canal_id_fkey FOREIGN KEY (canal_id) REFERENCES instancias(id) ON DELETE SET NULL;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanhas add constraint campanhas_publico_id_fkey FOREIGN KEY (publico_id) REFERENCES publicos(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanhas add constraint campanhas_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES auth.users(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table campanhas add constraint campanhas_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES instancias(id) ON DELETE SET NULL;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table contatos add constraint contatos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES auth.users(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table contatos add constraint contatos_publico_id_fkey FOREIGN KEY (publico_id) REFERENCES publicos(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversa_atendentes_historico add constraint conversa_atendentes_historico_conversa_id_fkey FOREIGN KEY (conversa_id) REFERENCES conversas(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversa_atendentes_historico add constraint conversa_atendentes_historico_profissional_id_fkey FOREIGN KEY (profissional_id) REFERENCES profissionais(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversa_atendentes_historico add constraint conversa_atendentes_historico_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversas add constraint conversas_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES instancias(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversas add constraint conversas_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table conversas add constraint conversas_assigned_to_professional_id_fkey FOREIGN KEY (assigned_to_professional_id) REFERENCES profissionais(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table disparos add constraint disparos_contato_id_fkey FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table disparos add constraint disparos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES auth.users(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table disparos add constraint disparos_campanha_id_fkey FOREIGN KEY (campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table disparos add constraint disparos_canal_id_fkey FOREIGN KEY (canal_id) REFERENCES instancias(id) ON DELETE SET NULL;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_configs add constraint followup_configs_campanha_id_fkey FOREIGN KEY (campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_campanha_id_fkey FOREIGN KEY (campanha_id) REFERENCES campanhas(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_etapa_id_fkey FOREIGN KEY (etapa_id) REFERENCES followup_etapas(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_contato_id_fkey FOREIGN KEY (contato_id) REFERENCES contatos(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_config_id_fkey FOREIGN KEY (config_id) REFERENCES followup_configs(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_disparos add constraint followup_disparos_canal_id_fkey FOREIGN KEY (canal_id) REFERENCES instancias(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table followup_etapas add constraint followup_etapas_config_id_fkey FOREIGN KEY (config_id) REFERENCES followup_configs(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table instancias add constraint instancias_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table instancias add constraint instancias_profissional_id_fkey FOREIGN KEY (profissional_id) REFERENCES profissionais(id) ON DELETE SET NULL;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES instancias(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_conversa_id_fkey FOREIGN KEY (conversa_id) REFERENCES conversas(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table mensagens add constraint mensagens_enviado_por_profissional_id_fkey FOREIGN KEY (enviado_por_profissional_id) REFERENCES profissionais(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table midias_conversas add constraint midias_conversas_mensagem_id_fkey FOREIGN KEY (mensagem_id) REFERENCES mensagens(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table midias_conversas add constraint midias_conversas_instancia_id_fkey FOREIGN KEY (instancia_id) REFERENCES instancias(id);
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table midias_conversas add constraint midias_conversas_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table profissionais add constraint profissionais_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table publicos add constraint publicos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES auth.users(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;
do $$ begin
  alter table usuarios add constraint usuarios_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
exception when duplicate_object then null; when duplicate_table then null; end $$;

-- ---------------------------------------------------------------------------
-- 3. Indices
-- ---------------------------------------------------------------------------
create unique index if not exists assistentes_instancia_uniq ON public.assistentes USING btree (instancia_id) WHERE (instancia_id IS NOT NULL);
create index if not exists campanha_logs_campanha_id_idx ON public.campanha_logs USING btree (campanha_id);
create index if not exists campanha_logs_created_at_idx ON public.campanha_logs USING btree (created_at DESC);
create index if not exists disparos_respondidos_idx ON public.disparos USING btree (campanha_id, contato_id) WHERE (respondido_em IS NOT NULL);
create index if not exists fu_configs_campanha_idx ON public.followup_configs USING btree (campanha_id);
create index if not exists fu_configs_usuario_idx ON public.followup_configs USING btree (usuario_id);
create index if not exists fu_disparos_contato_idx ON public.followup_disparos USING btree (contato_id, campanha_id);
create index if not exists fu_disparos_pendentes_idx ON public.followup_disparos USING btree (agendado_para) WHERE (status = 'pendente'::text);
create index if not exists idx_assistentes_instancia_id ON public.assistentes USING btree (instancia_id);
create index if not exists idx_campanhas_canal_id ON public.campanhas USING btree (canal_id);
create index if not exists idx_campanhas_instancia_id ON public.campanhas USING btree (instancia_id);
create index if not exists idx_campanhas_usuario_arquivada ON public.campanhas USING btree (usuario_id, arquivada);
create index if not exists idx_conversas_assigned_to ON public.conversas USING btree (assigned_to_professional_id);
create index if not exists idx_conversas_instancia ON public.conversas USING btree (instancia_id);
create index if not exists idx_conversas_nome_trgm ON public.conversas USING gin (nome_contato gin_trgm_ops) WHERE (deleted_at IS NULL);
create index if not exists idx_conversas_numero ON public.conversas USING btree (numero) WHERE (deleted_at IS NULL);
create index if not exists idx_conversas_usuario ON public.conversas USING btree (usuario_id);
create index if not exists idx_conversas_usuario_ultimo ON public.conversas USING btree (usuario_id, ultimo_horario DESC NULLS LAST) WHERE (deleted_at IS NULL);
create index if not exists idx_historico_conversa ON public.conversa_atendentes_historico USING btree (conversa_id);
create index if not exists idx_historico_profissional ON public.conversa_atendentes_historico USING btree (profissional_id);
create index if not exists idx_instancias_usuario_id ON public.instancias USING btree (usuario_id);
create index if not exists idx_mensagens_conversa ON public.mensagens USING btree (conversa_id, data_hora);
create index if not exists idx_mensagens_enviado_por_profissional ON public.mensagens USING btree (enviado_por_profissional_id);
create index if not exists idx_mensagens_usuario ON public.mensagens USING btree (usuario_id);
create index if not exists idx_mensagens_usuario_data ON public.mensagens USING btree (usuario_id, data_hora DESC);
create index if not exists idx_midias_conversas_mensagem ON public.midias_conversas USING btree (mensagem_id);
create index if not exists idx_profissionais_nome_trgm ON public.profissionais USING gin (nome gin_trgm_ops);
create index if not exists idx_validacoes_numeros_usuario_created ON public.validacoes_numeros USING btree (usuario_id, created_at DESC);
create unique index if not exists ux_assistente_por_profissional ON public.assistentes_profissionais USING btree (profissional_id);
create unique index if not exists ux_conversa_contato ON public.conversas USING btree (numero, usuario_id, instancia_id) WHERE (deleted_at IS NULL);
create unique index if not exists ux_instancia_por_profissional ON public.instancias USING btree (profissional_id) WHERE ((profissional_id IS NOT NULL) AND (status <> 'deleted'::text));
create unique index if not exists ux_mensagem_wa_id ON public.mensagens USING btree (wa_message_id) WHERE (wa_message_id IS NOT NULL);

-- ---------------------------------------------------------------------------
-- 4. Funcoes (RPCs do painel + funcoes de trigger)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.broadcast_conversa()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare rec jsonb; uid uuid;
begin
  if TG_OP = 'UPDATE' and (to_jsonb(OLD) - 'updated_at') is not distinct from (to_jsonb(NEW) - 'updated_at') then
    return null;
  end if;

  if TG_OP = 'DELETE' then rec := to_jsonb(OLD); uid := OLD.usuario_id;
  else rec := to_jsonb(NEW); uid := NEW.usuario_id; end if;
  if uid is null then return null; end if;

  begin
    perform realtime.send(
      jsonb_build_object('type', TG_OP, 'record', rec),
      'conversa',
      'usuario:' || uid::text,
      true
    );
  exception when others then null;
  end;
  return null;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.broadcast_mensagem()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare rec jsonb; uid uuid;
begin
  if TG_OP = 'DELETE' then rec := to_jsonb(OLD); uid := OLD.usuario_id;
  else rec := to_jsonb(NEW); uid := NEW.usuario_id; end if;
  if uid is null then return null; end if;

  begin
    perform realtime.send(
      jsonb_build_object('type', TG_OP, 'record', rec),
      'mensagem',
      'usuario:' || uid::text,
      true
    );
  exception when others then null; -- broadcast nunca pode quebrar a escrita
  end;
  return null;
end;
$function$
;

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
;

CREATE OR REPLACE FUNCTION public.get_atendimentos_detalhado(p_usuario_id uuid, p_inicio timestamp with time zone, p_fim timestamp with time zone)
 RETURNS TABLE(conversa_id uuid, profissional_id uuid, profissional_nome text, cliente_nome text, cliente_numero text, mensagens_recebidas bigint, mensagens_enviadas bigint, primeira_recebida_em timestamp with time zone, primeira_resposta_em timestamp with time zone, tmpr_seg numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if p_usuario_id is distinct from auth.uid() then
    raise exception 'forbidden';
  end if;

  return query
  with msgs as (
    select m.conversa_id as conv_id, m.direcao, m.data_hora
    from mensagens m
    where m.usuario_id = p_usuario_id
      and m.data_hora between p_inicio and p_fim
  ),
  contagem as (
    select conv_id,
      count(*) filter (where direcao = 'RECEIVED') as recebidas,
      count(*) filter (where direcao = 'SENT') as enviadas
    from msgs
    group by conv_id
  ),
  primeira_recebida as (
    select conv_id, min(data_hora) as recebida_em
    from msgs
    where direcao = 'RECEIVED'
    group by conv_id
  ),
  primeira_resposta as (
    select pr.conv_id, pr.recebida_em,
      (select mm.data_hora from mensagens mm
       where mm.conversa_id = pr.conv_id and mm.direcao = 'SENT' and mm.data_hora > pr.recebida_em
       order by mm.data_hora asc limit 1) as respondida_em
    from primeira_recebida pr
  )
  select
    c.id,
    i.profissional_id,
    p.nome,
    c.nome_contato,
    c.numero,
    coalesce(ct.recebidas, 0),
    coalesce(ct.enviadas, 0),
    pr2.recebida_em,
    pr2.respondida_em,
    case when pr2.respondida_em is not null
      then extract(epoch from (pr2.respondida_em - pr2.recebida_em))
    end
  from contagem ct
  join conversas c on c.id = ct.conv_id
  join instancias i on i.id = c.instancia_id
  left join profissionais p on p.id = i.profissional_id
  left join primeira_resposta pr2 on pr2.conv_id = ct.conv_id
  where c.usuario_id = p_usuario_id
    and i.profissional_id is not null
  order by pr2.recebida_em desc nulls last
  limit 2000;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.get_metricas_atendimento(p_usuario_id uuid, p_inicio timestamp with time zone, p_fim timestamp with time zone)
 RETURNS TABLE(profissional_id uuid, profissional_nome text, mensagens_recebidas bigint, mensagens_enviadas bigint, atendimentos bigint, tmpr_seg numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if p_usuario_id is distinct from auth.uid() then
    raise exception 'forbidden';
  end if;

  return query
  with recebidas as (
    select i.profissional_id, count(*) as qtd
    from mensagens m
    join instancias i on i.id = m.instancia_id
    where m.direcao = 'RECEIVED' and m.usuario_id = p_usuario_id
      and m.data_hora between p_inicio and p_fim
      and i.profissional_id is not null
    group by i.profissional_id
  ),
  enviadas as (
    select i.profissional_id, count(*) as qtd
    from mensagens m
    join instancias i on i.id = m.instancia_id
    where m.direcao = 'SENT' and m.usuario_id = p_usuario_id
      and m.data_hora between p_inicio and p_fim
      and i.profissional_id is not null
    group by i.profissional_id
  ),
  atendimentos_cte as (
    select c.assigned_to_professional_id as profissional_id, count(*) as qtd
    from conversas c
    where c.usuario_id = p_usuario_id and c.opened_at is not null
      and c.opened_at between p_inicio and p_fim
      and c.assigned_to_professional_id is not null
    group by c.assigned_to_professional_id
  ),
  primeira_recebida as (
    select distinct on (m.conversa_id) m.conversa_id, m.data_hora as recebida_em, c.instancia_id
    from mensagens m
    join conversas c on c.id = m.conversa_id
    where m.direcao = 'RECEIVED' and m.usuario_id = p_usuario_id
      and m.data_hora between p_inicio and p_fim
    order by m.conversa_id, m.data_hora asc
  ),
  primeira_resposta as (
    select pr.instancia_id, pr.recebida_em,
      (select mm.data_hora from mensagens mm
       where mm.conversa_id = pr.conversa_id and mm.direcao = 'SENT' and mm.data_hora > pr.recebida_em
       order by mm.data_hora asc limit 1) as respondida_em
    from primeira_recebida pr
  ),
  tmpr as (
    select i.profissional_id, avg(extract(epoch from (pr2.respondida_em - pr2.recebida_em))) as tmpr_seg
    from primeira_resposta pr2
    join instancias i on i.id = pr2.instancia_id
    where pr2.respondida_em is not null and i.profissional_id is not null
    group by i.profissional_id
  )
  select
    p.id,
    p.nome,
    coalesce(r.qtd, 0),
    coalesce(e.qtd, 0),
    coalesce(a.qtd, 0),
    t.tmpr_seg
  from profissionais p
  left join recebidas r on r.profissional_id = p.id
  left join enviadas e on e.profissional_id = p.id
  left join atendimentos_cte a on a.profissional_id = p.id
  left join tmpr t on t.profissional_id = p.id
  where p.usuario_id = p_usuario_id
  order by p.nome;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.get_metricas_atendimento_diario(p_usuario_id uuid, p_dias integer DEFAULT 30)
 RETURNS TABLE(dia date, mensagens_recebidas bigint, mensagens_enviadas bigint, atendimentos bigint, tmpr_medio_seg numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if p_usuario_id is distinct from auth.uid() then
    raise exception 'forbidden';
  end if;
  if p_dias is null or p_dias < 1 then p_dias := 30; end if;
  if p_dias > 365 then p_dias := 365; end if;

  return query
  with dias as (
    select generate_series(current_date - (p_dias - 1), current_date, interval '1 day')::date as dia
  ),
  recebidas as (
    select m.data_hora::date as dia, count(*) as qtd
    from mensagens m
    where m.usuario_id = p_usuario_id and m.direcao = 'RECEIVED'
      and m.data_hora >= current_date - (p_dias - 1)
    group by 1
  ),
  enviadas as (
    select m.data_hora::date as dia, count(*) as qtd
    from mensagens m
    where m.usuario_id = p_usuario_id and m.direcao = 'SENT'
      and m.data_hora >= current_date - (p_dias - 1)
    group by 1
  ),
  atendimentos_cte as (
    select c.opened_at::date as dia, count(*) as qtd
    from conversas c
    where c.usuario_id = p_usuario_id and c.opened_at is not null
      and c.opened_at >= current_date - (p_dias - 1)
    group by 1
  ),
  primeira_recebida as (
    select distinct on (m.conversa_id) m.conversa_id, m.data_hora as recebida_em
    from mensagens m
    where m.direcao = 'RECEIVED' and m.usuario_id = p_usuario_id
      and m.data_hora >= current_date - (p_dias - 1)
    order by m.conversa_id, m.data_hora asc
  ),
  respostas as (
    select pr.recebida_em,
      (select mm.data_hora from mensagens mm
       where mm.conversa_id = pr.conversa_id and mm.direcao = 'SENT' and mm.data_hora > pr.recebida_em
       order by mm.data_hora asc limit 1) as respondida_em
    from primeira_recebida pr
  ),
  tmpr_diario as (
    select r.recebida_em::date as dia, avg(extract(epoch from (r.respondida_em - r.recebida_em))) as tmpr
    from respostas r
    where r.respondida_em is not null
    group by 1
  )
  select d.dia, coalesce(rc.qtd, 0), coalesce(en.qtd, 0), coalesce(a.qtd, 0), t.tmpr
  from dias d
  left join recebidas rc on rc.dia = d.dia
  left join enviadas en on en.dia = d.dia
  left join atendimentos_cte a on a.dia = d.dia
  left join tmpr_diario t on t.dia = d.dia
  order by d.dia;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.instancia_atualizar_status_publica(p_token text, p_status text, p_phone text)
 RETURNS void
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  update public.instancias
  set status = p_status, phone = coalesce(p_phone, phone)
  where share_token = p_token;
$function$
;

CREATE OR REPLACE FUNCTION public.instancia_status_publica(p_token text)
 RETURNS TABLE(nome_instancia text, status text, phone text)
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select nome_instancia, status, phone
  from public.instancias
  where share_token = p_token
  limit 1;
$function$
;

CREATE OR REPLACE FUNCTION public.instancia_uazapi_token_publico(p_token text)
 RETURNS TABLE(id uuid, uazapi_token text)
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select id, uazapi_token
  from public.instancias
  where share_token = p_token
  limit 1;
$function$
;

CREATE OR REPLACE FUNCTION public.mensagens_after_insert_reabrir()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if NEW.direcao = 'RECEIVED' then
    update public.conversas
    set resolved_at = null, closed_at = null, status = 'aberta'
    where id = NEW.conversa_id
      and (resolved_at is not null or closed_at is not null);
  end if;
  return NEW;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.mensagens_before_insert()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  v_conversa_id uuid;
  v_preview text;
begin
  if NEW.conversa_id is null then
    select id into v_conversa_id
    from public.conversas
    where numero = NEW.numero
      and usuario_id = NEW.usuario_id
      and instancia_id is not distinct from NEW.instancia_id
      and deleted_at is null
    limit 1;

    if v_conversa_id is null then
      insert into public.conversas (usuario_id, instancia_id, numero, nome_contato, chatlid)
      values (NEW.usuario_id, NEW.instancia_id, NEW.numero, NEW.nome_contato, NEW.chatlid)
      returning id into v_conversa_id;
    end if;

    NEW.conversa_id := v_conversa_id;
  end if;

  v_preview := case NEW.kind
    when 'audio' then '🎵 Áudio'
    when 'image' then '📷 Imagem'
    when 'video' then '🎥 Vídeo'
    when 'document' then '📎 ' || coalesce(NEW.arquivo_nome, 'Arquivo')
    when 'sticker' then '🎨 Figurinha'
    else coalesce(NEW.mensagem, '')
  end;

  update public.conversas set
    ultima_mensagem = v_preview,
    ultimo_horario = NEW.data_hora,
    ultima_msg_cliente_em = case when NEW.direcao = 'RECEIVED' then NEW.data_hora else ultima_msg_cliente_em end,
    nao_lidas = case when NEW.direcao = 'RECEIVED' then nao_lidas + 1 else nao_lidas end,
    nome_contato = case when NEW.nome_contato is not null and not nome_editado then NEW.nome_contato else nome_contato end,
    updated_at = now()
  where id = NEW.conversa_id;

  return NEW;
end;
$function$
;

-- ---------------------------------------------------------------------------
-- 5. Triggers
-- ---------------------------------------------------------------------------
drop trigger if exists trg_broadcast_conversa on public.conversas;
CREATE TRIGGER trg_broadcast_conversa AFTER INSERT OR DELETE OR UPDATE ON public.conversas FOR EACH ROW EXECUTE FUNCTION broadcast_conversa();
drop trigger if exists trg_broadcast_mensagem on public.mensagens;
CREATE TRIGGER trg_broadcast_mensagem AFTER INSERT OR DELETE OR UPDATE ON public.mensagens FOR EACH ROW EXECUTE FUNCTION broadcast_mensagem();
drop trigger if exists trg_mensagens_after_insert_reabrir on public.mensagens;
CREATE TRIGGER trg_mensagens_after_insert_reabrir AFTER INSERT ON public.mensagens FOR EACH ROW EXECUTE FUNCTION mensagens_after_insert_reabrir();
drop trigger if exists trg_mensagens_before_insert on public.mensagens;
CREATE TRIGGER trg_mensagens_before_insert BEFORE INSERT ON public.mensagens FOR EACH ROW EXECUTE FUNCTION mensagens_before_insert();

-- ---------------------------------------------------------------------------
-- 6. Row Level Security
-- ---------------------------------------------------------------------------
alter table public.assistentes enable row level security;
alter table public.assistentes_profissionais enable row level security;
alter table public.campanha_logs enable row level security;
alter table public.campanhas enable row level security;
alter table public.contatos enable row level security;
alter table public.conversa_atendentes_historico enable row level security;
alter table public.conversas enable row level security;
alter table public.disparos enable row level security;
alter table public.followup_configs enable row level security;
alter table public.followup_disparos enable row level security;
alter table public.followup_etapas enable row level security;
alter table public.instancias enable row level security;
alter table public.integracoes enable row level security;
alter table public.mensagens enable row level security;
alter table public.midias_conversas enable row level security;
alter table public.profissionais enable row level security;
alter table public.publicos enable row level security;
alter table public.usuarios enable row level security;
alter table public.validacoes_numeros enable row level security;

-- ---------------------------------------------------------------------------
-- 7. Policies (isolamento por usuario_id = auth.uid())
-- ---------------------------------------------------------------------------
drop policy if exists "assistentes_delete" on public.assistentes;
create policy "assistentes_delete" on public.assistentes as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "assistentes_insert" on public.assistentes;
create policy "assistentes_insert" on public.assistentes as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "assistentes_select" on public.assistentes;
create policy "assistentes_select" on public.assistentes as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "assistentes_update" on public.assistentes;
create policy "assistentes_update" on public.assistentes as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "assistentes_profissionais_delete" on public.assistentes_profissionais;
create policy "assistentes_profissionais_delete" on public.assistentes_profissionais as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "assistentes_profissionais_insert" on public.assistentes_profissionais;
create policy "assistentes_profissionais_insert" on public.assistentes_profissionais as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "assistentes_profissionais_select" on public.assistentes_profissionais;
create policy "assistentes_profissionais_select" on public.assistentes_profissionais as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "assistentes_profissionais_update" on public.assistentes_profissionais;
create policy "assistentes_profissionais_update" on public.assistentes_profissionais as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "campanha_logs_insert" on public.campanha_logs;
create policy "campanha_logs_insert" on public.campanha_logs as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "campanha_logs_select" on public.campanha_logs;
create policy "campanha_logs_select" on public.campanha_logs as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "campanhas_delete" on public.campanhas;
create policy "campanhas_delete" on public.campanhas as permissive for delete to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "campanhas_insert" on public.campanhas;
create policy "campanhas_insert" on public.campanhas as permissive for insert to authenticated
  with check ((auth.uid() = usuario_id));
drop policy if exists "campanhas_select" on public.campanhas;
create policy "campanhas_select" on public.campanhas as permissive for select to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "campanhas_update" on public.campanhas;
create policy "campanhas_update" on public.campanhas as permissive for update to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "contatos_delete" on public.contatos;
create policy "contatos_delete" on public.contatos as permissive for delete to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "contatos_insert" on public.contatos;
create policy "contatos_insert" on public.contatos as permissive for insert to authenticated
  with check ((auth.uid() = usuario_id));
drop policy if exists "contatos_select" on public.contatos;
create policy "contatos_select" on public.contatos as permissive for select to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "contatos_update" on public.contatos;
create policy "contatos_update" on public.contatos as permissive for update to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "historico_delete" on public.conversa_atendentes_historico;
create policy "historico_delete" on public.conversa_atendentes_historico as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "historico_insert" on public.conversa_atendentes_historico;
create policy "historico_insert" on public.conversa_atendentes_historico as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "historico_select" on public.conversa_atendentes_historico;
create policy "historico_select" on public.conversa_atendentes_historico as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "historico_update" on public.conversa_atendentes_historico;
create policy "historico_update" on public.conversa_atendentes_historico as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "conversas_delete" on public.conversas;
create policy "conversas_delete" on public.conversas as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "conversas_insert" on public.conversas;
create policy "conversas_insert" on public.conversas as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "conversas_select" on public.conversas;
create policy "conversas_select" on public.conversas as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "conversas_update" on public.conversas;
create policy "conversas_update" on public.conversas as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "disparos_delete" on public.disparos;
create policy "disparos_delete" on public.disparos as permissive for delete to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "disparos_insert" on public.disparos;
create policy "disparos_insert" on public.disparos as permissive for insert to authenticated
  with check ((auth.uid() = usuario_id));
drop policy if exists "disparos_select" on public.disparos;
create policy "disparos_select" on public.disparos as permissive for select to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "disparos_update" on public.disparos;
create policy "disparos_update" on public.disparos as permissive for update to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "fu_configs_owner" on public.followup_configs;
create policy "fu_configs_owner" on public.followup_configs as permissive for all to public
  using ((usuario_id = auth.uid()))
  with check ((usuario_id = auth.uid()));
drop policy if exists "fu_disparos_owner" on public.followup_disparos;
create policy "fu_disparos_owner" on public.followup_disparos as permissive for all to public
  using ((usuario_id = auth.uid()));
drop policy if exists "fu_etapas_owner" on public.followup_etapas;
create policy "fu_etapas_owner" on public.followup_etapas as permissive for all to public
  using ((EXISTS ( SELECT 1
   FROM followup_configs c
  WHERE ((c.id = followup_etapas.config_id) AND (c.usuario_id = auth.uid())))));
drop policy if exists "instancias_delete" on public.instancias;
create policy "instancias_delete" on public.instancias as permissive for delete to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "instancias_insert" on public.instancias;
create policy "instancias_insert" on public.instancias as permissive for insert to authenticated
  with check ((auth.uid() = usuario_id));
drop policy if exists "instancias_select" on public.instancias;
create policy "instancias_select" on public.instancias as permissive for select to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "instancias_update" on public.instancias;
create policy "instancias_update" on public.instancias as permissive for update to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "integracoes_insert" on public.integracoes;
create policy "integracoes_insert" on public.integracoes as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "integracoes_select" on public.integracoes;
create policy "integracoes_select" on public.integracoes as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "integracoes_update" on public.integracoes;
create policy "integracoes_update" on public.integracoes as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "mensagens_delete" on public.mensagens;
create policy "mensagens_delete" on public.mensagens as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "mensagens_insert" on public.mensagens;
create policy "mensagens_insert" on public.mensagens as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "mensagens_select" on public.mensagens;
create policy "mensagens_select" on public.mensagens as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "mensagens_update" on public.mensagens;
create policy "mensagens_update" on public.mensagens as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "midias_conversas_delete" on public.midias_conversas;
create policy "midias_conversas_delete" on public.midias_conversas as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "midias_conversas_insert" on public.midias_conversas;
create policy "midias_conversas_insert" on public.midias_conversas as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "midias_conversas_select" on public.midias_conversas;
create policy "midias_conversas_select" on public.midias_conversas as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "midias_conversas_update" on public.midias_conversas;
create policy "midias_conversas_update" on public.midias_conversas as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "profissionais_delete" on public.profissionais;
create policy "profissionais_delete" on public.profissionais as permissive for delete to public
  using ((usuario_id = auth.uid()));
drop policy if exists "profissionais_insert" on public.profissionais;
create policy "profissionais_insert" on public.profissionais as permissive for insert to public
  with check ((usuario_id = auth.uid()));
drop policy if exists "profissionais_select" on public.profissionais;
create policy "profissionais_select" on public.profissionais as permissive for select to public
  using ((usuario_id = auth.uid()));
drop policy if exists "profissionais_update" on public.profissionais;
create policy "profissionais_update" on public.profissionais as permissive for update to public
  using ((usuario_id = auth.uid()));
drop policy if exists "publicos_delete" on public.publicos;
create policy "publicos_delete" on public.publicos as permissive for delete to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "publicos_insert" on public.publicos;
create policy "publicos_insert" on public.publicos as permissive for insert to authenticated
  with check ((auth.uid() = usuario_id));
drop policy if exists "publicos_select" on public.publicos;
create policy "publicos_select" on public.publicos as permissive for select to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "publicos_update" on public.publicos;
create policy "publicos_update" on public.publicos as permissive for update to authenticated
  using ((auth.uid() = usuario_id));
drop policy if exists "usuarios_insert_self" on public.usuarios;
create policy "usuarios_insert_self" on public.usuarios as permissive for insert to authenticated
  with check ((auth.uid() = id));
drop policy if exists "usuarios_select_self" on public.usuarios;
create policy "usuarios_select_self" on public.usuarios as permissive for select to authenticated
  using ((auth.uid() = id));
drop policy if exists "usuarios_update_self" on public.usuarios;
create policy "usuarios_update_self" on public.usuarios as permissive for update to authenticated
  using ((auth.uid() = id))
  with check ((auth.uid() = id));
drop policy if exists "validacoes_numeros_delete" on public.validacoes_numeros;
create policy "validacoes_numeros_delete" on public.validacoes_numeros as permissive for delete to public
  using ((auth.uid() = usuario_id));
drop policy if exists "validacoes_numeros_insert" on public.validacoes_numeros;
create policy "validacoes_numeros_insert" on public.validacoes_numeros as permissive for insert to public
  with check ((auth.uid() = usuario_id));
drop policy if exists "validacoes_numeros_select" on public.validacoes_numeros;
create policy "validacoes_numeros_select" on public.validacoes_numeros as permissive for select to public
  using ((auth.uid() = usuario_id));;

-- ---------------------------------------------------------------------------
-- 8. Permissoes das funcoes (espelha o banco de origem)
--    As RPCs "*_publica" sao chamadas SEM sessao (link publico de conexao do
--    canal), por isso anon executa. As de metricas sao so para quem esta logado.
-- ---------------------------------------------------------------------------
revoke all on function public.get_metricas_atendimento(uuid, timestamptz, timestamptz) from anon;
revoke all on function public.get_metricas_atendimento_diario(uuid, integer) from anon;
grant execute on function public.get_metricas_atendimento(uuid, timestamptz, timestamptz) to authenticated, service_role;
grant execute on function public.get_metricas_atendimento_diario(uuid, integer) to authenticated, service_role;
grant execute on function public.get_atendimentos_detalhado(uuid, timestamptz, timestamptz) to anon, authenticated, service_role;
grant execute on function public.contar_respostas_campanhas(uuid[]) to anon, authenticated, service_role;
grant execute on function public.instancia_status_publica(text) to anon, authenticated, service_role;
grant execute on function public.instancia_atualizar_status_publica(text, text, text) to anon, authenticated, service_role;
grant execute on function public.instancia_uazapi_token_publico(text) to anon, authenticated, service_role;

-- Funcoes de trigger (broadcast_*, mensagens_*) NAO recebem execute de anon /
-- authenticated: so postgres e service_role, como no banco de origem.
revoke all on function public.broadcast_conversa() from anon, authenticated;
revoke all on function public.broadcast_mensagem() from anon, authenticated;
revoke all on function public.mensagens_before_insert() from anon, authenticated;
revoke all on function public.mensagens_after_insert_reabrir() from anon, authenticated;

-- Grants padrao das tabelas (o Supabase ja aplica; aqui e garantia).
grant usage on schema public to anon, authenticated, service_role;
grant all on all tables in schema public to anon, authenticated, service_role;
grant all on all sequences in schema public to anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 9. Storage — bucket PRIVADO das midias das conversas
--    Caminho gravado: {usuario_id}/{audio|imagem|pdf|video|foto_perfil}/{arquivo}
--    O primeiro segmento ser o usuario_id e o que a policy usa para isolar o
--    dono — ver ai-service/app/services/storage.py. Nunca inverter a ordem.
--    Upload: ai-service com a SERVICE ROLE KEY (bypassa RLS).
--    Leitura: painel gera signed URL a partir de midias_conversas.storage_path.
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('conversas-midia', 'conversas-midia', false)
on conflict (id) do nothing;

drop policy if exists "conversas_midia_select_own" on storage.objects;
create policy "conversas_midia_select_own" on storage.objects
  for select to authenticated
  using (bucket_id = 'conversas-midia' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "conversas_midia_insert_own" on storage.objects;
create policy "conversas_midia_insert_own" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'conversas-midia' and (storage.foldername(name))[1] = auth.uid()::text);

-- ---------------------------------------------------------------------------
-- 10. Realtime — Broadcast privado por usuario (topico "usuario:{uuid}")
--     Os triggers broadcast_conversa / broadcast_mensagem publicam com
--     realtime.send(). O painel assina o canal privado usuario:{id}
--     (app/composables/useRealtimeConversas.ts). Sem esta policy o join e
--     recusado e a tela cai em CHANNEL_ERROR — a pagina Conversas para de
--     atualizar em tempo real.
-- ---------------------------------------------------------------------------
drop policy if exists "broadcast_usuario_receber" on realtime.messages;
create policy "broadcast_usuario_receber" on realtime.messages
  for select to authenticated
  using (extension = 'broadcast' and (select realtime.topic()) = 'usuario:' || auth.uid()::text);

-- ============================================================================
-- Fim. Confira com:
--   select count(*) from information_schema.tables where table_schema='public';  -- 19
--   select count(*) from pg_policies where schemaname='public';                  -- 62
--   select count(*) from pg_trigger where not tgisinternal;                      -- 4
--   select id from storage.buckets;                                              -- conversas-midia
-- ============================================================================
