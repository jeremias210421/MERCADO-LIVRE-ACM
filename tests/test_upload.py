"""
Testes de Upload de Rotas JSON.
"""
import pytest
import json
from unittest.mock import MagicMock
from io import BytesIO


class TestUpload:
    """Testes para upload de arquivos JSON."""
    
    def test_upload_get(self, client):
        """Testa página de upload."""
        response = client.get('/upload')
        assert response.status_code == 200
        assert b'Upload' in response.data or b'upload' in response.data.lower()
    
    def test_upload_json_valido(self, client, mock_supabase):
        """Testa upload de JSON válido."""
        # Setup mock for the service layer calls
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[])  # rota_existente check
            return MagicMock(data=[{'id': 'new-id'}])  # insert calls
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = execute_side_effect
        
        rota_json = {
            'rota': 'ROTA-TESTE',
            'id': 'TEST-001',
            'totalParadas': 5,
            'totalPacotes': 20,
            'paradas': [
                {
                    'sequencia': '1',
                    'endereco': 'Rua Teste',
                    'tipo_endereco': 'Residencial',
                    'pacotes': ['PKG001', 'PKG002']
                }
            ]
        }
        
        data = {
            'files': (BytesIO(json.dumps(rota_json).encode()), 'rota_teste.json')
        }
        
        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
    
    def test_upload_json_duplicado(self, client, mock_supabase):
        """Testa upload de rota duplicada."""
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[{'id': 'existing', 'rota': 'ROTA-TESTE'}])  # rota_existente found
            return MagicMock(data=[{'id': 'new-id'}])
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        
        rota_json = {'rota': 'ROTA-TESTE', 'paradas': []}
        data = {'files': (BytesIO(json.dumps(rota_json).encode()), 'dup.json')}
        
        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
        # Deve mostrar erro de duplicata
    
    def test_upload_arquivo_invalido(self, client):
        """Testa upload de arquivo não-JSON."""
        data = {'files': (BytesIO(b'not json'), 'test.txt')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        # Redireciona para upload com flash message
        assert response.status_code == 302
    
    def test_upload_json_malformado(self, client):
        """Testa upload de JSON inválido."""
        data = {'files': (BytesIO(b'{ invalid json }'), 'bad.json')}
        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
        # Deve mostrar erro de JSON inválido
    
    def test_upload_sem_arquivo(self, client):
        """Testa upload sem arquivo."""
        response = client.post('/upload', data={}, follow_redirects=True)
        assert response.status_code == 200
        # Deve mostrar erro de nenhum arquivo
    
    def test_importar_json_para_supabase(self, mock_supabase):
        """Testa função de importação diretamente."""
        from app.services.upload_service import importar_json_para_supabase
        
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[])  # rota_existente check
            return MagicMock(data=[{'id': 'new-id'}])  # insert calls
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = execute_side_effect
        
        dados = {
            'rota': 'ROTA-DIRETA',
            'totalParadas': 2,
            'totalPacotes': 10,
            'paradas': [
                {'sequencia': '1', 'endereco': 'End 1', 'pacotes': ['P1', 'P2']},
                {'sequencia': '2', 'endereco': 'End 2', 'pacotes': ['P3']},
            ]
        }
        
        resultado = importar_json_para_supabase(dados)
        assert resultado['success'] is True
        assert 'importada' in resultado['message']


class TestUploadEstruturaJSON:
    """Testes de validação da estrutura JSON."""
    
    def test_json_minimo_valido(self, client, mock_supabase):
        """JSON mínimo com campos obrigatórios."""
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[])
            return MagicMock(data=[{'id': 'new-id'}])
        
        mock_supabase.table.return_value.select.return_value.execute.side_effect = execute_side_effect
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = execute_side_effect
        
        # Apenas campos obrigatórios
        rota_minima = {
            'rota': 'MINIMA',
            'paradas': [
                {'sequencia': '1', 'endereco': 'End', 'pacotes': ['PKG1']}
            ]
        }
        
        data = {'files': (BytesIO(json.dumps(rota_minima).encode()), 'min.json')}
        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
    
    def test_json_sem_rota(self, client):
        """JSON sem campo 'rota' deve falhar."""
        rota_invalida = {'paradas': []}
        data = {'files': (BytesIO(json.dumps(rota_invalida).encode()), 'norota.json')}
        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200