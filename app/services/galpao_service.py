"""
Galpao Service - Database operations for warehouse conference.
"""

from typing import Any

from app.supabase_client import get_supabase


def scan_pacote(codigo: str, sessao_id: str) -> dict[str, Any]:
    """Scan a package in the warehouse.

    Nunca exige rota 'Fechamento de Galpao': registra o bipe mesmo se o
    pacote nao estiver na base (encontrado=False) ou se a RPC nao existir.
    """
    from app.timezone import agora_sp

    supabase = get_supabase()

    # Identify package automatically (best-effort: sem RPC = nao encontrado, mas grava)
    rota_id = None
    motorista_id = None
    endereco = None
    encontrado = False
    try:
        result = supabase.rpc("identificar_pacote", {"p_codigo": codigo}).execute()
        if result.data and len(result.data) > 0:
            info = result.data[0]
            encontrado = info.get("encontrado", False)
            rota_id = info.get("rota_id")
            motorista_id = info.get("motorista_id")
            endereco = info.get("endereco")
    except Exception as e:
        print(f"[galpao] identificar_pacote falhou ({e}), seguindo como nao encontrado")

    # Fallback sem RPC: tenta achar direto em pacotes->paradas (cobre banco sem funcao)
    if not encontrado:
        try:
            pc = (
                supabase.table("pacotes")
                .select("parada_id")
                .eq("codigo_pacote", codigo)
                .limit(1)
                .execute()
            )
            if pc.data:
                pid = pc.data[0].get("parada_id")
                if pid:
                    par = (
                        supabase.table("paradas")
                        .select("rota_id,endereco")
                        .eq("id", pid)
                        .limit(1)
                        .execute()
                    )
                    if par.data:
                        rota_id = rota_id or par.data[0].get("rota_id")
                        endereco = endereco or par.data[0].get("endereco")
                        encontrado = True
        except Exception:
            pass

    # Register scan (sempre grava — e' isso que dispensa criar rota manual)
    supabase.table("galpao_scans").insert(
        {
            "codigo_pacote": codigo,
            "rota_id": rota_id,
            "motorista_id": motorista_id,
            "endereco": endereco,
            "sessao_id": sessao_id,
            "escaneado_em": agora_sp().isoformat(),
        }
    ).execute()

    # Get motorista and rota names + data da rota.
    # session_date pode nao existir no banco (schema antigo) -> fallback p/ so' rota.
    motorista_nome = None
    rota_nome = None
    rota_data = None
    if motorista_id:
        try:
            m = (
                supabase.table("motoristas")
                .select("nome")
                .eq("id", motorista_id)
                .single()
                .execute()
            )
            if m.data:
                motorista_nome = m.data.get("nome")
        except Exception:
            pass
    if rota_id:
        try:
            r = (
                supabase.table("rotas")
                .select("rota,session_date")
                .eq("id", rota_id)
                .single()
                .execute()
            )
            if r.data:
                rota_nome = r.data.get("rota")
                rota_data = r.data.get("session_date")
        except Exception:
            try:
                r = (
                    supabase.table("rotas")
                    .select("rota")
                    .eq("id", rota_id)
                    .single()
                    .execute()
                )
                if r.data:
                    rota_nome = r.data.get("rota")
            except Exception:
                pass

    # Buyer contact (alocado pelo ETL)
    comprador_nome = None
    comprador_telefone = None
    try:
        pc = (
            supabase.table("pacotes")
            .select("nome_comprador,telefone")
            .eq("codigo_pacote", codigo)
            .limit(1)
            .execute()
        )
        if pc.data:
            comprador_nome = pc.data[0].get("nome_comprador")
            comprador_telefone = pc.data[0].get("telefone")
    except Exception:
        pass

    return {
        "success": True,
        "encontrado": encontrado,
        "codigo": codigo,
        "rota_nome": rota_nome,
        "rota_data": rota_data,
        "motorista_nome": motorista_nome,
        "endereco": endereco,
        "comprador_nome": comprador_nome,
        "comprador_telefone": comprador_telefone,
    }


