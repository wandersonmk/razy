# Foto e nome do contato, nono dígito, e badges/filtros da página de Conversas

Documento de referência: como o AGZAP captura **nome** e **foto** do cliente via UAZAPI, como isso é salvo no banco, como é tratado o **nono dígito**, e como funcionam os **badges** (IA Pausada / Canal) e os **filtros** (período / nome) na tela de Conversas.

---

## 1) Pipeline completo — do WhatsApp até o banco

```
Cliente manda mensagem no WhatsApp
        │
        ▼
UAZAPI (Baileys) dispara webhook  →  POST https://chain.agzap.com.br/uazapi/webhook
        │                              (ai-service, rodando no EasyPanel)
        ▼
ai-service/app/api/uazapi.py  →  uazapi_webhook()
        │  resolve a instância pelo token, decide o "engine_ia" da empresa
        ▼
ai-service/app/utils/normalize.py  →  normalize_uazapi(body)
        │  extrai nome, telefone, chatlid, foto, texto/mídia do payload cru
        ▼
INSERT em langchain.inbound_queue (Postgres) + NOTIFY langchain_inbound_queue
        │
        ▼
ai-service/app/worker/dispatcher.py  (worker em background, escuta o NOTIFY)
        │
        ▼
ai-service/app/db/supabase.py  →  insert_inbound_message()
        │  INSERT na tabela `mensagens` (Supabase)
        ▼
Triggers do Postgres (Supabase) fazem o resto em cascata:
  - auto_create_conversa_and_cliente  → cria/atualiza `conversas` e `clientes`
  - ensure_cliente_on_conversa        → garante o vínculo conversa↔cliente
        ▼
Front (conversas.vue) recebe via Realtime (Broadcast) e re-renderiza
        │
        ▼
Front dispara (background, silencioso) POST /api/contacts/sync-photo
        │  busca a foto de perfil na UAZAPI e sobe pro Cloudflare R2
        ▼
`conversas.photo` atualizado com a URL do R2 (permanente)
```

Os dois pontos-chave do pedido — **captura do nome** e **captura da foto** — não vivem no mesmo lugar: o **nome** é capturado no momento do INSERT da mensagem (`normalize.py` + trigger). A **foto** é capturada **depois**, sob demanda, pelo endpoint `sync-photo` chamado pelo front — a UAZAPI não manda uma URL de foto estável no payload do webhook.

---

## 2) Captura do NOME do contato (pushName da UAZAPI)

Arquivo: [ai-service/app/utils/normalize.py](../ai-service/app/utils/normalize.py)

A UAZAPI espalha o nome do contato em vários campos possíveis, dependendo da versão e do tipo de payload. O código varre esses campos **em ordem de confiança**:

```python
# Campos onde o nome do CONTATO pode vir no payload UAzAPI, em ordem de
# confianca. Antes so `wa_name` era lido — e quando ele vinha vazio (contato
# sem nome salvo na agenda do numero, caso comum no PRIMEIRO contato) o nome
# se perdia inteiro, com tres efeitos: cliente/conversa nascendo como
# 'Cliente 55...', prompt da IA sem o primeiro nome e webhook de franquia com
# nome_lead vazio.
#
# `chat.*` descreve o CONTATO do outro lado — vale nos dois sentidos.
_NOME_CHAT_KEYS = ("wa_name", "wa_contactName", "lead_name", "lead_fullName", "name")

# `message.*` descreve quem MANDOU aquela mensagem. So vale quando
# fromMe=False (a mensagem veio do contato). Em fromMe=True o remetente e o
# dono da instancia — usar esses campos carimbaria o nome da EMPRESA no
# cadastro do cliente e no prompt da IA.
_NOME_MSG_KEYS = ("senderName", "pushName", "notifyName", "verifiedBizName")
```

Função que decide se um candidato a nome é realmente aproveitável (`_nome_util`) — descarta números de telefone, strings só de dígito e o placeholder `"Cliente 55..."` que a própria UAZAPI devolve quando o nome do lead nasceu do nosso lado:

