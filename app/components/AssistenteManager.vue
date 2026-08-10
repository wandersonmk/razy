<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header -->
    <div class="flex items-center justify-between p-6 border-b border-border gap-3">
      <div class="flex items-center gap-3 min-w-0">
        <button v-if="assistenteId" type="button" @click="$emit('voltar')"
          class="p-2 -ml-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition shrink-0" title="Voltar">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
        </button>
        <div class="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center shrink-0">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
        </div>
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-foreground truncate">{{ form.nome || 'Assistente de Atendimento' }}</h2>
          <p class="text-sm text-muted-foreground">IA que atende o cliente e encaminha ao atendente</p>
        </div>
      </div>
      <!-- Toggle ativo -->
      <div class="flex items-center gap-2 shrink-0">
        <span class="text-sm text-muted-foreground">{{ form.ativo ? 'Ativo' : 'Inativo' }}</span>
        <button type="button" @click="form.ativo = !form.ativo"
          :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none', form.ativo ? 'bg-primary' : 'bg-muted']">
          <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ativo ? 'translate-x-5' : 'translate-x-0']"/>
        </button>
      </div>
    </div>

    <!-- Identidade: nome / tipo / canal vinculado -->
    <div class="p-6 border-b border-border grid gap-4 sm:grid-cols-3">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Nome do assistente</label>
        <input v-model="form.nome" maxlength="40" type="text" placeholder="Ex: Financeiro"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Tipo</label>
        <select v-model="form.tipo"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
          <option v-for="t in TIPOS_ASSISTENTE" :key="t.id" :value="t.id">{{ t.label }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Canal vinculado</label>
        <select v-model="instanciaId"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
          <option :value="null">Sem canal (órfão)</option>
          <option v-for="c in canais" :key="c.id" :value="c.id">
            {{ c.nome }}{{ c.telefone ? ' · ' + c.telefone : '' }}
          </option>
        </select>
        <p v-if="instanciaId && instanciaEmUsoPorOutro" class="text-[11px] text-amber-600 dark:text-amber-400 mt-1">
          Este canal está em uso por outro assistente — ao salvar, ele passa para este.
        </p>
      </div>
    </div>

    <!-- Abas -->
    <div class="flex border-b border-border px-6">
      <button @click="aba = 'atendimento'"
        :class="['py-3 px-1 mr-6 text-sm font-medium border-b-2 transition', aba === 'atendimento' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
        Atendimento
      </button>
      <button @click="aba = 'capacidades'"
        :class="['py-3 px-1 mr-6 text-sm font-medium border-b-2 transition flex items-center gap-1.5', aba === 'capacidades' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
        Capacidades
      </button>
      <button @click="aba = 'avancado'"
        :class="['py-3 px-1 text-sm font-medium border-b-2 transition', aba === 'avancado' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
        Configurações avançadas
      </button>
    </div>

    <div v-show="aba === 'atendimento'" class="p-6 space-y-5">
      <!-- Como funciona -->
      <div class="flex items-start gap-2 text-xs p-3 rounded-lg bg-primary/5 border border-primary/20 text-foreground">
        <svg class="w-4 h-4 shrink-0 mt-0.5 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
        <span>
          Quando o cliente responde a um disparo (texto ou <strong>áudio</strong>, que é transcrito automaticamente), o assistente
          atende usando as informações abaixo, coleta os dados e — quando a coleta termina — envia um resumo para o número do atendente.
          O contexto da conversa é mantido pelo número que recebeu a mensagem.
          Para ler <strong>imagens</strong> e <strong>documentos</strong>, ligue na aba <strong>Capacidades</strong>.
        </span>
      </div>

      <!-- Nome da empresa -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Nome da empresa</label>
        <input v-model="form.empresa_nome" type="text" placeholder="Ex: Razy Corretora"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
      </div>

      <!-- Informações da empresa -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Informações da empresa e dos planos</label>
        <textarea v-model="form.empresa_info" rows="5"
          placeholder="Descreva os produtos/planos, preços, diferenciais, coberturas, condições... A IA usa isso para responder o cliente."
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
      </div>

      <!-- Horário de funcionamento -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Horário de funcionamento</label>
        <input v-model="form.horario_funcionamento" type="text" placeholder="Ex: Seg a Sex, 8h às 18h"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
      </div>

      <!-- Instrução do assistente -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="block text-sm font-medium text-foreground">Instruções do assistente</label>
          <button type="button" @click="abrirExpandido"
            class="flex items-center gap-1 text-xs text-primary hover:underline"
            title="Expandir editor (localizar e substituir)">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
            </svg>
            Expandir
          </button>
        </div>
        <textarea v-model="form.instrucao" rows="5"
          placeholder="Como o assistente deve se comportar: tom de voz, o que perguntar ao cliente, quais dados coletar, quando encaminhar ao atendente..."
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
        <p class="text-xs text-muted-foreground mt-1">Ex: "Pergunte o nome, a cidade e o tipo de plano de interesse. Seja cordial. Quando tiver esses dados, encaminhe ao atendente."</p>
      </div>

      <!-- Atendentes (handoff) -->
      <div class="rounded-xl border border-border p-4 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-foreground">Atendentes (handoff)</p>
            <p class="text-xs text-muted-foreground mt-0.5">Quando a coleta terminar, o assistente envia o resumo para estes números via WhatsApp.</p>
          </div>
          <button @click="addAtendente" type="button" class="text-xs text-primary hover:underline flex items-center gap-1 shrink-0">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Adicionar atendente
          </button>
        </div>

        <div class="space-y-2">
          <div v-for="(_, idx) in atendentes" :key="idx" class="flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-[11px] shrink-0">{{ idx + 1 }}</span>
            <input
              :value="atendentes[idx]"
              @input="onTelInput(idx, ($event.target as HTMLInputElement).value)"
              type="text"
              inputmode="numeric"
              placeholder="(11) 91460-0243"
              class="flex-1 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button v-if="atendentes.length > 1" @click="removeAtendente(idx)" type="button" class="p-1.5 text-muted-foreground hover:text-red-500 transition shrink-0">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
        </div>

        <!-- Rodízio -->
        <div class="flex items-center justify-between gap-3 pt-2 border-t border-border">
          <div>
            <p class="text-sm text-foreground">Rodízio entre atendentes</p>
            <p class="text-xs text-muted-foreground mt-0.5">
              {{ form.notificar_rotativo
                ? 'Cada cliente é encaminhado a um atendente diferente, em rodízio (1º, 2º, 3º… e volta ao 1º).'
                : 'Todos os atendentes são notificados a cada novo cliente.' }}
            </p>
          </div>
          <button type="button" @click="form.notificar_rotativo = !form.notificar_rotativo"
            :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.notificar_rotativo ? 'bg-primary' : 'bg-muted']">
            <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.notificar_rotativo ? 'translate-x-5' : 'translate-x-0']"/>
          </button>
        </div>

        <div class="flex items-start gap-2 text-xs p-2 rounded-lg bg-violet-500/5 border border-violet-500/20 text-foreground">
          <svg class="w-3.5 h-3.5 shrink-0 mt-0.5 text-violet-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
          <span>As notificações saem por um canal marcado como <strong>"Número para notificar atendentes"</strong> em Configurações (se houver) — esse número fica fora do disparo de campanhas. Caso nenhum esteja marcado, usa o número da própria conversa.</span>
        </div>
      </div>
    </div>

    <!-- Aba: Capacidades da IA -->
    <div v-show="aba === 'capacidades'" class="p-6 space-y-4">
      <!-- Cabeçalho -->
      <div class="flex items-start gap-3 rounded-xl border border-border p-4">
        <div class="w-10 h-10 shrink-0 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
        </div>
        <div>
          <p class="text-sm font-semibold text-foreground">O que sua IA pode fazer</p>
          <p class="text-xs text-muted-foreground mt-0.5">Liga/desliga a leitura de mídias enviadas pelos clientes. Custos adicionais aplicam-se quando ligado.</p>
        </div>
      </div>

      <!-- Áudio: nativo, sem toggle -->
      <div class="flex items-center gap-3 rounded-xl border border-border p-4">
        <div class="w-9 h-9 shrink-0 rounded-lg bg-emerald-500/10 flex items-center justify-center">
          <svg class="w-4.5 h-4.5 text-emerald-500" style="width:1.125rem;height:1.125rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-14 0m7 7v4m0-4a3 3 0 003-3V6a3 3 0 00-6 0v9a3 3 0 003 3z"/></svg>
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-foreground">Áudio (voz)</p>
          <p class="text-xs text-muted-foreground mt-0.5">Transcrição automática via Whisper. Sempre ativo, sem custo extra significativo.</p>
        </div>
        <span class="shrink-0 px-2 py-1 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold tracking-wide">NATIVO</span>
      </div>

      <!-- Ler imagens -->
      <div class="rounded-xl border border-border overflow-hidden">
        <div class="flex items-center gap-3 p-4">
          <div class="w-9 h-9 shrink-0 rounded-lg bg-violet-500/10 flex items-center justify-center">
            <svg class="text-violet-500" style="width:1.125rem;height:1.125rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-foreground">Ler imagens</p>
            <p class="text-xs text-muted-foreground mt-0.5">Descreve fotos, comprovantes, prints. Permite reagir ao conteúdo da imagem.</p>
          </div>
          <button type="button" @click="form.ler_imagem = !form.ler_imagem"
            :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.ler_imagem ? 'bg-violet-500' : 'bg-muted']">
            <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ler_imagem ? 'translate-x-5' : 'translate-x-0']"/>
          </button>
        </div>
        <div v-if="form.ler_imagem" class="px-4 pb-4 border-t border-border pt-3">
          <label class="block text-xs font-medium text-foreground mb-1">Instrução customizada (opcional)</label>
          <textarea v-model="form.instrucao_imagem" rows="4"
            placeholder="Ex: Sempre que o cliente enviar comprovante de pagamento, transfira o atendimento para o assistente Financeiro."
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
          <p class="flex items-start gap-1.5 text-[11px] text-muted-foreground mt-1.5">
            <svg class="w-3.5 h-3.5 shrink-0 mt-px text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
            <span>A IA recebe a descrição da imagem + essa instrução. Use pra direcionar respostas (transferir, etiquetar, etc). Em branco, ela segue as instruções gerais do assistente.</span>
          </p>
        </div>
      </div>

      <!-- Ler documentos -->
      <div class="rounded-xl border border-border overflow-hidden">
        <div class="flex items-center gap-3 p-4">
          <div class="w-9 h-9 shrink-0 rounded-lg bg-amber-500/10 flex items-center justify-center">
            <svg class="text-amber-500" style="width:1.125rem;height:1.125rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-foreground">Ler documentos (PDF, Word, txt)</p>
            <p class="text-xs text-muted-foreground mt-0.5">Extrai o conteúdo do arquivo (até 8.000 caracteres) e injeta no contexto da IA.</p>
          </div>
          <button type="button" @click="form.ler_documento = !form.ler_documento"
            :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.ler_documento ? 'bg-amber-500' : 'bg-muted']">
            <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ler_documento ? 'translate-x-5' : 'translate-x-0']"/>
          </button>
        </div>
        <div v-if="form.ler_documento" class="px-4 pb-4 border-t border-border pt-3">
          <label class="block text-xs font-medium text-foreground mb-1">Instrução customizada (opcional)</label>
          <textarea v-model="form.instrucao_documento" rows="4"
            placeholder="Ex: Se for um currículo, faça um resumo das competências e transfira para o RH."
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
          <p class="flex items-start gap-1.5 text-[11px] text-muted-foreground mt-1.5">
            <svg class="w-3.5 h-3.5 shrink-0 mt-px text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
            <span>A IA recebe o texto do arquivo + essa instrução. Em branco, ela segue as instruções gerais do assistente. Formatos legados (.doc) e planilhas não são lidos.</span>
          </p>
        </div>
      </div>

      <div class="flex items-start gap-2 text-xs p-3 rounded-lg bg-primary/5 border border-primary/20 text-foreground">
        <svg class="w-4 h-4 shrink-0 mt-0.5 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
        <span>As capacidades valem <strong>só para este assistente</strong> (ou seja, para o número vinculado a ele). Com a leitura desligada, mídias continuam chegando no WhatsApp — a IA apenas não as interpreta e responde só pela legenda, se houver.</span>
      </div>
    </div>

    <!-- Aba: Configurações avançadas -->
    <div v-show="aba === 'avancado'" class="p-6 space-y-5">
      <div class="rounded-xl border border-border p-4 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-medium text-foreground">Pausar IA quando o dono responder</p>
            <p class="text-xs text-muted-foreground mt-0.5">Se você responder o cliente manualmente pelo celular, a IA para de responder aquele contato automaticamente.</p>
          </div>
          <button type="button" @click="form.pausa_ativa = !form.pausa_ativa"
            :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.pausa_ativa ? 'bg-primary' : 'bg-muted']">
            <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.pausa_ativa ? 'translate-x-5' : 'translate-x-0']"/>
          </button>
        </div>

        <div v-if="form.pausa_ativa" class="pt-1">
          <label class="block text-sm font-medium text-foreground mb-1">Tempo de pausa</label>
          <div class="flex items-center gap-2">
            <input v-model.number="form.pausa_minutos" type="number" min="1"
              class="w-28 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
            <span class="text-sm text-muted-foreground">minutos sem a IA responder após você assumir</span>
          </div>
          <p class="text-xs text-muted-foreground mt-1">Passado esse tempo sem nova mensagem sua, a IA volta a atender automaticamente. Sugestões: 30, 60, 120.</p>
        </div>
      </div>

      <div class="flex items-start gap-2 text-xs p-3 rounded-lg bg-primary/5 border border-primary/20 text-foreground">
        <svg class="w-4 h-4 shrink-0 mt-0.5 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
        <span>A pausa é por contato e fica guardada no servidor (Redis), identificada pelo telefone + empresa + número conectado — o mesmo padrão usado para manter o contexto da conversa. Expira sozinha no tempo definido.</span>
      </div>
    </div>

    <!-- Ações (compartilhado entre as abas) -->
    <div class="flex items-center justify-between gap-3 p-6 border-t border-border">
      <p v-if="sucesso" class="text-xs text-green-600 dark:text-green-400">✓ Configurações salvas!</p>
      <p v-else-if="erro" class="text-xs text-red-500">{{ erro }}</p>
      <span v-else class="text-xs text-muted-foreground"></span>
      <button
        @click="salvar"
        :disabled="salvando || carregando"
        class="px-5 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
      >
        {{ salvando ? 'Salvando...' : 'Salvar configurações' }}
      </button>
    </div>

    <!-- ── Editor expandido com Localizar/Substituir ── -->
    <Teleport to="body">
      <div v-if="expandido" class="fixed inset-0 z-50 flex flex-col bg-black/60 backdrop-blur-sm p-4 sm:p-8">
        <div class="bg-card border border-border rounded-2xl shadow-2xl flex flex-col flex-1 overflow-hidden">
          <!-- Header -->
          <div class="flex items-center justify-between p-4 border-b border-border shrink-0">
            <h3 class="text-base font-semibold text-foreground">Instruções do assistente</h3>
            <div class="flex items-center gap-2">
              <button @click="mostrarBusca = !mostrarBusca" type="button"
                :class="['flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition border', mostrarBusca ? 'bg-primary/10 text-primary border-primary/30' : 'border-border text-foreground hover:bg-muted']"
                title="Localizar e substituir (Ctrl+F)">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                Localizar
              </button>
              <button @click="fecharExpandido" type="button" class="p-2 text-muted-foreground hover:text-foreground transition" title="Fechar">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
          </div>

          <!-- Barra de localizar/substituir -->
          <div v-if="mostrarBusca" class="flex flex-wrap items-center gap-2 p-3 border-b border-border bg-muted/30 shrink-0">
            <div class="flex items-center gap-2">
              <input
                ref="findInputRef"
                v-model="findTerm"
                @input="recalcularMatches"
                @keydown.enter.prevent="proximoMatch"
                type="text"
                placeholder="Localizar"
                class="w-48 px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <span class="text-xs text-muted-foreground tabular-nums min-w-[60px]">
                {{ matchPositions.length ? `${currentMatch + 1} de ${matchPositions.length}` : (findTerm ? '0 de 0' : '') }}
              </span>
              <button @click="anteriorMatch" :disabled="!matchPositions.length" type="button" class="p-1.5 border border-border rounded-lg text-foreground hover:bg-muted disabled:opacity-40" title="Anterior">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/></svg>
              </button>
              <button @click="proximoMatch" :disabled="!matchPositions.length" type="button" class="p-1.5 border border-border rounded-lg text-foreground hover:bg-muted disabled:opacity-40" title="Próximo">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </button>
            </div>
            <div class="flex items-center gap-2">
              <input
                v-model="replaceTerm"
                type="text"
                placeholder="Substituir por"
                class="w-48 px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <button @click="substituirAtual" :disabled="!matchPositions.length" type="button" class="px-3 py-1.5 border border-border rounded-lg text-foreground text-sm hover:bg-muted disabled:opacity-40">
                Substituir
              </button>
              <button @click="substituirTodas" :disabled="!matchPositions.length" type="button" class="px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-40">
                Substituir todas
              </button>
            </div>
            <label class="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer ml-auto">
              <input type="checkbox" v-model="caseSensitive" @change="recalcularMatches" class="h-3.5 w-3.5 rounded border-border accent-primary">
              Diferenciar maiúsculas
            </label>
          </div>

          <!-- Editor -->
          <div class="flex-1 p-4 overflow-hidden">
            <textarea
              ref="editorRef"
              v-model="form.instrucao"
              @input="recalcularMatches"
              placeholder="Escreva as instruções do assistente..."
              class="w-full h-full resize-none px-4 py-3 rounded-lg border border-border bg-background text-foreground text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-between p-4 border-t border-border shrink-0">
            <span class="text-xs text-muted-foreground">{{ form.instrucao.length }} caracteres</span>
            <button @click="fecharExpandido" type="button" class="px-5 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition">
              Concluir
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAssistentes, TIPOS_ASSISTENTE } from '~/composables/useAssistentes'
import { useCanais } from '~/composables/useCanais'

