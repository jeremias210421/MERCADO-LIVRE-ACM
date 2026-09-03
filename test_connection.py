from app import create_app

app = create_app()
with app.app_context():
    from app.supabase_client import get_supabase, is_supabase_configured
    print(f'Supabase configurado: {is_supabase_configured()}')
    sb = get_supabase()
    if sb:
        result = sb.table('rotas').select('id, rota').limit(3).execute()
        print(f'Rotas encontradas: {len(result.data)}')
        for r in result.data:
            print(f'  - {r["rota"]} (ID: {r["id"]})')
    else:
        print('Erro: Supabase não conectado')