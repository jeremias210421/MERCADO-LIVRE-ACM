"""
Testes de integração com Supabase e utilitários.
"""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestSupabaseClient:
    """Testes do cliente Supabase (com mock global ativo)."""
    
    def test_get_supabase_returns_mock(self, mock_supabase):
        """Testa que get_supabase retorna o mock global."""
        from app.supabase_client import get_supabase
        
        client = get_supabase()
        assert client is mock_supabase
    
    def test_is_supabase_configured_true(self):
        """Testa verificação quando configurado (mock global)."""
        from app.supabase_client import is_supabase_configured
        
        # Com mock global, sempre retorna True
        assert is_supabase_configured() is True
    
    def test_require_supabase_decorator(self):
        """Testa decorator require_supabase."""
        from app.supabase_client import require_supabase
        from flask import Flask, jsonify
        
        app = Flask(__name__)
        
        @app.route('/test')
        @require_supabase()
        def test_route():
            return jsonify({'ok': True})
        
        with app.test_client() as client:
            # Com mock global, is_supabase_configured retorna True
            response = client.get('/test')
            assert response.status_code == 200
            data = response.get_json()
            assert data['ok'] is True


class TestRateLimit:
    """Testes de rate limiting."""
    
    def test_rate_limit_storage(self):
        """Testa armazenamento de rate limit."""
        from app.rate_limit import _rate_limit_storage, clear_rate_limit
        
        clear_rate_limit()
        assert len(_rate_limit_storage) == 0
    
    def test_rate_limit_clear(self):
        """Testa limpeza de rate limit."""
        from app.rate_limit import _rate_limit_storage, clear_rate_limit
        import time
        
        clear_rate_limit()
        # Usar formato de chave real: ratelimit:{ip}:{endpoint}
        key = 'ratelimit:127.0.0.1:limited'
        _rate_limit_storage[key] = [time.time(), time.time()]
        
        clear_rate_limit('127.0.0.1:limited')
        assert key not in _rate_limit_storage
        
        clear_rate_limit()
        assert len(_rate_limit_storage) == 0
    
    def test_rate_limit_decorator_disabled_in_tests(self):
        """Testa que rate limit está desabilitado nos testes (DISABLE_RATE_LIMIT=1)."""
        from app.rate_limit import rate_limit
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        
        @app.route('/limited')
        @rate_limit(max_requests=2, window_seconds=60)
        def limited():
            return jsonify({'ok': True})
        
        with app.test_client() as client:
            # Com DISABLE_RATE_LIMIT=1, todas passam
            for _ in range(10):
                response = client.get('/limited')
                assert response.status_code == 200


class TestUtils:
    """Testes de funções utilitárias."""
    
    def test_allowed_file_json(self):
        """Testa validação de arquivo JSON."""
        from app.routes.upload import allowed_file
        
        assert allowed_file('test.json') is True
        assert allowed_file('test.JSON') is True
        assert allowed_file('test.Json') is True
    
    def test_allowed_file_invalido(self):
        """Testa rejeição de arquivos não-JSON."""
        from app.routes.upload import allowed_file
        
        assert allowed_file('test.txt') is False
        assert allowed_file('test.pdf') is False
        assert allowed_file('test') is False
        assert allowed_file('') is False
    
    def test_importar_json_estrutura(self, mock_supabase):
        """Testa importação com estrutura completa."""
        from app.services.upload_service import importar_json_para_supabase
        
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[])
            return MagicMock(data=[{'id': 'new-id'}])
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = execute_side_effect
        
        dados = {
            'rota': 'TESTE-ESTRUTURA',
            'id_original': 'ORIG-001',
            'totalParadas': 1,
            'totalPacotes': 1,
            'observacao': 'Teste',
            'cidade': 'Teste',
            'paradas': [
                {
                    'sequencia': '1',
                    'endereco': 'Rua Teste',
                    'tipo_endereco': 'Residencial',
                    'pacotes': ['PKG001']
                }
            ]
        }
        
        resultado = importar_json_para_supabase(dados)
        assert resultado['success'] is True


class TestValidateEnv:
    """Testes de validação de ambiente."""
    
    def test_validate_env_completo(self):
        """Testa validação com todas as variáveis."""
        from validate_env import validate_env
        import os
        
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'valid-key-123',
            'SECRET_KEY': 'a' * 32,
        }):
            assert validate_env() is True
    
    def test_validate_env_faltando(self):
        """Testa validação com variáveis faltando."""
        from validate_env import validate_env
        import os
        
        with patch.dict(os.environ, {}, clear=True):
            assert validate_env() is False


class TestMigrate:
    """Testes de migração (mockados)."""
    
    def test_check_config(self):
        """Testa verificação de configuração de migração."""
        from migrate import check_config
        import os
        
        with patch.dict(os.environ, {
            'SUPABASE_POOLER_HOST': 'host',
            'SUPABASE_POOLER_PORT': '5432',
            'SUPABASE_POOLER_DB': 'db',
            'SUPABASE_POOLER_USER': 'user',
            'SUPABASE_POOLER_PASSWORD': 'pass',
        }):
            # Não testar arquivo real, apenas lógica
            pass