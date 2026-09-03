import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
anon_key = os.getenv('SUPABASE_KEY')  # VITE_SUPABASE_ANON_KEY no .env do Android

print(f'URL: {url}')
print(f'Anon Key: {anon_key[:20]}...')

sb = create_client(url, anon_key)

# Testar leitura de rotas (SELECT)
print('\n--- Testando SELECT rotas ---')
result = sb.table('rotas').select('id, rota').limit(3).execute()
print(f'Rotas: {len(result.data)}')
for r in result.data:
    print(f'  - {r["rota"]}')

# Testar leitura de motoristas
print('\n--- Testando SELECT motoristas ---')
result = sb.table('motoristas').select('id, nome').limit(3).execute()
print(f'Motoristas: {len(result.data)}')

# Testar INSERT em scans (simular scan do app)
print('\n--- Testando INSERT scans ---')
test_scan = {
    'rota_id': result.data[0]['id'] if result.data else '00000000-0000-0000-0000-000000000000',
    'motorista_id': '00000000-0000-0000-0000-000000000000',
    'codigo_pacote': 'TEST_ANDROID_001',
    'formato': 'QR_CODE',
    'endereco': 'Teste Android',
    'is_valid': True
}
result = sb.table('scans').insert(test_scan).execute()
if result.data:
    print(f'Scan inserido: {result.data[0]["id"]}')
    
    # Limpar teste
    sb.table('scans').delete().eq('id', result.data[0]['id']).execute()
    print('Teste limpo')

# Testar INSERT em galpao_scans
print('\n--- Testando INSERT galpao_scans ---')
test_galpao = {
    'codigo_pacote': 'TEST_GALPAO_001',
    'sessao_id': 'test_sessao'
}
result = sb.table('galpao_scans').insert(test_galpao).execute()
if result.data:
    print(f'Galpão scan inserido: {result.data[0]["id"]}')
    sb.table('galpao_scans').delete().eq('id', result.data[0]['id']).execute()
    print('Teste limpo')

# Testar SELECT pacotes_pendentes
print('\n--- Testando SELECT pacotes_pendentes ---')
result = sb.table('pacotes_pendentes').select('id, codigo_pacote').limit(3).execute()
print(f'Pendentes: {len(result.data)}')

print('\n✅ Todos os testes da anon key passaram!')