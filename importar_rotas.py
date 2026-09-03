#!/usr/bin/env python3
"""
Script legado para importar rotas - mantido para compatibilidade.
Uso: python importar_rotas.py
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do Supabase (via variáveis de ambiente)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: Variáveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar definidas no .env")
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("ERRO: Biblioteca 'supabase' não instalada. Execute: pip install supabase")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def importar_arquivo_json(caminho_arquivo):
    """Importa dados de um arquivo JSON para o Supabase."""
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    # Inserir rota
    rota_data = {
        'rota': dados['rota'],
        'id_original': dados['id'],
        'total_paradas': dados['totalParadas'],
        'total_pacotes': dados['totalPacotes'],
        'observacao': dados.get('observacao', ''),
        'cidade': dados.get('cidade', '')
    }
    
    rota_result = supabase.table('rotas').insert(rota_data).execute()
    rota_id = rota_result.data[0]['id']
    
    print(f"Rota {dados['rota']} inserida com ID: {rota_id}")
    
    # Inserir paradas e pacotes
    for parada in dados['paradas']:
        parada_data = {
            'rota_id': rota_id,
            'sequencia': parada['sequencia'],
            'endereco': parada['endereco'],
            'tipo_endereco': parada['tipo_endereco']
        }
        
        parada_result = supabase.table('paradas').insert(parada_data).execute()
        parada_id = parada_result.data[0]['id']
        
        # Inserir pacotes para esta parada
        for codigo_pacote in parada['pacotes']:
            pacote_data = {
                'parada_id': parada_id,
                'codigo_pacote': codigo_pacote
            }
            supabase.table('pacotes').insert(pacote_data).execute()
    
    print(f"Paradas e pacotes importados para rota {dados['rota']}")


def main():
    # Diretório atual
    diretorio = Path.cwd()
    
    # Encontrar todos os arquivos JSON
    arquivos_json = [f for f in diretorio.iterdir() if f.suffix == '.json']
    
    print(f"Encontrados {len(arquivos_json)} arquivos JSON")
    
    # Importar cada arquivo
    for arquivo in arquivos_json:
        caminho_completo = arquivo
        print(f"\nImportando {arquivo.name}...")
        try:
            importar_arquivo_json(caminho_completo)
        except Exception as e:
            print(f"Erro ao importar {arquivo.name}: {e}")
    
    print("\nImportação concluída!")


if __name__ == "__main__":
    main()