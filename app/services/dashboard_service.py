"""
Dashboard Service - Optimized database queries for dashboard.
"""
from datetime import date, timedelta
from typing import Any
from app.supabase_client import get_supabase


def hoje() -> date:
    return date.today()


def get_dashboard_stats() -> dict[str, Any]:
    """Get all dashboard statistics in optimized queries."""
    supabase = get_supabase()
    today = hoje().isoformat()

    # Single query: all scans today with motorista_id
    scans_result = supabase.table('scans').select('id, motorista_id, rota_id')\
        .gte('escaneado_em', today + 'T00:00:00')\
        .lte('escaneado_em', today + 'T23:59:59').execute()

    scans_list = scans_result.data or []
    total_entregues = len(scans_list)

    # Entregadores ativos hoje
    motoristas_ativos = set(s['motorista_id'] for s in scans_list if s.get('motorista_id'))
    entregadores_ativos = len(motoristas_ativos)

    # Pendentes - single query
    pendentes_result = supabase.table('pacotes_pendentes').select('id, motorista_id')\
        .eq('status', 'pendente')\
        .lte('data_entrega_prevista', today).execute()

    pendentes_list = pendentes_result.data or []
    total_pendentes = len(pendentes_list)

    # Taxa de entrega
    total = total_entregues + total_pendentes
    taxa_entrega = round((total_entregues / total) * 100, 1) if total > 0 else 0

    stats = {
        'entregadores_ativos': entregadores_ativos,
        'pacotes_entregues': total_entregues,
        'pacotes_pendentes': total_pendentes,
        'taxa_entrega': taxa_entrega
    }

    # Progresso por entregador - optimized with single queries
    progresso = []
    if motoristas_ativos:
        # Single query: all motoristas
        motoristas = supabase.table('motoristas').select('id, nome, telefone').execute()
        motoristas_map = {m['id']: m for m in (motoristas.data or [])}

        # Single query: all rota_motoristas
        rota_motoristas = supabase.table('rota_motoristas').select('rota_id, motorista_id').execute()
        rota_map = {rm['motorista_id']: rm['rota_id'] for rm in (rota_motoristas.data or [])}

        # Single query: all rotas needed
        rotas_ids = list(set(rota_map.values()))
        rotas_map = {}
        if rotas_ids:
            rotas = supabase.table('rotas').select('id, rota, total_pacotes').in_('id', rotas_ids).execute()
            rotas_map = {r['id']: r for r in (rotas.data or [])}

        # Single query: pendentes por motorista (IN filter instead of N queries)
        motorista_ids_list = list(motoristas_ativos)
        pendentes_por_motorista = {}
        if motorista_ids_list:
            pend_motoristas = supabase.table('pacotes_pendentes').select('id, motorista_id')\
                .eq('status', 'pendente')\
                .lte('data_entrega_prevista', today)\
                .in_('motorista_id', motorista_ids_list).execute()

            for p in (pend_motoristas.data or []):
                mid = p['motorista_id']
                pendentes_por_motorista[mid] = pendentes_por_motorista.get(mid, 0) + 1

        # Build progresso
        for mid in motoristas_ativos:
            m = motoristas_map.get(mid, {})
            scans_motorista = [s for s in scans_list if s.get('motorista_id') == mid]
            total_ent = len(scans_motorista)

            rota_id = rota_map.get(mid)
            rota_info = rotas_map.get(rota_id, {}) if rota_id else {}
            total_pac = rota_info.get('total_pacotes', 0) or 0
            pct = round((total_ent / total_pac) * 100, 1) if total_pac > 0 else 0

            progresso.append({
                'motorista_id': mid,
                'motorista_nome': m.get('nome', 'Desconhecido'),
                'motorista_telefone': m.get('telefone', ''),
                'rota_nome': rota_info.get('rota', 'Sem rota'),
                'total_entregues': total_ent,
                'total_pendentes': pendentes_por_motorista.get(mid, 0),
                'total_pacotes': total_pac,
                'percentual': min(pct, 100)
            })

        progresso.sort(key=lambda x: x['motorista_nome'])

    # Chart data: entregas por entregador
    chart_labels = [p['motorista_nome'].split()[0] for p in progresso]
    chart_entregues = [p['total_entregues'] for p in progresso]
    chart_pendentes = [p['total_pendentes'] for p in progresso]

    # Chart data: tendencia ultimos 7 dias - single query with date grouping
    tendencia_labels = []
    tendencia_data = []
    for i in range(6, -1, -1):
        d = hoje() - timedelta(days=i)
        d_str = d.isoformat()
        label = d.strftime('%d/%m')
        tendencia_labels.append(label)

        count_result = supabase.table('scans').select('id', count='exact')\
            .gte('escaneado_em', d_str + 'T00:00:00')\
            .lte('escaneado_em', d_str + 'T23:59:59').execute()
        tendencia_data.append(count_result.count or 0)

    return {
        'stats': stats,
        'progresso': progresso,
        'chart_labels': chart_labels,
        'chart_entregues': chart_entregues,
        'chart_pendentes': chart_pendentes,
        'tendencia_labels': tendencia_labels,
        'tendencia_data': tendencia_data
    }