const props = defineProps<{ assistenteId?: string | null }>()
const emit = defineEmits<{ voltar: []; salvo: [] }>()

let _supabase: any = null
function getSupabase() {
  if (!_supabase && typeof window !== 'undefined') _supabase = useSupabaseClient()
  return _supabase
}

let toast: any

const { atualizarAssistente, assistentes, fetchAssistentes } = useAssistentes()
const { canais, fetchCanais } = useCanais()

const aba = ref<'atendimento' | 'capacidades' | 'avancado'>('atendimento')

const form = ref({
  nome: '',
  tipo: 'principal',
  ativo: true,
  empresa_nome: '',
  empresa_info: '',
  horario_funcionamento: '',
  instrucao: '',
  notificar_rotativo: false,
  pausa_ativa: true,
  pausa_minutos: 30,
  ler_imagem: false,
  instrucao_imagem: '',
  ler_documento: false,
  instrucao_documento: ''
})

const instanciaId = ref<string | null>(null)
const carregando = ref(false)

// Lista de atendentes (exibida com máscara). Persistida em atendente_telefone separada por vírgula.
const atendentes = ref<string[]>([''])

const salvando = ref(false)
const sucesso = ref(false)
const erro = ref('')

// Canal já vinculado a OUTRO assistente?
const instanciaEmUsoPorOutro = computed(() =>
  !!instanciaId.value &&
  assistentes.value.some((a) => a.instancia_id === instanciaId.value && a.id !== props.assistenteId)
)

