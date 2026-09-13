"""
Consultas canônicas de bipagens do dia.

Colunas REAIS de scans (produção): code/route/operator_name/session_date
(motorista_id/rota_id quase sempre NULL — o app grava texto, não FK).
Por isso toda contagem "de hoje" usa session_date == hoje-SP + route,
e atribuição de entregador usa motorista_id OU operator_name→motoristas.
"""

from collections import Counter

from app.timezone import normaliza_data_iso


def norm_code(v: object) -> str:
    return str(v or "").strip().upper()


def _rows(res) -> list[dict]:
    """Extrai lista de dicts de resposta Supabase (ou [] se vier lixo/mock)."""
    try:
        data = res.data if res is not None else None
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict)]


def fetch_scans_dia(supabase, date_iso: str, limit: int = 5000) -> list[dict]:
    """Todas as bipagens de um dia (session_date canônico). 1 query."""
    try:
        res = (
            supabase.table("scans")
            .select("code,route,operator_name,motorista_id,session_date")
            .eq("session_date", date_iso)
            .limit(limit)
            .execute()
        )
        return _rows(res)
    except Exception:
        return []


def fetch_scans_tudo(supabase, cols: str = "code,route,session_date") -> list[dict]:
    """Tabela scans inteira, paginada de 1000 (PostgREST capa o limit).

    Necessário p/ agregar por (rota, sessão) histórica: limit alto sozinho
    retorna só as 1000 mais antigas e some com os dias recentes.
    """
    out: list[dict] = []
    off = 0
    while True:
        try:
            res = supabase.table("scans").select(cols).range(off, off + 999).execute()
        except Exception:
            break
        data = _rows(res)
        if not data:
            break
        out.extend(data)
        if len(data) < 1000:
            break
        off += 1000
        if off >= 50000:  # trava de segurança
            break
    return out


def fetch_scans_por_sessoes(
    supabase, sessoes: set[str], cols: str = "code,route,session_date"
) -> list[dict]:
    """Bipagens só das sessões pedidas (ex: session_date das rotas listadas).
    1 query com IN em vez da tabela inteira paginada."""
    lista = sorted(s for s in sessoes if s)
    if not lista:
        return []
    out: list[dict] = []
    try:
        # IN com muitas datas: fatia de 100
        for i in range(0, len(lista), 100):
            lote = lista[i : i + 100]
            off = 0
            while True:
                res = (
                    supabase.table("scans")
                    .select(cols)
                    .in_("session_date", lote)
                    .range(off, off + 999)
                    .execute()
                )
                data = _rows(res)
                if not data:
                    break
                out.extend(data)
                if len(data) < 1000:
                    break
                off += 1000
                if off >= 20000:
                    break
    except Exception:
        pass
    return out


def mapa_rota_sessao(rows: list[dict]) -> dict:
    """{(ROTA, YYYY-MM-DD): set(codes)} a partir de linhas code/route/session_date."""
    out: dict = {}
    for s in rows:
        code = norm_code(s.get("code"))
        rota = str(s.get("route") or "").strip().upper()
        sess = normaliza_data_iso(s.get("session_date"))
        if code and rota and sess:
            out.setdefault((rota, sess), set()).add(code)
    return out


def distinct_por_rota(rows: list[dict]) -> dict[str, set]:
    """Códigos únicos por rota (UPPER)."""
    out: dict[str, set] = {}
    for r in rows:
        code = norm_code(r.get("code"))
        rota = str(r.get("route") or "").strip().upper()
        if not code or not rota:
            continue
        out.setdefault(rota, set()).add(code)
    return out


