"""
Testes de Health Checks.
"""
import pytest


class TestHealthChecks:
    """Testes para endpoints de health check."""
    
    def test_health_check(self, client):
        """Testa health check básico."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'bipador-acm'
    
    def test_readiness_check(self, client, mock_supabase):
        """Testa readiness check com Supabase configurado."""
        response = client.get('/health/ready')
        # Pode ser 200 ou 503 dependendo do mock
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert 'status' in data
        assert 'checks' in data
    
    def test_liveness_check(self, client):
        """Testa liveness check."""
        response = client.get('/health/live')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'alive'


class TestErrorHandlers:
    """Testes para handlers de erro."""
    
    def test_404_json(self, client):
        """Testa 404 em endpoint API."""
        response = client.get('/api/inexistente')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_405_method_not_allowed(self, client):
        """Testa método não permitido."""
        response = client.post('/health')
        assert response.status_code == 405