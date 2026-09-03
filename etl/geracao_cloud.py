#!/usr/bin/env python3
"""ETL na nuvem (GitHub Actions): rotas de Ibotirama + compartilhadas -> Supabase.
   Sessao: AUTH_STATE_PATH (do secret OKTA_AUTH_STATE na 1a vez, depois do cache).
   Renovacao automatica se OKTA_TOTP_SEED + OKTA_USER/OKTA_PASS configurados.
   Uso: python etl/geracao_cloud.py [--only-jobs]"""
import json, time, sys, os, unicodedata
from pathlib import Path
from datetime import datetime, date

AUTH_PATH = Path(os.getenv("AUTH_STATE_PATH", "auth_state.json"))
HOJE = date.today().strftime("%Y-%m-%d")

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")

JS_DET = """async ({lote, csrf}) => {
    const re = /<span class="andes-form-control__label">([^<]+)<\\/span><\\/label><div class="andes-form-control__control"><input[^>]*?value="([^"]*)"/gs;
    const out = [];
    await Promise.all(lote.map(async (pid) => {
        try {
            const res = await fetch(`/logistics/package-management/3pl/package/${pid}`, {headers:{'x-csrf-token':csrf}, credentials:'include'});
            const buf = await res.arrayBuffer();
            const bytes = new Uint8Array(buf);
            let s = '';
            for (let j = 0; j < bytes.length; j++) s += String.fromCharCode(bytes[j]);
            let txt = '';
            try { txt = decodeURIComponent(escape(s)); } catch(e) { txt = s; }
            const vals = {};
            let m; re.lastIndex = 0;
            while ((m = re.exec(txt)) !== null) vals[m[1].trim()] = m[2];
            const pick = (test) => { for (const k of Object.keys(vals)) if (test(k)) return vals[k]; return ''; };
            const rua = vals['Rua'] || '';
            const num = pick(k => k.toLowerCase().replace(/[^a-z]/g,'').includes('mero'));
            const tipo = pick(k => k.toLowerCase().includes('tipo'));
            out.push({pid, nome: vals['Nome completo'] || '', tel: vals['Telefone'] || '',
                      end: (rua + ' ' + num).trim(), cidade: vals['Cidade'] || '',
                      bairro: vals['Bairro'] || '', tipo: tipo || 'Residencial'});
        } catch(e) { out.push({pid, erro: String(e).slice(0,60)}); }
    }));
    return out;
}"""

def monta_paradas(dets):
    paradas, ordem = {}, []
    for det in dets:
        if "erro" in det:
            continue
        chave = det["end"] or f"SEM ENDERECO {det['pid']}"
        if chave not in paradas:
            paradas[chave] = {"sequencia": "", "endereco": chave, "pacotes": [],
                              "tipo_endereco": det["tipo"] or "Residencial", "contatos": []}
            ordem.append(chave)
        elif det["tipo"].lower().startswith("comer"):
            paradas[chave]["tipo_endereco"] = det["tipo"]
        paradas[chave]["pacotes"].append(det["pid"])
        paradas[chave]["contatos"].append({"pacote": det["pid"], "nome_comprador": det["nome"],
                                           "telefone": det["tel"], "cidade": det.get("cidade", "")})
    lista = [paradas[k] for k in ordem]
    for i, par in enumerate(lista, 1):
        par["sequencia"] = f"{i:02d}" if i < len(lista) else "-"
    return lista

# --- supabase ---
from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
try:
    sb.table("pacotes").select("id,cidade").limit(1).execute()
    HAS_CIDADE = True
except Exception:
    HAS_CIDADE = False
    log("sem coluna pacotes.cidade; seguindo sem ela")

