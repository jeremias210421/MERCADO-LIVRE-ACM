-- Criação das tabelas para o sistema de rotas de entrega

-- Tabela de rotas
CREATE TABLE rotas (
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
CREATE TABLE paradas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rota_id UUID REFERENCES rotas(id) ON DELETE CASCADE,
    sequencia VARCHAR(10),
    endereco TEXT NOT NULL,
    tipo_endereco VARCHAR(50) CHECK (tipo_endereco IN ('Residencial', 'Comercial')),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de pacotes
CREATE TABLE pacotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parada_id UUID REFERENCES paradas(id) ON DELETE CASCADE,
    codigo_pacote VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente' CHECK (status IN ('pendente', 'entregue', 'falha', 'cancelado')),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhorar performance
CREATE INDEX idx_paradas_rota ON paradas(rota_id);
CREATE INDEX idx_pacotes_parada ON pacotes(parada_id);
CREATE INDEX idx_pacotes_codigo ON pacotes(codigo_pacote);
CREATE INDEX idx_rotas_nome ON rotas(rota);

-- Trigger para atualizar timestamp
CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_rotas_atualizado
    BEFORE UPDATE ON rotas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();

CREATE TRIGGER trigger_paradas_atualizado
    BEFORE UPDATE ON paradas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();

CREATE TRIGGER trigger_pacotes_atualizado
    BEFORE UPDATE ON pacotes
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();
