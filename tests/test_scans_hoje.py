"""
Testes dos helpers canônicos de bipagens (timezone + scans_hoje).
"""
from unittest.mock import MagicMock


def _sb(rows_list):
    """Mock supabase que pagina de 1000 em 1000."""
    sb = MagicMock()
    tbl = MagicMock()
    sb.table.return_value = tbl
    sel = MagicMock()
    tbl.select.return_value = sel
    for ch in ('eq', 'limit', 'order'):
        getattr(sel, ch).return_value = sel

    def _range(a, b):
        q = MagicMock()
        q.execute.return_value = MagicMock(data=rows_list[a:b + 1])
        return q
    sel.range.side_effect = _range
    return sb


class TestFetchScansTudo:
    def test_pagina_ate_fim(self):
        from app.scans_hoje import fetch_scans_tudo
        rows = [{'code': f'C{i}', 'route': 'R', 'session_date': '2026-09-09'} for i in range(2500)]
        sb = _sb(rows)
        out = fetch_scans_tudo(sb)
        assert len(out) == 2500

    def test_para_em_pagina_curta(self):
        from app.scans_hoje import fetch_scans_tudo
        sb = _sb([{'code': 'A'}])
        assert len(fetch_scans_tudo(sb)) == 1


class TestMapaRotaSessao:
    def test_agrupa_e_normaliza(self):
        from app.scans_hoje import mapa_rota_sessao
        rows = [
            {'code': 'a', 'route': 'h28_pm1', 'session_date': '2026-09-09'},
            {'code': 'A ', 'route': 'H28_PM1', 'session_date': '09/09/2026'},
            {'code': 'b', 'route': 'H28_PM1', 'session_date': '2026-09-08'},
            {'code': '', 'route': 'H28_PM1', 'session_date': '2026-09-09'},
        ]
        m = mapa_rota_sessao(rows)
        assert m[('H28_PM1', '2026-09-09')] == {'A'}
        assert m[('H28_PM1', '2026-09-08')] == {'B'}


class TestMotoristaMaps:
    def test_primeiro_nome_unico_e_sem_acento(self):
        from app.scans_hoje import motorista_id_da_linha
        por_nome = {'JEREMIAS MACEDO': 'jm', 'JEREMIAS': 'jm', 'VINICIUS': 'v'}
        assert motorista_id_da_linha({'operator_name': 'Jeremias', 'motorista_id': None}, por_nome) == 'jm'
        assert motorista_id_da_linha({'operator_name': 'Vinicius', 'motorista_id': None}, por_nome) == 'v'
        assert motorista_id_da_linha({'operator_name': 'X', 'motorista_id': None}, por_nome) is None
        assert motorista_id_da_linha({'operator_name': 'X', 'motorista_id': 'm9'}, por_nome) == 'm9'
