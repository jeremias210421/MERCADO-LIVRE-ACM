"""
Entregador Service - Database operations for motoristas.
"""
from datetime import date
from typing import Any
from app.supabase_client import get_supabase


def hoje() -> date:
    return date.today()


def create_motorista(nome: str, telefone: str) -> dict[str, Any]:
    """Create a new motorista."""
    supabase = get_supabase()
    result = supabase.table('motoristas').insert({
        'nome': nome,
        'telefone': telefone
    }).execute()
    return result.data[0] if result.data else {}


def update_motorista(motorista_id: str, nome: str, telefone: str) -> dict[str, Any]:
    """Update a motorista."""
    supabase = get_supabase()
    result = supabase.table('motoristas').update({
        'nome': nome,
        'telefone': telefone
    }).eq('id', motorista_id).execute()
    return result.data[0] if result.data else {}


def delete_motorista(motorista_id: str) -> bool:
    """Delete a motorista."""
    supabase = get_supabase()
    result = supabase.table('motoristas').delete().eq('id', motorista_id).execute()
    return bool(result.data)


def get_motorista(motorista_id: str) -> dict[str, Any] | None:
    """Get a single motorista by ID."""
    supabase = get_supabase()
    result = supabase.table('motoristas').select('*').eq('id', motorista_id).execute()
    return result.data[0] if result.data else None


def get_all_motoristas() -> list[dict[str, Any]]:
    """Get all motoristas ordered by name."""
    supabase = get_supabase()
    result = supabase.table('motoristas').select('*').order('nome').execute()
    return result.data or []


def get_motorista_stats(motorista_id: str) -> dict[str, int]:
    """Get stats for a motorista."""
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


def get_motoristas_with_stats() -> tuple[list[dict], dict]:
    """Get all motoristas with their stats - optimized."""
    supabase = get_supabase()
    today = hoje().isoformat()

    motoristas = supabase.table('motoristas').select('*').order('nome').execute()
    motoristas_list = motoristas.data or []

    stats_map = {}
    for m in motoristas_list:
        mid = m['id']
        stats_map[mid] = get_motorista_stats(mid)

    return motoristas_list, stats_map