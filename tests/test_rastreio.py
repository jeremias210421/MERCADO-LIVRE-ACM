"""
Testes do rastreio (linha do tempo do pacote).
"""

from unittest.mock import MagicMock


def _q(rows):
    q = MagicMock()
    for ch in ("select", "eq", "limit", "order"):
        getattr(q, ch).return_value = q
    q.execute.return_value = MagicMock(data=rows)
    return q


class TestHistoricoPacote:
    def test_monta_linha_do_tempo(self, mock_supabase):
        import app.services.rastreio_service as rs
        from app.services.rastreio_service import historico_pacote

        def table_side_effect(name):
            t = MagicMock()
            if name == "pacotes":
                t.select.return_value = _q([{"parada_id": "pa1", "status": "pendente"}])
            elif name == "paradas":
                t.select.return_value = _q(
                    [{"rota_id": "r1", "endereco": "Rua X", "sequencia": "01"}]
                )
            elif name == "rotas":
                t.select.return_value = _q(
                    [
                        {
                            "id": "r1",
                            "rota": "H28_PM1",
                            "session_date": "2026-09-09",
                            "criado_em": "2026-09-09T10:00:00",
                        }
                    ]
                )
            elif name == "romaneio":
                t.select.return_value = _q([])
            elif name == "scans":
                t.select.return_value = _q(
                    [
                        {
                            "route": "H28_PM1",
                            "operator_name": "Eric",
                            "session_date": "2026-09-09",
                            "scanned_at": "2026-09-09T15:00:00",
                            "motorista_id": None,
                        }
                    ]
                )
            elif (
                name == "galpao_scans"
                or name == "pacotes_pendentes"
                or name == "motoristas"
            ):
                t.select.return_value = _q([])
            else:
                t.select.return_value = _q([])
            return t

        mock_supabase.table.side_effect = table_side_effect
        orig = rs.get_supabase
        rs.get_supabase = lambda: mock_supabase
        try:
            h = historico_pacote("abc123")
        finally:
            rs.get_supabase = orig
            mock_supabase.table.side_effect = None

        assert h["code"] == "ABC123"
        tipos = [e["tipo"] for e in h["eventos"]]
        assert "romaneio" in tipos and "rua" in tipos
        assert h["rota_atual"] == "H28_PM1 (2026-09-09)"

    def test_sem_historico(self, mock_supabase):
        import app.services.rastreio_service as rs
        from app.services.rastreio_service import historico_pacote

        def table_side_effect(name):
            t = MagicMock()
            t.select.return_value = _q([])
            return t

        mock_supabase.table.side_effect = table_side_effect
        orig = rs.get_supabase
        rs.get_supabase = lambda: mock_supabase
        try:
            h = historico_pacote("ZZZ")
        finally:
            rs.get_supabase = orig
            mock_supabase.table.side_effect = None

        assert h["eventos"] == []
        assert h["status"] == "Sem histórico"


class TestRastreioRoute:
    def test_pagina_busca(self, client, mock_supabase):
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        response = client.get("/pacote?q=ABC123")
        assert response.status_code == 200
        assert b"ABC123" in response.data
