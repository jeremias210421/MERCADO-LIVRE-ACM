"""
Testes das APIs (para app Android).
"""
import pytest
import json
from unittest.mock import MagicMock
from datetime import date


class TestAPI:
    """Testes para endpoints de API."""
    
    def test_api_rotas(self, client, mock_supabase, sample_rota):
        """Testa API de listagem de rotas."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[sample_rota]
        )
        
        response = client.get('/api/rotas')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['rota'] == sample_rota['rota']
    
    def test_api_rota_detalhes(self, client, mock_supabase, sample_rota):
        """Testa API de detalhes da rota."""
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[sample_rota]),  # rota
            MagicMock(data=[{'id': 'parada-1', 'sequencia': '1', 'endereco': 'End'}]), # paradas
            MagicMock(data=[{'codigo_pacote': 'PKG001'}]), # pacotes
        ]
        
        response = client.get(f'/api/rota/{sample_rota["id"]}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'rota' in data
        assert 'paradas' in data
    
    def test_api_rota_nao_encontrada(self, client, mock_supabase):
        """Testa API rota não encontrada."""
        # Configurar mock para retornar rota não encontrada
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        response = client.get('/api/rota/inexistente')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_api_motoristas(self, client, mock_supabase, sample_motorista):
        """Testa API de motoristas."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[sample_motorista]
        )
        
        response = client.get('/api/motoristas')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert data[0]['nome'] == sample_motorista['nome']
    
    def test_api_upload_scans(self, client, mock_supabase):
        """Testa API de upload de scans."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': 'scan-1'}, {'id': 'scan-2'}]
        )
        
        scans = [
            {'codigo_pacote': 'PKG001', 'rota_id': 'rota-1', 'motorista_id': 'm1', 'escaneado_em': '2026-01-01T10:00:00Z'},
            {'codigo_pacote': 'PKG002', 'rota_id': 'rota-1', 'motorista_id': 'm1', 'escaneado_em': '2026-01-01T10:05:00Z'},
        ]
        
        response = client.post('/api/scans', json=scans)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] == 2
    
    def test_api_upload_scans_invalido(self, client):
        """Testa API upload com dados inválidos."""
        response = client.post('/api/scans', json='not a list')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_api_pendentes(self, client, mock_supabase, sample_pendente):
        """Testa API de pendências."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[sample_pendente]
        )
        
        response = client.get('/api/pendentes')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_api_pendentes_com_filtro(self, client, mock_supabase):
        """Testa API pendências com filtro de motorista."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        response = client.get('/api/pendentes?motorista_id=m1&data=2026-01-01')
        assert response.status_code == 200
    
    def test_api_dashboard(self, client, mock_supabase):
        """Testa API dashboard."""
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[{'id': 's1', 'motorista_id': 'm1'}]),  # scans
            MagicMock(data=[{'id': 'p1'}]),  # pendentes
        ]
        
        response = client.get('/api/dashboard')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entregadores_ativos' in data
        assert 'pacotes_entregues' in data
        assert 'pacotes_pendentes' in data
        assert 'data' in data
    
    def test_api_entregador_stats(self, client, mock_supabase):
        """Testa API stats do entregador."""
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(count=100),  # total geral
            MagicMock(count=10),   # total hoje
            MagicMock(count=3),    # pendentes
        ]
        
        response = client.get('/api/entregadores/motorista-123/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_geral'] == 100
        assert data['total_hoje'] == 10
        assert data['pendentes'] == 3


class TestAPIRateLimit:
    """Testes de rate limiting (simulado)."""
    
    def test_api_aceita_requisicoes_normais(self, client, mock_supabase):
        """APIs aceitam requisições normais."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        for _ in range(5):
            response = client.get('/api/rotas')
            assert response.status_code == 200
    
    def test_api_content_type_json(self, client, mock_supabase):
        """APIs retornam JSON."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        response = client.get('/api/rotas')
        assert response.content_type == 'application/json'