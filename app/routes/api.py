"""
Blueprint de APIs (para app Android).
"""
from flask import Blueprint, request, jsonify
from app.supabase_client import is_supabase_configured
from app.rate_limit import api_rate_limit
from app.services import (
    get_rotas,
    get_rota_detalhes,
    get_motoristas,
    upload_scans,
    get_pendentes,
    get_dashboard_resumo,
    get_entregador_stats
)
from app.schemas import ScansBatch, PendenteFilter
from pydantic import ValidationError

bp = Blueprint('api', __name__)


def validate_json(schema_class):
    """Decorator to validate JSON body against pydantic schema."""
    def decorator(f):
        def wrapped(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({'error': 'JSON inválido ou ausente'}), 400
                validated = schema_class(**data)
                return f(validated, *args, **kwargs)
            except ValidationError as e:
                return jsonify({'error': 'Dados inválidos', 'details': e.errors()}), 400
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator


@bp.route('/api/rotas')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_rotas():
    """API para listar rotas."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        return jsonify(get_rotas())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/rota/<rota_id>')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_detalhes_rota(rota_id):
    """API para detalhes de uma rota."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        data = get_rota_detalhes(rota_id)
        if not data:
            return jsonify({'error': 'Rota não encontrada'}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/motoristas')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_motoristas():
    """API para listar motoristas."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        return jsonify(get_motoristas())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/scans', methods=['POST'])
@api_rate_limit(max_requests=200, window_seconds=60)
@validate_json(ScansBatch)
def api_upload_scans(validated: ScansBatch):
    """API para receber scans do app Android."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        # Convert to list of dicts for service
        scans_data = [scan.model_dump() for scan in validated.scans]
        return jsonify(upload_scans(scans_data))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/pendentes')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_pendentes():
    """API para app Android buscar pendentes de um motorista."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        motorista_id = request.args.get('motorista_id')
        data_str = request.args.get('data', '')

        # Validate query params
        filter_data = PendenteFilter(motorista_id=motorista_id, data=data_str if data_str else None)
        return jsonify(get_pendentes(filter_data.motorista_id, filter_data.data.isoformat() if filter_data.data else ''))
    except ValidationError as e:
        return jsonify({'error': 'Parâmetros inválidos', 'details': e.errors()}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/dashboard')
@api_rate_limit(max_requests=30, window_seconds=60)
def api_dashboard():
    """API resumo do dashboard."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        return jsonify(get_dashboard_resumo())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/entregadores/<motorista_id>/stats')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_entregador_stats(motorista_id):
    """API estatísticas de um entregador."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        return jsonify(get_entregador_stats(motorista_id))
    except Exception as e:
        return jsonify({'error': str(e)}), 500