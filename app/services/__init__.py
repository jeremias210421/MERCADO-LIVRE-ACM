"""
Services Package - Business logic layer.
"""
from app.services.dashboard_service import (
    get_dashboard_stats,
    get_entregador_detalhe,
    get_entregadores_list,
    get_rotas_list
)
from app.services.entregador_service import (
    create_motorista,
    update_motorista,
    delete_motorista,
    get_motorista,
    get_all_motoristas,
    get_motorista_stats,
    get_motoristas_with_stats
)
from app.services.rota_service import (
    get_all_rotas,
    get_rota,
    get_rota_with_details,
    get_rotas_with_motoristas,
    assign_motorista
)
from app.services.galpao_service import (
    scan_pacote,
    finalizar_conferencia,
    get_session_scans
)
from app.services.pendentes_service import (
    get_all_pendentes,
    get_pendentes_for_motorista,
    marcar_entregue,
    cancelar_pendente
)
from app.services.upload_service import importar_json_para_supabase
from app.services.api_service import (
    get_rotas,
    get_rota_detalhes,
    get_motoristas,
    upload_scans,
    get_pendentes,
    get_dashboard_resumo,
    get_entregador_stats
)

__all__ = [
    # Dashboard
    'get_dashboard_stats',
    'get_entregador_detalhe',
    'get_entregadores_list',
    'get_rotas_list',
    # Entregador
    'create_motorista',
    'update_motorista',
    'delete_motorista',
    'get_motorista',
    'get_all_motoristas',
    'get_motorista_stats',
    'get_motoristas_with_stats',
    # Rota
    'get_all_rotas',
    'get_rota',
    'get_rota_with_details',
    'get_rotas_with_motoristas',
    'assign_motorista',
    # Galpao
    'scan_pacote',
    'finalizar_conferencia',
    'get_session_scans',
    # Pendentes
    'get_all_pendentes',
    'get_pendentes_for_motorista',
    'marcar_entregue',
    'cancelar_pendente',
    # Upload
    'importar_json_para_supabase',
    # API
    'get_rotas',
    'get_rota_detalhes',
    'get_motoristas',
    'upload_scans',
    'get_pendentes',
    'get_dashboard_resumo',
    'get_entregador_stats',
]