```python
def _nome_util(valor: Any, telefone: str) -> str | None:
    if not isinstance(valor, str):
        return None
    nome = valor.strip()
    if not nome:
        return None
    if _digits(nome) == nome:                     # so digitos
        return None
    if telefone and _digits(nome) in tel_vars(telefone):
        return None
    if re.fullmatch(r"Cliente \d{8,}", nome):
        return None
    return nome[:120]
```

Função principal de extração (`_extract_nome_contato`) — primeiro tenta `chat.*`, só cai para `message.*` (pushName) quando a mensagem **não** é `fromMe`:

```python
def _extract_nome_contato(
    chat: dict[str, Any], message: dict[str, Any], *, from_me: bool, telefone: str
) -> str:
    for chave in _NOME_CHAT_KEYS:
        nome = _nome_util(chat.get(chave), telefone)
        if nome:
            return nome

    if not from_me:
        for chave in _NOME_MSG_KEYS:
            nome = _nome_util(message.get(chave), telefone)
            if nome:
                return nome

    # Diagnostico: mostra em log quais chaves vieram, pra mapear campo novo
    # da UAzAPI sem precisar de tcpdump.
    log.info(
        "normalize_uazapi: sem nome do contato (from_me=%s, chat_keys=%s, msg_keys=%s)",
        from_me, sorted(chat.keys())[:20], sorted(message.keys())[:30],
    )
    return ""
```

O resultado entra no payload normalizado como `"nome"` (linha 756 de `normalize.py`):

```python
return {
    "source": "uazapi",
    "from_me": from_me,
    "telefone": telefone,
    "chatlid": chatlid,
    "nome": _extract_nome_contato(chat, message, from_me=from_me, telefone=telefone),
    "foto": chat.get("imagePreview") or "",
    ...
}
```

### Onde o nome vira `nome_contato` no banco

Arquivo: [ai-service/app/db/supabase.py](../ai-service/app/db/supabase.py) — `insert_inbound_message()`:

```python
row: dict[str, Any] = {
    "numero": telefone,
    "direcao": "RECEIVED",
    "nome_contato": payload.get("nome") or None,
    "chatlid": payload.get("chatlid") or None,
    ...
}
```

Essa linha é inserida na tabela `mensagens`. O trigger `auto_create_conversa_and_cliente` (Postgres) dispara no INSERT e propaga o nome para `conversas.nome_contato` e `clientes.nome`:

- **Conversa nova** (cliente ainda não existe): cria `clientes` com `nome = COALESCE(NEW.nome_contato, 'Cliente ' || NEW.numero)` — ou seja, se o nome veio vazio (raro, mas acontece no 1º contato de alguns aparelhos), o cadastro nasce como `"Cliente 5511999999999"`.
- **Conversa existente**: só atualiza `nome_contato` se a conversa **não foi editada manualmente** (`nome_editado = false`) — edição manual do atendente nunca é sobrescrita por uma mensagem nova.

```sql
nome_contato = CASE WHEN v_nome_editado THEN nome_contato ELSE COALESCE(NEW.nome_contato, nome_contato) END,
```

> Quando o nome nasce como placeholder e um pushName real chega numa mensagem seguinte, o trigger `trg_sync_nome_cliente` (migração `20260710_sync_nome_cliente_from_conversa.sql`) corrige o cadastro do cliente — ver memória [`project_saudacao_copiada_do_historico`](../MEMORIA-CLAUDE-COMPLETA.md) e afins.

---

## 3) Captura da FOTO do contato

A UAZAPI **não** entrega uma URL estável de foto de perfil no webhook de mensagem — o campo `chat.imagePreview` (quando existe) é só uma miniatura em base64/URL efêmera (`pps.whatsapp.net`, que expira rápido). Por isso a foto **não** é salva automaticamente no INSERT da mensagem: ela é sincronizada **sob demanda**, disparada pelo próprio front.

### 3.1) Gatilho no front (quando a sincronização acontece)

Arquivo: [app/pages/conversas.vue](../app/pages/conversas.vue)

Ao carregar a lista de conversas, o front varre até 5 conversas por vez que "precisam de sync" e chama `syncProfilePhoto` em background, sem travar a UI:

