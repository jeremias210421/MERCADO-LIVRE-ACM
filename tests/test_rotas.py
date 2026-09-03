"""
Testes de Rotas.
"""
import pytest
from unittest.mock import MagicMock


class TestRotas:
    """Testes para gestão de rotas."""
    
    def test_listar_rotas(self, client, mock_supabase, sample_rota, sample_motorista):
        """Testa listagem de rotas."""
        # The service layer calls get_rotas_with_motoristas which makes multiple separate calls:
        # 1. rotas table select
        # 2. motoristas table select
        # 3. rota_motoristas table select
        # 4. scans table select (count) for each rota
        
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[sample_rota])  # rotas
            elif call_count[0] == 2:
                return MagicMock(data=[sample_motorista])  # motoristas
            elif call_count[0] == 3:
                return MagicMock(data=[{'rota_id': 'rota-123', 'motorista_id': 'motorista-123'}])  # rota_motoristas
            elif call_count[0] >= 4:
                return MagicMock(count=10)  # scans hoje
            return MagicMock(data=[])
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        
        response = client.get('/rotas')
        assert response.status_code == 200
        assert b'Rota' in response.data or b'rota' in response.data.lower()
        assert sample_rota['rota'].encode() in response.data
    
    def test_listar_rotas_vazio(self, client, mock_supabase):
        """Testa listagem vazia."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        
        response = client.get('/rotas')
        assert response.status_code == 200
    
    def test_designar_motorista(self, client, mock_supabase):
        """Testa designação de motorista."""
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=[{'rota_id': 'rota-123', 'motorista_id': 'motorista-123'}]
        )
        
        response = client.post('/rotas/rota-123/designar', data={
            'motorista_id': 'motorista-123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_designar_motorista_sem_selecao(self, client):
        """Testa designação sem selecionar motorista."""
        response = client.post('/rotas/rota-123/designar', data={
            'motorista_id': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        # Deve mostrar erro/warning


class TestRotasProgresso:
    """Testes de cálculo de progresso."""
    
    def test_progresso_calculo(self, client, mock_supabase, sample_rota, sample_motorista):
        """Testa cálculo de percentual de progresso."""
        # Rota com 100 pacotes, 50 entregues = 50%
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[{**sample_rota, 'total_pacotes': 100}])  # rotas
            elif call_count[0] == 2:
                return MagicMock(data=[sample_motorista])  # motoristas
            elif call_count[0] == 3:
                return MagicMock(data=[{'rota_id': 'rota-123', 'motorista_id': 'motorista-123'}])  # vinculos
            elif call_count[0] >= 4:
                return MagicMock(count=50)  # scans hoje (50 entregues)
            return MagicMock(data=[])
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        
        response = client.get('/rotas')
        assert response.status_code == 200
        # Verifica se percentual aparece (50%)
        assert b'50' in response.data or b'50.0' in response.data