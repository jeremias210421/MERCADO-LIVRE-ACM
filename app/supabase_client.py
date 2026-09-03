"""
Cliente Supabase - Configuração centralizada.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_supabase = None
_supabase_configured = False


def get_supabase():
    """Retorna o cliente Supabase (singleton)."""
    global _supabase, _supabase_configured
    
    if _supabase is not None:
        return _supabase
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or 
        os.getenv("SUPABASE_SECRET_KEY") or 
        os.getenv("SUPABASE_KEY") or 
        os.getenv("SUPABASE_PUBLISHABLE_KEY")
    )
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("AVISO: Variáveis de ambiente do Supabase não configuradas")
        _supabase_configured = False
        return None
    
    try:
        from supabase import create_client, Client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        _supabase_configured = True
        print("Supabase conectado com sucesso")
    except Exception as e:
        print(f"Erro ao conectar ao Supabase: {e}")
        _supabase_configured = False
    
    return _supabase


def is_supabase_configured() -> bool:
    """Verifica se o Supabase está configurado e conectado."""
    global _supabase_configured
    if _supabase is None:
        get_supabase()
    return _supabase_configured


def require_supabase():
    """Decorator para rotas que requerem Supabase."""
    from functools import wraps
    from flask import jsonify
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not is_supabase_configured():
                return jsonify({'error': 'Supabase não configurado'}), 503
            return f(*args, **kwargs)
        return wrapped
    return decorator