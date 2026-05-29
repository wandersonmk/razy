// Traduções de erros do Supabase para português
export const errorTranslations: Record<string, string> = {
  // Erros de autenticação
  'Invalid login credentials': 'Credenciais de login inválidas',
  'Email not confirmed': 'Email não confirmado',
  'Invalid email': 'Email inválido',
  'Password is too weak': 'Senha muito fraca',
  'User not found': 'Usuário não encontrado',
  'Email already registered': 'Email já cadastrado',
  'User already registered': 'Usuário já cadastrado',
  'Invalid password': 'Senha inválida',
  'Email address not authorized': 'Endereço de email não autorizado',
  'Password does not meet requirements': 'Senha não atende aos requisitos',
  'Invalid phone number': 'Número de telefone inválido',
  'Phone number already registered': 'Número de telefone já cadastrado',
  'Invalid verification code': 'Código de verificação inválido',
  'Verification code expired': 'Código de verificação expirado',
  'Too many requests': 'Muitas tentativas. Tente novamente mais tarde',
  'Rate limit exceeded': 'Limite de tentativas excedido',
  'Account locked': 'Conta bloqueada',
  'Account disabled': 'Conta desabilitada',
  'Token expired': 'Token expirado',
  'Invalid token': 'Token inválido',
  'Session expired': 'Sessão expirada',
  'Unauthorized': 'Não autorizado',
  'Access denied': 'Acesso negado',
  'Forbidden': 'Proibido',
  
  // Erros de rede
  'Network error': 'Erro de conexão',
  'Connection failed': 'Falha na conexão',
  'Timeout': 'Tempo esgotado',
  'Server error': 'Erro do servidor',
  'Service unavailable': 'Serviço indisponível',
  'Internal server error': 'Erro interno do servidor',
  
  // Erros genéricos
  'Something went wrong': 'Algo deu errado',
  'Unknown error': 'Erro desconhecido',
  'Validation error': 'Erro de validação',
  'Required field': 'Campo obrigatório',
  'Invalid format': 'Formato inválido',
  'Field too long': 'Campo muito longo',
  'Field too short': 'Campo muito curto',
}

export function translateError(error: string | Error): string {
  const errorMessage = typeof error === 'string' ? error : error.message
  
  // Procura por traduções exatas primeiro
  if (errorTranslations[errorMessage]) {
    return errorTranslations[errorMessage]
  }
  
  // Procura por palavras-chave no erro
  const lowercaseError = errorMessage.toLowerCase()
  
  if (lowercaseError.includes('invalid login') || lowercaseError.includes('invalid credentials')) {
    return 'Email ou senha incorretos'
  }
  
  if (lowercaseError.includes('email') && lowercaseError.includes('already')) {
    return 'Este email já está em uso'
  }
  
  if (lowercaseError.includes('password') && lowercaseError.includes('weak')) {
    return 'Senha muito fraca. Use pelo menos 6 caracteres'
  }
  
  if (lowercaseError.includes('network') || lowercaseError.includes('connection')) {
    return 'Problema de conexão. Verifique sua internet'
  }
  
  if (lowercaseError.includes('rate limit') || lowercaseError.includes('too many')) {
    return 'Muitas tentativas. Aguarde um momento'
  }
  
  // Se não encontrar tradução específica, retorna mensagem genérica
  return 'Ocorreu um erro inesperado. Tente novamente'
}