def gerar_pendentes_sessao(supabase, sessao_id: str) -> int:
    """Gera pendentes reais a partir dos RETORNOS ao galpão.

    REGRA DO GALPÃO ÚNICO: o que voltou ao galpão NÃO foi entregue e vira
    pendente de amanhã. O que não está no galpão = entregue (não pendencia).
    Idempotente (pula pacotes já pendentes no dia).
    """
    from app.timezone import hoje_sp_iso, sessao_br_para_iso

    date_iso = sessao_br_para_iso(sessao_id) or hoje_sp_iso()

    sess = (
        supabase.table("galpao_scans")
        .select("codigo_pacote,rota_id,motorista_id,endereco")
        .eq("sessao_id", sessao_id)
        .limit(5000)
        .execute()
    )
    rows = sess.data or []
    if not rows:
        return 0

    # Todo retorno ao galpao vira pendente, COM ou SEM motorista/rota
    # identificados. Chave inclui motorista (pode ser None).
    cands: dict = {}
    end_scan: dict = {}
    for r in rows:
        code = str(r.get("codigo_pacote") or "").strip().upper()
        if not code:
            continue
        mid = r.get("motorista_id")
        rid = r.get("rota_id")
        cands.setdefault((code, mid), rid)
        if r.get("endereco") and code not in end_scan:
            end_scan[code] = r.get("endereco")
    if not cands:
        return 0

    # Endereço de cada código (pacotes→paradas, batch) — sem ele a lista mostra '-'
    end_por_code: dict = dict(end_scan)
    try:
        rids = [rid for (_, _), rid in cands.items() if rid]
        todas_paradas: dict = {}
        for i in range(0, len(set(rids)), 100):
            ch = list(set(rids))[i : i + 100]
            pars = (
                supabase.table("paradas")
                .select("id,rota_id,endereco")
                .in_("rota_id", ch)
                .limit(5000)
                .execute()
                .data
                or []
            )
            for p in pars:
                todas_paradas[p["id"]] = p
        pids = list(todas_paradas.keys())
        for i in range(0, len(pids), 200):
            pacs = (
                supabase.table("pacotes")
                .select("codigo_pacote,parada_id")
                .in_("parada_id", pids[i : i + 200])
                .limit(5000)
                .execute()
                .data
                or []
            )
            for pc in pacs:
                code = str(pc.get("codigo_pacote") or "").strip().upper()
                par = todas_paradas.get(pc.get("parada_id"), {})
                if code and code not in end_por_code and par.get("endereco"):
                    end_por_code[code] = par.get("endereco")
    except Exception:
        pass

    # Já pendentes no dia (evita duplicar)
    existentes: set = set()
    try:
        ex = (
            supabase.table("pacotes_pendentes")
            .select("codigo_pacote,motorista_id")
            .eq("data_pendencia", date_iso)
            .eq("status", "pendente")
            .limit(5000)
            .execute()
            .data
            or []
        )
        existentes = {
            (str(e.get("codigo_pacote") or "").strip().upper(), e.get("motorista_id"))
            for e in ex
        }
    except Exception:
        pass

    novos = [
        {
            "codigo_pacote": code,
            "motorista_id": mid,
            "rota_original_id": rid,
            "endereco": end_por_code.get(code),
            "data_pendencia": date_iso,
            "status": "pendente",
        }
        for (code, mid), rid in cands.items()
        if (code, mid) not in existentes
    ]

    criados = 0
    for i in range(0, len(novos), 200):
        try:
            supabase.table("pacotes_pendentes").insert(novos[i : i + 200]).execute()
            criados += len(novos[i : i + 200])
        except Exception as e:
            print(f"[galpao] insert pendentes falhou: {e}")
            break
    return criados