```js
// Background: sincronizar fotos de perfil que precisam de sync (ignora 'no-photo')
const precisaSync = conversas.value.filter(c => needsPhotoSync(c.photo)).slice(0, 5)
precisaSync.forEach(c => syncProfilePhoto(c))
```

Critério de "precisa sincronizar" (`needsPhotoSync`) — nunca tentou, ou a URL salva é do WhatsApp (expira), ou é do nosso Storage mas quebrou:

```js
function needsPhotoSync(url: string | null | undefined): boolean {
  if (!url) return true // Nunca tentou
  if (url === 'no-photo') return false // Já tentou, contato sem foto
  if (url.includes('pps.whatsapp.net')) return true // URL expirada do WA
  if (url.includes('files.agzap.com.br') || url.includes('/storage/v1/object/public/profile-photos/')) {
    return brokenPhotos.has(getPhotoBase(url)) // Re-sync se a URL salva está quebrada
  }
  return false
}
```

`syncProfilePhoto` chama o endpoint e, se vier sucesso, atualiza a foto **localmente** em todas as conversas com o mesmo telefone (evita esperar o realtime):

```js
async function syncProfilePhoto(conversa: any) {
  if (!conversa?.id) return
  if (photoSyncInProgress.has(conversa.id)) return
  if (conversa.photo && conversa.photo.includes('/storage/v1/object/public/profile-photos/')) return

  photoSyncInProgress.add(conversa.id)
  try {
    const supabase = useSupabaseClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) return

    const result = await $fetch<{ success: boolean; photoUrl?: string }>('/api/contacts/sync-photo', {
      method: 'POST',
      headers: { Authorization: `Bearer ${session.access_token}` },
      body: { conversaId: conversa.id }
    })

    if (result?.success && result.photoUrl) {
      conversas.value.forEach(c => {
        if (c.telefone === conversa.telefone) c.photo = result.photoUrl!
      })
      if (conversaSelecionada.value?.telefone === conversa.telefone) {
        conversaSelecionada.value.photo = result.photoUrl
      }
    }
  } finally { /* ... */ }
}
```

### 3.2) Endpoint que busca a foto na UAZAPI e salva no R2

Arquivo: [server/api/contacts/sync-photo.post.ts](../server/api/contacts/sync-photo.post.ts)

Passo a passo real do endpoint:

1. **Autentica** o usuário (Bearer token do Supabase) e resolve a `empresa_id`.
2. Busca a `conversa` (numero, chatlid, instancia_id, photo atual).
3. Se `conversas.photo` já aponta pro nosso Storage (R2 ou o antigo bucket Supabase `profile-photos`), **devolve direto, sem chamar a UAZAPI** (`cached: true`):
   ```ts
   if (conversa.photo && (conversa.photo.includes('files.agzap.com.br') || conversa.photo.includes('/storage/v1/object/public/profile-photos/'))) {
     return { success: true, photoUrl: conversa.photo, cached: true }
   }
   ```
4. Resolve o **token UAZAPI** da instância da conversa (ou qualquer instância `connected` da empresa, como fallback).
5. Chama a UAZAPI para pegar a foto de verdade:
   ```ts
   const detailsResponse = await fetch(`${UAZAPI_BASE_URL}/chat/details`, {
     method: 'POST',
     headers: { 'Accept': 'application/json', 'Content-Type': 'application/json', 'token': uazapiToken },
     body: JSON.stringify({ number: phone, preview: false })
   })
   const details = await detailsResponse.json() as any
   profilePicUrl = details?.image || details?.imagePreview || null
   ```
6. Se não veio foto, marca `photo = 'no-photo'` no banco (**para não ficar retentando** a cada carregamento de tela) e retorna erro.
7. Se veio, **baixa a imagem server-side** (evita CORS) e faz **upload pro Cloudflare R2**:
   ```ts
   const storagePath = `agzap-profiles/${empresaId}/${conversa.id}.${ext}`
   publicUrl = await uploadToR2({ key: storagePath, body: imageBuffer, contentType })
   ```
   > O nome do arquivo usa o **ID da conversa (UUID)**, nunca o telefone — evita que dois contatos com o mesmo número (bug de `@lid` do WhatsApp) compartilhem o mesmo arquivo e mostrem a foto um do outro.
