"""
Validação de variáveis de ambiente obrigatórias.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


REQUIRED_VARS = {
    'SUPABASE_URL': 'URL do projeto Supabase (ex: https://xyz.supabase.co)',
    'SUPABASE_SERVICE_ROLE_KEY': 'Service Role Key do Supabase (settings > API)',
    'SECRET_KEY': 'Chave secreta do Flask (gere com: python -c "import secrets; print(secrets.token_hex(32))")',
}

OPTIONAL_VARS = {
    'FLASK_ENV': 'Ambiente (development/production) - padrão: production',
    'FLASK_DEBUG': 'Debug mode (1/0) - padrão: 0',
}


def validate_env():
    """Valida variáveis de ambiente obrigatórias."""
    missing = []
    warnings = []
    
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if not value:
            missing.append(f"  - {var}: {description}")
        elif var == 'SUPABASE_URL' and not value.startswith('https://'):
            warnings.append(f"  - {var}: deve começar com https://")
        elif var == 'SECRET_KEY' and len(value) < 32:
            warnings.append(f"  - {var}: deve ter pelo menos 32 caracteres")
    
    if missing:
        print("❌ VARIÁVEIS OBRIGATÓRIAS FALTANDO:")
        for m in missing:
            print(m)
        print("\n💡 Crie um arquivo .env baseado no .env.example")
        return False
    
    if warnings:
        print("⚠️  AVISOS:")
        for w in warnings:
            print(w)
    
    print("✅ Variáveis de ambiente validadas com sucesso")
    return True


def print_env_status():
    """Imprime status das variáveis (sem expor valores sensíveis)."""
    print("\n📋 Status das variáveis de ambiente:")
    for var in REQUIRED_VARS:
        value = os.getenv(var, '')
        if value:
            masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ❌ {var}: NÃO DEFINIDA")
    
    for var in OPTIONAL_VARS:
        value = os.getenv(var, '(padrão)')
        print(f"  ℹ️  {var}: {value}")


if __name__ == '__main__':
    print("=" * 50)
    print("Validação de Ambiente - Bipador ACM")
    print("=" * 50)
    
    if validate_env():
        print_env_status()
        print("\n✅ Ambiente pronto para execução")
        sys.exit(0)
    else:
        print_env_status()
        print("\n❌ Configure as variáveis faltantes e tente novamente")
        sys.exit(1)