"""
Upload Service - Import JSON routes to Supabase.

Enriquece cada pacote no ato do upload com:
- nome_comprador / telefone / cidade (do JSON: paradas[].contatos[])
- descricao_produto / valor_produto / status_looker (por ID via
  Supabase `product_descriptions` + fallback local `data/descricao_map.json`)
"""

import json
from pathlib import Path
from typing import Any

from app.supabase_client import get_supabase

_DESC_MAP: dict | None = None


def _carregar_mapa_local() -> dict:
    """Carrega descricao_map.json local (bundled em data/). Cache em memória."""
    global _DESC_MAP
    if _DESC_MAP is not None:
        return _DESC_MAP
    _DESC_MAP = {}
    candidatos = [
        Path(__file__).resolve().parents[2] / "data" / "descricao_map.json",
        Path.cwd() / "data" / "descricao_map.json",
        Path(r"C:\Users\Jeremias\Downloads\MELI CONTATOS\A_DADOS\descricao_map.json"),
    ]
    for p in candidatos:
        try:
            if p.exists():
                _DESC_MAP = json.loads(p.read_text(encoding="utf-8"))
                break
        except Exception:
            continue
    return _DESC_MAP or {}


def _buscar_descricoes_supabase(supabase, codigos: list[str]) -> dict:
    """Busca descrições em lote na tabela product_descriptions. Best-effort."""
    resultado: dict[str, dict] = {}
    if not supabase or not codigos:
        return resultado
    try:
        unicos = sorted(set(codigos))
        for i in range(0, len(unicos), 200):
            lote = unicos[i : i + 200]
            r = (
                supabase.table("product_descriptions")
                .select("package_id,descricao,valor,status_looker")
                .in_("package_id", lote)
                .execute()
            )
            for row in r.data or []:
                pid = str(row.get("package_id") or "").strip().upper()
                if pid:
                    resultado[pid] = {
                        "descricao": row.get("descricao") or "",
                        "valor": row.get("valor") or "",
                        "status": row.get("status_looker") or "",
                    }
    except Exception:
        pass
    return resultado


def _payload_enriquecido(codigo: str, contato: dict, desc: dict | None) -> dict:
    """Monta payload do pacote com contato + descrição (só campos preenchidos)."""
    payload: dict[str, Any] = {}
    if contato:
        if contato.get("nome_comprador"):
            payload["nome_comprador"] = contato["nome_comprador"]
        if contato.get("telefone"):
            payload["telefone"] = contato["telefone"]
        if contato.get("cidade"):
            payload["cidade"] = contato["cidade"]
    if desc:
        if desc.get("descricao"):
            payload["descricao_produto"] = desc["descricao"]
        if desc.get("valor"):
            payload["valor_produto"] = desc["valor"]
        if desc.get("status"):
            payload["status_looker"] = desc["status"]
    return payload


