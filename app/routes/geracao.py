"""
Pagina de geracao (controle pelo celular) + API de jobs.
A pagina pede, o agente no PC executa.
"""
import os
from flask import Blueprint, render_template, request, jsonify
from app.supabase_client import is_supabase_configured
from app.rate_limit import api_rate_limit
from app.services.jobs_service import (
    criar_job, listar_jobs, get_job, get_rotas_hoje_ibotirama, get_rota_contatos,
)


def disparar_github(job_id: str) -> bool:
    """Avisa o GitHub Actions para executar agora (best-effort)."""
    repo = os.getenv("GITHUB_REPO", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not (repo and token):
        return False
    try:
        import httpx
        r = httpx.post(
            f"https://api.github.com/repos/{repo}/dispatches",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"event_type": "gerar", "client_payload": {"job_id": job_id}},
            timeout=10,
        )
        return r.status_code == 204
    except Exception:
        return False

bp = Blueprint('geracao', __name__)


@bp.route('/geracao')
def pagina_geracao():
    """Pagina de controle (mobile)."""
    rotas, jobs, erro = [], [], None
    if is_supabase_configured():
        try:
            rotas = get_rotas_hoje_ibotirama()
            jobs = listar_jobs(10)
        except Exception as e:
            erro = str(e)
    return render_template('geracao.html', rotas=rotas, jobs=jobs, erro=erro)


@bp.route('/api/jobs', methods=['POST'])
@api_rate_limit(max_requests=20, window_seconds=60)
def api_criar_job():
    """Enfileira um trabalho: {tipo: gerar_ibotirama|renovar_sessao, totp?}."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        data = request.get_json() or {}
        job = criar_job(data.get('tipo', ''), {'totp': str(data.get('totp') or '')} if data.get('totp') else {})
        job['nuvem_avisada'] = disparar_github(job.get('id', '')) if data.get('tipo') == 'gerar_ibotirama' else False
        return jsonify(job), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/jobs')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_listar_jobs():
    """Ultimos jobs com status."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        return jsonify(listar_jobs(10))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/jobs/<job_id>')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_get_job(job_id):
    """Status de um job."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({'error': 'Job não encontrado'}), 404
        return jsonify(job)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/geracao/rotas/<rota_id>/contatos')
@api_rate_limit(max_requests=60, window_seconds=60)
def api_rota_contatos(rota_id):
    """Paradas da rota com nome/telefone (expansao na pagina)."""
    if not is_supabase_configured():
        return jsonify({'error': 'Supabase não configurado'}), 503
    try:
        data = get_rota_contatos(rota_id)
        if not data:
            return jsonify({'error': 'Rota não encontrada'}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
