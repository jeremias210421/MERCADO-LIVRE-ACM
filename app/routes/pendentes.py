"""
Blueprint de Pendentes.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services import cancelar_pendente, get_all_pendentes, marcar_entregue
from app.supabase_client import is_supabase_configured

bp = Blueprint("pendentes", __name__)


@bp.route("/pendentes")
def listar_pendentes():
    """Lista pendências com filtros de data e status (?data=YYYY-MM-DD&status=)."""
    filtro_data = (request.args.get("data") or "").strip() or None
    filtro_status = (request.args.get("status") or "").strip() or None
    if not is_supabase_configured():
        return render_template(
            "pendentes.html",
            pendentes=[],
            agrupado={},
            datas=[],
            filtro_data=filtro_data,
            filtro_status=filtro_status,
        )

    try:
        pendentes_list, agrupado, datas = get_all_pendentes(filtro_data, filtro_status)
        return render_template(
            "pendentes.html",
            pendentes=pendentes_list,
            agrupado=agrupado,
            datas=datas,
            filtro_data=filtro_data,
            filtro_status=filtro_status,
        )
    except Exception as e:
        flash(f"Erro ao carregar pendentes: {e!s}", "danger")
        return render_template(
            "pendentes.html",
            pendentes=[],
            agrupado={},
            datas=[],
            filtro_data=filtro_data,
            filtro_status=filtro_status,
        )


@bp.route("/pendentes/<pendente_id>/entregar", methods=["POST"])
def marcar_entregue_route(pendente_id):
    """Marca pendente como entregue."""
    try:
        marcar_entregue(pendente_id)
        flash("Marcado como entregue!", "success")
    except Exception as e:
        flash(f"Erro: {e!s}", "danger")
    return redirect(url_for("pendentes.listar_pendentes"))


@bp.route("/pendentes/<pendente_id>/cancelar", methods=["POST"])
def cancelar_pendente_route(pendente_id):
    """Cancela pendente."""
    try:
        cancelar_pendente(pendente_id)
        flash("Pendente cancelado.", "success")
    except Exception as e:
        flash(f"Erro: {e!s}", "danger")
    return redirect(url_for("pendentes.listar_pendentes"))
