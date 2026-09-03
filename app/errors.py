"""
Handlers de erro e health checks.
"""
from flask import Blueprint, jsonify, render_template, request
from app.supabase_client import is_supabase_configured, get_supabase

bp = Blueprint('health', __name__)


@bp.route('/health')
def health_check():
    """Health check básico para load balancers."""
    return jsonify({
        'status': 'healthy',
        'service': 'bipador-acm',
        'version': '1.0.0'
    }), 200


@bp.route('/health/ready')
def readiness_check():
    """Readiness check - verifica dependências (Supabase)."""
    checks = {
        'supabase': False,
        'database': False
    }
    
    if is_supabase_configured():
        try:
            supabase = get_supabase()
            # Query simples para testar conexão
            result = supabase.table('rotas').select('id').limit(1).execute()
            checks['supabase'] = True
            checks['database'] = True
        except Exception as e:
            checks['database'] = False
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks
    }), status_code


@bp.route('/health/live')
def liveness_check():
    """Liveness check - apenas verifica se o processo está vivo."""
    return jsonify({'status': 'alive'}), 200


# Error handlers
def register_error_handlers(app):
    """Registra handlers de erro globais."""
    
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Requisição inválida', 'message': str(e)}), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Não autorizado', 'message': str(e)}), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Acesso negado', 'message': str(e)}), 403
    
    @app.errorhandler(404)
    def not_found(e):
        # Se for API, retorna JSON
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Recurso não encontrado'}), 404
        # Senão retorna template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Método não permitido'}), 405
    
    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Erro interno: {e}')
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Erro interno do servidor'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(503)
    def service_unavailable(e):
        return jsonify({'error': 'Serviço indisponível', 'message': str(e)}), 503