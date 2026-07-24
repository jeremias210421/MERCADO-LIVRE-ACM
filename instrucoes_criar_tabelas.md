# Instruções para Criar Tabelas no Supabase

Como a API do Supabase não permite execução direta de SQL por segurança, você precisa criar as tabelas manualmente no painel do Supabase.

## Passo 1: Acessar o SQL Editor

1. Acesse [https://supabase.com](https://supabase.com)
2. Faça login na sua conta
3. Selecione o projeto: `sfplhlhvcaicbtomjyqv`
4. No menu lateral, clique em **SQL Editor**
5. Clique em **"New query"** para criar uma nova consulta

## Passo 2: Executar o Script SQL

1. Abra o arquivo `schema.sql` neste diretório
2. Copie todo o conteúdo do arquivo
3. Cole no SQL Editor do Supabase
4. Clique no botão **"Run"** (ou pressione Ctrl+Enter)

## Passo 3: Verificar se as tabelas foram criadas

1. No menu lateral, clique em **Table Editor**
2. Você deve ver as tabelas:
   - `rotas`
   - `paradas`
   - `pacotes`

## Passo 4: Importar os dados

Depois de criar as tabelas, execute:

```bash
python importar_direto.py
```

## Script SQL Alternativo

Se preferir, pode executar este SQL diretamente no SQL Editor:

```sql
-- Criação das tabelas para o sistema de rotas de entrega

-- Tabela de rotas
CREATE TABLE IF NOT EXISTS rotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rota VARCHAR(50) NOT NULL UNIQUE,
    id_original VARCHAR(50),
    total_paradas INTEGER,
    total_pacotes INTEGER,
    observacao TEXT,
    cidade VARCHAR(100),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de paradas
CREATE TABLE IF NOT EXISTS paradas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rota_id UUID REFERENCES rotas(id) ON DELETE CASCADE,
    sequencia VARCHAR(10),
    endereco TEXT NOT NULL,
    tipo_endereco VARCHAR(50) CHECK (tipo_endereco IN ('Residencial', 'Comercial')),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de pacotes
CREATE TABLE IF NOT EXISTS pacotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parada_id UUID REFERENCES paradas(id) ON DELETE CASCADE,
    codigo_pacote VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente' CHECK (status IN ('pendente', 'entregue', 'falha', 'cancelado')),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_paradas_rota ON paradas(rota_id);
CREATE INDEX IF NOT EXISTS idx_pacotes_parada ON pacotes(parada_id);
CREATE INDEX IF NOT EXISTS idx_pacotes_codigo ON pacotes(codigo_pacote);
CREATE INDEX IF NOT EXISTS idx_rotas_nome ON rotas(rota);

-- Função para atualizar timestamp
CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para atualizar timestamp
DROP TRIGGER IF EXISTS trigger_rotas_atualizado ON rotas;
CREATE TRIGGER trigger_rotas_atualizado
    BEFORE UPDATE ON rotas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();

DROP TRIGGER IF EXISTS trigger_paradas_atualizado ON paradas;
CREATE TRIGGER trigger_paradas_atualizado
    BEFORE UPDATE ON paradas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();

DROP TRIGGER IF EXISTS trigger_pacotes_atualizado ON pacotes;
CREATE TRIGGER trigger_pacotes_atualizado
    BEFORE UPDATE ON pacotes
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();
```

## Após criar as tabelas

Execute o script de importação:

```bash
python importar_direto.py
```

Isso irá importar todos os 11 arquivos JSON para o banco de dados.
