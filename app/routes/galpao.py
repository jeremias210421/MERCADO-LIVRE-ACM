"""
Blueprint do Galpão (Conferência).
"""

from flask import Blueprint, jsonify, render_template, request

from app.services import finalizar_conferencia, scan_pacote
from app.supabase_client import is_supabase_configured, require_supabase

bp = Blueprint("galpao", __name__)


@bp.route("/galpao")
def conferencia_galpao():
    """Fechamento do galpão: abre a sessão pedida, a de hoje ou a última com dados."""
    from app.services import get_session_scans_enriquecidos, resolver_sessao

    sessao_pedida = (request.args.get("sessao") or "").strip()
    if not is_supabase_configured():
        from flask import flash

        flash("Supabase não configurado", "danger")
        return render_template(
            "galpao.html", sessao_id=sessao_pedida or "", sessoes=[], scans_salvos=[]
        )
    try:
        sessao_id, sessoes = resolver_sessao(sessao_pedida or None)
        scans_salvos = get_session_scans_enriquecidos(sessao_id) if sessao_id else []
        ranking = []
        try:
            from app.services import ranking_devolucao

            ranking = ranking_devolucao()
        except Exception:
            pass
    except Exception:
        sessao_id, sessoes, scans_salvos = sessao_pedida, [], []
        ranking = []
    return render_template(
        "galpao.html",
        sessao_id=sessao_id,
        sessoes=sessoes,
        scans_salvos=scans_salvos,
        ranking=ranking,
    )


@bp.route("/galpao/scan", methods=["POST"])
@require_supabase()
def galpao_scan():
    """Registra scan de pacote no galpão."""
    try:
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({"error": "JSON inválido ou ausente"}), 400
        codigo = str(dados.get("codigo_pacote", "")).strip()
        sessao_id = dados.get("sessao_id", "")

        if not codigo:
            return jsonify({"error": "Código vazio"}), 400

        result = scan_pacote(codigo, sessao_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/galpao/finalizar", methods=["POST"])
@require_supabase()
def galpao_finalizar():
    """Finaliza conferência e gera pendências."""
    try:
        sessao_id = request.json.get("sessao_id", "")
        result = finalizar_conferencia(sessao_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
