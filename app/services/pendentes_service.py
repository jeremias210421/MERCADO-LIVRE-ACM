"""
Pendentes Service - Database operations for pending packages.
"""

from datetime import date

from app.supabase_client import get_supabase
from app.timezone import hoje_sp


def hoje() -> date:
    # Fuso canônico America/Sao_Paulo (servidor roda em UTC)
    return hoje_sp()


def get_all_pendentes(
    data: str | None = None, status: str | None = None
) -> tuple[list[dict], dict, list]:
    """Get all pendentes grouped by motorista, com filtros opcionais de data e status."""
    supabase = get_supabase()

    q = (
        supabase.table("pacotes_pendentes")
        .select("*")
        .order("data_pendencia", desc=True)
        .order("motorista_id")
    )
    if data:
        q = q.eq("data_pendencia", data)
    if status in ("pendente", "entregue", "cancelado"):
        q = q.eq("status", status)
    pendentes = q.execute()

    pendentes_list = pendentes.data or []

    # Get motorista names
    motorista_ids = list(
        {p["motorista_id"] for p in pendentes_list if p.get("motorista_id")}
    )
    motoristas_map = {}
    if motorista_ids:
        motoristas = (
            supabase.table("motoristas")
            .select("id, nome, telefone")
            .in_("id", motorista_ids)
            .execute()
        )
        motoristas_map = {m["id"]: m for m in (motoristas.data or [])}

    # Get rota names + datas
    rota_ids = list(
        {p["rota_original_id"] for p in pendentes_list if p.get("rota_original_id")}
    )
    rotas_map = {}
    if rota_ids:
        rotas = (
            supabase.table("rotas")
            .select("id, rota, session_date")
            .in_("id", rota_ids)
            .execute()
        )
        rotas_map = {r["id"]: r for r in (rotas.data or [])}

    # Enrich data
    for p in pendentes_list:
        mid = p.get("motorista_id")
        p["motorista_nome"] = (
            motoristas_map.get(mid, {}).get("nome", "Desconhecido") if mid else "N/A"
        )
        p["motorista_telefone"] = (
            motoristas_map.get(mid, {}).get("telefone", "") if mid else ""
        )
        rota_info = rotas_map.get(p.get("rota_original_id"), {})
        p["rota_nome"] = rota_info.get("rota", "N/A")
        p["rota_data"] = rota_info.get("session_date") or ""

    # Group by motorista
    agrupado: dict[str, list] = {}
    for p in pendentes_list:
        nome = p.get("motorista_nome", "N/A")
        if nome not in agrupado:
            agrupado[nome] = []
        agrupado[nome].append(p)

    # Datas e status disponíveis p/ filtros (1 query leve)
    datas_disponiveis: list = []
    try:
        dd = (
            supabase.table("pacotes_pendentes")
            .select("data_pendencia,status")
            .order("data_pendencia", desc=True)
            .limit(2000)
            .execute()
            .data
            or []
        )
        vistas: set = set()
        for r in dd:
            chave = (r.get("data_pendencia") or "", r.get("status") or "")
            if not chave[0] or chave in vistas:
                continue
            vistas.add(chave)
            datas_disponiveis.append({"data": chave[0], "status": chave[1]})
    except Exception:
        pass

    return pendentes_list, agrupado, datas_disponiveis


def get_pendentes_for_motorista(
    motorista_id: str, data_str: str | None = None
) -> list[dict]:
    """Get pendentes for a specific motorista (for Android app)."""
    supabase = get_supabase()
    data = data_str or hoje().isoformat()

    query = (
        supabase.table("pacotes_pendentes")
        .select("*")
        .eq("status", "pendente")
        .eq("motorista_id", motorista_id)
        .lte("data_entrega_prevista", data)
        .order("data_pendencia", desc=True)
    )

    result = query.execute()
    return result.data or []


def marcar_entregue(pendente_id: str) -> bool:
    """Mark pendente as delivered."""
    supabase = get_supabase()
    from datetime import datetime, timezone

    result = (
        supabase.table("pacotes_pendentes")
        .update(
            {
                "status": "entregue",
                "escaneado_em": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", pendente_id)
        .execute()
    )
    return bool(result.data)


def cancelar_pendente(pendente_id: str) -> bool:
    """Cancel a pendente."""
    supabase = get_supabase()
    result = (
        supabase.table("pacotes_pendentes")
        .update({"status": "cancelado"})
        .eq("id", pendente_id)
        .execute()
    )
    return bool(result.data)
