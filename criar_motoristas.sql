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
