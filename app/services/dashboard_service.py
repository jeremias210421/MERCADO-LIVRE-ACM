"""
Dashboard Service - Optimized database queries for dashboard.
"""

from datetime import timedelta
from typing import Any

from app.supabase_client import get_supabase
from app.timezone import hoje_sp


def hoje():
    # Fuso canônico America/Sao_Paulo (servidor roda em UTC)
    return hoje_sp()


def get_dashboard_stats() -> dict[str, Any]:
    """Get all dashboard statistics in optimized queries.

    Usa session_date + route/operator_name (colunas reais gravadas pelo app;
    motorista_id/rota_id são quase sempre NULL e escaneado_em mistura fusos).
    """
    from app.scans_hoje import (
        fetch_scans_dia,
        motorista_id_da_linha,
        motorista_maps,
        tendencia_por_session_date,
    )

    supabase = get_supabase()
    today = hoje().isoformat()

    # Bipagens de hoje: pacotes únicos (dedupe por pacote)
    scans_list = fetch_scans_dia(supabase, today)
    vistos = set()
    unicos = []
    for s in scans_list:
        code = str(s.get("code") or "").strip().upper()
        if not code or code in vistos:
            continue
        vistos.add(code)
        unicos.append(s)
    total_entregues = len(unicos)

    # Entregadores ativos hoje (id direto ou operator_name→cadastro)
    _, por_nome = motorista_maps(supabase)
    motoristas_ativos = {
        m for m in (motorista_id_da_linha(s, por_nome) for s in unicos) if m
    }
    entregadores_ativos = len(motoristas_ativos)

    # Pendentes - single query
    pendentes_result = (
        supabase.table("pacotes_pendentes")
        .select("id, motorista_id")
        .eq("status", "pendente")
        .lte("data_entrega_prevista", today)
        .execute()
    )

    pendentes_list = pendentes_result.data or []
    total_pendentes = len(pendentes_list)

    # Taxa de entrega
    total = total_entregues + total_pendentes
    taxa_entrega = round((total_entregues / total) * 100, 1) if total > 0 else 0

    stats = {
        "entregadores_ativos": entregadores_ativos,
        "pacotes_entregues": total_entregues,
        "pacotes_pendentes": total_pendentes,
        "taxa_entrega": taxa_entrega,
    }

    # Progresso por entregador - optimized with single queries
    progresso = []
    if motoristas_ativos:
        # Single query: all motoristas
        motoristas = supabase.table("motoristas").select("id, nome, telefone").execute()
        motoristas_map = {m["id"]: m for m in (motoristas.data or [])}

        # Single query: all rota_motoristas
        rota_motoristas = (
            supabase.table("rota_motoristas").select("rota_id, motorista_id").execute()
        )
        rota_map = {
            rm["motorista_id"]: rm["rota_id"] for rm in (rota_motoristas.data or [])
        }

        # Single query: all rotas (para vínculo designado + fallback pela rota
        # mais bipada do entregador quando não há designação no painel)
        rotas_ids = list(set(rota_map.values()))
        rotas_map = {}
        rotas_por_nome: dict = {}
        if rotas_ids:
            rotas = (
                supabase.table("rotas")
                .select("id, rota, total_pacotes")
                .in_("id", rotas_ids)
                .execute()
            )
            rotas_map = {r["id"]: r for r in (rotas.data or [])}
        try:
            todas = (
                supabase.table("rotas")
                .select("id, rota, total_pacotes")
                .limit(1000)
                .execute()
                .data
                or []
            )
            for r in todas:
                rotas_por_nome[str(r.get("rota") or "").strip().upper()] = r
                if r["id"] not in rotas_map:
                    rotas_map[r["id"]] = r
        except Exception:
            pass

        # Single query: pendentes por motorista (IN filter instead of N queries)
        motorista_ids_list = list(motoristas_ativos)
        pendentes_por_motorista: dict = {}
        if motorista_ids_list:
            pend_motoristas = (
                supabase.table("pacotes_pendentes")
                .select("id, motorista_id")
                .eq("status", "pendente")
                .lte("data_entrega_prevista", today)
                .in_("motorista_id", motorista_ids_list)
                .execute()
            )

            for p in pend_motoristas.data or []:
                mid = p["motorista_id"]
                pendentes_por_motorista[mid] = pendentes_por_motorista.get(mid, 0) + 1

        # Build progresso
        for mid in motoristas_ativos:
            m = motoristas_map.get(mid, {})
            scans_motorista = [
                s for s in unicos if motorista_id_da_linha(s, por_nome) == mid
            ]
            total_ent = len(scans_motorista)

            rota_id = rota_map.get(mid)
            rota_info = rotas_map.get(rota_id, {}) if rota_id else {}
            if not rota_info:
                # Sem designação: infere pela rota mais bipada do entregador hoje
                from collections import Counter as _Counter

                top = _Counter(
                    str(s.get("route") or "").strip().upper() for s in scans_motorista
                ).most_common(1)
                if top and top[0][0]:
                    rota_info = rotas_por_nome.get(top[0][0], {})
            total_pac = rota_info.get("total_pacotes", 0) or 0
            pct = round((total_ent / total_pac) * 100, 1) if total_pac > 0 else 0

            progresso.append(
                {
                    "motorista_id": mid,
                    "motorista_nome": m.get("nome", "Desconhecido"),
                    "motorista_telefone": m.get("telefone", ""),
                    "rota_nome": rota_info.get("rota", "Sem rota"),
                    "total_entregues": total_ent,
                    "total_pendentes": pendentes_por_motorista.get(mid, 0),
                    "total_pacotes": total_pac,
                    "percentual": min(pct, 100),
                }
            )

        progresso.sort(key=lambda x: x["motorista_nome"])

    # Chart data: entregas por entregador
    chart_labels = [p["motorista_nome"].split()[0] for p in progresso]
    chart_entregues = [p["total_entregues"] for p in progresso]
    chart_pendentes = [p["total_pendentes"] for p in progresso]

    # Chart data: tendencia ultimos 7 dias - 1 query agrupada por
    # session_date (TZ-safe; escaneado_em mistura fusos e é mais caro)
    tendencia_labels, tendencia_data = tendencia_por_session_date(supabase)

    return {
        "stats": stats,
        "progresso": progresso,
        "chart_labels": chart_labels,
        "chart_entregues": chart_entregues,
        "chart_pendentes": chart_pendentes,
        "tendencia_labels": tendencia_labels,
        "tendencia_data": tendencia_data,
    }


