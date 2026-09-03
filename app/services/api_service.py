"""
API Service - Business logic for Android app endpoints.
"""
from datetime import date
from typing import Any
from app.supabase_client import get_supabase


def hoje() -> date:
    return date.today()


def get_rotas() -> list[dict[str, Any]]:
    """Get all rotas for API."""
    supabase = get_supabase()
    result = supabase.table('rotas').select('*').order('rota').execute()
    return result.data or []


def get_rota_detalhes(rota_id: str) -> dict[str, Any] | None:
    """Get rota details for API."""
    supabase = get_supabase()
    rota = supabase.table('rotas').select('*').eq('id', rota_id).execute()
    if not rota.data:
        return None

    paradas = supabase.table('paradas').select('*').eq('rota_id', rota_id).order('sequencia').execute()
    for parada in paradas.data:
        pacotes = supabase.table('pacotes').select('*').eq('parada_id', parada['id']).execute()
        parada['pacotes'] = pacotes.data

    return {'rota': rota.data[0], 'paradas': paradas.data}


def get_motoristas() -> list[dict[str, Any]]:
    """Get all motoristas for API."""
    supabase = get_supabase()
    result = supabase.table('motoristas').select('id, nome, telefone').order('nome').execute()
    return result.data or []


def upload_scans(scans: list[dict]) -> dict[str, Any]:
    """Upload scans from Android app."""
    supabase = get_supabase()
    result = supabase.table('scans').insert(scans).execute()
    return {'success': True, 'count': len(result.data)}


def get_pendentes(motorista_id: str | None, data_str: str) -> list[dict[str, Any]]:
    """Get pendentes for Android app."""
    supabase = get_supabase()

    query = supabase.table('pacotes_pendentes').select('*')\
        .eq('status', 'pendente')

    if motorista_id:
        query = query.eq('motorista_id', motorista_id)

    query = query.lte('data_entrega_prevista', data_str)\
        .order('data_pendencia', desc=True)

    result = query.execute()
    return result.data or []


def get_dashboard_resumo() -> dict[str, Any]:
    """Get dashboard summary for API."""
    supabase = get_supabase()
    today = hoje().isoformat()

    scans = supabase.table('scans').select('id, motorista_id')\
        .gte('escaneado_em', today + 'T00:00:00')\
        .lte('escaneado_em', today + 'T23:59:59').execute()

    pendentes = supabase.table('pacotes_pendentes').select('id')\
        .eq('status', 'pendente').lte('data_entrega_prevista', today).execute()

    motoristas_ativos = len(set(s['motorista_id'] for s in (scans.data or []) if s.get('motorista_id')))

    return {
        'entregadores_ativos': motoristas_ativos,
        'pacotes_entregues': len(scans.data or []),
        'pacotes_pendentes': len(pendentes.data or []),
        'data': today
    }


def get_entregador_stats(motorista_id: str) -> dict[str, int]:
    """Get motorista stats for API."""
    supabase = get_supabase()
    today = hoje().isoformat()

    total = supabase.table('scans').select('id', count='exact')\
        .eq('motorista_id', motorista_id).execute()

    hoje_count = supabase.table('scans').select('id', count='exact')\
        .eq('motorista_id', motorista_id)\
        .gte('escaneado_em', today + 'T00:00:00')\
        .lte('escaneado_em', today + 'T23:59:59').execute()

    pend = supabase.table('pacotes_pendentes').select('id', count='exact')\
        .eq('motorista_id', motorista_id).eq('status', 'pendente').execute()

    return {
        'total_geral': total.count or 0,
        'total_hoje': hoje_count.count or 0,
        'pendentes': pend.count or 0
    }