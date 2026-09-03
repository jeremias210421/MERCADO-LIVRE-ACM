"""
Blueprint de Pendentes.
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from app.supabase_client import is_supabase_configured
from app.services import get_all_pendentes, marcar_entregue, cancelar_pendente

bp = Blueprint('pendentes', __name__)


@bp.route('/pendentes')
def listar_pendentes():
    """Lista todas as pendências."""
    if not is_supabase_configured():
        return render_template('pendentes.html', pendentes=[], agrupado={})

    try:
        pendentes_list, agrupado = get_all_pendentes()
        return render_template('pendentes.html', pendentes=pendentes_list, agrupado=agrupado)
    except Exception as e:
        flash(f'Erro ao carregar pendentes: {str(e)}', 'danger')
        return render_template('pendentes.html', pendentes=[], agrupado={})


@bp.route('/pendentes/<pendente_id>/entregar', methods=['POST'])
def marcar_entregue_route(pendente_id):
    """Marca pendente como entregue."""
    try:
        marcar_entregue(pendente_id)
        flash('Marcado como entregue!', 'success')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('pendentes.listar_pendentes'))


@bp.route('/pendentes/<pendente_id>/cancelar', methods=['POST'])
def cancelar_pendente_route(pendente_id):
    """Cancela pendente."""
    try:
        cancelar_pendente(pendente_id)
        flash('Pendente cancelado.', 'success')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('pendentes.listar_pendentes'))