def _sem_acento(s: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def motorista_maps(supabase) -> tuple[dict, dict]:
    """Retorna ({id: {nome}}, {NOME_UPPER: id}).

    Chaves sem acento também (bip antigo gravou 'Vinicius', cadastro é
    'Vinícius'). Primeiro nome só entra se for único.
    """
    try:
        res = supabase.table("motoristas").select("id,nome").execute()
    except Exception:
        return {}, {}
    por_id: dict = {}
    por_nome: dict = {}
    primeiros: dict = {}
    for m in _rows(res):
        mid = m.get("id")
        nome = (m.get("nome") or "").strip()
        if not mid:
            continue
        por_id[mid] = m
        for chave in {nome.upper(), _sem_acento(nome.upper())}:
            if chave and chave not in por_nome:
                por_nome[chave] = mid
        if nome:
            for prim in {nome.upper().split()[0], _sem_acento(nome.upper()).split()[0]}:
                # só mapeia primeiro nome se for ÚNICO (evita colidir dois "Thiago")
                if prim not in primeiros:
                    primeiros[prim] = mid
                elif primeiros[prim] != mid:
                    primeiros[prim] = None
    for prim, mid in primeiros.items():
        if mid and prim not in por_nome:
            por_nome[prim] = mid
    return por_id, por_nome


def enriquecer_endereco(supabase, rows: list[dict]) -> list[dict]:
    """Preenche row['endereco'] via pacotes→paradas quando o bip não tem.

    2 queries batch, independente do nº de linhas.
    """
    try:
        codes = list(
            {norm_code(r.get("code")) for r in rows if norm_code(r.get("code"))}
        )
        sem_end = [
            r for r in rows if not r.get("endereco") and norm_code(r.get("code"))
        ]
        if not codes or not sem_end:
            return rows
        pacs: dict = {}
        for i in range(0, len(codes), 200):
            chunk = codes[i : i + 200]
            res = (
                supabase.table("pacotes")
                .select("codigo_pacote,parada_id")
                .in_("codigo_pacote", chunk)
                .limit(5000)
                .execute()
            )
            for p in _rows(res):
                pacs[norm_code(p.get("codigo_pacote"))] = p.get("parada_id")
        pids = list({v for v in pacs.values() if v})
        ends: dict = {}
        for i in range(0, len(pids), 200):
            chunk = pids[i : i + 200]
            res = (
                supabase.table("paradas")
                .select("id,endereco")
                .in_("id", chunk)
                .limit(5000)
                .execute()
            )
            for p in _rows(res):
                if p.get("id") and p.get("endereco"):
                    ends[p["id"]] = p["endereco"]
        for r in sem_end:
            pid = pacs.get(norm_code(r.get("code")))
            if pid and pid in ends:
                r["endereco"] = ends[pid]
    except Exception:
        pass
    return rows


def motorista_id_da_linha(row: dict, por_nome: dict) -> str | None:
    """Atribui entregador: motorista_id direto ou operator_name→cadastro
    (exato, sem acento ou primeiro nome único)."""
    mid = row.get("motorista_id")
    if mid:
        return mid
    nome = str(row.get("operator_name") or "").strip().upper()
    if not nome:
        return None
    return por_nome.get(nome) or por_nome.get(_sem_acento(nome))


def scans_do_motorista(
    supabase,
    motorista_id: str,
    nome: str,
    date_iso: str | None = None,
    limit: int = 5000,
    por_nome: dict | None = None,
) -> list[dict]:
    """Bipagens atribuídas ao entregador, com dedupe por pacote.

    Usa o mesmo motor de atribuição do resto do sistema (id direto, nome
    exato/sem acento/primeiro-nome-único). date_iso=None traz tudo.
    """
    if por_nome is None:
        _, por_nome = motorista_maps(supabase)
    vistos: set = set()
    out: list[dict] = []
    for off in range(0, 20000, 5000):
        try:
            q = supabase.table("scans").select(
                "code,codigo_pacote,route,operator_name,endereco,scanned_at,escaneado_em,session_date,motorista_id"
            )
            if date_iso:
                q = q.eq("session_date", date_iso)
            res = q.range(off, off + 4999).execute()
            data = _rows(res)
            if not data:
                break
            for r in data:
                if motorista_id_da_linha(r, por_nome) != motorista_id:
                    continue
                code = norm_code(r.get("code"))
                if not code or code in vistos:
                    continue
                vistos.add(code)
                # compat: templates antigos leem codigo_pacote
                r.setdefault("codigo_pacote", code)
                out.append(r)
            if len(data) < 5000:
                break
        except Exception:
            break
    return out


def contagem_hoje_por_motorista(rows: list[dict], por_nome: dict) -> Counter:
    """Códigos únicos por motorista_id no dia (dedupe por pacote)."""
    vistos: set = set()
    cnt: Counter = Counter()
    for r in rows:
        code = norm_code(r.get("code"))
        mid = motorista_id_da_linha(r, por_nome)
        if not code or not mid:
            continue
        chave = (mid, code)
        if chave in vistos:
            continue
        vistos.add(chave)
        cnt[mid] += 1
    return cnt


def tendencia_por_session_date(
    supabase, dias: int = 7, limit: int = 10000
) -> tuple[list[str], list[int]]:
    """Últimos N dias (SP) agrupados por session_date normalizado. 1 query."""
    from datetime import timedelta

    from app.timezone import hoje_sp

    labels: list[str] = []
    ordre: list[str] = []
    for i in range(dias - 1, -1, -1):
        d = hoje_sp() - timedelta(days=i)
        ordre.append(d.isoformat())
        labels.append(d.strftime("%d/%m"))
    try:
        inicio = ordre[0]
        res = (
            supabase.table("scans")
            .select("session_date")
            .gte("session_date", inicio)
            .limit(limit)
            .execute()
        )
        por_dia: Counter = Counter()
        for r in _rows(res):
            iso = normaliza_data_iso(r.get("session_date"))
            if iso:
                por_dia[iso] += 1
        return labels, [por_dia.get(d, 0) for d in ordre]
    except Exception:
        return labels, [0] * len(labels)
