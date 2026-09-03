"""
Testes do Dashboard.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestDashboard:
    """Testes para rotas do dashboard."""
    
    def test_dashboard_index(self, client, mock_supabase):
        """Testa carregamento do dashboard."""
        # Configurar mocks
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{'id': 'scan-1', 'motorista_id': 'm1', 'codigo_pacote': 'PKG001'}],
            count=1
        )
        
        response = client.get('/')
        assert response.status_code == 200
        assert b'Dashboard' in response.data or b'dashboard' in response.data.lower()
    
    def test_dashboard_stats_structure(self, client, mock_supabase):
        """Testa estrutura das stats no dashboard."""
        # Mock para scans de hoje
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[{'id': 's1', 'motorista_id': 'm1'}], count=1),  # scans
            MagicMock(data=[], count=0),  # pendentes
            MagicMock(data=[{'id': 'm1', 'nome': 'João', 'telefone': '123'}]),  # motoristas
            MagicMock(data=[]),  # rota_motoristas
            MagicMock(data=[]),  # rotas
        ]
        
        response = client.get('/')
        assert response.status_code == 200
    
    def test_dashboard_with_no_supabase(self, client):
        """Testa dashboard sem Supabase configurado."""
        with patch('app.routes.dashboard.is_supabase_configured', return_value=False):
            response = client.get('/')
            assert response.status_code == 200