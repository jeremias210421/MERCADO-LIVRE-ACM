"""
Rota Service - Database operations for rotas.
"""

from typing import Any

from app.supabase_client import get_supabase


def get_all_rotas() -> list[dict[str, Any]]:
    """Get all rotas ordered by name."""
    supabase = get_supabase()
    result = supabase.table("rotas").select("*").order("rota").execute()
    return result.data or []


def get_rota(rota_id: str) -> dict[str, Any] | None:
    """Get a single rota by ID."""
    supabase = get_supabase()
    result = supabase.table("rotas").select("*").eq("id", rota_id).execute()
    return result.data[0] if result.data else None


def get_rota_with_details(rota_id: str) -> dict[str, Any] | None:
    """Get rota with paradas and pacotes."""
    supabase = get_supabase()
    rota_result = supabase.table("rotas").select("*").eq("id", rota_id).execute()
    if not rota_result.data:
        return None

    rota = rota_result.data[0]
    paradas = (
        supabase.table("paradas")
        .select("*")
        .eq("rota_id", rota_id)
        .order("sequencia")
        .execute()
    )

    for parada in paradas.data:
        pacotes = (
            supabase.table("pacotes")
            .select("*")
            .eq("parada_id", parada["id"])
            .execute()
        )
        parada["pacotes"] = pacotes.data

    return {"rota": rota, "paradas": paradas.data}


def get_rotas_with_motoristas() -> tuple[list[dict], list[dict], dict]:
    """Get rotas with motorista assignments and today's stats.

    Batch: 4 queries no total (antes: 3 + N sequenciais — estourava timeout
    com ~200 rotas no serverless). Stats contam pacotes ÚNICOS por rota via
    session_date + route (colunas reais; rota_id é quase sempre NULL).
    """

    supabase = get_supabase()

    rotas = supabase.table("rotas").select("*").order("rota").execute()
    rotas_list = rotas.data or []

    motoristas = supabase.table("motoristas").select("id, nome").order("nome").execute()
    motoristas_list = motoristas.data or []

    # Vinculos rota-motorista
    rm = supabase.table("rota_motoristas").select("rota_id, motorista_id").execute()
    rota_motoristas = {r["rota_id"]: r["motorista_id"] for r in (rm.data or [])}

    # Stats por SESSÃO do card (não só hoje): rotas antigas mostram seus números reais.
    # Busca paginada (PostgREST capa o limit em ~1000; sem paginar, os dias
    # recentes somem do resultado).
    from app.scans_hoje import fetch_scans_por_sessoes, mapa_rota_sessao
    from app.timezone import normaliza_data_iso

    sessoes = {normaliza_data_iso(rota.get("session_date")) for rota in rotas_list}
    sessoes.discard("")
    try:
        por_rota_sessao = mapa_rota_sessao(fetch_scans_por_sessoes(supabase, sessoes))
    except Exception:
        por_rota_sessao = {}
    for rota in rotas_list:
        chave = str(rota.get("rota") or "").strip().upper()
        sess = normaliza_data_iso(rota.get("session_date"))
        entregues = len(por_rota_sessao.get((chave, sess), set())) if sess else 0
        total = rota.get("total_pacotes", 0) or 0
        rota["entregues_hoje"] = entregues
        rota["percentual_hoje"] = (
            round((entregues / total) * 100, 1) if total > 0 else 0
        )

    return rotas_list, motoristas_list, rota_motoristas


def assign_motorista(rota_id: str, motorista_id: str) -> dict[str, Any]:
    """Assign motorista to rota."""
    supabase = get_supabase()
    result = (
        supabase.table("rota_motoristas")
        .upsert(
            {"rota_id": rota_id, "motorista_id": motorista_id},
            on_conflict="rota_id,motorista_id",
        )
        .execute()
    )
    return result.data[0] if result.data else {}
