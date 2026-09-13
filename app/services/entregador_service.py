"""
Entregador Service - Database operations for motoristas.
"""

from datetime import date
from typing import Any

from app.supabase_client import get_supabase
from app.timezone import hoje_sp


def hoje() -> date:
    # Fuso canônico America/Sao_Paulo (servidor roda em UTC)
    return hoje_sp()


def create_motorista(nome: str, telefone: str) -> dict[str, Any]:
    """Create a new motorista."""
    supabase = get_supabase()
    result = (
        supabase.table("motoristas")
        .insert({"nome": nome, "telefone": telefone})
        .execute()
    )
    return result.data[0] if result.data else {}


def update_motorista(motorista_id: str, nome: str, telefone: str) -> dict[str, Any]:
    """Update a motorista."""
    supabase = get_supabase()
    result = (
        supabase.table("motoristas")
        .update({"nome": nome, "telefone": telefone})
        .eq("id", motorista_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def delete_motorista(motorista_id: str) -> bool:
    """Delete a motorista."""
    supabase = get_supabase()
    result = supabase.table("motoristas").delete().eq("id", motorista_id).execute()
    return bool(result.data)


def get_motorista(motorista_id: str) -> dict[str, Any] | None:
    """Get a single motorista by ID."""
    supabase = get_supabase()
    result = supabase.table("motoristas").select("*").eq("id", motorista_id).execute()
    return result.data[0] if result.data else None


def get_all_motoristas() -> list[dict[str, Any]]:
    """Get all motoristas ordered by name."""
    supabase = get_supabase()
    result = supabase.table("motoristas").select("*").order("nome").execute()
    return result.data or []


def get_motorista_stats(motorista_id: str) -> dict[str, int]:
    """Get stats for a motorista (mesmo motor de atribuição do sistema)."""
    from app.scans_hoje import scans_do_motorista

    supabase = get_supabase()
    today = hoje().isoformat()

    m = (
        supabase.table("motoristas")
        .select("nome")
        .eq("id", motorista_id)
        .limit(1)
        .execute()
    )
    nome = str((m.data or [{}])[0].get("nome") or "")

    # scans_do_motorista já devolve pacotes únicos atribuídos
    from app.scans_hoje import motorista_maps

    _, por_nome = motorista_maps(supabase)
    total_n = len(scans_do_motorista(supabase, motorista_id, nome, por_nome=por_nome))
    hoje_n = len(
        scans_do_motorista(supabase, motorista_id, nome, today, por_nome=por_nome)
    )

    pend = (
        supabase.table("pacotes_pendentes")
        .select("id", count="exact")
        .eq("motorista_id", motorista_id)
        .eq("status", "pendente")
        .execute()
    )

    return {"total_geral": total_n, "total_hoje": hoje_n, "pendentes": pend.count or 0}


def get_motoristas_with_stats() -> tuple[list[dict], dict]:
    """Get all entregadores with stats — batch (1 query do dia + 1 pendentes)."""
    from collections import Counter

    from app.scans_hoje import (
        contagem_hoje_por_motorista,
        fetch_scans_dia,
        motorista_maps,
    )

    supabase = get_supabase()
    today = hoje().isoformat()

    motoristas = supabase.table("motoristas").select("*").order("nome").execute()
    motoristas_list = motoristas.data or []

    if not motoristas_list:
        return [], {}

    _por_id, por_nome = motorista_maps(supabase)
    hoje_counter = contagem_hoje_por_motorista(
        fetch_scans_dia(supabase, today), por_nome
    )

    total_counter: Counter = Counter()
    try:
        for off in range(0, 20000, 5000):
            res = (
                supabase.table("scans")
                .select("code, operator_name, motorista_id")
                .range(off, off + 4999)
                .execute()
            )
            data = res.data or []
            if not data:
                break
            for r in data:
                code = str(r.get("code") or "").strip().upper()
                mid = r.get("motorista_id") or por_nome.get(
                    str(r.get("operator_name") or "").strip().upper(), None
                )
                if code and mid:
                    total_counter[(mid, code)] += 1
            if len(data) < 5000:
                break
    except Exception:
        pass
    total_por_mid: Counter = Counter()
    for mid, _code in total_counter:
        total_por_mid[mid] += 1

    pend_counter: Counter = Counter()
    try:
        res = (
            supabase.table("pacotes_pendentes")
            .select("motorista_id")
            .eq("status", "pendente")
            .limit(5000)
            .execute()
        )
        for r in res.data or []:
            if r.get("motorista_id"):
                pend_counter[r["motorista_id"]] += 1
    except Exception:
        pass

    stats_map = {}
    for m in motoristas_list:
        mid = m["id"]
        stats_map[mid] = {
            "total_geral": total_por_mid.get(mid, 0),
            "total_hoje": hoje_counter.get(mid, 0),
            "pendentes": pend_counter.get(mid, 0),
        }

    return motoristas_list, stats_map
