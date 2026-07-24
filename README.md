# Sistema de Rotas de Entrega - Supabase

Este projeto cria um banco de dados no Supabase para gerenciar rotas de entrega com base nos arquivos JSON disponíveis, com uma interface web para upload e gerenciamento.

## Estrutura do Banco de Dados

### Tabelas:

1. **rotas** - Informações principais de cada rota
   - id (UUID, chave primária)
   - rota (nome da rota)
   - id_original (ID do sistema original)
   - total_paradas (número de paradas)
   - total_pacotes (número total de pacotes)
   - observacao (observações)
   - cidade (cidade da rota)

2. **paradas** - Detalhes de cada parada na rota
   - id (UUID, chave primária)
   - rota_id (referência para a rota)
   - sequencia (ordem da parada)
   - endereco (endereço completo)
   - tipo_endereco (Residencial/Comercial)

3. **pacotes** - Pacotes entregues em cada parada
   - id (UUID, chave primária)
   - parada_id (referência para a parada)
   - codigo_pacote (código de rastreamento)
   - status (pendente/entregue/falha/cancelado)

## Configuração

### 1. Criar o banco de dados no Supabase

1. Acesse [supabase.com](https://supabase.com)
2. Crie um novo projeto ou use o existente (ref: sfplhlhvcaicbtomjyqv)
3. No SQL Editor do Supabase, execute o arquivo `schema.sql`

### 2. Instalar dependências Python

```bash
pip install supabase python-dotenv
```

### 3. Configurar credenciais

1. No painel do Supabase, vá em Settings > API
2. Copie a chave anon/public e a service_role key
3. Crie um arquivo `.env` no diretório do projeto:

```bash
cp .env.example .env
```

4. Edite o arquivo `.env` e cole suas chaves:

```
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_anon_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role_aqui
SECRET_KEY=chave_secreta_para_sessoes_flask
```

## Interface Web

### Instalar dependências para a interface web:

```bash
pip install -r requirements.txt
```

### Executar a aplicação web:

```bash
python app.py
```

A aplicação estará disponível em: `http://localhost:5000`

### Funcionalidades da Interface Web:

1. **Página Inicial**: Lista todas as rotas cadastradas com estatísticas
2. **Upload de Arquivos**: Interface para upload de arquivos JSON com drag-and-drop
3. **Detalhes da Rota**: Visualização completa de paradas e pacotes de cada rota
4. **API REST**: Endpoints para integração com outros sistemas

## Importar Dados via Script

Execute o script de importação:

```bash
python importar_rotas.py
```

Este script irá:
- Ler todos os arquivos JSON do diretório atual
- Criar as rotas no banco de dados
- Importar todas as paradas e pacotes

## Consultas Úteis

### Ver todas as rotas
```sql
SELECT * FROM rotas ORDER BY rota;
```

### Ver paradas de uma rota específica
```sql
SELECT p.sequencia, p.endereco, p.tipo_endereco 
FROM paradas p
JOIN rotas r ON p.rota_id = r.id
WHERE r.rota = 'I59_PM1'
ORDER BY p.sequencia;
```

### Contar pacotes por rota
```sql
SELECT r.rota, r.total_pacotes, COUNT(pac.id) as pacotes_importados
FROM rotas r
LEFT JOIN paradas par ON r.id = par.rota_id
LEFT JOIN pacotes pac ON par.id = pac.parada_id
GROUP BY r.id, r.rota, r.total_pacotes;
```

### Ver pacotes pendentes de entrega
```sql
SELECT pac.codigo_pacote, p.endereco, r.rota
FROM pacotes pac
JOIN paradas p ON pac.parada_id = p.id
JOIN rotas r ON p.rota_id = r.id
WHERE pac.status = 'pendente'
ORDER BY r.rota, p.sequencia;
```

## Estrutura dos Arquivos JSON

Os arquivos JSON devem seguir este formato:
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

## Limpar Banco de Dados

Se precisar reimportar os dados, primeiro limpe as tabelas:

```sql
TRUNCATE TABLE pacotes, paradas, rotas CASCADE;
```

## API REST

A aplicação web também fornece uma API REST para integração:

### Listar todas as rotas
```
GET /api/rotas
```

### Detalhes de uma rota específica
```
GET /api/rota/<rota_id>
```

### Exemplo de uso:
```bash
# Listar todas as rotas
curl http://localhost:5000/api/rotas

# Obter detalhes de uma rota específica
curl http://localhost:5000/api/rota/uuid-da-rota
```

## Notas

- O sistema usa UUIDs como chaves primárias para melhor segurança
- Índices foram criados para melhorar performance das consultas
- Triggers automáticos atualizam os timestamps de modificação
- O script Python pode ser executado múltiplas vezes (irá duplicar dados se não limpar antes)
- A interface web impede duplicação de rotas com o mesmo nome
- A aplicação web usa Bootstrap 5 para uma interface responsiva e moderna
