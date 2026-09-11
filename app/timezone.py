"""
Timezone canônico do sistema: America/Sao_Paulo.
O servidor (Vercel) roda em UTC — usar date.today()/datetime.now() aqui
desloca o "hoje" e zera dashboard, entregadores e rotas de madrugada.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

SP_TZ = ZoneInfo("America/Sao_Paulo")


def agora_sp() -> datetime:
    return datetime.now(SP_TZ)


def hoje_sp() -> date:
    return agora_sp().date()


def hoje_sp_iso() -> str:
    return hoje_sp().isoformat()


def sessao_br_para_iso(sessao_id: str) -> str | None:
    """DD-MM-YYYY -> YYYY-MM-DD (sessão do galpão)."""
    import re
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", (sessao_id or "").strip())
    if not m:
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def normaliza_data_iso(val: object) -> str:
    """Normaliza qualquer formato (ISO, DD/MM/YYYY, DD-MM-YYYY, timestamp) p/ YYYY-MM-DD."""
    import re
    s = str(val or "").strip()
    if not s:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(SP_TZ).date().isoformat()
    except Exception:
        return ""
