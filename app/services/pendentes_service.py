"""
Pendentes Service - Database operations for pending packages.
"""
from datetime import date
from typing import Any
from app.supabase_client import get_supabase


def hoje() -> date:
    return date.today()


def get_all_pendentes() -> tuple[list[dict], dict]:
    """Get all pendentes grouped by motorista."""
    supabase = get_supabase()

    pendentes = supabase.table('pacotes_pendentes').select('*')\
        .order('data_pendencia', desc=True)\
        .order('motorista_id').execute()

    pendentes_list = pendentes.data or []

    # Get motorista names
    motorista_ids = list(set(p['motorista_id'] for p in pendentes_list if p.get('motorista_id')))
    motoristas_map = {}
    if motorista_ids:
        motoristas = supabase.table('motoristas').select('id, nome, telefone').in_('id', motorista_ids).execute()
        motoristas_map = {m['id']: m for m in (motoristas.data or [])}

    # Get rota names
    rota_ids = list(set(p['rota_original_id'] for p in pendentes_list if p.get('rota_original_id')))
    rotas_map = {}
    if rota_ids:
        rotas = supabase.table('rotas').select('id, rota').in_('id', rota_ids).execute()
        rotas_map = {r['id']: r['rota'] for r in (rotas.data or [])}

    # Enrich data
    for p in pendentes_list:
        mid = p.get('motorista_id')
        p['motorista_nome'] = motoristas_map.get(mid, {}).get('nome', 'Desconhecido') if mid else 'N/A'
        p['motorista_telefone'] = motoristas_map.get(mid, {}).get('telefone', '') if mid else ''
        p['rota_nome'] = rotas_map.get(p.get('rota_original_id'), 'N/A')

    # Group by motorista
    agrupado = {}
    for p in pendentes_list:
        nome = p.get('motorista_nome', 'N/A')
        if nome not in agrupado:
            agrupado[nome] = []
        agrupado[nome].append(p)

    return pendentes_list, agrupado


def get_pendentes_for_motorista(motorista_id: str, data_str: str | None = None) -> list[dict]:
    """Get pendentes for a specific motorista (for Android app)."""
    supabase = get_supabase()
    data = data_str or hoje().isoformat()

    query = supabase.table('pacotes_pendentes').select('*')\
        .eq('status', 'pendente')\
        .eq('motorista_id', motorista_id)\
        .lte('data_entrega_prevista', data)\
        .order('data_pendencia', desc=True)

    result = query.execute()
    return result.data or []


def marcar_entregue(pendente_id: str) -> bool:
    """Mark pendente as delivered."""
    supabase = get_supabase()
    from datetime import datetime
    result = supabase.table('pacotes_pendentes').update({
        'status': 'entregue',
        'escaneado_em': datetime.now().isoformat()
    }).eq('id', pendente_id).execute()
    return bool(result.data)


def cancelar_pendente(pendente_id: str) -> bool:
    """Cancel a pendente."""
    supabase = get_supabase()
    result = supabase.table('pacotes_pendentes').update({
        'status': 'cancelado'
    }).eq('id', pendente_id).execute()
    return bool(result.data)