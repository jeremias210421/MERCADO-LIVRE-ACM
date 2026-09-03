"""
Blueprint do Galpão (Conferência).
"""
from flask import Blueprint, render_template, request, jsonify
import uuid
from app.supabase_client import is_supabase_configured, require_supabase
from app.services import scan_pacote, finalizar_conferencia

bp = Blueprint('galpao', __name__)


@bp.route('/galpao')
def conferencia_galpao():
    """Interface de conferência do galpão."""
    if not is_supabase_configured():
        from flask import flash
        flash('Supabase não configurado', 'danger')
    sessao_id = str(uuid.uuid4())[:8]
    return render_template('galpao.html', sessao_id=sessao_id)


@bp.route('/galpao/scan', methods=['POST'])
@require_supabase()
def galpao_scan():
    """Registra scan de pacote no galpão."""
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'JSON inválido ou ausente'}), 400
        codigo = dados.get('codigo_pacote', '').strip()
        sessao_id = dados.get('sessao_id', '')

        if not codigo:
            return jsonify({'error': 'Código vazio'}), 400

        result = scan_pacote(codigo, sessao_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/galpao/finalizar', methods=['POST'])
@require_supabase()
def galpao_finalizar():
    """Finaliza conferência e gera pendências."""
    try:
        sessao_id = request.json.get('sessao_id', '')
        result = finalizar_conferencia(sessao_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500