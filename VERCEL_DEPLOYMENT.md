# Instruções para Deploy no Vercel

## Configuração de Variáveis de Ambiente

No painel do Vercel, vá em **Settings > Environment Variables** e adicione as seguintes variáveis:

### Variáveis Obrigatórias

- **SUPABASE_URL**: URL do seu projeto Supabase (ex: `https://sfplhlhvcaicbtomjyqv.supabase.co`)
- **SUPABASE_KEY**: Chave `anon/public` do Supabase (obtida em Settings > API)
- **SUPABASE_SERVICE_ROLE_KEY**: Chave `service_role` do Supabase (obtida em Settings > API)
- **SECRET_KEY**: Uma chave secreta aleatória para o Flask (ex: `sua-chave-secreta-aqui`)

## Como Adicionar Variáveis de Ambiente

1. Acesse seu projeto no Vercel
2. Clique em **Settings**
3. Clique em **Environment Variables**
4. Para cada variável:
   - Digite o nome (ex: `SUPABASE_URL`)
   - Digite o valor
   - Clique em **Add**
5. Repita para todas as variáveis
6. **Importante**: Após adicionar as variáveis, você precisa fazer um novo deploy para que elas sejam aplicadas

## Deploy

### Opção 1: Via Git

1. Faça commit das mudanças
2. Push para o GitHub
3. O Vercel fará deploy automático

### Opção 2: Via Vercel CLI

```bash
vercel --prod
```

## Estrutura do Projeto

```
├── api/
│   └── index.py        # Entry point para Vercel
├── templates/          # Arquivos HTML
├── requirements.txt    # Dependências Python
└── vercel.json         # Configuração do Vercel
```

## Solução de Problemas

### Erro: "Template not found"
- Verifique se a pasta `templates` está no diretório raiz do projeto
- O caminho está configurado automaticamente no `api/index.py`

### Erro: "SUPABASE_KEY não encontrada"
- Verifique se as variáveis de ambiente estão configuradas no Vercel
- Faça um novo deploy após adicionar as variáveis

### Erro: "Module not found"
- Verifique se `requirements.txt` está atualizado
- Confirme que todas as dependências estão listadas

## Variáveis de Ambiente vs .env

No desenvolvimento local, use o arquivo `.env`. No Vercel, configure as variáveis no painel do Vercel. O arquivo `.env` não é usado no deploy.
