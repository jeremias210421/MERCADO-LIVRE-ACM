import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do Supabase
SUPABASE_URL = "https://sfplhlhvcaicbtomjyqv.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def importar_arquivo_json(caminho_arquivo):
    """Importa dados de um arquivo JSON para o Supabase"""
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
    diretorio = os.getcwd()
    
    # Encontrar todos os arquivos JSON
    arquivos_json = [f for f in os.listdir(diretorio) if f.endswith('.json')]
    
    print(f"Encontrados {len(arquivos_json)} arquivos JSON")
    
    # Importar cada arquivo
    for arquivo in arquivos_json:
        caminho_completo = os.path.join(diretorio, arquivo)
        print(f"\nImportando {arquivo}...")
        try:
            importar_arquivo_json(caminho_completo)
        except Exception as e:
            print(f"Erro ao importar {arquivo}: {e}")
    
    print("\nImportação concluída!")

if __name__ == "__main__":
    main()
