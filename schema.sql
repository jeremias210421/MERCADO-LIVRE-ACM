-- ============================================================
-- Schema completo para Bipador ACM - Ibotirama
-- Data: 2026-08-06
-- ============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABELAS PRINCIPAIS
-- ============================================================

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
    codigo_pacote VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente' CHECK (status IN ('pendente', 'entregue', 'falha', 'cancelado')),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de motoristas
CREATE TABLE IF NOT EXISTS motoristas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(150) NOT NULL,
    telefone VARCHAR(20),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de scans (entregas realizadas)
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rota_id UUID REFERENCES rotas(id) ON DELETE SET NULL,
    motorista_id UUID REFERENCES motoristas(id) ON DELETE SET NULL,
    codigo_pacote VARCHAR(100) NOT NULL,
    formato VARCHAR(50),
    endereco TEXT,
    is_valid BOOLEAN,
    escaneado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de vínculo rota-motorista
CREATE TABLE IF NOT EXISTS rota_motoristas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rota_id UUID NOT NULL REFERENCES rotas(id) ON DELETE CASCADE,
    motorista_id UUID NOT NULL REFERENCES motoristas(id) ON DELETE CASCADE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(rota_id, motorista_id)
);

-- Tabela de scans do galpão (conferência)
CREATE TABLE IF NOT EXISTS galpao_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_pacote VARCHAR(100) NOT NULL,
    rota_id UUID REFERENCES rotas(id) ON DELETE SET NULL,
    motorista_id UUID REFERENCES motoristas(id) ON DELETE SET NULL,
    endereco TEXT,
    escaneado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usuario_id TEXT,
    sessao_id TEXT
);

-- Tabela de pacotes pendentes
CREATE TABLE IF NOT EXISTS pacotes_pendentes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_pacote VARCHAR(100) NOT NULL,
    rota_original_id UUID REFERENCES rotas(id) ON DELETE SET NULL,
    motorista_id UUID REFERENCES motoristas(id) ON DELETE SET NULL,
    endereco TEXT,
    data_pendencia DATE NOT NULL DEFAULT CURRENT_DATE,
    data_entrega_prevista DATE NOT NULL DEFAULT (CURRENT_DATE + INTERVAL '1 day'),
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'entregue', 'cancelado')),
    escaneado_em TIMESTAMP WITH TIME ZONE,
    galpao_scan_id UUID REFERENCES galpao_scans(id) ON DELETE SET NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_paradas_rota ON paradas(rota_id);
CREATE INDEX IF NOT EXISTS idx_pacotes_parada ON pacotes(parada_id);
CREATE INDEX IF NOT EXISTS idx_pacotes_codigo ON pacotes(codigo_pacote);
CREATE INDEX IF NOT EXISTS idx_rotas_nome ON rotas(rota);

CREATE INDEX IF NOT EXISTS idx_scans_motorista ON scans(motorista_id);
CREATE INDEX IF NOT EXISTS idx_scans_rota ON scans(rota_id);
CREATE INDEX IF NOT EXISTS idx_scans_data ON scans(escaneado_em);
CREATE INDEX IF NOT EXISTS idx_scans_pacote ON scans(codigo_pacote);

CREATE INDEX IF NOT EXISTS idx_rota_motoristas_rota ON rota_motoristas(rota_id);
CREATE INDEX IF NOT EXISTS idx_rota_motoristas_motorista ON rota_motoristas(motorista_id);

CREATE INDEX IF NOT EXISTS idx_galpao_scans_data ON galpao_scans(escaneado_em);
CREATE INDEX IF NOT EXISTS idx_galpao_scans_rota ON galpao_scans(rota_id);
CREATE INDEX IF NOT EXISTS idx_galpao_scans_motorista ON galpao_scans(motorista_id);
CREATE INDEX IF NOT EXISTS idx_galpao_scans_sessao ON galpao_scans(sessao_id);

CREATE INDEX IF NOT EXISTS idx_pendentes_motorista ON pacotes_pendentes(motorista_id, status);
CREATE INDEX IF NOT EXISTS idx_pendentes_data ON pacotes_pendentes(data_entrega_prevista, status);
CREATE INDEX IF NOT EXISTS idx_pendentes_codigo ON pacotes_pendentes(codigo_pacote);

-- ============================================================
-- CONSTRAINTS E REGRAS DE NEGÓCIO
-- ============================================================

-- Constraint UNIQUE: um mesmo pacote não pode ser escaneado duas vezes na mesma rota no mesmo dia
-- Criamos função imutável para extrair data do timestamp
CREATE OR REPLACE FUNCTION date_of_timestamp(ts TIMESTAMPTZ)
RETURNS DATE
LANGUAGE SQL
IMMUTABLE
AS $$ SELECT ts::date $$;

