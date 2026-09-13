"""
Testes de Pendências.
"""

from unittest.mock import MagicMock


class TestPendentes:
    """Testes para pendências."""

    def test_listar_pendentes(
        self, client, mock_supabase, sample_pendente, sample_motorista
    ):
        """Testa listagem de pendências."""
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[sample_pendente]),  # pendentes
            MagicMock(data=[sample_motorista]),  # motoristas
            MagicMock(data=[{"id": "rota-123", "rota": "ROTA-001"}]),  # rotas
        ]

        response = client.get("/pendentes")
        assert response.status_code == 200
        assert b"Pendente" in response.data or b"pendent" in response.data.lower()

    def test_listar_pendentes_vazio(self, client, mock_supabase):
        """Testa listagem vazia."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        response = client.get("/pendentes")
        assert response.status_code == 200

    def test_marcar_entregue(self, client, mock_supabase):
        """Testa marcar pendente como entregue."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "pendente-123", "status": "entregue"}]
        )

        response = client.post(
            "/pendentes/pendente-123/entregar", follow_redirects=True
        )
        assert response.status_code == 200

    def test_cancelar_pendente(self, client, mock_supabase):
        """Testa cancelar pendente."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "pendente-123", "status": "cancelado"}]
        )

        response = client.post(
            "/pendentes/pendente-123/cancelar", follow_redirects=True
        )
        assert response.status_code == 200


class TestPendentesAgrupamento:
    """Testes de agrupamento por motorista."""

    def test_agrupamento_por_motorista(self, client, mock_supabase):
        """Testa agrupamento correto."""
        pendentes = [
            {
                "id": "p1",
                "codigo_pacote": "PKG001",
                "motorista_id": "m1",
                "rota_original_id": "r1",
                "status": "pendente",
                "data_pendencia": "2026-01-01",
            },
            {
                "id": "p2",
                "codigo_pacote": "PKG002",
                "motorista_id": "m1",
                "rota_original_id": "r1",
                "status": "pendente",
                "data_pendencia": "2026-01-01",
            },
            {
                "id": "p3",
                "codigo_pacote": "PKG003",
                "motorista_id": "m2",
                "rota_original_id": "r2",
                "status": "pendente",
                "data_pendencia": "2026-01-01",
            },
        ]

        motoristas = [
            {"id": "m1", "nome": "Motorista 1"},
            {"id": "m2", "nome": "Motorista 2"},
        ]
        rotas = [{"id": "r1", "rota": "ROTA-1"}, {"id": "r2", "rota": "ROTA-2"}]

        # Dispatch por tabela (deterministico, independe da ordem das queries)
        def _chain(data):
            m = MagicMock()
            m.execute.return_value = MagicMock(data=data)
            for meth in (
                "select",
                "order",
                "eq",
                "in_",
                "gte",
                "lte",
                "limit",
                "range",
                "single",
                "or_",
            ):
                getattr(m, meth).return_value = m
            return m

        calls = {"n": 0}

        def table_dispatch(name):
            if name == "pacotes_pendentes":
                # 1a chamada: linhas; demais: amostra p/ datas do filtro
                if calls["n"] == 0:
                    calls["n"] += 1
                    return _chain(pendentes)
                return _chain([{"data_pendencia": "2026-01-01", "status": "pendente"}])
            if name == "motoristas":
                return _chain(motoristas)
            if name == "rotas":
                return _chain(rotas)
            return _chain([])

        mock_supabase.table.side_effect = table_dispatch

        response = client.get("/pendentes")
        assert response.status_code == 200
        # Verifica se ambos motoristas aparecem
        assert b"Motorista 1" in response.data
        assert b"Motorista 2" in response.data
