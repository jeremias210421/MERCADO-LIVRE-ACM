# Testes Automatizados - Bipador ACM

## Configuração de Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-cov pytest-mock httpx

# Executar todos os testes
pytest -v

# Executar com coverage
pytest --cov=app --cov-report=html
```

## Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── test_health.py           # Health checks
├── test_dashboard.py        # Dashboard routes
├── test_entregadores.py     # Entregadores CRUD
├── test_galpao.py           # Conferencia galpao
├── test_pendentes.py        # Pendencias
├── test_rotas.py            # Rotas
├── test_upload.py           # Upload JSON
├── test_api.py              # APIs Android
├── test_supabase.py         # Integração Supabase
└── test_utils.py            # Utilitários
```