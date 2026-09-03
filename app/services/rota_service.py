"""
Rota Service - Database operations for rotas.
"""
from datetime import date
from typing import Any
from app.supabase_client import get_supabase


def hoje() -> date:
    return date.today()


def get_all_rotas() -> list[dict[str, Any]]:
    """Get all rotas ordered by name."""
    supabase = get_supabase()
    result = supabase.table('rotas').select('*').order('rota').execute()
    return result.data or []


def get_rota(rota_id: str) -> dict[str, Any] | None:
    """Get a single rota by ID."""
    supabase = get_supabase()
    result = supabase.table('rotas').select('*').eq('id', rota_id).execute()
    return result.data[0] if result.data else None


def get_rota_with_details(rota_id: str) -> dict[str, Any] | None:
    """Get rota with paradas and pacotes."""
    supabase = get_supabase()
    rota_result = supabase.table('rotas').select('*').eq('id', rota_id).execute()
    if not rota_result.data:
        return None

    rota = rota_result.data[0]
    paradas = supabase.table('paradas').select('*').eq('rota_id', rota_id).order('sequencia').execute()
    
    for parada in paradas.data:
        pacotes = supabase.table('pacotes').select('*').eq('parada_id', parada['id']).execute()
        parada['pacotes'] = pacotes.data

    return {'rota': rota, 'paradas': paradas.data}


def get_rotas_with_motoristas() -> tuple[list[dict], list[dict], dict]:
    """Get rotas with motorista assignments and today's stats."""
    supabase = get_supabase()
    today = hoje().isoformat()

    rotas = supabase.table('rotas').select('*').order('rota').execute()
    rotas_list = rotas.data or []

    motoristas = supabase.table('motoristas').select('id, nome').order('nome').execute()
    motoristas_list = motoristas.data or []

    # Vinculos rota-motorista
    rm = supabase.table('rota_motoristas').select('rota_id, motorista_id').execute()
    rota_motoristas = {r['rota_id']: r['motorista_id'] for r in (rm.data or [])}

    # Stats de hoje por rota
    for rota in rotas_list:
        scans = supabase.table('scans').select('id', count='exact')\
            .eq('rota_id', rota['id'])\
            .gte('escaneado_em', today + 'T00:00:00')\
            .lte('escaneado_em', today + 'T23:59:59').execute()
        rota['entregues_hoje'] = scans.count or 0
        total = rota.get('total_pacotes', 0) or 0
        rota['percentual_hoje'] = round((rota['entregues_hoje'] / total) * 100, 1) if total > 0 else 0

    return rotas_list, motoristas_list, rota_motoristas


def assign_motorista(rota_id: str, motorista_id: str) -> dict[str, Any]:
    """Assign motorista to rota."""
    supabase = get_supabase()
    result = supabase.table('rota_motoristas').upsert(
        {'rota_id': rota_id, 'motorista_id': motorista_id},
        on_conflict='rota_id,motorista_id'
    ).execute()
    return result.data[0] if result.data else {}