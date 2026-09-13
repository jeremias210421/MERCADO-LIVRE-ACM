"""
Services Package - Business logic layer.
"""

from app.services.api_service import (
    get_dashboard_resumo,
    get_entregador_stats,
    get_motoristas,
    get_pendentes,
    get_rota_detalhes,
    get_rotas,
    upload_scans,
)
from app.services.dashboard_service import (
    get_dashboard_stats,
    get_entregador_detalhe,
    get_entregadores_list,
    get_rotas_list,
)
from app.services.entregador_service import (
    create_motorista,
    delete_motorista,
    get_all_motoristas,
    get_motorista,
    get_motorista_stats,
    get_motoristas_with_stats,
    update_motorista,
)
from app.services.galpao_service import (
    finalizar_conferencia,
    fora_na_rua,
    gerar_pendentes_sessao,
    get_session_scans,
    get_session_scans_enriquecidos,
    listar_sessoes,
    ranking_devolucao,
    resolver_sessao,
    scan_pacote,
    sessao_hoje_sp,
)
from app.services.pendentes_service import (
    cancelar_pendente,
    get_all_pendentes,
    get_pendentes_for_motorista,
    marcar_entregue,
)
from app.services.rota_service import (
    assign_motorista,
    get_all_rotas,
    get_rota,
    get_rota_with_details,
    get_rotas_with_motoristas,
)
from app.services.upload_service import importar_json_para_supabase

__all__ = [
    "assign_motorista",
    "cancelar_pendente",
    "create_motorista",
    "delete_motorista",
    "finalizar_conferencia",
    "fora_na_rua",
    "gerar_pendentes_sessao",
    "get_all_motoristas",
    "get_all_pendentes",
    "get_all_rotas",
    "get_dashboard_resumo",
    "get_dashboard_stats",
    "get_entregador_detalhe",
    "get_entregador_stats",
    "get_entregadores_list",
    "get_motorista",
    "get_motorista_stats",
    "get_motoristas",
    "get_motoristas_with_stats",
    "get_pendentes",
    "get_pendentes_for_motorista",
    "get_rota",
    "get_rota_detalhes",
    "get_rota_with_details",
    "get_rotas",
    "get_rotas_list",
    "get_rotas_with_motoristas",
    "get_session_scans",
    "get_session_scans_enriquecidos",
    "importar_json_para_supabase",
    "listar_sessoes",
    "marcar_entregue",
    "ranking_devolucao",
    "resolver_sessao",
    "scan_pacote",
    "sessao_hoje_sp",
    "update_motorista",
    "upload_scans",
]
