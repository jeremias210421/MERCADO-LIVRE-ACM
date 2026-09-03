"""
Blueprint de Entregadores (CRUD).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.supabase_client import is_supabase_configured
from app.services import (
    get_motoristas_with_stats,
    create_motorista,
    update_motorista,
    delete_motorista,
    get_motorista
)

bp = Blueprint('entregadores', __name__)


@bp.route('/entregadores')
def listar_entregadores():
    """Lista todos os entregadores."""
    if not is_supabase_configured():
        flash('Supabase não configurado', 'danger')
        return render_template('entregadores.html', motoristas=[], stats_map={})

    try:
        motoristas_list, stats_map = get_motoristas_with_stats()
        return render_template('entregadores.html', motoristas=motoristas_list, stats_map=stats_map)
    except Exception as e:
        flash(f'Erro ao carregar entregadores: {str(e)}', 'danger')
        return render_template('entregadores.html', motoristas=[], stats_map={})


@bp.route('/entregadores/novo', methods=['GET', 'POST'])
def novo_entregador():
    """Cadastra novo entregador."""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()

        if not nome:
            flash('Nome é obrigatório', 'warning')
            return render_template('entregador_form.html', motorista=None)

        try:
            create_motorista(nome, telefone)
            flash(f'Entregador {nome} cadastrado com sucesso!', 'success')
            return redirect(url_for('entregadores.listar_entregadores'))
        except Exception as e:
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')
            return render_template('entregador_form.html', motorista={'nome': nome, 'telefone': telefone})

    return render_template('entregador_form.html', motorista=None)


@bp.route('/entregadores/<motorista_id>/editar', methods=['GET', 'POST'])
def editar_entregador(motorista_id):
    """Edita um entregador."""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()

        if not nome:
            flash('Nome é obrigatório', 'warning')
            return render_template('entregador_form.html', motorista={'id': motorista_id, 'nome': nome, 'telefone': telefone})

        try:
            update_motorista(motorista_id, nome, telefone)
            flash(f'Entregador {nome} atualizado!', 'success')
            return redirect(url_for('entregadores.listar_entregadores'))
        except Exception as e:
            flash(f'Erro ao atualizar: {str(e)}', 'danger')

    try:
        motorista = get_motorista(motorista_id)
        if not motorista:
            flash('Entregador não encontrado', 'danger')
            return redirect(url_for('entregadores.listar_entregadores'))
        return render_template('entregador_form.html', motorista=motorista)
    except Exception as e:
        flash(f'Erro ao carregar: {str(e)}', 'danger')
        return redirect(url_for('entregadores.listar_entregadores'))


@bp.route('/entregadores/<motorista_id>/excluir', methods=['POST'])
def excluir_entregador(motorista_id):
    """Exclui um entregador."""
    try:
        delete_motorista(motorista_id)
        flash('Entregador excluído!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir: {str(e)}', 'danger')
    return redirect(url_for('entregadores.listar_entregadores'))