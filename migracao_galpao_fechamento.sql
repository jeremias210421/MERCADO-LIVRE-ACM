-- ============================================================
-- Migracao: Fechamento de Galpao como ferramenta separada
-- Rode UMA VEZ no SQL Editor do Supabase (idempotente).
-- Resolve:
--  1) rotas.session_date inexistente (codigo espera, schema.sql nao tem)
--  2) rotas.rota UNIQUE impede repetir o mesmo nome em dias diferentes
--  3) pacotes sem colunas de contato/descricao (scan do galpao mostra '-')
--  4) RPCs identificar_pacote / gerar_pendencias_diarias ausentes
-- ============================================================

-- 1) rotas.session_date (data da sessao em SP, YYYY-MM-DD)
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS session_date DATE;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS id_original VARCHAR(50);
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_rotas_session ON rotas(session_date);
CREATE INDEX IF NOT EXISTS idx_rotas_nome ON rotas(rota);

-- Backfill: quem nasceu sem session_date herda a data de criado_em
UPDATE rotas SET session_date = (criado_em AT TIME ZONE 'America/Sao_Paulo')::date
WHERE session_date IS NULL AND criado_em IS NOT NULL;

-- 2) Permitir o mesmo nome de rota em dias diferentes.
-- O schema antigo tem UNIQUE(rota), que quebra o upload diario
-- (I46_PM1 de hoje x I46_PM1 de amanha) e forca gambiarra tipo
-- criar rota "Fechamento de Galpao" todo dia.
DO $$
BEGIN
    -- remove a constraint UNIQUE(rota) se existir (nome varia por banco)
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'rotas'::regclass AND contype = 'u'
          AND array_length(conkey, 1) = 1
          AND (SELECT attname FROM pg_attribute
               WHERE attrelid = 'rotas'::regclass AND attnum = conkey[1]) = 'rota'
    ) THEN
        ALTER TABLE rotas DROP CONSTRAINT rotas_rota_key;
    END IF;
EXCEPTION WHEN undefined_object THEN
    NULL;
END $$;

-- UNIQUE(rota, session_date): mesmo nome pode repetir em outro dia, mas nao duplica no dia
CREATE UNIQUE INDEX IF NOT EXISTS uq_rotas_nome_sessao ON rotas(rota, session_date);

-- 3) pacotes: contato do comprador + descricao (o galpao e o upload esperam)
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS nome_comprador TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS telefone VARCHAR(30);
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS descricao_produto TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS valor_produto TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS status_looker TEXT;
CREATE INDEX IF NOT EXISTS idx_pacotes_codigo ON pacotes(codigo_pacote);
CREATE INDEX IF NOT EXISTS idx_pacotes_cidade ON pacotes(cidade);

-- 4) scans: colunas texto que o app celular grava (o codigo novo le session_date/route)
ALTER TABLE scans ADD COLUMN IF NOT EXISTS code TEXT;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS route TEXT;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS operator_name TEXT;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS session_date DATE;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS scanned_at TIMESTAMPTZ;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS endereco TEXT;
CREATE INDEX IF NOT EXISTS idx_scans_session ON scans(session_date);

-- Backfill best-effort do legado para o novo (nao sobrescreve o que ja tem)
UPDATE scans SET code = codigo_pacote WHERE code IS NULL AND codigo_pacote IS NOT NULL;
UPDATE scans SET session_date = (escaneado_em AT TIME ZONE 'America/Sao_Paulo')::date
WHERE session_date IS NULL AND escaneado_em IS NOT NULL;

-- 5) galpao_scans: garantir coluna de sessao
ALTER TABLE galpao_scans ADD COLUMN IF NOT EXISTS sessao_id TEXT;
ALTER TABLE galpao_scans ADD COLUMN IF NOT EXISTS endereco TEXT;
CREATE INDEX IF NOT EXISTS idx_galpao_scans_sessao ON galpao_scans(sessao_id);

-- 6) RPC identificar_pacote (o /galpao/scan depende dela; sem ela todo bipe da "nao encontrado")
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
    SELECT pa.parada_id INTO v_parada_id
    FROM pacotes pa
    WHERE pa.codigo_pacote = p_codigo
    LIMIT 1;

    IF v_parada_id IS NULL THEN
        RETURN QUERY SELECT NULL::UUID, NULL::TEXT, NULL::UUID, NULL::VARCHAR(150), NULL::TEXT, false;
        RETURN;
    END IF;

    SELECT par.rota_id, par.endereco INTO v_rota_id, v_endereco
    FROM paradas par WHERE par.id = v_parada_id LIMIT 1;

    SELECT r.rota::TEXT INTO v_rota_nome FROM rotas r WHERE r.id = v_rota_id LIMIT 1;

    SELECT rm.motorista_id INTO v_motorista_id
    FROM rota_motoristas rm WHERE rm.rota_id = v_rota_id
    ORDER BY rm.criado_em DESC LIMIT 1;

    IF v_motorista_id IS NOT NULL THEN
        SELECT m.nome INTO v_motorista_nome FROM motoristas m WHERE m.id = v_motorista_id LIMIT 1;
    END IF;

    RETURN QUERY SELECT v_rota_id, v_rota_nome, v_motorista_id, v_motorista_nome, v_endereco, true;
END;
$$ LANGUAGE plpgsql;

-- 7) RPC gerar_pendencias_diarias (o /galpao/finalizar depende dela)
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
        gs.codigo_pacote, gs.rota_id, gs.motorista_id, gs.endereco,
        v_data_pendencia, v_data_entrega, 'pendente', gs.id
    FROM galpao_scans gs
    WHERE DATE(gs.escaneado_em) = v_data_pendencia
      AND (p_sessao_id IS NULL OR gs.sessao_id = p_sessao_id)
      -- SEM exigir motorista/rota: fechamento funciona mesmo sem designar
      AND NOT EXISTS (
          SELECT 1 FROM pacotes_pendentes pp
          WHERE pp.codigo_pacote = gs.codigo_pacote
            AND pp.data_pendencia = v_data_pendencia
            AND pp.status = 'pendente'
      );
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