// ── Máscara de telefone BR ──────────────────────────────────────────────────
function maskTel(valor: string): string {
  let d = (valor || '').replace(/\D/g, '')
  if (d.length > 11 && d.startsWith('55')) d = d.slice(2)
  d = d.slice(0, 11)
  if (d.length <= 2) return d.length ? `(${d}` : ''
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
}

function soDigitos(valor: string): string {
  return (valor || '').replace(/\D/g, '')
}

function onTelInput(idx: number, valor: string) {
  atendentes.value[idx] = maskTel(valor)
}

function addAtendente() {
  atendentes.value.push('')
}

function removeAtendente(idx: number) {
  atendentes.value.splice(idx, 1)
  if (atendentes.value.length === 0) atendentes.value.push('')
}

function aplicar(data: any) {
  form.value = {
    nome: data.nome || '',
    tipo: data.tipo || 'principal',
    ativo: data.ativo ?? true,
    empresa_nome: data.empresa_nome || '',
    empresa_info: data.empresa_info || '',
    horario_funcionamento: data.horario_funcionamento || '',
    instrucao: data.instrucao || '',
    notificar_rotativo: data.notificar_rotativo ?? false,
    pausa_ativa: data.pausa_ativa ?? true,
    pausa_minutos: data.pausa_minutos ?? 30,
    ler_imagem: data.ler_imagem ?? false,
    instrucao_imagem: data.instrucao_imagem || '',
    ler_documento: data.ler_documento ?? false,
    instrucao_documento: data.instrucao_documento || ''
  }
  instanciaId.value = data.instancia_id ?? null
  const nums = (data.atendente_telefone || '').split(',').map((n: string) => maskTel(n)).filter(Boolean)
  atendentes.value = nums.length ? nums : ['']
}