8. Salva a URL final (com cache-bust `?t=timestamp`) em `conversas.photo`.
9. **Propaga a foto** para a mesma pessoa em outras instâncias da empresa — mas só quando **chatlid E numero batem os dois**, nunca um sozinho:
   ```ts
   // A identidade exige chatlid E numero iguais. Já tentamos cada um sozinho
   // e os dois vazam foto entre contatos diferentes:
   //   - só por numero  -> dois contatos distintos que caem no mesmo numero
   //                       (bug @lid do WhatsApp) trocam de foto;
   //   - só por chatlid -> um payload que traz o @lid de outro contato faz a
   //                       conversa herdar aquela identidade e, na próxima
   //                       sincronização, a foto do outro (caso real: a foto
   //                       da Priscilla apareceu no card da AGZAP).
   if (conversa.chatlid) {
     await supabaseService.from('conversas')
       .update({ photo: finalUrl })
       .eq('chatlid', conversa.chatlid)
       .eq('numero', conversa.numero)
       .eq('empresa_id', empresaId)
       .neq('id', conversaId)
   }
   ```

### 3.3) Estrutura de pastas no bucket R2

Arquivo: [server/utils/r2.ts](../server/utils/r2.ts) — bucket único `agzap`, separado por prefixo:

```
imagens/{empresa}/{instancia}/{mensagem}/       → imagens de conversa
audio/{empresa}/{instancia}/{mensagem}.ext      → áudios uazapi e enviados pelo operador
audios_meta/{empresa}/{instancia}/{mensagem}.ext → áudios recebidos pela API Oficial Meta
pdf/{empresa}/{instancia}/{mensagem}/           → PDFs
documentos/{empresa}/{instancia}/{mensagem}/    → docs
video/{empresa}/{instancia}/{mensagem}/         → vídeos
agzap-profiles/{empresa}/{conversa_id}.jpg      → fotos de perfil (foco deste doc)
```

Upload em si (`uploadToR2`) é um `PutObjectCommand` simples via S3 SDK (R2 é compatível com S3), devolvendo `{r2PublicUrl}/{key}`.

### 3.4) Como a foto é usada depois (renderização)

No front, a foto só é exibida se passar em `isPhotoValid`:

```js
function isPhotoValid(url: string | null | undefined): url is string {
  if (!url) return false
  if (url === 'no-photo') return false
  // URLs do WhatsApp (pps.whatsapp.net) expiram rapidamente - nunca tentar carregá-las
  if (url.includes('pps.whatsapp.net')) return false
  return !brokenPhotos.has(getPhotoBase(url))
}
```

Usada em 3 lugares da tela de Conversas: avatar do card na lista, avatar do cabeçalho do chat, e avatar do painel lateral (clicável, abre a foto ampliada). Sem foto válida, cai num avatar placeholder com gradiente + inicial do nome. Um `@error` no `<img>` marca a URL como "quebrada" (`handlePhotoError`) pra não repetir tentativa de carregar a mesma URL morta.

---

## 4) Como o nono dígito é tratado (com/sem o 9)

O problema de fundo: o **banco** grava telefone normalizado (geralmente **com** o 9), mas a **UAZAPI** às vezes entrega o número **sem** o nono dígito para DDDs interioranos (75, 71...). A mesma pessoa pode aparecer como `5575991198502` (banco/front) e `557591198502` (payload UAZAPI) — bloqueio, desbloqueio e match de conversa precisam casar as duas formas.

### 4.1) No ai-service (Python) — `tel_vars()`

Arquivo: [ai-service/app/utils/normalize.py](../ai-service/app/utils/normalize.py)

```python
def tel_vars(value: str | None) -> list[str]:
    """Variantes BR do telefone com/sem o nono digito do celular."""
    d = _digits(value)
    if not d:
        return []
    out = [d]
    ...
    elif len(d) == 11 and d.startswith("1") and ("55" + d)[4] in "01":
        out.append("55" + d)
    elif d.startswith("55") and len(d) == 13:      # 55 DD 9 XXXXXXXX -> sem nono
        out.append(d[:4] + d[5:])
    elif d.startswith("55") and len(d) == 12:      # 55 DD XXXXXXXX -> com nono
        out.append(d[:4] + "9" + d[4:])
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]
```

