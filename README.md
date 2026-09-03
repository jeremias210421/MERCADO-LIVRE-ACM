# Bipador ACM - Ibotirama

Sistema de gestão de rotas, motoristas e entregas para a ACM Ibotirama.

## 📋 Funcionalidades

- **Dashboard**: Visão geral de entregas, entregadores ativos e taxa de entrega
- **Gestão de Entregadores**: CRUD completo de motoristas
- **Gestão de Rotas**: Upload de rotas via JSON, designação de motoristas
- **Conferência do Galpão**: Scanner para conferir pacotes restantes
- **Pendências**: Acompanhamento de pacotes não entregues
- **APIs**: Endpoints para integração com app Android

## 🚀 Instalação

### Pré-requisitos

- Python 3.11+
- Conta no Supabase

### Configuração

1. Clone o repositório:
```bash
git clone <repo-url>
cd BIPADOR-ACM
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite .env com suas credenciais do Supabase
```

5. Execute as migrações no Supabase (SQL Editor):
- Execute o conteúdo de `schema.sql` no SQL Editor do Supabase

6. Importe as rotas (opcional):
```bash
python importar_direto.py
```

7. Execute a aplicação:
```bash
python run.py
```

A aplicação estará disponível em `http://localhost:5000`

## 📁 Estrutura do Projeto

```
BIPADOR-ACM/
├── app/                    # Aplicação Flask (novo padrão)
│   ├── __init__.py         # Factory da aplicação
│   ├── supabase_client.py  # Cliente Supabase centralizado
│   └── routes/             # Blueprints organizados por funcionalidade
│       ├── dashboard.py
│       ├── entregadores.py
│       ├── galpao.py
│       ├── pendentes.py
│       ├── rotas.py
│       ├── upload.py
│       └── api.py
├── templates/              # Templates Jinja2
│   ├── base.html
│   ├── dashboard.html
│   ├── entregadores.html
│   ├── entregador_detalhe.html
│   ├── entregador_form.html
│   ├── galpao.html
│   ├── pendentes.html
│   ├── rotas.html
│   └── upload.html
├── acm-ibotirama/          # App Android (React + Capacitor)
├── schema.sql              # Schema completo do banco
├── importar_direto.py      # Script de importação de rotas
├── run.py                  # Ponto de entrada
├── requirements.txt        # Dependências Python
├── vercel.json             # Configuração Vercel
└── .env.example            # Exemplo de variáveis de ambiente
```

## 🗄️ Banco de Dados (Supabase)

### Tabelas Principais

- `rotas` - Rotas de entrega
- `paradas` - Paradas de cada rota
- `pacotes` - Pacotes de cada parada
- `motoristas` - Entregadores cadastrados
- `scans` - Entregas realizadas (bipagens)
- `rota_motoristas` - Vínculo rota-motorista
- `galpao_scans` - Conferência do galpão
- `pacotes_pendentes` - Pacotes não entregues

### Funções SQL

- `identificar_pacote(codigo)` - Identifica rota/motorista de um pacote
- `gerar_pendencias_diarias(sessao_id)` - Gera pendências do galpão
- `dashboard_resumo_diario(data)` - Resumo para dashboard
- `progresso_entregadores_diario(data)` - Progresso por entregador

## 📱 App Android

O app Android está em `acm-ibotirama/` e usa:
- React + TypeScript + Vite
- Capacitor para build nativo
- html5-qrcode para scanner
- Supabase para sincronização

### Build do APK

```bash
cd acm-ibotirama
npm install
npm run build
npx cap sync android
npx cap build android
```

## 🔧 Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `SUPABASE_URL` | URL do projeto Supabase | Sim |
| `SUPABASE_SERVICE_ROLE_KEY` | Service Role Key do Supabase | Sim |
| `SECRET_KEY` | Chave secreta do Flask | Sim |
| `FLASK_ENV` | Ambiente (development/production) | Não |
| `FLASK_DEBUG` | Debug mode (1/0) | Não |

## 📦 Deploy no Vercel

1. Conecte o repositório no Vercel
2. Configure as variáveis de ambiente no painel do Vercel
3. O deploy é automático via `vercel.json`

## 🐛 Solução de Problemas

### Erro de conexão com Supabase
- Verifique se `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` estão corretos
- Confirme se o IP está liberado no Supabase (Settings > API)

### Tabelas não encontradas
- Execute o `schema.sql` no SQL Editor do Supabase

### Erro de constraint UNIQUE em scans
- A constraint `uq_scans_rota_pacote_data` impede bipar o mesmo pacote na mesma rota no mesmo dia
- Para testar, use códigos diferentes ou dias diferentes

## 📝 Licença

Projeto interno ACM Ibotirama.