def finalizar_conferencia(sessao_id: str) -> dict[str, Any]:
    """Finalize warehouse conference and generate pendentes."""
    supabase = get_supabase()

    # Generate pendentes via RPC se existir, senão gera de verdade no servidor
    count = 0
    try:
        result = supabase.rpc(
            "gerar_pendencias_diarias", {"p_sessao_id": sessao_id}
        ).execute()
        data = result.data
        if isinstance(data, int):
            count = data
        elif isinstance(data, list) and data and isinstance(data[0], int):
            count = data[0]
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            count = int(data[0].get("count", 0) or 0)
    except Exception as e:
        print(
            f"[galpao] RPC gerar_pendencias_diarias falhou ({e}), gerando no servidor"
        )
        try:
            count = gerar_pendentes_sessao(supabase, sessao_id)
        except Exception as e2:
            print(f"[galpao] fallback gerar_pendentes_sessao falhou: {e2}")
            count = 0

    # Get session summary
    scans_sessao = (
        supabase.table("galpao_scans")
        .select("codigo_pacote, motorista_id")
        .eq("sessao_id", sessao_id)
        .execute()
    )

    # Group by motorista (SEM motorista entra como bucket proprio p/ funcionar sem designar)
    por_motorista: dict[str, dict[str, Any]] = {}
    for scan in scans_sessao.data or []:
        mid = scan.get("motorista_id") or "SEM_MOTORISTA"
        if mid not in por_motorista:
            por_motorista[mid] = {
                "nome": None if mid != "SEM_MOTORISTA" else "Sem motorista",
                "count": 0,
            }
        por_motorista[mid]["count"] += 1

    # Get motorista names (best-effort: .single() falha se nao achar)
    for mid, entry in por_motorista.items():
        if mid == "SEM_MOTORISTA":
            continue
        try:
            m = (
                supabase.table("motoristas")
                .select("nome")
                .eq("id", mid)
                .single()
                .execute()
            )
            if m.data:
                entry["nome"] = m.data["nome"]
        except Exception:
            try:
                m = (
                    supabase.table("motoristas")
                    .select("nome")
                    .eq("id", mid)
                    .limit(1)
                    .execute()
                )
                if m.data:
                    entry["nome"] = m.data[0].get("nome")
            except Exception:
                pass

    return {
        "success": True,
        "pendencias_criadas": count,
        "total_bipados": len(scans_sessao.data or []),
        "por_motorista": por_motorista,
    }


def get_session_scans(sessao_id: str) -> list[dict[str, Any]]:
    """Get all scans for a session."""
    supabase = get_supabase()
    result = (
        supabase.table("galpao_scans").select("*").eq("sessao_id", sessao_id).execute()
    )
    return result.data or []


