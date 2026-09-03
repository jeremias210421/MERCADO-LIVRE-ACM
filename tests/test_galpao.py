"""
Testes do Galpão (Conferência).
"""
import pytest
from unittest.mock import MagicMock
import json


class TestGalpao:
    """Testes para conferência do galpão."""
    
    def test_conferencia_galpao_get(self, client):
        """Testa página de conferência."""
        response = client.get('/galpao')
        assert response.status_code == 200
        assert b'Confer' in response.data or b'galp' in response.data.lower()
        # Verifica se tem sessao_id
        assert b'sessao' in response.data.lower() or b'session' in response.data.lower()
    
    def test_galpao_scan_valido(self, client, mock_supabase):
        """Testa scan de pacote encontrado."""
        # Mock da função identificar_pacote
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{
                'encontrado': True,
                'rota_id': 'rota-123',
                'rota_nome': 'ROTA-001',
                'motorista_id': 'motorista-123',
                'motorista_nome': 'João Silva',
                'endereco': 'Rua Teste, 123'
            }]
        )
        # Mock motoristas select single
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={'nome': 'João Silva'}
        )
        # Mock rotas select single
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={'rota': 'ROTA-001'}
        )
        # Mock galpao_scans insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': 'scan-1'}])
        
        response = client.post('/galpao/scan', json={
            'codigo_pacote': 'PKG001',
            'sessao_id': 'abc12345'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['encontrado'] is True
        assert data['rota_nome'] == 'ROTA-001'
    
    def test_galpao_scan_nao_encontrado(self, client, mock_supabase):
        """Testa scan de pacote não encontrado."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{'encontrado': False}]
        )
        
        response = client.post('/galpao/scan', json={
            'codigo_pacote': 'INEXISTENTE',
            'sessao_id': 'abc12345'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['encontrado'] is False
    
    def test_galpao_scan_codigo_vazio(self, client):
        """Testa scan com código vazio."""
        response = client.post('/galpao/scan', json={
            'codigo_pacote': '',
            'sessao_id': 'abc12345'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_galpao_finalizar(self, client, mock_supabase):
        """Testa finalização da conferência."""
        # Mock RPC gerar_pendencias_diarias
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=5)
        
        # Mock galpao_scans select chain - the service calls:
        # supabase.table('galpao_scans').select('codigo_pacote, motorista_id').eq('sessao_id', sessao_id).execute()
        mock_galpao_scans_table = MagicMock()
        mock_galpao_scans_select = MagicMock()
        mock_galpao_scans_eq = MagicMock()
        mock_galpao_scans_table.select.return_value = mock_galpao_scans_select
        mock_galpao_scans_select.eq.return_value = mock_galpao_scans_eq
        mock_galpao_scans_eq.execute.return_value = MagicMock(
            data=[
                {'codigo_pacote': 'PKG001', 'motorista_id': 'm1'},
                {'codigo_pacote': 'PKG002', 'motorista_id': 'm1'},
            ]
        )
        
        # Mock motoristas table for name lookup
        mock_motoristas_table = MagicMock()
        mock_motoristas_select = MagicMock()
        mock_motoristas_eq = MagicMock()
        mock_motoristas_single = MagicMock()
        mock_motoristas_table.select.return_value = mock_motoristas_select
        mock_motoristas_select.eq.return_value = mock_motoristas_eq
        mock_motoristas_eq.single.return_value = mock_motoristas_single
        mock_motoristas_single.execute.return_value = MagicMock(
            data={'nome': 'João Silva'}
        )
        
        # Configure table() to return different mocks based on table name
        def table_side_effect(table_name):
            if table_name == 'galpao_scans':
                return mock_galpao_scans_table
            elif table_name == 'motoristas':
                return mock_motoristas_table
            return MagicMock()
        
        mock_supabase.table.side_effect = table_side_effect
        
        response = client.post('/galpao/finalizar', json={
            'sessao_id': 'abc12345'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['pendencias_criadas'] == 5
        assert 'por_motorista' in data


class TestGalpaoValidation:
    """Testes de validação do galpão."""
    
    def test_scan_requer_json(self, client):
        """Scan requer JSON."""
        response = client.post('/galpao/scan', data='codigo=PKG001', content_type='application/x-www-form-urlencoded')
        assert response.status_code in (400, 415)
    
    def test_finalizar_requer_sessao(self, client, mock_supabase):
        """Finalizar aceita sessao_id vazio."""
        # Mock RPC para retornar 0 pendências
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=0)
        # Mock galpao_scans vazio
        mock_galpao_scans_table = MagicMock()
        mock_galpao_scans_select = MagicMock()
        mock_galpao_scans_eq = MagicMock()
        mock_galpao_scans_table.select.return_value = mock_galpao_scans_select
        mock_galpao_scans_select.eq.return_value = mock_galpao_scans_eq
        mock_galpao_scans_eq.execute.return_value = MagicMock(data=[])
        
        def table_side_effect(table_name):
            if table_name == 'galpao_scans':
                return mock_galpao_scans_table
            return MagicMock()
        
        mock_supabase.table.side_effect = table_side_effect
        
        response = client.post('/galpao/finalizar', json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['pendencias_criadas'] == 0