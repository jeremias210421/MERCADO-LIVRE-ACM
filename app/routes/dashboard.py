"""
Blueprint do Dashboard principal.
"""
from flask import Blueprint, render_template, flash
from app.supabase_client import is_supabase_configured
from app.services import get_dashboard_stats, get_entregador_detalhe

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    """Dashboard principal do gestor."""
    if not is_supabase_configured():
        return render_template('dashboard.html', stats={
            'entregadores_ativos': 0, 'pacotes_entregues': 0,
            'pacotes_pendentes': 0, 'taxa_entrega': 0
        }, progresso=[], chart_labels=[], chart_entregues=[],
           chart_pendentes=[], tendencia_labels=[], tendencia_data=[])

    try:
        data = get_dashboard_stats()
        return render_template('dashboard.html', **data)
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html', stats={
            'entregadores_ativos': 0, 'pacotes_entregues': 0,
            'pacotes_pendentes': 0, 'taxa_entrega': 0
        }, progresso=[], chart_labels=[], chart_entregues=[],
           chart_pendentes=[], tendencia_labels=[], tendencia_data=[])


@bp.route('/entregador/<motorista_id>')
def detalhe_entregador(motorista_id: str):
    """Detalhes e histórico de um entregador."""
    if not is_supabase_configured():
        flash('Supabase não configurado', 'danger')
        from flask import redirect, url_for
        return redirect(url_for('entregadores.listar_entregadores'))

    try:
        data = get_entregador_detalhe(motorista_id)
        if not data:
            flash('Entregador não encontrado', 'danger')
            from flask import redirect, url_for
            return redirect(url_for('entregadores.listar_entregadores'))

        return render_template('entregador_detalhe.html', **data)
    except Exception as e:
        flash(f'Erro ao carregar: {str(e)}', 'danger')
        from flask import redirect, url_for
        return redirect(url_for('entregadores.listar_entregadores'))