"""
Rate limiting para APIs usando Redis ou memoria local.
"""
import os
import time
from functools import wraps
from flask import request, jsonify, current_app
from collections import defaultdict


# Verificar se rate limiting está desabilitado (para testes)
DISABLE_RATE_LIMIT = os.environ.get('DISABLE_RATE_LIMIT', '0') == '1'

# Storage em memória (para desenvolvimento)
# Em produção, usar Redis
_rate_limit_storage = defaultdict(list)


def rate_limit(max_requests=100, window_seconds=60, key_func=None):
    """
    Decorator para rate limiting.
    
    Args:
        max_requests: Máximo de requisições permitidas
        window_seconds: Janela de tempo em segundos
        key_func: Função para gerar chave única (padrão: IP do cliente)
    """
    # Se desabilitado, retorna decorator que não faz nada
    if DISABLE_RATE_LIMIT:
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapped
        return decorator

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Determinar chave de rate limit
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or 'unknown'
            
            key = f"ratelimit:{key}:{request.endpoint}"
            now = time.time()
            
            # Limpar entradas antigas
            _rate_limit_storage[key] = [
                timestamp for timestamp in _rate_limit_storage[key]
                if now - timestamp < window_seconds
            ]
            
            # Verificar limite
            if len(_rate_limit_storage[key]) >= max_requests:
                current_app.logger.warning(
                    f"Rate limit excedido para {key}: {len(_rate_limit_storage[key])} reqs"
                )
                return jsonify({
                    'error': 'Rate limit excedido',
                    'message': f'Máximo {max_requests} requisições por {window_seconds}s',
                    'retry_after': window_seconds
                }), 429
            
            # Registrar requisição
            _rate_limit_storage[key].append(now)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


def api_rate_limit(max_requests=60, window_seconds=60):
    """Rate limit específico para APIs (mais restritivo)."""
    return rate_limit(max_requests=max_requests, window_seconds=window_seconds)


def auth_rate_limit(max_requests=10, window_seconds=300):
    """Rate limit para endpoints de autenticação (muito restritivo)."""
    return rate_limit(max_requests=max_requests, window_seconds=window_seconds)


def get_rate_limit_stats(key=None):
    """Retorna estatísticas de rate limit (para debug/monitoring)."""
    now = time.time()
    stats = {}
    
    for k, timestamps in _rate_limit_storage.items():
        recent = [t for t in timestamps if now - t < 60]
        if recent:
            stats[k] = len(recent)
    
    return stats


def clear_rate_limit(key=None):
    """Limpa rate limit para uma chave específica ou todas."""
    if key:
        k = f"ratelimit:{key}"
        if k in _rate_limit_storage:
            del _rate_limit_storage[k]
    else:
        _rate_limit_storage.clear()