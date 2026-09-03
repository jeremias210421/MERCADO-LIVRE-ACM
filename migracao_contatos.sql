-- Contatos do comprador por pacote (dados do 3pl)
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS nome_comprador TEXT;
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS telefone VARCHAR(30);
CREATE INDEX IF NOT EXISTS idx_pacotes_telefone ON pacotes(telefone);
-- Cidade do pacote (para achar pacotes de Ibotirama em rotas compartilhadas)
ALTER TABLE pacotes ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_pacotes_cidade ON pacotes(cidade);