onMounted(async () => {
  toast = await useToastSafe()
  fetchCanais({ silent: true })
  fetchAssistentes({ silent: true })

  const sb = getSupabase()
  if (!sb) return
  carregando.value = true
  try {
    let query = sb.from('assistentes')
      .select('id, instancia_id, nome, tipo, ativo, empresa_nome, empresa_info, horario_funcionamento, instrucao, atendente_telefone, notificar_rotativo, pausa_ativa, pausa_minutos, ler_imagem, instrucao_imagem, ler_documento, instrucao_documento')
    if (props.assistenteId) {
      const { data } = await query.eq('id', props.assistenteId).maybeSingle()
      if (data) aplicar(data)
    } else {
      // Compat: sem id explícito, pega o assistente do usuário (fluxo antigo).
      const { data: { user } } = await sb.auth.getUser()
      if (user) {
        const { data } = await query.eq('usuario_id', user.id).order('created_at', { ascending: true }).limit(1).maybeSingle()
        if (data) aplicar(data)
      }
    }
  } catch { /* silencia */ } finally {
    carregando.value = false
  }
})

// ── Editor expandido + Localizar/Substituir ─────────────────────────────────
const expandido = ref(false)
const mostrarBusca = ref(false)
const findTerm = ref('')
const replaceTerm = ref('')
const caseSensitive = ref(false)
const matchPositions = ref<number[]>([])
const currentMatch = ref(0)
const editorRef = ref<HTMLTextAreaElement | null>(null)
const findInputRef = ref<HTMLInputElement | null>(null)

