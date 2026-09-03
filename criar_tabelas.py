import os
from dotenv import load_dotenv
import httpx
import json

load_dotenv()

# Configurações do Supabase (via variáveis de ambiente)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

# Script SQL para criar as tabelas
SQL_SCRIPT = """
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

-- Tabela de motoristas
CREATE TABLE IF NOT EXISTS motoristas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(150) NOT NULL,
    telefone VARCHAR(20),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trigger_motoristas_atualizado ON motoristas;
CREATE TRIGGER trigger_motoristas_atualizado
    BEFORE UPDATE ON motoristas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();
"""

def criar_tabelas():
    """Executa o script SQL no Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Usar o endpoint de SQL do Supabase
    url = f"{SUPABASE_URL}/rest/v1/sql"
    
    payload = {
        "query": SQL_SCRIPT
    }
    
    try:
        response = httpx.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print("SUCCESS: Tabelas criadas com sucesso!")
            return True
        else:
            print(f"ERROR: Falha ao criar tabelas. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR: Erro ao executar SQL: {e}")
        return False

if __name__ == "__main__":
    print("Criando tabelas no Supabase...")
    print("=" * 50)
    
    if criar_tabelas():
        print("=" * 50)
        print("As tabelas foram criadas com sucesso!")
        print("Agora voce pode executar: python importar_direto.py")
    else:
        print("=" * 50)
        print("Houve um erro ao criar as tabelas.")
        print("Por favor, execute o script schema.sql manualmente no SQL Editor do Supabase.")