import uuid
def upsert_rota(rota_nome, id_original, cidade, paradas, observacao=""):
    paradas = list(paradas)
    total_pac = sum(len(p["pacotes"]) for p in paradas)
    rota_id = None
    for col, val in (("id_original", id_original), ("rota", rota_nome)):
        if not val:
            continue
        r = sb.table("rotas").select("id,criado_em").eq(col, val).execute()
        for row in (r.data or []):
            if (row.get("criado_em") or "")[:10] == HOJE:
                rota_id = row["id"]; break
        if rota_id:
            break
    if not rota_id:
        rota_id = str(uuid.uuid4())
        ins = sb.table("rotas").insert({"id": rota_id, "rota": rota_nome, "id_original": id_original,
            "total_paradas": len(paradas), "total_pacotes": total_pac,
            "observacao": observacao, "cidade": cidade}).execute()
        if ins.data:
            rota_id = ins.data[0]["id"]
    else:
        sb.table("rotas").update({"total_paradas": len(paradas), "total_pacotes": total_pac,
            "cidade": cidade, "observacao": observacao,
            "atualizado_em": datetime.utcnow().isoformat()}).eq("id", rota_id).execute()
    novos = 0
    for idx, par in enumerate(paradas):
        seq = par["sequencia"]
        seq = str(idx + 1).zfill(2) if (not seq or seq == "-" or not seq.isdigit()) else seq.zfill(2)
        rp = sb.table("paradas").select("id").eq("rota_id", rota_id).eq("sequencia", seq).limit(1).execute()
        parada_id = rp.data[0]["id"] if rp.data else None
        if not parada_id:
            parada_id = str(uuid.uuid4())
            ins = sb.table("paradas").insert({"id": parada_id, "rota_id": rota_id, "sequencia": seq,
                "endereco": par["endereco"], "tipo_endereco": par.get("tipo_endereco") or "Residencial"}).execute()
            if ins.data:
                parada_id = ins.data[0]["id"]
        for c in par["contatos"]:
            code = str(c["pacote"]).strip().upper()
            ex = sb.table("pacotes").select("id").eq("parada_id", parada_id).eq("codigo_pacote", code).limit(1).execute()
            row = {"nome_comprador": c.get("nome_comprador") or None, "telefone": c.get("telefone") or None}
            if HAS_CIDADE:
                row["cidade"] = c.get("cidade") or None
            row = {k: v for k, v in row.items() if v}
            if ex.data:
                if row:
                    sb.table("pacotes").update(row).eq("id", ex.data[0]["id"]).execute()
                continue
            row.update({"parada_id": parada_id, "codigo_pacote": code, "status": "pendente"})
            sb.table("pacotes").insert(row).execute()
            novos += 1
    log(f"Supabase {rota_nome}: {len(paradas)} paradas, {novos} pacotes novos")
    return rota_id

def set_job(jid, **kw):
    kw["atualizado_em"] = datetime.utcnow().isoformat()
    sb.table("jobs").update(kw).eq("id", jid).execute()

# --- MELI ---
from playwright.sync_api import sync_playwright


def listar_pacotes(api_get, filtro=None):
    """Varre /api/packages/ e retorna {routeId: [ids]} (filtrado se filtro dado)."""
    grupos, limit, offset, total = {}, 100, 0, None
    while True:
        rr = api_get(f"https://envios.adminml.com/logistics/package-management/api/packages/?offset={offset}&limit={limit}")
        d = json.loads(rr["b"])
        if total is None:
            total = d.get("total", 0)
        for pkg in d.get("packages", []):
            rid = str(pkg.get("routeId"))
            if filtro is None or rid in filtro:
                grupos.setdefault(rid, []).append(str(pkg["id"]))
        offset += limit
        if offset >= total:
            break
    return grupos


def run_daily(api_post, api_get, fetch_dets, job_note=""):
    log(f"inicio {job_note}")
    rotas, pg = [], 1
    while True:
        rr = api_post("/logistics/api/monitoring/get-routes-list",
                      {"serviceCenterId": "SBA7", "page": pg, "pageSize": 50, "siteId": "MLB", "order_by": "performance"})
        d = json.loads(rr["b"])
        rotas.extend(d.get("routes", []))
        if not d.get("pagination", {}).get("hasNext"):
            break
        pg += 1
    nomes = {str(r["id"]): (r.get("cluster") or str(r["id"])).replace(">", "") for r in rotas}
    log(f"rotas hoje: {len(nomes)}")

    grupos = listar_pacotes(api_get)
    # 1 amostra por rota -> cidade
    rid_cidade = {}
    amostras = [(rid, ids[0]) for rid, ids in grupos.items() if ids]
    for i in range(0, len(amostras), 15):
        for r in fetch_dets([pid for _, pid in amostras[i:i + 15]]):
            for rid, pid in amostras[i:i + 15]:
                if pid == r.get("pid"):
                    rid_cidade[rid] = r.get("cidade", "")
    ib = [rid for rid, cid in rid_cidade.items() if "ibotirama" in norm(cid)]
    log(f"Ibotirama: {[(nomes.get(r, r), r) for r in ib if r in nomes]}")
    for rid in ib:
        if rid not in nomes:
            continue
        dets = fetch_dets(grupos.get(rid, []))
        for x in dets:
            x["cidade"] = "Ibotirama"
        upsert_rota(nomes[rid], rid, "Ibotirama", monta_paradas(dets))
    # compartilhadas: rotas de hoje com pacotes de Ibotirama (importa COMPLETA)
    from collections import Counter
    resto = [rid for rid in nomes if rid not in ib]
    todos = [(rid, pid) for rid in resto for pid in grupos.get(rid, [])]
    log(f"rastreando {len(todos)} pacotes de outras rotas...")
    det_por_pid = {}
    for i in range(0, len(todos), 15):
        lote = todos[i:i + 15]
        for r in fetch_dets([pid for _, pid in lote]):
            det_por_pid[r.get("pid")] = r
    ach = {}
    for rid, pid in todos:
        if "ibotirama" in norm(det_por_pid.get(pid, {}).get("cidade", "")):
            ach.setdefault(rid, []).append(pid)
    log(f"compartilhadas: {[(nomes.get(r, r), len(v)) for r, v in ach.items()]}")
    for rid in ach:
        dets = [det_por_pid[pid] for pid in grupos.get(rid, []) if pid in det_por_pid]
        if not dets:
            continue
        maioria = Counter(d.get("cidade", "?") for d in dets).most_common(1)[0][0]
        n_ib = len(ach[rid])
        upsert_rota(nomes.get(rid, rid), rid, maioria, monta_paradas(dets),
                    observacao=f"Compartilhada: {n_ib} pacotes de Ibotirama")
    log("run_daily ok")

