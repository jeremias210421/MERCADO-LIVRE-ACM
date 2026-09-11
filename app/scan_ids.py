"""
IDs determinísticos de bipagem — PORT EXATO do frontend (src/lib/supabase/helpers.ts).

Garante que o mesmo pacote+rota+dia vire a MESMA linha no banco vindo de
qualquer cliente (PWA, Android, painel): rebip = upsert, nunca duplicata.
Não alterar o algoritmo: mudaria todos os IDs gerados pelo app.
"""
from app.timezone import normaliza_data_iso

_M32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return ((a & _M32) * (b & _M32)) & _M32


def _shr(x: int, n: int) -> int:
    return (x & _M32) >> n


def cyrb53(s: str, seed: int = 0) -> int:
    h1 = 0xDEADBEEF ^ seed
    h2 = 0x41C6CE57 ^ seed
    for ch in s:
        # charCodeAt do JS = unidade UTF-16; códigos/rotas/datas são ASCII
        code = ord(ch)
        if code > 0xFFFF:
            # surrogate pair como o JS veria
            code -= 0x10000
            for code in (0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF)):
                h1 = _imul(h1 ^ code, 2654435761)
                h2 = _imul(h2 ^ code, 1597334677)
            continue
        h1 = _imul(h1 ^ code, 2654435761)
        h2 = _imul(h2 ^ code, 1597334677)
    h1 = _imul(h1 ^ _shr(h1, 16), 2246822507) ^ _imul(h2 ^ _shr(h2, 13), 3266489909)
    h2 = _imul(h2 ^ _shr(h2, 16), 2246822507) ^ _imul(h1 ^ _shr(h1, 13), 3266489909)
    return 4294967296 * (2097151 & h2) + (h1 & _M32)


def deterministic_uuid(key: str) -> str:
    parts = []
    for seed in (0x9E37, 0x7F4A, 0x1656, 0x85EB):
        # .toString(16).padStart(12,'0').slice(-12) == low 48 bits em 12 hex
        parts.append(format(cyrb53(key, seed) & 0xFFFFFFFFFFFF, "012x"))
    hx = "".join(parts)[:32]
    return f"{hx[0:8]}-{hx[8:12]}-4{hx[13:16]}-8{hx[17:20]}-{hx[20:32]}"


def scan_db_id(code: str, route: str, date) -> str:
    c = str(code or "").strip().upper()
    r = str(route or "").strip().upper()
    d = normaliza_data_iso(date) or ""
    return deterministic_uuid(f"scan|{c}|{r}|{d}")


def galpao_db_id(code: str, sessao_id: str) -> str:
    c = str(code or "").strip().upper()
    s = str(sessao_id or "").strip()
    return deterministic_uuid(f"galpao|{c}|{s}")