function abrirExpandido() {
  expandido.value = true
  nextTick(() => editorRef.value?.focus())
}

function fecharExpandido() {
  expandido.value = false
  mostrarBusca.value = false
}

function escaparRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function recalcularMatches() {
  const termo = findTerm.value
  if (!termo) { matchPositions.value = []; currentMatch.value = 0; return }
  const flags = caseSensitive.value ? 'g' : 'gi'
  const re = new RegExp(escaparRegex(termo), flags)
  const texto = form.value.instrucao || ''
  const posicoes: number[] = []
  let m: RegExpExecArray | null
  while ((m = re.exec(texto)) !== null) {
    posicoes.push(m.index)
    if (m.index === re.lastIndex) re.lastIndex++
  }
  matchPositions.value = posicoes
  if (currentMatch.value >= posicoes.length) currentMatch.value = 0
}

function focarMatch() {
  const pos = matchPositions.value[currentMatch.value]
  if (pos === undefined || !editorRef.value) return
  const el = editorRef.value
  el.focus()
  el.setSelectionRange(pos, pos + findTerm.value.length)
  const linhasAntes = (form.value.instrucao.slice(0, pos).match(/\n/g) || []).length
  const lineHeight = 22
  el.scrollTop = Math.max(0, linhasAntes * lineHeight - el.clientHeight / 2)
}