`mesmo_telefone(a, b)` usa isso para comparar dois números tolerando o 9. Há ainda `_nucleo_br()`, uma variante mais permissiva (tolera também a ausência do DDI `55`) usada especificamente no **modo teste** do assistente, porque o número de teste é digitado à mão e geralmente vem sem o `55`.

Essa mesma lógica é espelhada no lado Meta (`telVars()` em `server/api/meta/webhook.post.ts`), citado no comentário do código — a invariante vale pros dois canais.

### 4.2) No front (Nuxt/Vue) — `app/utils/telefone.ts`

Arquivo: [app/utils/telefone.ts](../app/utils/telefone.ts)

Convenção do projeto:
- **Banco**: sempre canônico, só dígitos com código do país. Ex.: `5511914600243`.
- **Frontend**: sempre mascarado. Ex.: `(11) 91460-0243`.

Geração de variantes para busca tolerante (usada pelo filtro de nome/telefone da tela de Conversas — seção 6):

```ts
export const variantesBuscaTelefone = (valor?: string | null): string[] => {
  const digits = apenasDigitos(valor)
  if (!digits) return []

  let local = digits
  if ((digits.length === 12 || digits.length === 13) && digits.startsWith('55')) {
    local = digits.slice(2)
  }

  const locais = new Set<string>([local])
  // Celular com nono digito (11 digitos, 3o = 9) -> tambem a forma SEM o nono.
  if (local.length === 11 && local[2] === '9') {
    locais.add(local.slice(0, 2) + local.slice(3))
  }
  // Numero sem nono digito (10 digitos) -> tambem a forma COM o nono.
  if (local.length === 10) {
    locais.add(local.slice(0, 2) + '9' + local.slice(2))
  }

  const variantes = new Set<string>([digits])
  for (const l of locais) {
    variantes.add(l)
    variantes.add('55' + l)
  }
  return [...variantes]
}

export const telefoneCombinaBusca = (telefone?: string | null, termo?: string | null): boolean => {
  const q = apenasDigitos(termo)
  if (!q) return false
  return variantesBuscaTelefone(telefone).some(v => v.includes(q))
}
```

### 4.3) No banco (Postgres) — trigger `chatlid_seguro` e `auto_create_conversa_and_cliente`

A conversa é chaveada por `(empresa_id, instancia_id, numero)` **exatamente como está gravado** — o trigger não normaliza o 9 dentro do SQL; a tolerância ao nono dígito é resolvida **antes** de chegar ao banco (no `normalize_uazapi`, que resolve `telefone` a partir de `sender_pn`/`wa_chatid`). O SQL só garante que o `@lid` (`chatlid`) de uma conversa nunca troca de dono depois de setado (ver função `chatlid_seguro`, migração `20260727_chatlid_nao_troca_de_dono.sql`) — é a segunda camada de defesa contra identidade cruzada, incluindo os casos em que o número aparenta ser o mesmo por causa do nono dígito.

---

## 5) Badge "IA Pausada" e badge de Canal (nome do canal/instância)

Arquivo: [app/pages/conversas.vue](../app/pages/conversas.vue) — bloco de badges do card da lista de conversas (por volta da linha 658):

### 5.1) Badge de Canal (nome da instância)

```html
<!-- Badge de Instância (apenas multi-número) -->
<span
  v-if="temMultiplasInstanciasAtivas && conversa.instancia_id && instanciaById(conversa.instancia_id)"
  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[8px] font-semibold leading-none border"
  :class="[instanciaById(conversa.instancia_id)?.corBg, instanciaById(conversa.instancia_id)?.cor, instanciaById(conversa.instancia_id)?.corBorder]"
  :title="instanciaById(conversa.instancia_id)?.status === 'connected' ? `${instanciaById(conversa.instancia_id)?.nome} — Online` : `${instanciaById(conversa.instancia_id)?.nome} — Offline`"
>
  <span
    class="w-1.5 h-1.5 rounded-full flex-shrink-0"
    :class="instanciaById(conversa.instancia_id)?.status === 'connected' ? 'bg-emerald-500' : 'bg-red-500'"
  ></span>
  {{ instanciaById(conversa.instancia_id)?.nome }}
</span>
```

