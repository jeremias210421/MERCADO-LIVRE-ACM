"""
API Service - Business logic for Android app endpoints.
"""

from datetime import date
from typing import Any

from app.supabase_client import get_supabase
from app.timezone import hoje_sp


def hoje() -> date:
    # Fuso canônico America/Sao_Paulo (servidor roda em UTC)
    return hoje_sp()


def get_rotas() -> list[dict[str, Any]]:
    """Get all rotas for API."""
    supabase = get_supabase()
    result = supabase.table("rotas").select("*").order("rota").execute()
    return result.data or []


def get_rota_detalhes(rota_id: str) -> dict[str, Any] | None:
    """Get rota details for API."""
    supabase = get_supabase()
    rota = supabase.table("rotas").select("*").eq("id", rota_id).execute()
    if not rota.data:
        return None

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

    return {"rota": rota.data[0], "paradas": paradas.data}


def get_motoristas() -> list[dict[str, Any]]:
    """Get all motoristas for API."""
    supabase = get_supabase()
    result = (
        supabase.table("motoristas")
        .select("id, nome, telefone")
        .order("nome")
        .execute()
    )
    return result.data or []


def _norm_upper(v) -> str:
    return str(v or "").strip().upper()


def upload_scans(scans: list[dict]) -> dict[str, Any]:
    """Upload scans do app com id determinístico + upsert.

    Aceita legado (rota_id/motorista_id/codigo_pacote) ou texto
    (code/route/operator_name/session_date). Resolve FKs no servidor e
    grava com o MESMO id do PWA (pacote+rota+dia): rebip = upsert,
    nunca linha duplicada.
    """
    from app.scan_ids import scan_db_id
    from app.timezone import agora_sp, hoje_sp_iso, normaliza_data_iso

    supabase = get_supabase()
    if not scans:
        return {"success": True, "count": 0}

    # mapas p/ resolução (1 query cada, fora do loop)
    rotas_por_nome: dict = {}
    try:
        rs = (
            supabase.table("rotas")
            .select("id,rota,session_date")
            .limit(2000)
            .execute()
            .data
            or []
        )
        for r in rs:
            rn = _norm_upper(r.get("rota"))
            if rn and rn not in rotas_por_nome:
                rotas_por_nome[rn] = r
    except Exception:
        pass
    mot_por_nome: dict = {}
    try:
        ms = supabase.table("motoristas").select("id,nome").execute().data or []
        for m in ms:
            n = _norm_upper(m.get("nome"))
            if n and n not in mot_por_nome:
                mot_por_nome[n] = m["id"]
    except Exception:
        pass

    agora = agora_sp().isoformat()
    rows = []
    for s in scans:
        if not isinstance(s, dict):
            continue
        code = _norm_upper(s.get("codigo_pacote") or s.get("code"))
        if not code:
            continue
        route = _norm_upper(s.get("route") or s.get("rota"))
        rota_id = s.get("rota_id")
        if not route and rota_id:
            try:
                rr = (
                    supabase.table("rotas")
                    .select("rota")
                    .eq("id", rota_id)
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if rr:
                    route = _norm_upper(rr[0].get("rota"))
            except Exception:
                pass
        operator = str(s.get("operator_name") or s.get("operator") or "").strip()
        motorista_id = s.get("motorista_id")
        if not motorista_id and operator and _norm_upper(operator) in mot_por_nome:
            motorista_id = mot_por_nome[_norm_upper(operator)]
        data_iso = (
            normaliza_data_iso(
                s.get("session_date")
                or s.get("data")
                or s.get("escaneado_em")
                or s.get("scanned_at")
            )
            or hoje_sp_iso()
        )
        ts = s.get("escaneado_em") or s.get("scanned_at") or agora
        fmt = s.get("format") or s.get("formato") or "QR_CODE"
        try:
            rid = scan_db_id(code, route, data_iso)
        except Exception:
            import uuid as _uuid

            rid = str(_uuid.uuid4())
        rows.append(
            {
                "id": rid,
                "code": code,
                "codigo": code,  # espelhos legados (prod tem NOT NULL)
                "codigo_pacote": code,
                "format": fmt,
                "formato": fmt,
                "route": route or None,
                "rota": route or None,
                "operator_name": operator or None,
                "rota_id": rota_id,
                "motorista_id": motorista_id,
                "scanned_at": ts,
                "escaneado_em": ts,
                "session_date": data_iso,
                "data": data_iso,
            }
        )

    if not rows:
        return {"success": True, "count": 0}
    result = supabase.table("scans").upsert(rows, on_conflict="id").execute()
    return {"success": True, "count": len(result.data or rows)}


def get_pendentes(motorista_id: str | None, data_str: str) -> list[dict[str, Any]]:
    """Get pendentes for Android app."""
    supabase = get_supabase()

    query = supabase.table("pacotes_pendentes").select("*").eq("status", "pendente")

    if motorista_id:
        query = query.eq("motorista_id", motorista_id)

    query = query.lte("data_entrega_prevista", data_str).order(
        "data_pendencia", desc=True
    )

    result = query.execute()
    return result.data or []


def get_dashboard_resumo() -> dict[str, Any]:
    """Get dashboard summary for API (session_date + operator_name reais)."""
    from app.scans_hoje import fetch_scans_dia, motorista_id_da_linha, motorista_maps

    supabase = get_supabase()
    today = hoje().isoformat()

    scans = fetch_scans_dia(supabase, today)
    unicos = {
        str(s.get("code") or "").strip().upper()
        for s in scans
        if str(s.get("code") or "").strip()
    }
    _, por_nome = motorista_maps(supabase)
    ativos = {m for m in (motorista_id_da_linha(s, por_nome) for s in scans) if m}

    pendentes = (
        supabase.table("pacotes_pendentes")
        .select("id")
        .eq("status", "pendente")
        .lte("data_entrega_prevista", today)
        .execute()
    )

    return {
        "entregadores_ativos": len(ativos),
        "pacotes_entregues": len(unicos),
        "pacotes_pendentes": len(pendentes.data or []),
        "data": today,
    }


def get_entregador_stats(motorista_id: str) -> dict[str, int]:
    """Get motorista stats for API (mesmo motor de atribuição do sistema)."""
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