def importar_json_para_supabase(dados_json: dict) -> dict[str, Any]:
    """Import route JSON to Supabase - com upsert e fallback romaneio (igual ao app celular)."""
    supabase = get_supabase()
    try:
        rota_nome = (
            str(dados_json.get("rota") or dados_json.get("route") or "").strip().upper()
        )
        if not rota_nome:
            return {"success": False, "message": "JSON sem campo rota"}
        id_original = str(dados_json.get("id") or "").strip()
        total_paradas = dados_json.get("totalParadas") or len(
            dados_json.get("paradas") or []
        )
        total_pacotes = dados_json.get("totalPacotes") or sum(
            len(p.get("pacotes") or []) for p in dados_json.get("paradas") or []
        )

        # 1) busca rota existente da MESMA DATA (hoje SP) - mesmo nome em dias diferentes = nova rota
        from app.timezone import agora_sp, hoje_sp

        hoje = hoje_sp().isoformat()
        rota_id = None
        # tenta por id_original + data de hoje (session_date manda; criado_em é fallback)
        if id_original:
            try:
                r = (
                    supabase.table("rotas")
                    .select("id,criado_em,session_date")
                    .eq("id_original", id_original)
                    .execute()
                )
                for row in r.data or []:
                    dia = (row.get("session_date") or "")[:10] or (
                        row.get("criado_em") or ""
                    )[:10]
                    if dia == hoje:
                        rota_id = row["id"]
                        break
            except:
                pass
        # tenta por nome + data de hoje
        if not rota_id:
            try:
                r = (
                    supabase.table("rotas")
                    .select("id,criado_em,session_date")
                    .eq("rota", rota_nome)
                    .execute()
                )
                for row in r.data or []:
                    dia = (row.get("session_date") or "")[:10] or (
                        row.get("criado_em") or ""
                    )[:10]
                    if dia == hoje:
                        rota_id = row["id"]
                        break
            except:
                pass

        if not rota_id:
            import uuid

            rota_id = str(uuid.uuid4())
            ins = (
                supabase.table("rotas")
                .insert(
                    {
                        "id": rota_id,
                        "rota": rota_nome,
                        "id_original": id_original,
                        "total_paradas": total_paradas,
                        "total_pacotes": total_pacotes,
                        "observacao": dados_json.get("observacao", ""),
                        "cidade": dados_json.get("cidade", ""),
                        # SEMPRE datada (SP): sem isso nasce NULL e some dos filtros do dia
                        "session_date": hoje,
                    }
                )
                .execute()
            )
            if ins.data:
                rota_id = ins.data[0]["id"]
        else:
            try:
                supabase.table("rotas").update(
                    {
                        "total_paradas": total_paradas,
                        "total_pacotes": total_pacotes,
                        "session_date": hoje,
                        "atualizado_em": agora_sp().isoformat(),
                    }
                ).eq("id", rota_id).execute()
            except:
                pass

        # 1b) pré-carrega descrições por ID (Supabase primeiro, local como fallback)
        todos_codigos: list[str] = []
        for parada in dados_json.get("paradas") or []:
            for code in parada.get("pacotes") or []:
                c = str(code).strip().upper()
                if c:
                    todos_codigos.append(c)
        desc_sb = _buscar_descricoes_supabase(supabase, todos_codigos)
        mapa_local = _carregar_mapa_local()

        importados = 0
        atualizados = 0
        com_contato = 0
        com_descricao = 0
        fallback_minimo = False

        for idx, parada in enumerate(dados_json.get("paradas") or []):
            seq = str(parada.get("sequencia") or "").strip()
            if not seq or seq == "-" or not seq.isdigit():
                seq = str(idx + 1).zfill(2)
            else:
                seq = seq.zfill(2)
            endereco = str(parada.get("endereco") or "").strip()
            tipo = parada.get("tipo_endereco") or "Residencial"
            # mapa pacote -> contato desta parada
            cmap: dict[str, dict] = {}
            for ct in parada.get("contatos") or []:
                try:
                    key = str(ct.get("pacote") or "").strip().upper()
                except Exception:
                    continue
                if key:
                    cmap[key] = {
                        "nome_comprador": str(ct.get("nome_comprador") or "").strip(),
                        "telefone": str(ct.get("telefone") or "").strip(),
                        "cidade": str(ct.get("cidade") or "").strip(),
                    }

            parada_id = None
            try:
                rp = (
                    supabase.table("paradas")
                    .select("id")
                    .eq("rota_id", rota_id)
                    .eq("sequencia", seq)
                    .limit(1)
                    .execute()
                )
                if rp.data:
                    parada_id = rp.data[0]["id"]
            except:
                pass
            if not parada_id:
                import uuid

                parada_id = str(uuid.uuid4())
                try:
                    ins = (
                        supabase.table("paradas")
                        .insert(
                            {
                                "id": parada_id,
                                "rota_id": rota_id,
                                "sequencia": seq,
                                "endereco": endereco,
                                "tipo_endereco": tipo,
                            }
                        )
                        .execute()
                    )
                    if ins.data:
                        parada_id = ins.data[0]["id"]
                except Exception as e:
                    # RLS bloqueando paradas -> fallback para romaneio
                    if "row-level security" in str(e).lower() or "42501" in str(e):
                        for code in parada.get("pacotes") or []:
                            c = str(code).strip().upper()
                            if not c:
                                continue
                            try:
                                supabase.table("romaneio").upsert(
                                    {
                                        "id": str(uuid.uuid4()),
                                        "route": rota_nome,
                                        "code": c,
                                        "sequence": int(seq)
                                        if seq.isdigit()
                                        else idx + 1,
                                        "address": endereco,
                                        "neighborhood": tipo,
                                    },
                                    on_conflict="id",
                                ).execute()
                                importados += 1
                            except:
                                pass
                        continue
                    else:
                        continue

            for code in parada.get("pacotes") or []:
                c = str(code).strip().upper()
                if not c:
                    continue
                contato = cmap.get(c) or {}
                desc = desc_sb.get(c)
                if not desc:
                    m = mapa_local.get(c) or {}
                    if m:
                        desc = {
                            "descricao": m.get("descricao") or "",
                            "valor": m.get("valor") or "",
                            "status": m.get("status") or "",
                        }
                extra = _payload_enriquecido(c, contato, desc)
                if contato.get("nome_comprador") or contato.get("telefone"):
                    com_contato += 1
                if (desc or {}).get("descricao"):
                    com_descricao += 1

                try:
                    ex = (
                        supabase.table("pacotes")
                        .select("id")
                        .eq("parada_id", parada_id)
                        .eq("codigo_pacote", c)
                        .limit(1)
                        .execute()
                    )
                    existente = ex.data[0]["id"] if ex.data else None
                except:
                    existente = None
                if existente:
                    if extra:
                        try:
                            supabase.table("pacotes").update(extra).eq(
                                "id", existente
                            ).execute()
                        except Exception as e:
                            # coluna ainda não migrada no banco -> ignora enriquecimento
                            if "column" in str(e).lower() or "PGRST" in str(e):
                                fallback_minimo = True
                    atualizados += 1
                    continue
                row = {"parada_id": parada_id, "codigo_pacote": c, "status": "pendente"}
                row.update(extra)
                try:
                    supabase.table("pacotes").insert(row).execute()
                    importados += 1
                except Exception as e:
                    msg = str(e).lower()
                    if "column" in msg or "pgrst" in msg or "schema cache" in msg:
                        # banco sem as novas colunas: insere o mínimo para não perder a rota
                        fallback_minimo = True
                        try:
                            supabase.table("pacotes").insert(
                                {
                                    "parada_id": parada_id,
                                    "codigo_pacote": c,
                                    "status": "pendente",
                                }
                            ).execute()
                            importados += 1
                        except Exception as e2:
                            if "row-level security" in str(
                                e2
                            ).lower() or "42501" in str(e2):
                                try:
                                    import uuid

                                    supabase.table("romaneio").upsert(
                                        {
                                            "id": str(uuid.uuid4()),
                                            "route": rota_nome,
                                            "code": c,
                                            "sequence": int(seq)
                                            if seq.isdigit()
                                            else idx + 1,
                                            "address": endereco,
                                        },
                                        on_conflict="id",
                                    ).execute()
                                    importados += 1
                                except:
                                    pass
                    elif "row-level security" in msg or "42501" in msg:
                        try:
                            import uuid

                            supabase.table("romaneio").upsert(
                                {
                                    "id": str(uuid.uuid4()),
                                    "route": rota_nome,
                                    "code": c,
                                    "sequence": int(seq) if seq.isdigit() else idx + 1,
                                    "address": endereco,
                                },
                                on_conflict="id",
                            ).execute()
                            importados += 1
                        except:
                            pass

        # best-effort: sincroniza descrições de pacotes antigos via RPC (se existir)
        try:
            supabase.rpc("sync_pacotes_descriptions").execute()
        except Exception:
            pass

        detalhe = (
            f"Rota {rota_nome} sincronizada: {importados} novos, {atualizados} atualizados "
            f"({total_pacotes} no arquivo) em {len(dados_json.get('paradas') or [])} paradas | "
            f"{com_contato} com contato, {com_descricao} com descrição"
        )
        if fallback_minimo:
            detalhe += " | AVISO: rode migracao_descriptions.sql no Supabase para gravar contato/descrição"
        return {"success": True, "message": detalhe}

    except Exception as e:
        return {"success": False, "message": f"Erro: {e!s}"}