- Só aparece quando a empresa tem **mais de uma instância** (`temMultiplasInstanciasAtivas`), pra não poluir o card de quem só tem um número.
- `instanciaById()` vem do composable [`useInstancias`](../app/composables/useInstancias.ts): resolve nome, cor e status (`connected`/`disconnected`) tanto de instâncias UAZAPI quanto Meta (API Oficial), com uma paleta rotativa de 4 cores (azul/roxo/teal/laranja) atribuída por ordem de criação.
- Ponto (`●`) verde = instância conectada; vermelho = desconectada.

### 5.2) Badge "IA Pausada" / "IA Ativa"

```html
<!-- Badge de Status IA -->
<span
  v-if="getTempoRestante(conversa) > 0"
  class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[8px] font-semibold leading-none bg-orange-500/10 text-orange-600 dark:text-orange-400"
>
  IA Pausada
</span>
<span
  v-else
  class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[8px] font-semibold leading-none bg-green-500/10 text-green-600 dark:text-green-400"
>
  IA Ativa
</span>
```

`getTempoRestante(conversa)` calcula quanto falta da pausa (`conversa.tempo_pausa` menos o tempo decorrido desde `tempo_pausa_inicio`):

```js
const getTempoRestante = (conversa: any) => {
  if (!conversa) return 0
  const total = conversa.tempo_pausa || 0
  if (!total || total <= 0) return 0
  if (!conversa.tempo_pausa_inicio) return total
  const inicio = new Date(conversa.tempo_pausa_inicio).getTime()
  if (Number.isNaN(inicio)) return total
  const agora = tempoAtual.value
  const decorrido = Math.floor((agora - inicio) / 1000)
  return Math.max(total - decorrido, 0)
}
```

**Mesmo modelo de badge** — tamanho (`text-[8px]`), formato (`rounded-md`, `px-1.5 py-0.5`) e paleta (`bg-<cor>-500/10` + `text-<cor>-600 dark:text-<cor>-400`) — é reaproveitado por outros badges do mesmo card (ex.: contador de não lidas usa outra cor sólida). Ao pedir um badge novo no mesmo estilo, basta seguir essa mesma classe base trocando a cor semântica.

Existe também a versão "grande" do mesmo badge, no painel lateral da conversa selecionada (linha ~2166-2177), com texto completo e ícone, incluindo o caso de pausa **permanente**:

```html
<div v-if="getTempoRestante(conversaSelecionada) > 0" class="mt-3 px-3 py-2 bg-orange-500/20 border border-orange-500/30 rounded-lg">
  <div class="flex items-center gap-2 text-xs">
    <svg class="w-4 h-4 text-orange-300 flex-shrink-0" ...>...</svg>
    <div class="flex-1 text-orange-200">
      <p v-if="conversaSelecionada.tempo_pausa === 31_536_000" class="font-semibold">IA Pausada Permanente</p>
      <p v-else class="font-semibold">IA pausada por {{ formatarTempo(getTempoRestante(conversaSelecionada)) }}</p>
    </div>
  </div>
</div>
```

> Pausa **otimista**: ao atendente enviar uma mensagem, o front marca `tempo_pausa`/`tempo_pausa_inicio` localmente na hora (`marcarPausaOtimista`), sem esperar o Realtime — evita o atendente ver "IA Ativa" por alguns segundos logo após assumir a conversa.

---

## 6) Filtros de período e de nome (tela de Conversas)

### 6.1) Filtro de período

UI (por volta da linha 272-303 de `conversas.vue`) — presets rápidos + intervalo customizado:

