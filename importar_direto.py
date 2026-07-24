import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configurações do Supabase (usando variáveis de ambiente)
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

# Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def importar_arquivo_json(caminho_arquivo):
    """Importa dados de um arquivo JSON para o Supabase"""
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    print(f"Processando rota: {dados['rota']}")
    
    # Verificar se rota já existe
    rota_existente = supabase.table('rotas').select('*').eq('rota', dados['rota']).execute()
    
    if rota_existente.data:
        print(f"  ATENCAO: Rota {dados['rota']} ja existe, pulando...")
        return {'success': False, 'message': f"Rota {dados['rota']} ja existe"}
    
    # Inserir rota
    rota_data = {
        'rota': dados['rota'],
        'id_original': dados.get('id', ''),
        'total_paradas': dados.get('totalParadas', 0),
        'total_pacotes': dados.get('totalPacotes', 0),
        'observacao': dados.get('observacao', ''),
        'cidade': dados.get('cidade', '')
    }
    
    try:
        rota_result = supabase.table('rotas').insert(rota_data).execute()
        rota_id = rota_result.data[0]['id']
        print(f"  OK: Rota inserida com ID: {rota_id}")
    except Exception as e:
        print(f"  ERRO: Erro ao inserir rota: {e}")
        return {'success': False, 'message': f"Erro ao inserir rota: {e}"}
    
    # Inserir paradas e pacotes
    total_paradas_inseridas = 0
    total_pacotes_inseridos = 0
    
    for parada in dados.get('paradas', []):
        parada_data = {
            'rota_id': rota_id,
            'sequencia': parada.get('sequencia', ''),
            'endereco': parada.get('endereco', ''),
            'tipo_endereco': parada.get('tipo_endereco', 'Residencial')
        }
        
        try:
            parada_result = supabase.table('paradas').insert(parada_data).execute()
            parada_id = parada_result.data[0]['id']
            total_paradas_inseridas += 1
            
            # Inserir pacotes para esta parada
            for codigo_pacote in parada.get('pacotes', []):
                pacote_data = {
                    'parada_id': parada_id,
                    'codigo_pacote': codigo_pacote
                }
                supabase.table('pacotes').insert(pacote_data).execute()
                total_pacotes_inseridos += 1
                
        except Exception as e:
            print(f"  ERRO: Erro ao inserir parada {parada.get('sequencia', '?')}: {e}")
            continue
    
    print(f"  OK: {total_paradas_inseridas} paradas e {total_pacotes_inseridos} pacotes importados")
    return {'success': True, 'message': f"Rota {dados['rota']} importada com sucesso"}

def main():
    # Diretório atual
    diretorio = os.getcwd()
    
    # Encontrar todos os arquivos JSON
    arquivos_json = [f for f in os.listdir(diretorio) if f.endswith('.json') and f.startswith(('I', 'J', 'K'))]
    
    print(f"Encontrados {len(arquivos_json)} arquivos JSON para importar")
    print("=" * 50)
    
    # Importar cada arquivo
    sucesso = 0
    falha = 0
    
    for arquivo in sorted(arquivos_json):
        caminho_completo = os.path.join(diretorio, arquivo)
        print(f"\nProcessando: {arquivo}")
        try:
            resultado = importar_arquivo_json(caminho_completo)
            if resultado['success']:
                sucesso += 1
            else:
                falha += 1
        except Exception as e:
            print(f"  ERRO: Erro ao processar {arquivo}: {e}")
            falha += 1
    
    print("\n" + "=" * 50)
    print(f"RESUMO:")
    print(f"  Sucesso: {sucesso}")
    print(f"  Falhas: {falha}")
    print(f"  Total processados: {sucesso + falha}")
    print("=" * 50)

if __name__ == "__main__":
    main()
