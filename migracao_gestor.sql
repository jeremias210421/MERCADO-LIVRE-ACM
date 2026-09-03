-- ============================================================
-- Migracao: Painel do Gestor - Conferencia de Pendentes
-- Data: 2026-07-29
-- Descricao: Tabelas galpao_scans e pacotes_pendentes,
--            funcoes de identificacao e geracao de pendencias
-- ============================================================

-- 1. Tabela de scans do galpao (quando o gestor bipa pacotes restantes)
CREATE TABLE IF NOT EXISTS galpao_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_pacote VARCHAR(100) NOT NULL,
    rota_id UUID REFERENCES rotas(id) ON DELETE SET NULL,
    motorista_id UUID REFERENCES motoristas(id) ON DELETE SET NULL,
    endereco TEXT,
    escaneado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usuario_id TEXT,
    sessao_id TEXT  -- agrupa scans da mesma sessao de conferencia
);

CREATE INDEX IF NOT EXISTS idx_galpao_scans_data ON galpao_scans(escaneado_em);
CREATE INDEX IF NOT EXISTS idx_galpao_scans_rota ON galpao_scans(rota_id);
CREATE INDEX IF NOT EXISTS idx_galpao_scans_motorista ON galpao_scans(motorista_id);
CREATE INDEX IF NOT EXISTS idx_galpao_scans_sessao ON galpao_scans(sessao_id);

-- 2. Tabela de pacotes pendentes (gerada a partir dos scans do galpao)
CREATE TABLE IF NOT EXISTS pacotes_pendentes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_pacote VARCHAR(100) NOT NULL,
    rota_original_id UUID REFERENCES rotas(id) ON DELETE SET NULL,
    motorista_id UUID REFERENCES motoristas(id) ON DELETE SET NULL,
    endereco TEXT,
    data_pendencia DATE NOT NULL DEFAULT CURRENT_DATE,
    data_entrega_prevista DATE NOT NULL DEFAULT (CURRENT_DATE + INTERVAL '1 day'),
    status VARCHAR(20) DEFAULT 'pendente',  -- pendente | entregue | cancelado
    escaneado_em TIMESTAMP WITH TIME ZONE,  -- quando foi entregue pelo motorista
    galpao_scan_id UUID REFERENCES galpao_scans(id) ON DELETE SET NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pendentes_motorista ON pacotes_pendentes(motorista_id, status);
CREATE INDEX IF NOT EXISTS idx_pendentes_data ON pacotes_pendentes(data_entrega_prevista, status);
CREATE INDEX IF NOT EXISTS idx_pendentes_codigo ON pacotes_pendentes(codigo_pacote);

-- 3. Habilitar Realtime para as novas tabelas
ALTER PUBLICATION supabase_realtime ADD TABLE galpao_scans;
ALTER PUBLICATION supabase_realtime ADD TABLE pacotes_pendentes;

-- 4. Funcao para identificar automaticamente um pacote bipado no galpao
-- Busca em pacotes -> paradas -> rotas e o motorista via rota_motoristas
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
        -- Pacote nao encontrado na base de rotas
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

-- 5. Funcao para gerar pendencias diarias a partir dos scans do galpao
-- Retorna o numero de pendencias criadas
CREATE OR REPLACE FUNCTION gerar_pendencias_diarias(p_sessao_id TEXT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_data_pendencia DATE := CURRENT_DATE;
    v_data_entrega DATE := CURRENT_DATE + INTERVAL '1 day';
BEGIN
    -- Para cada scan do galpao de hoje que ainda nao tem pendencia correspondente
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

-- 6. Funcao para buscar resumo do dashboard (usado pela API e pelo painel)
CREATE OR REPLACE FUNCTION dashboard_resumo_diario(p_data DATE DEFAULT CURRENT_DATE)
RETURNS TABLE (
    entregadores_ativos BIGINT,
    pacotes_entregues BIGINT,
    pacotes_pendentes BIGINT,
    taxa_entrega NUMERIC
) AS $$
BEGIN
    -- Entregadores que fizeram scan hoje
    SELECT COUNT(DISTINCT s.motorista_id) INTO entregadores_ativos
    FROM scans s
    WHERE DATE(s.escaneado_em) = p_data AND s.motorista_id IS NOT NULL;

    -- Total de pacotes entregues hoje
    SELECT COUNT(*) INTO pacotes_entregues
    FROM scans s
    WHERE DATE(s.escaneado_em) = p_data;

    -- Total de pendentes (nao entregues)
    SELECT COUNT(*) INTO pacotes_pendentes
    FROM pacotes_pendentes pp
    WHERE pp.data_entrega_prevista <= p_data AND pp.status = 'pendente';

    -- Taxa de entrega (pendentes entregues / total esperado)
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

-- 7. Funcao para buscar progresso de cada entregador no dia
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
