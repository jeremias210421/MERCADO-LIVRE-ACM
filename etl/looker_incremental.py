"""Job incremental de descricoes do Looker (nuvem-ready).

1) busca no Supabase os pacotes SEM descricao (distintos, recentes primeiro)
2) filtra um por um no Looker via cookies (GOOGLE_COOKIES ou arquivo)
3) upsert em product_descriptions + sync nos pacotes

Env:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (obrigatorias)
  GOOGLE_COOKIES  (conteudo Netscape cookies.txt)  OU  COOKIES_PATH (arquivo)
  LIMITE  (padrao 200)
"""
import os
import re
import sys
import time
from pathlib import Path

URL = "https://datastudio.google.com/u/0/reporting/112f0bdc-ae58-477f-af52-7be2a71c3629/page/tEnnC?pli=1"
LIMITE = int(os.getenv("LIMITE", "200"))

from dotenv import load_dotenv

load_dotenv()
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SECRET_KEY")
    or os.getenv("SUPABASE_KEY")
)
assert SUPABASE_URL and SUPABASE_KEY, "Sem credenciais Supabase no ambiente"
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1) IDs sem descricao ---
faltando: list[str] = []
offset = 0
while len(faltando) < LIMITE:
    r = (sb.table("pacotes").select("codigo_pacote")
         .is_("descricao_produto", "null").order("criado_em", desc=True)
         .range(offset, offset + 999).execute())
    if not r.data:
        break
    for row in r.data:
        c = str(row.get("codigo_pacote") or "").strip().upper()
        if c and c not in faltando:
            faltando.append(c)
            if len(faltando) >= LIMITE:
                break
    offset += 1000
print(f"sem descricao: {len(faltando)} (limite {LIMITE})", flush=True)
if not faltando:
    print("nada a fazer")
    raise SystemExit(0)

# --- 2) cookies (secret ou arquivo) ---
raw_cookies = os.getenv("GOOGLE_COOKIES", "")
cookie_path = os.getenv("COOKIES_PATH", "")
lines: list[str] = []
if raw_cookies.strip():
    lines = [l for l in raw_cookies.splitlines() if l.strip() and not l.startswith("#")]
elif cookie_path and Path(cookie_path).exists():
    lines = [l.strip() for l in open(cookie_path, encoding="utf-8")
             if l.strip() and not l.startswith("#")]
if not lines:
    print("Sem cookies (GOOGLE_COOKIES ou COOKIES_PATH). Abortando.")
    raise SystemExit(3)
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
print(f"cookies: {len(cookies)}", flush=True)

# --- 3) Looker por filtro ---
from playwright.sync_api import sync_playwright

achados: dict[str, dict] = {}
with sync_playwright() as x:
    b = x.chromium.launch(headless=True, args=["--no-sandbox"])
    c = b.new_context(viewport={"width": 1600, "height": 1000}, locale="pt-BR")
    c.add_cookies(cookies)
    pg = c.new_page()
    pg.goto(URL, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(12000)
    if "accounts.google.com" in pg.url:
        print("SESSAO EXPIRADA: atualize o secret GOOGLE_COOKIES e rode de novo.")
        b.close()
        raise SystemExit(2)
    box = pg.query_selector('input[placeholder="Insira um valor"]')
    if not box:
        print("filtro nao encontrado")
        b.close()
        raise SystemExit(3)
    for i, pid in enumerate(faltando, 1):
        try:
            box.click()
            box.fill(pid)
            pg.wait_for_timeout(800)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(7000)
            body = pg.inner_text("body")
            m = re.search(re.escape(pid) + r"\s*\n([^\n]{1,40})\n([^\n]{1,200})\n(?:[^\n]*?R\$\s*([\d.,]+))?",
                          body)
            if m and not re.fullmatch(r"(47|48)\d{9}", (m.group(2) or "").strip()):
                achados[pid] = {"status": m.group(1).strip()[:40],
                                "descricao": m.group(2).strip()[:200],
                                "valor": (m.group(3) or "").strip()}
                print(f"[{i}/{len(faltando)}] OK {pid}: {achados[pid]['descricao'][:50]}", flush=True)
            else:
                print(f"[{i}/{len(faltando)}] -- {pid} (sem dados no relatorio)", flush=True)
        except Exception as e:
            print(f"[{i}/{len(faltando)}] ERRO {pid}: {str(e)[:100]}", flush=True)
    b.close()

# --- 4) upsert + sync ---
print(f"achados: {len(achados)}/{len(faltando)}", flush=True)
items = [{"package_id": k, "descricao": v["descricao"], "valor": v["valor"], "status": v["status"]}
         for k, v in achados.items()]
for i in range(0, len(items), 500):
    sb.rpc("upsert_product_descriptions", {"descriptions": items[i:i + 500]}).execute()
try:
    n = sb.rpc("sync_pacotes_descriptions").execute()
    print("pacotes sincronizados:", n.data, flush=True)
except Exception as e:
    print("sync falhou:", str(e)[:150], flush=True)
print("FIM incremental")
