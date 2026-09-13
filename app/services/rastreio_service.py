"""
Rastreio - linha do tempo de um pacote por todas as tabelas.
"""

from typing import Any

from app.supabase_client import get_supabase
from app.timezone import normaliza_data_iso


def _ev(quando_iso: str, tipo: str, titulo: str, detalhe: str = "") -> dict:
    return {
        "quando": quando_iso or "",
        "tipo": tipo,
        "titulo": titulo,
        "detalhe": detalhe or "",
    }


def historico_pacote(code: str) -> dict[str, Any]:
    """Monta a linha do tempo de um pacote (mais recente primeiro)."""
    supabase = get_supabase()
    clean = str(code or "").strip().upper()
    eventos: list = []
    rota_atual = None
    motorista_atual = None
    produto_descricao = produto_valor = produto_status = None
    nome_comprador = telefone_comprador = None

    # 0) dados enriquecidos do pacote (contato + descricao por ID) - best-effort
    try:
        pcs = (
            supabase.table("pacotes")
            .select(
                "descricao_produto,valor_produto,status_looker,nome_comprador,telefone"
            )
            .eq("codigo_pacote", clean)
            .limit(10)
            .execute()
            .data
            or []
        )
        for pc in pcs:
            produto_descricao = produto_descricao or pc.get("descricao_produto") or None
            produto_valor = produto_valor or pc.get("valor_produto") or None
            produto_status = produto_status or pc.get("status_looker") or None
            nome_comprador = nome_comprador or pc.get("nome_comprador") or None
            telefone_comprador = telefone_comprador or pc.get("telefone") or None
            if produto_descricao and nome_comprador:
                break
    except Exception:
        pass
    if not produto_descricao:
        try:
            dd = (
                supabase.table("product_descriptions")
                .select("descricao,valor,status_looker")
                .eq("package_id", clean)
                .limit(1)
                .execute()
                .data
                or []
            )
            if dd:
                produto_descricao = dd[0].get("descricao")
                produto_valor = produto_valor or dd[0].get("valor")
                produto_status = produto_status or dd[0].get("status_looker")
        except Exception:
            pass

    def nome_motorista(mid):
        if not mid:
            return None
        try:
            m = (
                supabase.table("motoristas")
                .select("nome")
                .eq("id", mid)
                .limit(1)
                .execute()
            )
            return (m.data or [{}])[0].get("nome")
        except Exception:
            return None

    # 1) manifesto: pacotes -> paradas -> rotas
    try:
        pacs = (
            supabase.table("pacotes")
            .select("parada_id,status")
            .eq("codigo_pacote", clean)
            .limit(20)
            .execute()
            .data
            or []
        )
        for pc in pacs:
            pid = pc.get("parada_id")
            if not pid:
                continue
            try:
                pa = (
                    supabase.table("paradas")
                    .select("rota_id,endereco,sequencia")
                    .eq("id", pid)
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
            except Exception:
                pa = []
            if not pa:
                continue
            rota = sess = None
            try:
                r = (
                    supabase.table("rotas")
                    .select("id,rota,session_date,criado_em")
                    .eq("id", pa[0].get("rota_id"))
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if r:
                    rota = r[0].get("rota")
                    sess = normaliza_data_iso(
                        r[0].get("session_date")
                    ) or normaliza_data_iso(r[0].get("criado_em"))
            except Exception:
                pass
            if not rota_atual and rota:
                rota_atual = f"{rota}" + (f" ({sess})" if sess else "")
            eventos.append(
                _ev(
                    sess or "",
                    "romaneio",
                    f"Entrou no romaneio {rota or ''}".strip(),
                    f"{pa[0].get('endereco') or ''} • parada {pa[0].get('sequencia') or '?'} • status {pc.get('status') or 'pendente'}".strip(
                        " •"
                    ),
                )
            )
    except Exception:
        pass

    # 2) romaneio legado
    try:
        rom = (
            supabase.table("romaneio")
            .select("route,address,session_date")
            .eq("code", clean)
            .limit(20)
            .execute()
            .data
            or []
        )
        for r in rom:
            eventos.append(
                _ev(
                    normaliza_data_iso(r.get("session_date")),
                    "romaneio",
                    f"Romaneio {r.get('route') or ''}".strip(),
                    str(r.get("address") or ""),
                )
            )
            if not rota_atual and r.get("route"):
                rota_atual = str(r.get("route"))
    except Exception:
        pass

    # 3) bips na rua
    try:
        sc = (
            supabase.table("scans")
            .select("route,operator_name,session_date,scanned_at,motorista_id")
            .eq("code", clean)
            .order("scanned_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        for s in sc:
            op = s.get("operator_name")
            mid = s.get("motorista_id")
            nome = nome_motorista(mid) if mid and not op else op
            if nome and not motorista_atual:
                motorista_atual = nome
            eventos.append(
                _ev(
                    normaliza_data_iso(s.get("session_date"))
                    or str(s.get("scanned_at") or "")[:10],
                    "rua",
                    f"Bipado na rua — {s.get('route') or ''}".strip(),
                    f"por {nome}" if nome else "",
                )
            )
    except Exception:
        pass

    # 4) galpão (data = a sessão, não o carimbo da migração)
    try:
        from app.timezone import sessao_br_para_iso

        gs = (
            supabase.table("galpao_scans")
            .select("sessao_id,motorista_id,escaneado_em")
            .eq("codigo_pacote", clean)
            .order("escaneado_em", desc=True)
            .limit(20)
            .execute()
            .data
            or []
        )
        for g in gs:
            nome = nome_motorista(g.get("motorista_id"))
            if nome and not motorista_atual:
                motorista_atual = nome
            sess = str(g.get("sessao_id") or "")
            eventos.append(
                _ev(
                    sessao_br_para_iso(sess) or str(g.get("escaneado_em") or "")[:10],
                    "galpao",
                    f"Retornou ao galpão ({sess})",
                    f"com {nome}" if nome else "",
                )
            )
    except Exception:
        pass

    # 5) pendentes
    try:
        pd = (
            supabase.table("pacotes_pendentes")
            .select("status,data_pendencia,motorista_id")
            .eq("codigo_pacote", clean)
            .order("data_pendencia", desc=True)
            .limit(20)
            .execute()
            .data
            or []
        )
        for p in pd:
            st = (p.get("status") or "").strip().lower()
            tipo = (
                "entregue"
                if st == "entregue"
                else ("pendente" if st == "pendente" else "pendente_hist")
            )
            nome = nome_motorista(p.get("motorista_id"))
            eventos.append(
                _ev(
                    str(p.get("data_pendencia") or "")[:10],
                    tipo,
                    "Marcado como entregue" if st == "entregue" else "Virou pendente",
                    f"com {nome}" if nome else "",
                )
            )
    except Exception:
        pass

    eventos = [e for e in eventos if e["quando"] or e["titulo"]]
    eventos.sort(key=lambda e: e["quando"], reverse=True)

    # status atual = evento mais recente (desempate: pendente > galpão > rua)
    status = "Sem histórico"
    if eventos:
        prio = {
            "pendente": 0,
            "galpao": 1,
            "rua": 2,
            "entregue": 3,
            "pendente_hist": 4,
            "romaneio": 5,
        }
        ult = max(eventos, key=lambda e: (e["quando"], -prio.get(e["tipo"], 9)))
        mapa = {
            "pendente": "Pendente",
            "galpao": "No galpão",
            "rua": "Na rua / entregue",
            "entregue": "Entregue ✔",
            "pendente_hist": "Pendente (hist.)",
            "romaneio": "No romaneio",
        }
        status = mapa.get(ult["tipo"], "Sem histórico")

    return {
        "code": clean,
        "status": status,
        "rota_atual": rota_atual,
        "motorista_atual": motorista_atual,
        "eventos": eventos,
        "produto_descricao": produto_descricao,
        "produto_valor": produto_valor,
        "produto_status": produto_status,
        "nome_comprador": nome_comprador,
        "telefone": telefone_comprador,
    }
