"""Full scan do Looker em FATIAS resumiveis (nuvem-ready).

- Le a pagina inicial em scan_state(last_page) e avanca rapido ate la
- Coleta PAGES paginas (scroll + parse) com upsert direto no Supabase
- Atualiza scan_state a cada pagina (resume seguro entre runs)

Env:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  GOOGLE_COOKIES (conteudo Netscape) ou COOKIES_PATH
  PAGES (padrao 120) | HEADLESS (padrao 1)
"""
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()
from supabase import create_client
from playwright.sync_api import sync_playwright

URL = "https://datastudio.google.com/u/0/reporting/112f0bdc-ae58-477f-af52-7be2a71c3629/page/tEnnC?pli=1"
PAGES = int(os.getenv("PAGES", "120"))
HEADLESS = os.getenv("HEADLESS", "1") == "1"

sb = create_client(os.getenv("SUPABASE_URL"),
                   os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def log(m, **kw):
    print(m, flush=True)


def get_state():
    try:
        r = sb.table("scan_state").select("last_page").eq("id", 1).limit(1).execute()
        if r.data:
            return int(r.data[0].get("last_page") or 1)
    except Exception as e:
        log(f"scan_state indisponivel ({str(e)[:100]}), comecando da pag 1")
    return 1


def set_state(pag):
    try:
        sb.table("scan_state").upsert(
            {"id": 1, "last_page": pag}, on_conflict="id").execute()
    except Exception as e:
        log(f"falha ao salvar estado: {str(e)[:100]}")


def upsert_batch(mapa: dict):
    items = [{"package_id": k, "descricao": v["descricao"],
              "valor": v["valor"], "status": v["status"]}
             for k, v in mapa.items()]
    for i in range(0, len(items), 500):
        sb.rpc("upsert_product_descriptions",
               {"descriptions": items[i:i + 500]}).execute()


def parse_visivel(body):
    linhas = [l.strip() for l in body.split("\n")]
    res = {}
    i = 0
    while i < len(linhas):
        if re.fullmatch(r"(47|48)\d{9}", linhas[i] or ""):
            pid = linhas[i]
            status = linhas[i + 1] if i + 1 < len(linhas) else ""
            desc = linhas[i + 2] if i + 2 < len(linhas) else ""
            valor = ""
            if i + 3 < len(linhas):
                mv = re.search(r"R\$\s*([\d.,]+)", linhas[i + 3])
                valor = mv.group(1) if mv else ""
            if desc and not re.fullmatch(r"(47|48)\d{9}", desc) and "R$" not in desc:
                res[pid] = {"status": status[:40], "descricao": desc[:200], "valor": valor}
            i += 4
        else:
            i += 1
    return res


# cookies
raw = os.getenv("GOOGLE_COOKIES", "")
cpath = os.getenv("COOKIES_PATH", "")
lines = ([l for l in raw.splitlines() if l.strip() and not l.startswith("#")]
         if raw.strip()
         else [l.strip() for l in open(cpath, encoding="utf-8")]
         if cpath else [])
cookies = []
for line in lines:
    p = line.split("\t")
    if len(p) < 7:
        continue
    domain, _, path, secure, exp, name, val = p[:7]
    cookies.append({"name": name, "value": val, "domain": domain, "path": path,
                    "secure": secure.upper() == "TRUE",
                    "expires": int(float(exp)) if exp.isdigit() else -1,
                    "sameSite": "None" if secure.upper() == "TRUE" else "Lax"})
assert cookies, "Sem cookies (GOOGLE_COOKIES ou COOKIES_PATH)"

inicio = get_state()
log(f"estado inicial: pag {inicio} | meta: +{PAGES} pags")

with sync_playwright() as x:
    b = x.chromium.launch(headless=HEADLESS, args=["--no-sandbox"])
    c = b.new_context(viewport={"width": 1600, "height": 1000}, locale="pt-BR")
    c.add_cookies(cookies)
    pg = c.new_page()
    pg.goto(URL, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(12000)
    if "accounts.google.com" in pg.url:
        log("SESSAO EXPIRADA: atualize o secret GOOGLE_COOKIES.")
        b.close()
        raise SystemExit(2)

    def lbl():
        try:
            return pg.evaluate("() => { const l = document.querySelector('.pageLabel'); return l ? l.textContent.trim() : ''; }")
        except Exception:
            return ""

    def espera(diferente_de=None, ts=25):
        import time as _t
        t0 = _t.time()
        while _t.time() - t0 < ts:
            l = lbl()
            if l and l != (diferente_de or ""):
                return l
            pg.wait_for_timeout(1200)
        return lbl()

    log("tabela: " + espera())

    # SEEK rapido ate a pagina do estado (sem scroll/coleta)
    if inicio > 1:
        log(f"avancando ate pag {inicio}...")
        for _ in range(inicio - 1):
            antes = lbl()
            pg.evaluate("""() => { const f = document.querySelector('.pageForward');
                if (f && !f.classList.contains('disabled')) f.click(); }""")
            novo = espera(diferente_de=antes, ts=15)
            if novo == antes:
                break
        log("posicionado em: " + lbl())

    # COLETA
    pag = inicio
    for _ in range(PAGES):
        antes_total = None
        pg.evaluate("""async () => {
            const cont = document.querySelector('.centerColsContainer');
            const roda = () => new Promise(r => setTimeout(r, 500));
            if (cont) { cont.scrollTop = 0; await roda(); }
            for (let i = 0; i < 25; i++) {
                if (!cont || cont.scrollTop + cont.clientHeight >= cont.scrollHeight - 20) break;
                cont.scrollTop += 500;
                await roda();
            }
        }""")
        mapa = {}
        for frac in [0, 0.5, 1.0]:
            pg.evaluate(f"""() => {{ const cont = document.querySelector('.centerColsContainer');
                if (cont) cont.scrollTop = cont.scrollHeight * {frac}; }}""")
            pg.wait_for_timeout(900)
            mapa.update(parse_visivel(pg.inner_text("body")))
        if mapa:
            upsert_batch(mapa)
        try:
            sb.rpc("sync_pacotes_descriptions").execute()
        except Exception:
            pass
        log(f"pag {pag} [{lbl()}]: +{len(mapa)} ids", flush=True)
        set_state(pag + 1)
        # proxima
        lbl_antes = lbl()
        avancou = False
        for _ in range(6):
            pg.evaluate("""() => { const f = document.querySelector('.pageForward');
                if (f && !f.classList.contains('disabled')) f.click(); }""")
            if espera(diferente_de=lbl_antes, ts=12) != lbl_antes:
                avancou = True
                break
        pag += 1
        if not avancou:
            dis = pg.evaluate("() => { const f = document.querySelector('.pageForward'); return !f || f.classList.contains('disabled'); }")
            if dis:
                log("ultima pagina: reiniciando do inicio na proxima run")
                set_state(1)
                break
    b.close()
log("FIM fatia")