def get_entregador_detalhe(motorista_id: str) -> dict[str, Any] | None:
    """Get detailed stats for a single entregador."""
    supabase = get_supabase()
    today = hoje().isoformat()

    # Motorista
    m_result = supabase.table("motoristas").select("*").eq("id", motorista_id).execute()
    if not m_result.data:
        return None
    motorista = m_result.data[0]

    # Scans de hoje (mesmo motor de atribuição do resto do sistema)
    from app.scans_hoje import enriquecer_endereco, motorista_maps, scans_do_motorista

    _, por_nome_det = motorista_maps(supabase)
    scans_hoje = scans_do_motorista(
        supabase, motorista_id, motorista.get("nome", ""), today, por_nome=por_nome_det
    )
    scans_hoje = enriquecer_endereco(supabase, scans_hoje)

    # Rota designada
    rm = (
        supabase.table("rota_motoristas")
        .select("rota_id")
        .eq("motorista_id", motorista_id)
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )

    rota_nome = "Sem rota"
    if rm.data:
        rota = (
            supabase.table("rotas")
            .select("rota, total_pacotes")
            .eq("id", rm.data[0]["rota_id"])
            .single()
            .execute()
        )
        if rota.data:
            rota_nome = rota.data.get("rota", "Sem rota")

    # Pendentes
    pendentes = (
        supabase.table("pacotes_pendentes")
        .select("*")
        .eq("motorista_id", motorista_id)
        .eq("status", "pendente")
        .order("data_pendencia", desc=True)
        .execute()
    )

    # Total geral + últimos 7 dias (mesmo motor de atribuição)
    from app.scans_hoje import norm_code
    from app.timezone import hoje_sp

    total_unset = {
        norm_code(r.get("code"))
        for r in scans_do_motorista(
            supabase, motorista_id, motorista.get("nome", ""), por_nome=por_nome_det
        )
    }
    total_unset.discard("")
    dias_labels = []
    dias_data = []
    for i in range(6, -1, -1):
        d = hoje_sp() - timedelta(days=i)
        d_str = d.isoformat()
        dias_labels.append(d.strftime("%d/%m"))
        try:
            dd = scans_do_motorista(
                supabase,
                motorista_id,
                motorista.get("nome", ""),
                d_str,
                por_nome=por_nome_det,
            )
            dias_data.append(len(dd))
        except Exception:
            dias_data.append(0)

    return {
        "motorista": motorista,
        "scans_hoje": scans_hoje,
        "rota_nome": rota_nome,
        "pendentes": pendentes.data or [],
        "total_geral": len(total_unset),
        "dias_labels": dias_labels,
        "dias_data": dias_data,
    }


def get_entregadores_list() -> tuple[list[dict], dict]:
    """Get all entregadores with their stats.

    Batch: motoristas + bipagens de hoje (session_date) + pendentes.
    Atribuição por motorista_id OU operator_name (coluna real do app).
    """
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

    # Hoje: 1 query + contagem em memória (pacotes únicos por entregador)
    hoje_counter = contagem_hoje_por_motorista(
        fetch_scans_dia(supabase, today), por_nome
    )

    # Total geral por entregador: 1 query paginada + atribuição em memória
    from collections import Counter

    total_counter: Counter = Counter()
    vistos_tot: set = set()
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
                if not code or not mid:
                    continue
                chave = (mid, code)
                if chave in vistos_tot:
                    continue
                vistos_tot.add(chave)
                total_counter[mid] += 1
            if len(data) < 5000:
                break
    except Exception:
        pass

    # Pendentes: 1 query + contagem em memória
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
            mid = r.get("motorista_id")
            if mid:
                pend_counter[mid] += 1
    except Exception:
        pass

    stats_map = {}
    for m in motoristas_list:
        mid = m["id"]
        stats_map[mid] = {
            "total_geral": total_counter.get(mid, 0),
            "total_hoje": hoje_counter.get(mid, 0),
            "pendentes": pend_counter.get(mid, 0),
        }

    return motoristas_list, stats_map


def get_rotas_list() -> tuple[list[dict], list[dict], dict]:
    """Get rotas with motoristas and today's stats (batch, sem N+1)."""

    supabase = get_supabase()

    rotas = supabase.table("rotas").select("*").order("rota").execute()
    rotas_list = rotas.data or []

    motoristas = supabase.table("motoristas").select("id, nome").order("nome").execute()
    motoristas_list = motoristas.data or []

    # Vinculos rota-motorista
    rm = supabase.table("rota_motoristas").select("rota_id, motorista_id").execute()
    rota_motoristas = {r["rota_id"]: r["motorista_id"] for r in (rm.data or [])}

    # Stats por SESSÃO do card (rotas antigas mostram seus números reais).
    # Só as sessões listadas (1 query com IN, sem varrer a tabela inteira).
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
