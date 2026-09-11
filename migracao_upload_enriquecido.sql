-- ============================================================
-- Upload enriquecido: contato + descricao por ID
-- Rode UMA VEZ no SQL Editor do Supabase (idempotente).
-- ============================================================

-- 1) Colunas de contato no pacote (se ainda não existem)
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS nome_comprador TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS telefone VARCHAR(30);
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);

-- 2) Colunas de descricao do produto (Looker) no pacote
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS descricao_produto TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS valor_produto TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS status_looker TEXT;

-- 3) Índices úteis
CREATE INDEX IF NOT EXISTS idx_pacotes_telefone ON pacotes(telefone);
CREATE INDEX IF NOT EXISTS idx_pacotes_cidade ON pacotes(cidade);
CREATE INDEX IF NOT EXISTS idx_pacotes_codigo ON pacotes(codigo_pacote);

-- 4) Tabela de descrições (espelho do descricao_map.json / Looker)
CREATE TABLE IF NOT EXISTS product_descriptions (
    package_id TEXT PRIMARY KEY,
    descricao TEXT,
    valor TEXT,
    status_looker TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5) Sync: preenche pacotes a partir de product_descriptions (só onde falta/difere)
CREATE OR REPLACE FUNCTION sync_pacotes_descriptions()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE pacotes p
    SET
        descricao_produto = pd.descricao,
        valor_produto = pd.valor,
        status_looker = pd.status_looker
    FROM product_descriptions pd
    WHERE p.codigo_pacote = pd.package_id
      AND (
        p.descricao_produto IS DISTINCT FROM pd.descricao
        OR p.valor_produto IS DISTINCT FROM pd.valor
        OR p.status_looker IS DISTINCT FROM pd.status_looker
      );
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;

-- 6) Popular product_descriptions em lote (chamado pelo popular_descriptions.py)
CREATE OR REPLACE FUNCTION upsert_product_descriptions(descriptions JSONB)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO product_descriptions (package_id, descricao, valor, status_looker, updated_at)
    SELECT
        (item->>'package_id')::TEXT,
        item->>'descricao',
        item->>'valor',
        item->>'status',
        NOW()
    FROM jsonb_array_elements(descriptions) AS item
    ON CONFLICT (package_id) DO UPDATE SET
        descricao = EXCLUDED.descricao,
        valor = EXCLUDED.valor,
        status_looker = EXCLUDED.status_looker,
        updated_at = NOW();
END;
$$;