```html
<label>Período</label>
<div class="flex flex-wrap gap-1 mb-2">
  <button
    v-for="op in [{ v: 'todos', l: 'Todos' }, { v: 'hoje', l: 'Hoje' }, { v: '7d', l: '7 dias' }, { v: '30d', l: '30 dias' }, { v: 'custom', l: 'Personalizado' }]"
    :key="op.v" type="button" @click="filtroPeriodoConversas = op.v as any" ...>
    {{ op.l }}
  </button>
</div>
<div v-if="filtroPeriodoConversas === 'custom'" class="flex items-center gap-1.5">
  <input v-model="filtroDataInicioConversa" type="date" ... />
  <span>até</span>
  <input v-model="filtroDataFimConversa" type="date" ... />
</div>
```

Resolução do intervalo em milissegundos (`intervaloFiltroConversas`, computed):

```js
const intervaloFiltroConversas = computed<{ inicioMs: number; fimMs: number } | null>(() => {
  const modo = filtroPeriodoConversas.value
  if (modo === 'todos') return null
  if (modo === 'custom') {
    if (!filtroDataInicioConversa.value && !filtroDataFimConversa.value) return null
    const inicioMs = filtroDataInicioConversa.value
      ? new Date(`${filtroDataInicioConversa.value}T00:00:00`).getTime() : 0
    const fimMs = filtroDataFimConversa.value
      ? new Date(`${filtroDataFimConversa.value}T23:59:59`).getTime() : Number.MAX_SAFE_INTEGER
    return { inicioMs, fimMs }
  }
  if (modo === 'hoje') {
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0)
    return { inicioMs: hoje.getTime(), fimMs: Date.now() }
  }
  const dias = modo === '7d' ? 7 : 30
  const fimMs = Date.now()
  const inicioMs = fimMs - dias * 86400000
  return { inicioMs, fimMs }
})
```

Aplicação do filtro (dentro de `aplicarFiltrosBusca`) — filtra por **última atividade** da conversa (`ultimo_horario`, com fallback pra `created_at`); conversa sem data conhecida **não é escondida**:

```js
const intervalo = intervaloFiltroConversas.value
if (intervalo) {
  lista = lista.filter(conversa => {
    const ref = conversa.ultimo_horario || conversa.created_at || conversa.ultima_msg_cliente_em
    if (!ref) return true
    const ms = new Date(ref).getTime()
    if (Number.isNaN(ms)) return true
    return ms >= intervalo.inicioMs && ms <= intervalo.fimMs
  })
}
```

### 6.2) Filtro por nome (barra de busca)

Campo `buscaConversa` (input no topo da lista, `v-model="buscaConversa"`, linha ~102). A função `aplicarFiltrosBusca` (usada tanto na lista quanto na contagem das abas, pra nunca ficar dessincronizado) faz:

1. **Normaliza** o termo digitado (remove acento/caixa) com `normalizarTextoBusca` — "joao" acha "João".
2. Também deriva uma versão **numérica** do termo (`normalizarTelefone`), pra permitir buscar por telefone digitando só números.
3. Filtra por **nome contém** OU **telefone (como exibido) contém** OU **telefone tolerante ao nono dígito/DDI** via `telefoneCombinaBusca` (seção 4.2):

```js
if (buscaConversa.value.trim()) {
  const busca = normalizarTextoBusca(buscaConversa.value.trim())
  const buscaNumerica = normalizarTelefone(busca)

  lista = lista.filter(conversa => {
    const nome = normalizarTextoBusca(conversa.nome)
    const telefoneOriginal = (conversa.telefone || '').toLowerCase()
    if (nome.includes(busca) || telefoneOriginal.includes(busca)) return true
    return buscaNumerica.length > 0 && telefoneCombinaBusca(conversa.telefone, buscaNumerica)
  })

  // Ranking de relevância: nome IGUAL > palavra igual > começa com > substring.
  // Sem isso, "gabriel" enterrava contatos antigos embaixo de "Gabriela"s recentes.
  const rankPorId = new Map<string, number>()
  for (const conversa of lista) {
    const nome = normalizarTextoBusca(conversa.nome)
    let rank = 3
    if (nome === busca) rank = 0
    else if (nome) {
      const palavras = nome.split(/[^a-z0-9]+/).filter(Boolean)
      if (palavras.includes(busca)) rank = 1
      else if (nome.startsWith(busca) || palavras.some(p => p.startsWith(busca))) rank = 2
    }
    rankPorId.set(conversa.id, rank)
  }
  lista = [...lista].sort((a, b) => (rankPorId.get(a.id) ?? 3) - (rankPorId.get(b.id) ?? 3))
}
```

