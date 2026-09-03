-- ============================================================
-- Migracao: Melhorias do Bipador ACM
-- Data: 2026-07-29
-- Descricao: Tabela rota_motoristas, constraint UNIQUE em scans,
--            e habilitacao do Supabase Realtime
-- ============================================================

-- 1. Tabela de vinculo entre rotas e motoristas
CREATE TABLE IF NOT EXISTS rota_motoristas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rota_id UUID NOT NULL REFERENCES rotas(id) ON DELETE CASCADE,
    motorista_id UUID NOT NULL REFERENCES motoristas(id) ON DELETE CASCADE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(rota_id, motorista_id)
);

CREATE INDEX IF NOT EXISTS idx_rota_motoristas_rota ON rota_motoristas(rota_id);
CREATE INDEX IF NOT EXISTS idx_rota_motoristas_motorista ON rota_motoristas(motorista_id);

-- 2. Constraint UNIQUE na tabela scans para evitar duplicidade
--    Um mesmo pacote nao pode ser escaneado duas vezes na mesma rota no mesmo dia
ALTER TABLE scans 
    ADD CONSTRAINT uq_scans_rota_pacote_data 
    UNIQUE (rota_id, codigo_pacote, escaneado_em);

-- 3. Habilitar Realtime para a tabela scans
--    (necessario para sync bidirecional entre dispositivos)
ALTER PUBLICATION supabase_realtime ADD TABLE scans;

-- 4. Funcao para buscar motoristas de uma rota
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

-- 5. Funcao para buscar scans de uma rota no dia
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