ALTER TABLE scans DROP CONSTRAINT IF EXISTS uq_scans_rota_pacote_data;
DROP INDEX IF EXISTS uq_scans_rota_pacote_data;

CREATE UNIQUE INDEX uq_scans_rota_pacote_data 
    ON scans (rota_id, codigo_pacote, date_of_timestamp(escaneado_em));

-- ============================================================
-- TRIGGERS PARA ATUALIZAR TIMESTAMP
-- ============================================================
CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

DROP TRIGGER IF EXISTS trigger_motoristas_atualizado ON motoristas;
CREATE TRIGGER trigger_motoristas_atualizado
    BEFORE UPDATE ON motoristas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();

-- ============================================================
-- HABILITAR REALTIME
-- ============================================================
DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE scans;
EXCEPTION WHEN duplicate_object THEN
    -- tabela já está na publication
    NULL;
END $$;

DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE galpao_scans;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE pacotes_pendentes;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- ============================================================
-- FUNÇÕES AUXILIARES
-- ============================================================

-- Função para buscar motoristas de uma rota
CREATE OR REPLACE FUNCTION buscar_motoristas_rota(p_rota_id UUID)
RETURNS TABLE (
    motorista_id UUID,
    nome VARCHAR(150),
    telefone VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT m.id, m.nome, m.telefone
    FROM motoristas m
    INNER JOIN rota_motoristas rm ON rm.motorista_id = m.id
    WHERE rm.rota_id = p_rota_id
    ORDER BY m.nome;
END;
$$ LANGUAGE plpgsql;

-- Função para buscar scans de uma rota no dia
CREATE OR REPLACE FUNCTION buscar_scans_rota_dia(p_rota_id UUID, p_data DATE DEFAULT CURRENT_DATE)
RETURNS TABLE (
    scan_id UUID,
    codigo_pacote VARCHAR(100),
    motorista_nome VARCHAR(150),
    endereco_scan TEXT,
    escaneado_em TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.codigo_pacote,
        m.nome,
        s.endereco,
        s.escaneado_em
    FROM scans s
    LEFT JOIN motoristas m ON s.motorista_id = m.id
    WHERE s.rota_id = p_rota_id
      AND DATE(s.escaneado_em) = p_data
    ORDER BY s.escaneado_em DESC;
END;
$$ LANGUAGE plpgsql;

-- Função para identificar automaticamente um pacote bipado no galpão
CREATE OR REPLACE FUNCTION identificar_pacote(p_codigo VARCHAR(100))
RETURNS TABLE (
    rota_id UUID,
    rota_nome TEXT,
    motorista_id UUID,
    motorista_nome VARCHAR(150),
    endereco TEXT,
    encontrado BOOLEAN
) AS $$
DECLARE
    v_parada_id UUID;
    v_rota_id UUID;
    v_rota_nome TEXT;
    v_motorista_id UUID;
    v_motorista_nome VARCHAR(150);
    v_endereco TEXT;
BEGIN
    -- Buscar o pacote na tabela pacotes
    SELECT pa.parada_id INTO v_parada_id
    FROM pacotes pa
    WHERE pa.codigo_pacote = p_codigo
    LIMIT 1;

    IF v_parada_id IS NULL THEN
        RETURN QUERY SELECT NULL::UUID, NULL::TEXT, NULL::UUID, NULL::VARCHAR(150), NULL::TEXT, false;
        RETURN;
    END IF;

    -- Buscar a rota da parada
    SELECT par.rota_id, par.endereco INTO v_rota_id, v_endereco
    FROM paradas par
    WHERE par.id = v_parada_id
    LIMIT 1;

    -- Buscar nome da rota
    SELECT r.rota::TEXT INTO v_rota_nome
    FROM rotas r
    WHERE r.id = v_rota_id
    LIMIT 1;

    -- Buscar o motorista designado para esta rota (mais recente)
    SELECT rm.motorista_id INTO v_motorista_id
    FROM rota_motoristas rm
    WHERE rm.rota_id = v_rota_id
    ORDER BY rm.criado_em DESC
    LIMIT 1;

    -- Buscar nome do motorista
    IF v_motorista_id IS NOT NULL THEN
        SELECT m.nome INTO v_motorista_nome
        FROM motoristas m
        WHERE m.id = v_motorista_id
        LIMIT 1;
    END IF;

    RETURN QUERY SELECT v_rota_id, v_rota_nome, v_motorista_id, v_motorista_nome, v_endereco, true;
END;
$$ LANGUAGE plpgsql;

-- Função para gerar pendências diárias a partir dos scans do galpão
CREATE OR REPLACE FUNCTION gerar_pendencias_diarias(p_sessao_id TEXT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_data_pendencia DATE := CURRENT_DATE;
    v_data_entrega DATE := CURRENT_DATE + INTERVAL '1 day';
BEGIN
    INSERT INTO pacotes_pendentes (
        codigo_pacote, rota_original_id, motorista_id, endereco,
        data_pendencia, data_entrega_prevista, status, galpao_scan_id
    )
    SELECT
        gs.codigo_pacote,
        gs.rota_id,
        gs.motorista_id,
        gs.endereco,
        v_data_pendencia,
        v_data_entrega,
        'pendente',
        gs.id
    FROM galpao_scans gs
    WHERE DATE(gs.escaneado_em) = v_data_pendencia
      AND (p_sessao_id IS NULL OR gs.sessao_id = p_sessao_id)
      AND NOT EXISTS (
          SELECT 1 FROM pacotes_pendentes pp
          WHERE pp.codigo_pacote = gs.codigo_pacote
            AND pp.data_pendencia = v_data_pendencia
            AND pp.status = 'pendente'
      )
    RETURNING id;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Função para buscar resumo do dashboard
CREATE OR REPLACE FUNCTION dashboard_resumo_diario(p_data DATE DEFAULT CURRENT_DATE)
RETURNS TABLE (
    entregadores_ativos BIGINT,
    pacotes_entregues BIGINT,
    pacotes_pendentes BIGINT,
    taxa_entrega NUMERIC
) AS $$
BEGIN
    SELECT COUNT(DISTINCT s.motorista_id) INTO entregadores_ativos
    FROM scans s
    WHERE DATE(s.escaneado_em) = p_data AND s.motorista_id IS NOT NULL;

    SELECT COUNT(*) INTO pacotes_entregues
    FROM scans s
    WHERE DATE(s.escaneado_em) = p_data;

    SELECT COUNT(*) INTO pacotes_pendentes
    FROM pacotes_pendentes pp
    WHERE pp.data_entrega_prevista <= p_data AND pp.status = 'pendente';

    IF (pacotes_entregues + pacotes_pendentes) > 0 THEN
        taxa_entrega := ROUND(
            (pacotes_entregues::NUMERIC / (pacotes_entregues + pacotes_pendentes)) * 100, 1
        );
    ELSE
        taxa_entrega := 0;
    END IF;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Função para buscar progresso de cada entregador no dia
CREATE OR REPLACE FUNCTION progresso_entregadores_diario(p_data DATE DEFAULT CURRENT_DATE)
RETURNS TABLE (
    motorista_id UUID,
    motorista_nome VARCHAR(150),
    motorista_telefone VARCHAR(20),
    rota_nome TEXT,
    total_entregues BIGINT,
    total_pendentes BIGINT,
    total_pacotes BIGINT,
    percentual NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id AS motorista_id,
        m.nome AS motorista_nome,
        m.telefone AS motorista_telefone,
        COALESCE(r.rota::TEXT, 'Sem rota') AS rota_nome,
        COUNT(DISTINCT s.id) AS total_entregues,
        COALESCE(pp.total_pend, 0) AS total_pendentes,
        COALESCE(r.total_pacotes, 0)::BIGINT AS total_pacotes,
        CASE
            WHEN COALESCE(r.total_pacotes, 0) > 0
            THEN ROUND((COUNT(DISTINCT s.id)::NUMERIC / r.total_pacotes) * 100, 1)
            ELSE 0
        END AS percentual
    FROM motoristas m
    LEFT JOIN scans s ON s.motorista_id = m.id AND DATE(s.escaneado_em) = p_data
    LEFT JOIN rota_motoristas rm ON rm.motorista_id = m.id
    LEFT JOIN rotas r ON r.id = rm.rota_id
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS total_pend
        FROM pacotes_pendentes pp
        WHERE pp.motorista_id = m.id
          AND pp.data_entrega_prevista <= p_data
          AND pp.status = 'pendente'
    ) pp ON true
    WHERE m.id IN (
        SELECT DISTINCT s2.motorista_id
        FROM scans s2
        WHERE DATE(s2.escaneado_em) = p_data AND s2.motorista_id IS NOT NULL
    )
    GROUP BY m.id, m.nome, m.telefone, r.rota, r.total_pacotes, pp.total_pend
    ORDER BY m.nome;
END;
$$ LANGUAGE plpgsql;