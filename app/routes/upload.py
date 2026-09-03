"""
Blueprint de Upload.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import json
from app.supabase_client import is_supabase_configured
from app.services import importar_json_para_supabase

bp = Blueprint('upload', __name__)


ALLOWED_EXTENSIONS = {'json'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Upload de arquivos JSON."""
    if not is_supabase_configured():
        flash('Supabase não configurado', 'danger')
        return render_template('upload.html')

    if request.method == 'POST':
        if 'files' not in request.files:
            flash('Nenhum arquivo selecionado', 'warning')
            return redirect(request.url)

        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            flash('Nenhum arquivo selecionado', 'warning')
            return redirect(request.url)

        valid_files = [f for f in files if f and allowed_file(f.filename)]
        if not valid_files:
            flash('Apenas arquivos JSON são permitidos', 'warning')
            return redirect(request.url)

        success_count = 0
        error_count = 0
        results = []

        for file in valid_files:
            filename = secure_filename(file.filename)
            try:
                conteudo = file.read().decode('utf-8')
                dados_json = json.loads(conteudo)
                resultado = importar_json_para_supabase(dados_json)

                if resultado['success']:
                    success_count += 1
                    results.append(f"OK {filename}: {resultado['message']}")
                else:
                    error_count += 1
                    results.append(f"ERRO {filename}: {resultado['message']}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_count += 1
                results.append(f"ERRO {filename}: JSON inválido")
            except Exception as e:
                error_count += 1
                results.append(f"ERRO {filename}: {str(e)}")

        flash(f'Processamento: {success_count} sucessos, {error_count} erros',
              'success' if error_count == 0 else 'warning')
        for result in results:
            flash(result, 'success' if result.startswith('OK') else 'danger')

        return redirect(url_for('rotas.listar_rotas'))

    return render_template('upload.html')