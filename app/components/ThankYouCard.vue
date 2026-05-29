<template>
  <div class="min-h-screen bg-background flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-secondary rounded-2xl shadow-xl p-8 text-center border border-border">
      <!-- Ícone de sucesso -->
      <div class="flex items-center justify-center w-20 h-20 mx-auto mb-6 bg-green-100 rounded-full">
        <svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
      </div>

      <!-- Título principal -->
      <h1 class="text-3xl font-bold text-foreground mb-4">
        Obrigado!
      </h1>

      <!-- Subtítulo -->
      <h2 class="text-xl font-bold text-foreground mb-6">
        Bem-vindo ao Sistema Razy
      </h2>

      <!-- Mensagem de agradecimento -->
      <p class="text-base text-gray-300 mb-8 leading-relaxed">
        Agradecemos por se cadastrar no <strong class="text-primary font-semibold">Razy</strong>!
        <br><br>
        Sua conta foi criada com sucesso. Verifique seu email para confirmar 
        sua conta e começar a usar nossa plataforma.
      </p>

      <!-- Informações adicionais -->
      <div class="bg-muted rounded-lg p-4 mb-8 border border-border">
        <h3 class="font-bold text-foreground mb-2 text-base">Próximos passos:</h3>
        <ul class="text-sm text-gray-300 space-y-1">
          <li>✉️ Verifique sua caixa de entrada</li>
          <li>🔗 Clique no link de confirmação</li>
          <li>🚀 Comece a usar o sistema</li>
        </ul>
      </div>


      <!-- Logo ou marca -->
      <div class="mt-8 pt-6 border-t border-border">
        <p class="text-sm font-semibold text-foreground">
          Razy Gestão de Relatórios
        </p>
        <p class="text-xs text-gray-400 mt-1">
          © 2025 Razy - Todos os direitos reservados
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
async function goToLogin() {
  await navigateTo('/login')
}
</script>

