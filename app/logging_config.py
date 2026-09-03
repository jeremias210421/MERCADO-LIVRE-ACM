"""
Configuração de logging estruturado para produção com structlog.
"""
import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import structlog


def setup_logging(app):
    """Configura logging estruturado para a aplicação Flask."""

    log_level = logging.DEBUG if app.debug else logging.INFO

    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Handler para console (stdout) - JSON em produção, pretty em dev
    console_handler = logging.StreamHandler(sys.stdout)
    if app.debug:
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
    else:
        console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer()
        ))
    console_handler.setLevel(log_level)

    # Handler para arquivo - pular em Vercel (read-only filesystem)
    is_vercel = os.environ.get('VERCEL') == '1'
    handlers = [console_handler]

    if not is_vercel:
        # Local development - usar arquivo
        if not os.path.exists('logs'):
            os.makedirs('logs')

        log_file = f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=30, encoding='utf-8'
        )
        file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer()
        ))
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    else:
        # Em Vercel: logs vão para stdout (Vercel captura automaticamente)
        pass

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = handlers

    # Loggers específicos
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('supabase').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

    app.logger.info('Logging estruturado configurado com sucesso')

    return root_logger


# Instâncias de logger estruturado para uso nos módulos
dashboard_logger = structlog.get_logger('app.dashboard')
entregadores_logger = structlog.get_logger('app.entregadores')
galpao_logger = structlog.get_logger('app.galpao')
pendentes_logger = structlog.get_logger('app.pendentes')
rotas_logger = structlog.get_logger('app.rotas')
upload_logger = structlog.get_logger('app.upload')
api_logger = structlog.get_logger('app.api')