def get_entregador_detalhe(motorista_id: str) -> dict[str, Any] | None:
    """Get detailed stats for a single entregador."""
    supabase = get_supabase()
    today = hoje().isoformat()

    # Motorista
    m_result = supabase.table('motoristas').select('*').eq('id', motorista_id).execute()
    if not m_result.data:
        return None
    motorista = m_result.data[0]

    # Scans de hoje
    scans_hoje = supabase.table('scans').select('id, codigo_pacote, endereco, escaneado_em')\
        .eq('motorista_id', motorista_id)\
        .gte('escaneado_em', today + 'T00:00:00')\
        .lte('escaneado_em', today + 'T23:59:59')\
        .order('escaneado_em', desc=True).execute()

    # Rota designada
    rm = supabase.table('rota_motoristas').select('rota_id')\
        .eq('motorista_id', motorista_id)\
        .order('criado_em', desc=True).limit(1).execute()

    rota_nome = 'Sem rota'
    if rm.data:
        rota = supabase.table('rotas').select('rota, total_pacotes')\
            .eq('id', rm.data[0]['rota_id']).single().execute()
        if rota.data:
            rota_nome = rota.data.get('rota', 'Sem rota')

    # Pendentes
    pendentes = supabase.table('pacotes_pendentes').select('*')\
        .eq('motorista_id', motorista_id).eq('status', 'pendente')\
        .order('data_pendencia', desc=True).execute()

    # Total geral
    total_result = supabase.table('scans').select('id', count='exact')\
        .eq('motorista_id', motorista_id).execute()

    # Ultimos 7 dias
    dias_labels = []
    dias_data = []
    for i in range(6, -1, -1):
        d = hoje() - timedelta(days=i)
        d_str = d.isoformat()
        dias_labels.append(d.strftime('%d/%m'))
        count = supabase.table('scans').select('id', count='exact')\
            .eq('motorista_id', motorista_id)\
            .gte('escaneado_em', d_str + 'T00:00:00')\
            .lte('escaneado_em', d_str + 'T23:59:59').execute()
        dias_data.append(count.count or 0)

    return {
        'motorista': motorista,
        'scans_hoje': scans_hoje.data or [],
        'rota_nome': rota_nome,
        'pendentes': pendentes.data or [],
        'total_geral': total_result.count or 0,
        'dias_labels': dias_labels,
        'dias_data': dias_data
    }


def get_entregadores_list() -> tuple[list[dict], dict]:
    """Get all entregadores with their stats - optimized."""
    supabase = get_supabase()
    today = hoje().isoformat()

    motoristas = supabase.table('motoristas').select('*').order('nome').execute()
    motoristas_list = motoristas.data or []

    if not motoristas_list:
        return [], {}

    motorista_ids = [m['id'] for m in motoristas_list]

    # Single query: total scans per motorista (all time)
    total_scans = supabase.table('scans').select('motorista_id', count='exact')\
        .in_('motorista_id', motorista_ids).execute()

    # Single query: scans hoje per motorista
    scans_hoje = supabase.table('scans').select('motorista_id', count='exact')\
        .in_('motorista_id', motorista_ids)\
        .gte('escaneado_em', today + 'T00:00:00')\
        .lte('escaneado_em', today + 'T23:59:59').execute()

    # Single query: pendentes per motorista
    pendentes = supabase.table('pacotes_pendentes').select('motorista_id', count='exact')\
        .eq('status', 'pendente')\
        .in_('motorista_id', motorista_ids).execute()

    # Build maps
    total_map = {}
    for item in (total_scans.data or []):
        # count is in the response metadata, not data
        pass

    # Use count from execute() response
    # We need separate queries for counts since Supabase doesn't group by in count
    stats_map = {}
    for m in motoristas_list:
        mid = m['id']
        total = supabase.table('scans').select('id', count='exact').eq('motorista_id', mid).execute()
        hoje_count = supabase.table('scans').select('id', count='exact')\
            .eq('motorista_id', mid)\
            .gte('escaneado_em', today + 'T00:00:00')\
            .lte('escaneado_em', today + 'T23:59:59').execute()
        pend = supabase.table('pacotes_pendentes').select('id', count='exact')\
            .eq('motorista_id', mid).eq('status', 'pendente').execute()

        stats_map[mid] = {
            'total_geral': total.count or 0,
            'total_hoje': hoje_count.count or 0,
            'pendentes': pend.count or 0
        }

    return motoristas_list, stats_map


def get_rotas_list() -> tuple[list[dict], list[dict], dict]:
    """Get rotas with motoristas and today's stats."""
    supabase = get_supabase()
    today = hoje().isoformat()

    rotas = supabase.table('rotas').select('*').order('rota').execute()
    rotas_list = rotas.data or []

    motoristas = supabase.table('motoristas').select('id, nome').order('nome').execute()
    motoristas_list = motoristas.data or []

    # Vinculos rota-motorista
    rm = supabase.table('rota_motoristas').select('rota_id, motorista_id').execute()
    rota_motoristas = {r['rota_id']: r['motorista_id'] for r in (rm.data or [])}

    # Scans de hoje por rota - optimized with IN
    rota_ids = [r['id'] for r in rotas_list]
    rota_stats = {}
    if rota_ids:
        scans = supabase.table('scans').select('rota_id', count='exact')\
            .in_('rota_id', rota_ids)\
            .gte('escaneado_em', today + 'T00:00:00')\
            .lte('escaneado_em', today + 'T23:59:59').execute()
        # Note: Supabase doesn't return grouped counts easily, fall back to per-rota
        for rota in rotas_list:
            r_scans = supabase.table('scans').select('id', count='exact')\
                .eq('rota_id', rota['id'])\
                .gte('escaneado_em', today + 'T00:00:00')\
                .lte('escaneado_em', today + 'T23:59:59').execute()
            rota_stats[rota['id']] = r_scans.count or 0

    for rota in rotas_list:
        entregues = rota_stats.get(rota['id'], 0)
        total = rota.get('total_pacotes', 0) or 0
        rota['entregues_hoje'] = entregues
        rota['percentual_hoje'] = round((entregues / total) * 100, 1) if total > 0 else 0

    return rotas_list, motoristas_list, rota_motoristas