function proximoMatch() {
  if (!matchPositions.value.length) return
  currentMatch.value = (currentMatch.value + 1) % matchPositions.value.length
  nextTick(focarMatch)
}

function anteriorMatch() {
  if (!matchPositions.value.length) return
  currentMatch.value = (currentMatch.value - 1 + matchPositions.value.length) % matchPositions.value.length
  nextTick(focarMatch)
}

function substituirAtual() {
  if (!matchPositions.value.length) return
  const pos = matchPositions.value[currentMatch.value]
  if (pos === undefined) return
  const texto = form.value.instrucao
  form.value.instrucao = texto.slice(0, pos) + replaceTerm.value + texto.slice(pos + findTerm.value.length)
  nextTick(() => {
    recalcularMatches()
    if (currentMatch.value >= matchPositions.value.length) currentMatch.value = Math.max(0, matchPositions.value.length - 1)
    nextTick(focarMatch)
  })
}

function substituirTodas() {
  if (!findTerm.value) return
  const flags = caseSensitive.value ? 'g' : 'gi'
  const re = new RegExp(escaparRegex(findTerm.value), flags)
  const qtd = matchPositions.value.length
  form.value.instrucao = (form.value.instrucao || '').replace(re, replaceTerm.value)
  recalcularMatches()
  toast?.success(`${qtd} ocorrência(s) substituída(s)`)
}