def fora_na_rua(sessao_id: str) -> dict[str, Any]:
    """Pacotes do manifest das rotas da sessão que não voltaram nem foram
    bipados: provavelmente ainda estão na rua com o entregador.

    Retorna {total, por_motorista: [{nome, count, exemplos:[{code, address}]}]}.
    """
    from app.timezone import hoje_sp_iso, sessao_br_para_iso

    supabase = get_supabase()
    date_iso = sessao_br_para_iso(sessao_id) or hoje_sp_iso()
    try:
        rows = (
            supabase.table("galpao_scans")
            .select("codigo_pacote,rota_id,motorista_id")
            .eq("sessao_id", sessao_id)
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception:
        return {"total": 0, "por_motorista": []}
    if not rows:
        return {"total": 0, "por_motorista": []}

    galpao_codes = {
        str(r.get("codigo_pacote") or "").strip().upper()
        for r in rows
        if str(r.get("codigo_pacote") or "").strip()
    }
    rota_ids = list({r["rota_id"] for r in rows if r.get("rota_id")})
    if not rota_ids:
        return {"total": 0, "por_motorista": []}

    # Manifest das rotas (batch) + rota de cada pacote
    manifest: dict = {}
    rota_de: dict = {}
    for i in range(0, len(rota_ids), 100):
        try:
            pars = (
                supabase.table("paradas")
                .select("id,rota_id,endereco")
                .in_("rota_id", rota_ids[i : i + 100])
                .limit(5000)
                .execute()
                .data
                or []
            )
        except Exception:
            continue
        pid_info = {p["id"]: p for p in pars if p.get("id")}
        for j in range(0, len(pid_info), 200):
            ch = list(pid_info.keys())[j : j + 200]
            try:
                pacs = (
                    supabase.table("pacotes")
                    .select("codigo_pacote,parada_id")
                    .in_("parada_id", ch)
                    .limit(5000)
                    .execute()
                    .data
                    or []
                )
            except Exception:
                continue
            for pc in pacs:
                code = str(pc.get("codigo_pacote") or "").strip().upper()
                info = pid_info.get(pc.get("parada_id"), {})
                if code and code not in manifest:
                    manifest[code] = {
                        "rota_id": info.get("rota_id"),
                        "address": info.get("endereco"),
                    }
                    rota_de[code] = info.get("rota_id")
    # rua: bipados no dia
    rua: set = set()
    try:
        st = (
            supabase.table("scans")
            .select("code")
            .eq("session_date", date_iso)
            .limit(5000)
            .execute()
            .data
            or []
        )
        rua = {
            str(r.get("code") or "").strip().upper()
            for r in st
            if str(r.get("code") or "").strip()
        }
    except Exception:
        pass

    # Para atribuir rota/motorista de cada faltante, resolve via pacotes de novo com rota
    rota_de2: dict = {}
    try:
        for i in range(0, len(rota_ids), 100):
            pars = (
                supabase.table("paradas")
                .select("id,rota_id")
                .in_("rota_id", rota_ids[i : i + 100])
                .limit(5000)
                .execute()
                .data
                or []
            )
            pid_rota = {p["id"]: p.get("rota_id") for p in pars}
            pids = list(pid_rota.keys())
            for j in range(0, len(pids), 200):
                pacs = (
                    supabase.table("pacotes")
                    .select("codigo_pacote,parada_id")
                    .in_("parada_id", pids[j : j + 200])
                    .limit(5000)
                    .execute()
                    .data
                    or []
                )
                for pc in pacs:
                    code = str(pc.get("codigo_pacote") or "").strip().upper()
                    if code and code not in rota_de2:
                        rota_de2[code] = pid_rota.get(pc.get("parada_id"))
    except Exception:
        pass

    mot_por_rota: dict = {}
    try:
        rms = (
            supabase.table("rota_motoristas")
            .select("rota_id,motorista_id")
            .in_("rota_id", rota_ids[:100])
            .limit(1000)
            .execute()
            .data
            or []
        )
        for rm in rms:
            if (
                rm.get("rota_id")
                and rm.get("motorista_id")
                and rm["rota_id"] not in mot_por_rota
            ):
                mot_por_rota[rm["rota_id"]] = rm["motorista_id"]
    except Exception:
        pass
    nomes: dict = {}
    mids = list({m for m in mot_por_rota.values() if m})
    for i in range(0, len(mids), 100):
        try:
            mm = (
                supabase.table("motoristas")
                .select("id,nome")
                .in_("id", mids[i : i + 100])
                .limit(500)
                .execute()
                .data
                or []
            )
            for x in mm:
                nomes[x["id"]] = x.get("nome")
        except Exception:
            pass

    por_mot: dict = {}
    for code, entry in manifest.items():
        if code in rua or code in galpao_codes:
            continue
        rid = rota_de2.get(code)
        mid = mot_por_rota.get(rid) if rid else None
        nome = nomes.get(mid, "Sem motorista") if mid else "Sem motorista"
        e = por_mot.setdefault(nome, {"nome": nome, "count": 0, "exemplos": []})
        e["count"] += 1
        if len(e["exemplos"]) < 5:
            e["exemplos"].append(
                {"code": code, "address": (entry or {}).get("address")}
            )
    ranking = sorted(por_mot.values(), key=lambda x: -x["count"])
    return {"total": sum(e["count"] for e in ranking), "por_motorista": ranking}


def ranking_devolucao(dias: int = 30, limit: int = 10) -> list[dict[str, Any]]:
    """Top entregadores que mais retornam pacotes (últimos N dias)."""
    from datetime import timedelta

    from app.timezone import hoje_sp

    supabase = get_supabase()
    try:
        rows = (
            supabase.table("galpao_scans")
            .select("codigo_pacote,motorista_id,escaneado_em")
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception:
        return []
    corte = (hoje_sp() - timedelta(days=dias)).isoformat()
    cont: dict = {}
    for r in rows:
        if not r.get("motorista_id"):
            continue
        if str(r.get("escaneado_em") or "") < corte and r.get("escaneado_em"):
            continue
        code = str(r.get("codigo_pacote") or "").strip().upper()
        if not code:
            continue
        cont[r["motorista_id"]] = cont.get(r["motorista_id"], set())
        cont[r["motorista_id"]].add(code)
    if not cont:
        return []
    nomes: dict = {}
    mids = list(cont.keys())
    for i in range(0, len(mids), 100):
        try:
            mm = (
                supabase.table("motoristas")
                .select("id,nome")
                .in_("id", mids[i : i + 100])
                .limit(500)
                .execute()
                .data
                or []
            )
            for x in mm:
                nomes[x["id"]] = x.get("nome")
        except Exception:
            pass
    rank = [
        {"nome": nomes.get(mid, "?"), "total": len(codes)}
        for mid, codes in cont.items()
    ]
    rank.sort(key=lambda x: -x["total"])
    return rank[:limit]


def listar_sessoes(limit: int = 15) -> list[dict[str, Any]]:
    """Últimas sessões com contagem, da mais recente p/ a mais antiga.

    Sessão é DD-MM-YYYY; ordena por data real (inverte p/ ISO na ordenação).
    """
    supabase = get_supabase()
    try:
        res = (
            supabase.table("galpao_scans")
            .select("sessao_id,escaneado_em")
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception:
        return []
    from collections import Counter

    cont: Counter = Counter()
    visto: dict = {}
    for r in res:
        s = str(r.get("sessao_id") or "").strip()
        if not s:
            continue
        cont[s] += 1
        esc = str(r.get("escaneado_em") or "")
        if s not in visto or esc > visto[s]:
            visto[s] = esc

    def chave(s: str) -> str:
        import re

        m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", s)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        return ""

    sessoes = [{"sessao_id": s, "total": cont[s]} for s in cont]
    sessoes.sort(key=lambda x: chave(x["sessao_id"]) or "", reverse=True)
    return sessoes[:limit]


def sessao_hoje_sp() -> str:
    """Sessão padrão: hoje em SP no formato DD-MM-YYYY (igual ao PWA)."""
    from app.timezone import agora_sp

    return agora_sp().strftime("%d-%m-%Y")


def resolver_sessao(sessao_pedida: str | None) -> tuple[str, list[dict]]:
    """Resolve qual sessão abrir: pedida > hoje (se tem dados) > última com dados.

    Retorna (sessao_id, sessoes_recentes).
    """
    sessoes = listar_sessoes()
    if sessao_pedida and sessao_pedida.strip():
        return sessao_pedida.strip(), sessoes
    hoje = sessao_hoje_sp()
    if any(s["sessao_id"] == hoje for s in sessoes):
        return hoje, sessoes
    if sessoes:
        return sessoes[0]["sessao_id"], sessoes
    return hoje, sessoes


def get_session_scans_enriquecidos(sessao_id: str) -> list[dict[str, Any]]:
    """Scans da sessão com código, rota, motorista e endereço resolvidos."""
    supabase = get_supabase()
    try:
        res = (
            supabase.table("galpao_scans")
            .select("*")
            .eq("sessao_id", sessao_id)
            .order("escaneado_em", desc=True)
            .limit(2000)
            .execute()
        )
    except Exception:
        return []
    rows = res.data or []
    items = []
    for r in rows:
        code = str(r.get("codigo_pacote") or r.get("code") or "").strip().upper()
        if not code:
            continue
        items.append(
            {
                "code": code,
                "rota_id": r.get("rota_id"),
                "motorista_id": r.get("motorista_id"),
                "endereco": r.get("endereco") or r.get("address"),
                "escaneado_em": r.get("escaneado_em"),
            }
        )
    # Nomes em batch (2 queries por lote, não 2 por pacote)
    mids = list({i["motorista_id"] for i in items if i["motorista_id"]})
    rids = list({i["rota_id"] for i in items if i["rota_id"]})
    nomes: dict = {}
    rotas: dict = {}
    for i in range(0, len(mids), 100):
        try:
            m = (
                supabase.table("motoristas")
                .select("id,nome")
                .in_("id", mids[i : i + 100])
                .limit(500)
                .execute()
            )
            for x in m.data or []:
                nomes[x["id"]] = x.get("nome")
        except Exception:
            pass
    for i in range(0, len(rids), 100):
        try:
            q = (
                supabase.table("rotas")
                .select("id,rota,session_date")
                .in_("id", rids[i : i + 100])
                .limit(500)
                .execute()
            )
            for x in q.data or []:
                rotas[x["id"]] = (x.get("rota"), x.get("session_date"))
        except Exception:
            try:
                q = (
                    supabase.table("rotas")
                    .select("id,rota")
                    .in_("id", rids[i : i + 100])
                    .limit(500)
                    .execute()
                )
                for x in q.data or []:
                    rotas[x["id"]] = (x.get("rota"), None)
            except Exception:
                pass
    out = []
    for item in items:
        rn, rd = (
            rotas.get(item["rota_id"], (None, None))
            if item["rota_id"]
            else (None, None)
        )
        out.append(
            {
                "code": item["code"],
                "rota_nome": rn,
                "rota_data": rd,
                "motorista_nome": nomes.get(item["motorista_id"])
                if item["motorista_id"]
                else None,
                "endereco": item["endereco"],
                "escaneado_em": item["escaneado_em"],
            }
        )
    return out
