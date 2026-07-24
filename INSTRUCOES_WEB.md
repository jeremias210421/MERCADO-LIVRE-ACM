# Instruções para Configurar a Interface Web

## Passo 1: Configurar o Supabase

1. Acesse [supabase.com](https://supabase.com) e faça login
2. Selecione seu projeto (sfplhlhvcaicbtomjyqv)
3. Vá em **SQL Editor** e execute o conteúdo do arquivo `schema.sql`
4. Vá em **Settings > API** e copie a chave `anon/public`

## Passo 2: Configurar variáveis de ambiente

1. Copie o arquivo de exemplo:
```bash
copy .env.example .env
```

2. Edite o arquivo `.env` e adicione suas credenciais:
```
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_anon_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role_aqui
SECRET_KEY=uma_chave_secreta_aleatoria_para_o_flask
```

## Passo 3: Instalar dependências

```bash
pip install -r requirements.txt
```

## Passo 4: Executar a aplicação

```bash
python app.py
```

## Passo 5: Acessar a interface

Abra seu navegador e acesse: `http://localhost:5000`

## Funcionalidades

### 1. Página Inicial (`/`)
- Lista todas as rotas cadastradas
- Mostra estatísticas (paradas, pacotes)
- Clique em uma rota para ver detalhes

### 2. Upload de Arquivos (`/upload`)
- Interface com drag-and-drop
- Aceita apenas arquivos JSON
- Valida o formato antes de importar
- Impede duplicação de rotas

### 3. Detalhes da Rota (`/rota/<id>`)
- Mostra informações completas da rota
- Lista todas as paradas com sequência
- Exibe todos os pacotes de cada parada
- Estatísticas resumidas

### 4. API REST
- `GET /api/rotas` - Lista todas as rotas em JSON
- `GET /api/rota/<id>` - Detalhes de uma rota específica

## Solução de Problemas

### Erro: "SUPABASE_KEY não encontrada"
- Verifique se o arquivo `.env` existe
- Confirme que a variável SUPABASE_KEY está definida

### Erro: "Conexão com Supabase falhou"
- Verifique se a chave do Supabase está correta
- Confirme se as tabelas foram criadas no SQL Editor

### Erro: "Porta 5000 já em uso"
- Altere a porta no arquivo `app.py` na última linha:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use outra porta
```

### Upload falha
- Verifique se o arquivo JSON é válido
- Confirme que o formato corresponde ao esperado
- Verifique se o nome da rota já existe no banco

## Formato do Arquivo JSON

O arquivo deve seguir este formato:

```json
{
  "rota": "I59_PM1",
  "id": "409704037",
  "totalParadas": 39,
  "totalPacotes": 47,
  "paradas": [
    {
      "sequencia": "01",
      "endereco": "Rua Jj Seabra 69",
      "pacotes": ["47491788377", "47491788603"],
      "tipo_endereco": "Comercial"
    }
  ],
  "observacao": "",
  "cidade": ""
}
```

## Segurança

- Não comite o arquivo `.env` no controle de versão
- Use chaves fortes para SECRET_KEY
- Em produção, desative o modo debug
- Considere usar autenticação para proteção adicional