4. Além disso, digitar na busca dispara (com debounce de 400ms) uma **busca no servidor** (`buscarConversasNoServidor`, via RPC `buscar_conversas_ids`) pra também trazer conversas **antigas** que não estão carregadas na paginação local — a lista local (`conversasFiltradas`) e a busca no servidor trabalham juntas, uma cobre o que já está na tela, a outra cobre o que ainda não foi carregado.

---

## 7) EasyPanel — onde o ai-service roda

Referência: [ai-service/README.md](../ai-service/README.md)

O `ai-service` (FastAPI + LangChain + LangGraph, responsável por normalizar o webhook da UAZAPI, rodar a IA e inserir as mensagens) roda numa **VPS Hostinger via EasyPanel**, **não** na Vercel — deploy é **manual** (diferente do Nuxt, que tem auto-deploy na Vercel a cada push).

Passo a passo de setup (resumo do README):

1. **SQL inicial**: conectar no Postgres do EasyPanel (o mesmo que o n8n usava) e rodar `ai-service/sql/000_init.sql`.
2. **Criar o app no EasyPanel**:
   - Project → **+ Service → App**
   - Name: `agzap-ai-service`
   - Source: GitHub, branch `main`
   - **Build Path: `ai-service`** ← crítico, faz o EasyPanel rodar o `Dockerfile` só dessa subpasta do monorepo
   - Build Type: Dockerfile (auto-detectado)
   - Domain: `chain.agzap.com.br`, porta interna `8000`
   - Resources iniciais: 0.5 CPU / 512 MB RAM (escalável depois)
   - Replicas: 1 (sobe pra 2-3 depois de validado)
3. **Environment Variables**: coladas direto no painel do EasyPanel (nunca commitadas em arquivo) — inclui conexão Postgres, Redis Upstash, chaves de IA, etc.
4. **Deploy**: botão **Deploy** no EasyPanel, acompanhar logs do build, validar com `curl /healthz` e `/readyz` após "Container running".

Esse é o motivo pelo qual uma alteração em `ai-service/**` (normalize.py, dispatcher.py, etc.) **não** sobe sozinha — precisa clicar em Deploy manualmente no painel do EasyPanel, diferente do restante do app (Nuxt), que sobe automático na Vercel a cada push pro `main`.

---

## 8) Resumo rápido (TL;DR)

| O quê | Onde | Quando roda |
|---|---|---|
| Captura do **nome** (pushName) | [normalize.py](../ai-service/app/utils/normalize.py) `_extract_nome_contato` | No instante do webhook, por mensagem |
| Nome vira `conversas.nome_contato` / `clientes.nome` | Trigger `auto_create_conversa_and_cliente` (Postgres) | INSERT em `mensagens` (cascata) |
| Captura da **foto** | [sync-photo.post.ts](../server/api/contacts/sync-photo.post.ts) via UAZAPI `/chat/details` | Sob demanda, disparado pelo front (até 5 por carregamento da lista) |
| Foto salva em | Cloudflare R2, pasta `agzap-profiles/{empresa}/{conversa_id}.ext` | Após download server-side da imagem |
| Tolerância ao **nono dígito** | `tel_vars()` (Python) / `variantesBuscaTelefone()` (front) | Normalização de telefone, busca, bloqueio/desbloqueio |
| Badge **IA Pausada/Ativa** | `conversas.vue`, `getTempoRestante(conversa)` | Reativo, recalculado a cada tick do relógio local |
| Badge de **Canal** | `conversas.vue` + `useInstancias().instanciaById()` | Só visível com múltiplas instâncias ativas |
| Filtro de **período** | `intervaloFiltroConversas` (computed) | Sobre `ultimo_horario`/`created_at` |
| Filtro de **nome** | `aplicarFiltrosBusca` + busca no servidor (RPC) | Local (carregado) + servidor (histórico) |
| Deploy do ai-service | EasyPanel, manual, Build Path = `ai-service` | Só quando alguém clica em Deploy |
