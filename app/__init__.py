"""
ACM Ibotirama - Bipador de Entregas
Aplicação Flask para gestão de rotas, motoristas e entregas.
"""

import os

from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFProtect

# Carregar variáveis de ambiente
load_dotenv()

# Importar configuração do Supabase
from app.supabase_client import get_supabase, is_supabase_configured

# CSRF Protection
csrf = CSRFProtect()


def create_app():
    """Factory pattern para criar a aplicação Flask."""
    template_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "templates"
    )
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

    # Configurações
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
    app.config["ALLOWED_EXTENSIONS"] = {"json"}
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # No time limit for tokens
    app.config["WTF_CSRF_SSL_STRICT"] = not app.debug  # Strict in production

    # Configurar logging
    from app.logging_config import setup_logging

    setup_logging(app)

    # Inicializar CSRF
    csrf.init_app(app)

    # Isentar APIs do CSRF (usam rate limiting + auth).
    # Flask-WTF>=1 compara "modulo.funcao" (view.__module__ + __name__), NÃO o
    # endpoint "blueprint.funcao" — strings curtas nunca casam e o exempt morre
    # em silêncio (toda API POST dava 400 CSRF). Usar paths completos.
    csrf.exempt("app.routes.api.api_rotas")
    csrf.exempt("app.routes.api.api_detalhes_rota")
    csrf.exempt("app.routes.api.api_motoristas")
    csrf.exempt("app.routes.api.api_upload_scans")
    csrf.exempt("app.routes.api.api_pendentes")
    csrf.exempt("app.routes.api.api_dashboard")
    csrf.exempt("app.routes.api.api_entregador_stats")
    csrf.exempt("app.routes.geracao.api_criar_job")
    csrf.exempt("app.routes.geracao.api_listar_jobs")
    csrf.exempt("app.routes.geracao.api_get_job")
    csrf.exempt("app.routes.geracao.api_rota_contatos")
    csrf.exempt("app.routes.geracao.api_rota_download")
    csrf.exempt("app.routes.galpao.galpao_scan")
    csrf.exempt("app.routes.galpao.galpao_finalizar")

    # Inicializar Supabase
    get_supabase()
    if not is_supabase_configured():
        app.logger.warning(
            "Supabase não configurado. Verifique as variáveis de ambiente."
        )

    # Context processors
    @app.context_processor
    def inject_globals():
        from app.timezone import agora_sp, hoje_sp

        return {"now": agora_sp(), "hoje": hoje_sp()}

    # Registrar blueprints
    from app.errors import bp as health_bp
    from app.routes.api import bp as api_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.entregadores import bp as entregadores_bp
    from app.routes.galpao import bp as galpao_bp
    from app.routes.geracao import bp as geracao_bp
    from app.routes.pendentes import bp as pendentes_bp
    from app.routes.rastreio import bp as rastreio_bp
    from app.routes.rotas import bp as rotas_bp
    from app.routes.upload import bp as upload_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(entregadores_bp)
    app.register_blueprint(galpao_bp)
    app.register_blueprint(pendentes_bp)
    app.register_blueprint(rotas_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(geracao_bp)
    app.register_blueprint(rastreio_bp)
    app.register_blueprint(health_bp)

    # Registrar error handlers
    from app.errors import register_error_handlers

    register_error_handlers(app)

    # Rota raiz
    @app.route("/")
    def index():
        from flask import redirect, url_for

        return redirect(url_for("dashboard.index"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
