"""
Configuração compartilhada para testes pytest.
Patches globais aplicados ANTES de qualquer importação do app.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar variáveis de ambiente para testes
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'test-key')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing-only-32chars')
os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('FLASK_DEBUG', '0')

# Desabilitar rate limiting nos testes
os.environ['DISABLE_RATE_LIMIT'] = '1'

# ============================================================
# PATCHES GLOBAIS - Aplicados ANTES de importar app
# ============================================================

# Criar mock global do Supabase
_mock_supabase_client = MagicMock()
_mock_table = MagicMock()
_mock_supabase_client.table.return_value = _mock_table

# Select chain
_mock_select = MagicMock()
_mock_table.select.return_value = _mock_select
_mock_select.eq.return_value = _mock_select
_mock_select.gte.return_value = _mock_select
_mock_select.lte.return_value = _mock_select
_mock_select.order.return_value = _mock_select
_mock_select.limit.return_value = _mock_select
_mock_select.single.return_value = _mock_select
_mock_select.execute.return_value = MagicMock(data=[], count=0)

# Insert chain
_mock_insert = MagicMock()
_mock_table.insert.return_value = _mock_insert
_mock_insert.execute.return_value = MagicMock(data=[{'id': 'test-id'}])

# Update chain
_mock_update = MagicMock()
_mock_table.update.return_value = _mock_update
_mock_update.eq.return_value = _mock_update
_mock_update.execute.return_value = MagicMock(data=[])

# Delete chain
_mock_delete = MagicMock()
_mock_table.delete.return_value = _mock_delete
_mock_delete.eq.return_value = _mock_delete
_mock_delete.execute.return_value = MagicMock(data=[])

# Upsert chain
_mock_upsert = MagicMock()
_mock_table.upsert.return_value = _mock_upsert
_mock_upsert.execute.return_value = MagicMock(data=[])

# RPC
_mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(data=0)

# Aplicar patches nos SERVICES (que são usados pelas routes)
_global_patches = [
    patch('app.services.dashboard_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.services.entregador_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.services.galpao_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.services.pendentes_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.services.rota_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.services.upload_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.services.api_service.get_supabase', return_value=_mock_supabase_client),
    patch('app.supabase_client.get_supabase', return_value=_mock_supabase_client),
    patch('app.supabase_client.is_supabase_configured', return_value=True),
]

# Iniciar patches ANTES de importar app
for p in _global_patches:
    p.start()

# Importar app DEPOIS dos patches
from app import create_app

import pytest


def pytest_sessionfinish(session, exitstatus):
    """Limpar patches no final da sessão."""
    for p in _global_patches:
        p.stop()


@pytest.fixture(scope='function')
def app():
    """Cria instância da aplicação para testes."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def client(app):
    """Cliente de teste Flask."""
    return app.test_client()


@pytest.fixture(scope='function')
def mock_supabase():
    """Retorna o mock global do Supabase para configuração nos testes."""
    # Apenas reconfigurar execute return values para cada teste
    # NÃO usar reset_mock() pois quebra as chains (eq, gte, etc.)
    # Limpar side_effect se houver
    _mock_select.execute.side_effect = None
    _mock_insert.execute.side_effect = None
    _mock_update.execute.side_effect = None
    _mock_delete.execute.side_effect = None
    _mock_upsert.execute.side_effect = None
    _mock_supabase_client.rpc.return_value.execute.side_effect = None

    _mock_select.execute.return_value = MagicMock(data=[], count=0)
    _mock_insert.execute.return_value = MagicMock(data=[{'id': 'test-id'}])
    _mock_update.execute.return_value = MagicMock(data=[])
    _mock_delete.execute.return_value = MagicMock(data=[])
    _mock_upsert.execute.return_value = MagicMock(data=[])
    _mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(data=0)

    yield _mock_supabase_client


@pytest.fixture(scope='function')
def sample_rota():
    """Dados de exemplo para rota."""
    return {
        'id': 'rota-123',
        'rota': 'ROTA-001',
        'id_original': 'I46_PM1',
        'total_paradas': 10,
        'total_pacotes': 50,
        'observacao': 'Rota teste',
        'cidade': 'Ibotirama',
        'criado_em': '2026-01-01T00:00:00Z'
    }


@pytest.fixture(scope='function')
def sample_motorista():
    """Dados de exemplo para motorista."""
    return {
        'id': 'motorista-123',
        'nome': 'João Silva',
        'telefone': '(77) 99999-9999',
        'criado_em': '2026-01-01T00:00:00Z'
    }


@pytest.fixture(scope='function')
def sample_scan():
    """Dados de exemplo para scan."""
    return {
        'id': 'scan-123',
        'rota_id': 'rota-123',
        'motorista_id': 'motorista-123',
        'codigo_pacote': 'PKG001',
        'formato': 'QR_CODE',
        'endereco': 'Rua Teste, 123',
        'is_valid': True,
        'escaneado_em': '2026-01-01T10:00:00Z'
    }


@pytest.fixture(scope='function')
def sample_pendente():
    """Dados de exemplo para pendente."""
    return {
        'id': 'pendente-123',
        'codigo_pacote': 'PKG001',
        'rota_original_id': 'rota-123',
        'motorista_id': 'motorista-123',
        'endereco': 'Rua Teste, 123',
        'data_pendencia': '2026-01-01',
        'data_entrega_prevista': '2026-01-02',
        'status': 'pendente',
        'criado_em': '2026-01-01T10:00:00Z'
    }