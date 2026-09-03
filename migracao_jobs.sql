-- Fila de trabalhos: a pagina no Vercel pede, o agente no PC executa
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'executando', 'concluido', 'erro')),
    payload JSONB DEFAULT '{}'::jsonb,
    log TEXT DEFAULT '',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, criado_em);

DROP TRIGGER IF EXISTS trigger_jobs_atualizado ON jobs;
CREATE TRIGGER trigger_jobs_atualizado
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();
