"""
Blueprint de Rotas.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.supabase_client import is_supabase_configured
from app.services import get_rotas_with_motoristas, assign_motorista

bp = Blueprint('rotas', __name__)


@bp.route('/rotas')
def listar_rotas():
    """Lista todas as rotas com status."""
    if not is_supabase_configured():
        return render_template('rotas.html', rotas=[], motoristas=[], rota_motoristas={})

    try:
        rotas_list, motoristas_list, rota_motoristas = get_rotas_with_motoristas()
        return render_template('rotas.html',
            rotas=rotas_list, motoristas=motoristas_list,
            rota_motoristas=rota_motoristas)
    except Exception as e:
        flash(f'Erro ao carregar rotas: {str(e)}', 'danger')
        return render_template('rotas.html', rotas=[], motoristas=[], rota_motoristas={})


@bp.route('/rotas/<rota_id>/designar', methods=['POST'])
def designar_motorista(rota_id):
    """Designa motorista para uma rota."""
    try:
        motorista_id = request.form.get('motorista_id')
        if not motorista_id:
            flash('Selecione um motorista', 'warning')
            return redirect(url_for('rotas.listar_rotas'))

        assign_motorista(rota_id, motorista_id)
        flash('Motorista designado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('rotas.listar_rotas'))