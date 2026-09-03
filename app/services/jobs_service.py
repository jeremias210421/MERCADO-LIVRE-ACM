"""
Jobs Service - fila de trabalhos (pagina pede, agente no PC executa).
"""
from typing import Any
from app.supabase_client import get_supabase

TIPOS_VALIDOS = ('gerar_ibotirama', 'renovar_sessao')


def criar_job(tipo: str, payload: dict | None = None) -> dict[str, Any]:
    """Cria um job pendente."""
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo inválido: {tipo}")
    supabase = get_supabase()
    r = supabase.table('jobs').insert({
        'tipo': tipo, 'status': 'pendente', 'payload': payload or {},
    }).execute()
    return r.data[0] if r.data else {}


def listar_jobs(limit: int = 10) -> list[dict[str, Any]]:
    """Jobs mais recentes."""
    supabase = get_supabase()
    r = supabase.table('jobs').select('*').order('criado_em', desc=True).limit(limit).execute()
    return r.data or []


def get_job(job_id: str) -> dict[str, Any] | None:
    """Um job por ID."""
    supabase = get_supabase()
    r = supabase.table('jobs').select('*').eq('id', job_id).limit(1).execute()
    return r.data[0] if r.data else None


def get_rotas_hoje_ibotirama() -> list[dict[str, Any]]:
    """Rotas de hoje cuja cidade contenha Ibotirama (inclui compartilhadas)."""
    from datetime import date
    supabase = get_supabase()
    hoje = date.today().isoformat()
    r = supabase.table('rotas').select('id,rota,total_paradas,total_pacotes,cidade,criado_em') \
        .ilike('cidade', '%ibotirama%') \
        .gte('criado_em', hoje + 'T00:00:00').order('rota').execute()
    return r.data or []


def get_rota_contatos(rota_id: str) -> dict[str, Any]:
    """Paradas da rota com pacotes + nome/telefone."""
    supabase = get_supabase()
    rota = supabase.table('rotas').select('id,rota,total_paradas,total_pacotes,cidade').eq('id', rota_id).limit(1).execute()
    if not rota.data:
        return {}
    paradas = supabase.table('paradas').select('id,sequencia,endereco,tipo_endereco').eq('rota_id', rota_id).order('sequencia').execute()
    out = []
    for par in (paradas.data or []):
        pacs = supabase.table('pacotes').select('codigo_pacote,nome_comprador,telefone').eq('parada_id', par['id']).execute()
        out.append({
            'sequencia': par['sequencia'], 'endereco': par['endereco'],
            'tipo_endereco': par.get('tipo_endereco'),
            'pacotes': pacs.data or [],
        })
    return {'rota': rota.data[0], 'paradas': out}