function onKeydownGlobal(e: KeyboardEvent) {
  if (expandido.value && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
    e.preventDefault()
    mostrarBusca.value = true
    nextTick(() => findInputRef.value?.focus())
  } else if (expandido.value && e.key === 'Escape') {
    fecharExpandido()
  }
}

onMounted(() => { if (typeof window !== 'undefined') window.addEventListener('keydown', onKeydownGlobal) })
onUnmounted(() => { if (typeof window !== 'undefined') window.removeEventListener('keydown', onKeydownGlobal) })

async function salvar() {
  if (!props.assistenteId) {
    erro.value = 'Assistente não identificado'
    toast?.error(erro.value)
    return
  }
  salvando.value = true
  erro.value = ''
  sucesso.value = false
  try {
    const telefones = atendentes.value
      .map(soDigitos)
      .filter((d) => d.length >= 10)
      .join(',')

    await atualizarAssistente(props.assistenteId, {
      nome: form.value.nome,
      tipo: form.value.tipo,
      ativo: form.value.ativo,
      empresa_nome: form.value.empresa_nome,
      empresa_info: form.value.empresa_info,
      horario_funcionamento: form.value.horario_funcionamento,
      instrucao: form.value.instrucao,
      notificar_rotativo: form.value.notificar_rotativo,
      pausa_ativa: form.value.pausa_ativa,
      pausa_minutos: form.value.pausa_minutos,
      // Instrução vazia vira null: é assim que o serviço de IA entende
      // "sem instrução customizada, siga a instrução padrão do assistente".
      ler_imagem: form.value.ler_imagem,
      instrucao_imagem: form.value.instrucao_imagem.trim() || null,
      ler_documento: form.value.ler_documento,
      instrucao_documento: form.value.instrucao_documento.trim() || null,
      atendente_telefone: telefones,
      instancia_id: instanciaId.value
    })
    sucesso.value = true
    toast?.success('Configurações do assistente salvas!')
    emit('salvo')
    setTimeout(() => { sucesso.value = false }, 3000)
  } catch (e: any) {
    erro.value = e.message || 'Erro ao salvar'
    toast?.error(erro.value)
  } finally {
    salvando.value = false
  }
}
</script>
