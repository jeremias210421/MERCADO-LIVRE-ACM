"""
Galpao Service - Database operations for warehouse conference.
"""
import uuid
from typing import Any
from app.supabase_client import get_supabase


def scan_pacote(codigo: str, sessao_id: str) -> dict[str, Any]:
    """Scan a package in the warehouse."""
    supabase = get_supabase()

    # Identify package automatically
    result = supabase.rpc('identificar_pacote', {'p_codigo': codigo}).execute()

    rota_id = None
    motorista_id = None
    endereco = None
    encontrado = False

    if result.data and len(result.data) > 0:
        info = result.data[0]
        encontrado = info.get('encontrado', False)
        rota_id = info.get('rota_id')
        motorista_id = info.get('motorista_id')
        endereco = info.get('endereco')

    # Register scan
    supabase.table('galpao_scans').insert({
        'codigo_pacote': codigo,
        'rota_id': rota_id,
        'motorista_id': motorista_id,
        'endereco': endereco,
        'sessao_id': sessao_id
    }).execute()

    # Get motorista and rota names
    motorista_nome = None
    rota_nome = None
    if motorista_id:
        m = supabase.table('motoristas').select('nome').eq('id', motorista_id).single().execute()
        if m.data:
            motorista_nome = m.data.get('nome')
    if rota_id:
        r = supabase.table('rotas').select('rota').eq('id', rota_id).single().execute()
        if r.data:
            rota_nome = r.data.get('rota')

    # Buyer contact (alocado pelo ETL)
    comprador_nome = None
    comprador_telefone = None
    try:
        pc = supabase.table('pacotes').select('nome_comprador,telefone').eq('codigo_pacote', codigo).limit(1).execute()
        if pc.data:
            comprador_nome = pc.data[0].get('nome_comprador')
            comprador_telefone = pc.data[0].get('telefone')
    except Exception:
        pass

    return {
        'success': True,
        'encontrado': encontrado,
        'codigo': codigo,
        'rota_nome': rota_nome,
        'motorista_nome': motorista_nome,
        'endereco': endereco,
        'comprador_nome': comprador_nome,
        'comprador_telefone': comprador_telefone
    }


def finalizar_conferencia(sessao_id: str) -> dict[str, Any]:
    """Finalize warehouse conference and generate pendentes."""
    supabase = get_supabase()

    # Generate pendentes
    result = supabase.rpc('gerar_pendencias_diarias', {'p_sessao_id': sessao_id}).execute()
    count = result.data if isinstance(result.data, int) else 0

    # Get session summary
    scans_sessao = supabase.table('galpao_scans').select('codigo_pacote, motorista_id')\
        .eq('sessao_id', sessao_id).execute()

    # Group by motorista
    por_motorista = {}
    for scan in (scans_sessao.data or []):
        mid = scan.get('motorista_id')
        if mid:
            if mid not in por_motorista:
                por_motorista[mid] = {'nome': None, 'count': 0}
            por_motorista[mid]['count'] += 1

    # Get motorista names
    for mid in por_motorista:
        m = supabase.table('motoristas').select('nome').eq('id', mid).single().execute()
        if m.data:
            por_motorista[mid]['nome'] = m.data['nome']

    return {
        'success': True,
        'pendencias_criadas': count,
        'total_bipados': len(scans_sessao.data or []),
        'por_motorista': por_motorista
    }


def get_session_scans(sessao_id: str) -> list[dict[str, Any]]:
    """Get all scans for a session."""
    supabase = get_supabase()
    result = supabase.table('galpao_scans').select('*').eq('sessao_id', sessao_id).execute()
    return result.data or []