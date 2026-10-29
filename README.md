# Agzap - Gestão de Clientes

## Instalar esta aplicação para outro cliente

Para subir uma cópia completa e independente (Supabase, Vercel, EasyPanel e OpenAI novos),
siga [INSTALACAO_NOVA_INSTANCIA.md](INSTALACAO_NOVA_INSTANCIA.md). O banco inteiro está em
[supabase/schema_completo.sql](supabase/schema_completo.sql); as variáveis de ambiente saem do `.env` desta instalação, com todos os valores trocados (ver a seção 3.3 do guia).

## Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto com as credenciais do Supabase:

```
NUXT_PUBLIC_SUPABASE_URL=coloque_aqui
NUXT_PUBLIC_SUPABASE_ANON_KEY=coloque_aqui
```

Observações:
- Variáveis iniciadas com `NUXT_PUBLIC_` são expostas no cliente (uso no navegador).
- Nunca coloque a Service Role Key no cliente. Se precisar usá-la, mantenha-a apenas no servidor.

Look at the [Nuxt documentation](https://nuxt.com/docs/getting-started/introduction) to learn more.

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.