def relogin_com_seed(page, context):
    """Renova a sessao usando OKTA_TOTP_SEED (pyotp). Retorna True/False."""
    import pyotp
    seed = os.environ.get("OKTA_TOTP_SEED", "").replace(" ", "")
    user = os.environ.get("OKTA_USER", "ext_almeida")
    pwd = os.environ.get("OKTA_PASS", "")
    if not (seed and pwd):
        return False
    page.goto("https://envios.adminml.com/logistics/monitoring-distribution", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    try:
        page.wait_for_selector('input[name="identifier"]', timeout=8000).fill(user)
        page.wait_for_timeout(400)
        page.query_selector('input[type="submit"], button[type="submit"]').click()
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        t = page.query_selector('input[name="credentials.totp"]')
        if not (t and t.is_visible()):
            return False
        t.fill(pyotp.TOTP(seed).now())
        page.wait_for_timeout(400)
        page.query_selector('input[type="submit"], button:has-text("Verify"), button[type="submit"]').click()
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        pw = page.query_selector('input[type="password"]')
        if pw and pw.is_visible():
            pw.fill(pwd)
            page.wait_for_timeout(400)
            page.query_selector('input[type="submit"], button[type="submit"]').click()
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(3000)
        ok = "envios.adminml.com" in page.url and "auth-meli" not in page.url
        if ok:
            context.storage_state(path=str(AUTH_PATH))
        return ok
    except Exception as e:
        log(f"relogin: {e}")
        return False

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(storage_state=str(AUTH_PATH) if AUTH_PATH.exists() else None)
    page = context.new_page()
    page.goto("https://envios.adminml.com/logistics/package-management/3pl", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(6000)
    if "auth-meli" in page.url or "login" in page.url:
        log("sessao expirada; tentando renovar com seed...")
        if not relogin_com_seed(page, context):
            log("FALHA renovacao: cadastre OKTA_TOTP_SEED ou renove pelo PC/celular.")
            browser.close(); sys.exit(2)
        log("sessao renovada")
        page.goto("https://envios.adminml.com/logistics/package-management/3pl", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
    csrf = page.evaluate("() => document.querySelector('meta[name=\"csrf-token\"]')?.content || ''")

    def api_post(path, payload):
        return page.evaluate("""async ({path, payload, csrf}) => {
            const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json','x-csrf-token':csrf}, credentials:'include', body: JSON.stringify(payload)});
            return {s: res.status, b: await res.text()};
        }""", {"path": path, "payload": payload, "csrf": csrf})

    def api_get(url):
        return page.evaluate("""async ({url, csrf}) => {
            const res = await fetch(url, {headers:{'x-csrf-token':csrf,'Accept':'application/json'}, credentials:'include'});
            return {s: res.status, b: await res.text()};
        }""", {"url": url, "csrf": csrf})

    def fetch_dets(ids):
        dets = []
        for i in range(0, len(ids), 15):
            dets.extend(page.evaluate(JS_DET, {"lote": ids[i:i + 15], "csrf": csrf}))
        return [x for x in dets if "erro" not in x]

    def fetch_dets(ids):
        dets = []
        for i in range(0, len(ids), 15):
            dets.extend(page.evaluate(JS_DET, {"lote": ids[i:i + 15], "csrf": csrf}))
        return [x for x in dets if "erro" not in x]

    # jobs pendentes do tipo gerar (disparo pelo celular)
    pend = sb.table("jobs").select("*").eq("status", "pendente").eq("tipo", "gerar_ibotirama").order("criado_em").execute().data or []
    log(f"jobs pendentes: {len(pend)}")
    for job in pend:
        set_job(job["id"], status="executando", log="iniciado na nuvem")
    if pend or "--only-jobs" not in sys.argv:
        try:
            run_daily(api_post, api_get, fetch_dets, job_note=f"{len(pend)} job(s)")
            for job in pend:
                set_job(job["id"], status="concluido", log="rotas de Ibotirama geradas")
        except Exception as e:
            for job in pend:
                set_job(job["id"], status="erro", log=str(e)[:1000])
    browser.close()
log("FIM")
