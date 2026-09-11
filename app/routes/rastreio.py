"""
Rastreio de pacote - linha do tempo.
"""
from flask import Blueprint, render_template, request
from app.supabase_client import is_supabase_configured
from app.services.rastreio_service import historico_pacote

bp = Blueprint('rastreio', __name__)


@bp.route('/pacote')
def buscar_pacote():
    """Busca + linha do tempo (?q=CODIGO)."""
    code = (request.args.get('q') or '').strip().upper()
    dados = None
    if code and is_supabase_configured():
        try:
            dados = historico_pacote(code)
        except Exception as e:
            from flask import flash
            flash(f'Erro ao rastrear: {str(e)}', 'danger')
    return render_template('pacote.html', code=code, dados=dados)


@bp.route('/pacote/<code>')
def ver_pacote(code):
    """Atalho direto /pacote/CODIGO."""
    if not is_supabase_configured():
        from flask import flash
        flash('Supabase não configurado', 'danger')
        return render_template('pacote.html', code=code.strip().upper(), dados=None)
    try:
        dados = historico_pacote(code)
    except Exception as e:
        from flask import flash
        flash(f'Erro ao rastrear: {str(e)}', 'danger')
        dados = None
    return render_template('pacote.html', code=code.strip().upper(), dados=dados)
