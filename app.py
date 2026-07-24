from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configurar template folder para funcionar no Vercel
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_padrao")

# Configurações do Supabase (usando variáveis de ambiente)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")

# Debug logging
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY: {SUPABASE_KEY[:10] if SUPABASE_KEY else None}...")

# Inicializar Supabase apenas se variáveis estiverem configuradas
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase conectado com sucesso")
    except Exception as e:
        print(f"Erro ao conectar ao Supabase: {e}")
else:
    print("AVISO: Variáveis de ambiente do Supabase não configuradas")

# Configuração de upload
ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def importar_json_para_supabase(dados_json):
    """Importa dados JSON para o Supabase"""
    try:
        # Verificar se rota já existe
        rota_existente = supabase.table('rotas').select('*').eq('rota', dados_json['rota']).execute()
        
        if rota_existente.data:
            return {'success': False, 'message': f"Rota {dados_json['rota']} já existe no banco de dados"}
        
        # Inserir rota
        rota_data = {
            'rota': dados_json['rota'],
            'id_original': dados_json.get('id', ''),
            'total_paradas': dados_json.get('totalParadas', 0),
            'total_pacotes': dados_json.get('totalPacotes', 0),
            'observacao': dados_json.get('observacao', ''),
            'cidade': dados_json.get('cidade', '')
        }
        
        rota_result = supabase.table('rotas').insert(rota_data).execute()
        rota_id = rota_result.data[0]['id']
        
        # Inserir paradas e pacotes
        for parada in dados_json.get('paradas', []):
            parada_data = {
                'rota_id': rota_id,
                'sequencia': parada.get('sequencia', ''),
                'endereco': parada.get('endereco', ''),
                'tipo_endereco': parada.get('tipo_endereco', 'Residencial')
            }
            
            parada_result = supabase.table('paradas').insert(parada_data).execute()
            parada_id = parada_result.data[0]['id']
            
            # Inserir pacotes para esta parada
            for codigo_pacote in parada.get('pacotes', []):
                pacote_data = {
                    'parada_id': parada_id,
                    'codigo_pacote': codigo_pacote
                }
                supabase.table('pacotes').insert(pacote_data).execute()
        
        return {'success': True, 'message': f"Rota {dados_json['rota']} importada com sucesso"}
    
    except Exception as e:
        return {'success': False, 'message': f"Erro ao importar: {str(e)}"}

@app.route('/')
def index():
    """Página principal"""
    if not supabase:
        return jsonify({"status": "error", "message": "Supabase não configurado"})
    try:
        # Buscar rotas cadastradas
        rotas = supabase.table('rotas').select('*').order('rota').execute()
        return render_template('index.html', rotas=rotas.data)
    except Exception as e:
        flash(f"Erro ao carregar rotas: {str(e)}", 'error')
        return render_template('index.html', rotas=[])

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Página de upload de arquivos"""
    if request.method == 'POST':
        if 'files' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('files')
        
        if not files or files[0].filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        # Filtrar apenas arquivos JSON válidos
        valid_files = [f for f in files if f and allowed_file(f.filename)]
        
        if not valid_files:
            flash('Apenas arquivos JSON são permitidos', 'error')
            return redirect(request.url)
        
        # Processar cada arquivo
        success_count = 0
        error_count = 0
        results = []
        
        for file in valid_files:
            filename = secure_filename(file.filename)
            
            # Ler e processar o JSON direto da memória (sem salvar em disco)
            try:
                conteudo = file.read().decode('utf-8')
                dados_json = json.loads(conteudo)
                
                resultado = importar_json_para_supabase(dados_json)
                
                if resultado['success']:
                    success_count += 1
                    results.append(f"✅ {filename}: {resultado['message']}")
                else:
                    error_count += 1
                    results.append(f"❌ {filename}: {resultado['message']}")
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_count += 1
                results.append(f"❌ {filename}: Arquivo JSON inválido")
            except Exception as e:
                error_count += 1
                results.append(f"❌ {filename}: Erro ao processar - {str(e)}")
        
        # Mostrar resumo dos resultados
        flash(f'Processamento concluído: {success_count} sucessos, {error_count} erros', 'success' if error_count == 0 else 'warning')
        
        # Mostrar detalhes de cada arquivo
        for result in results:
            flash(result, 'success' if '✅' in result else 'error')
        
        return redirect(url_for('index'))
    
    return render_template('upload.html')

@app.route('/rota/<rota_id>')
def detalhes_rota(rota_id):
    """Detalhes de uma rota específica"""
    try:
        # Buscar rota
        rota = supabase.table('rotas').select('*').eq('id', rota_id).execute()
        
        if not rota.data:
            flash('Rota não encontrada', 'error')
            return redirect(url_for('index'))
        
        # Buscar paradas da rota
        paradas = supabase.table('paradas').select('*').eq('rota_id', rota_id).order('sequencia').execute()
        
        # Para cada parada, buscar os pacotes
        for parada in paradas.data:
            pacotes = supabase.table('pacotes').select('*').eq('parada_id', parada['id']).execute()
            parada['pacotes'] = pacotes.data
        
        return render_template('detalhes.html', rota=rota.data[0], paradas=paradas.data)
    
    except Exception as e:
        flash(f"Erro ao carregar detalhes: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/api/rotas')
def api_rotas():
    """API para listar rotas"""
    try:
        rotas = supabase.table('rotas').select('*').order('rota').execute()
        return jsonify(rotas.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rota/<rota_id>')
def api_detalhes_rota(rota_id):
    """API para detalhes de uma rota"""
    try:
        rota = supabase.table('rotas').select('*').eq('id', rota_id).execute()
        
        if not rota.data:
            return jsonify({'error': 'Rota não encontrada'}), 404
        
        paradas = supabase.table('paradas').select('*').eq('rota_id', rota_id).order('sequencia').execute()
        
        for parada in paradas.data:
            pacotes = supabase.table('pacotes').select('*').eq('parada_id', parada['id']).execute()
            parada['pacotes'] = pacotes.data
        
        return jsonify({
            'rota': rota.data[0],
            'paradas': paradas.data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
