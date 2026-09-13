"""
Testes das APIs (para app Android).
"""

from unittest.mock import MagicMock


class TestAPI:
    """Testes para endpoints de API."""

    def test_api_rotas(self, client, mock_supabase, sample_rota):
        """Testa API de listagem de rotas."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[sample_rota])
        )

        response = client.get("/api/rotas")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["rota"] == sample_rota["rota"]

    def test_api_rota_detalhes(self, client, mock_supabase, sample_rota):
        """Testa API de detalhes da rota."""
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[sample_rota]),  # rota
            MagicMock(
                data=[{"id": "parada-1", "sequencia": "1", "endereco": "End"}]
            ),  # paradas
            MagicMock(data=[{"codigo_pacote": "PKG001"}]),  # pacotes
        ]

        response = client.get(f"/api/rota/{sample_rota['id']}")
        assert response.status_code == 200
        data = response.get_json()
        assert "rota" in data
        assert "paradas" in data

    def test_api_rota_nao_encontrada(self, client, mock_supabase):
        """Testa API rota não encontrada."""
        # Configurar mock para retornar rota não encontrada
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        response = client.get("/api/rota/inexistente")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_api_motoristas(self, client, mock_supabase, sample_motorista):
        """Testa API de motoristas."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[sample_motorista])
        )

        response = client.get("/api/motoristas")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert data[0]["nome"] == sample_motorista["nome"]

    def test_api_upload_scans(self, client, mock_supabase):
        """Testa API de upload de scans (formato legado com FKs)."""
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock(data=[{"id": "scan-1"}, {"id": "scan-2"}])
        )

        scans = [
            {
                "codigo_pacote": "PKG001",
                "rota_id": "rota-1",
                "motorista_id": "m1",
                "escaneado_em": "2026-01-01T10:00:00Z",
            },
            {
                "codigo_pacote": "PKG002",
                "rota_id": "rota-1",
                "motorista_id": "m1",
                "escaneado_em": "2026-01-01T10:05:00Z",
            },
        ]

        response = client.post("/api/scans", json=scans)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2

    def test_api_upload_scans_texto(self, client, mock_supabase):
        """Testa upload no formato texto do PWA (code/route/operator_name)."""
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock(data=[{"id": "x"}])
        )

        scans = [
            {
                "code": "PKG9",
                "route": "H28_PM1",
                "operator_name": "Eric",
                "session_date": "2026-09-09",
            }
        ]

        response = client.post("/api/scans", json=scans)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 1
        # upsert com id determinístico (não insert cego)
        args, kwargs = mock_supabase.table.return_value.upsert.call_args
        assert kwargs.get("on_conflict") == "id"
        row = args[0][0]
        assert row["code"] == "PKG9" and row["route"] == "H28_PM1"
        assert row["id"] and row["id"] != ""

    def test_api_upload_scans_id_deterministico(self, client, mock_supabase):
        """Mesmo pacote+rota+dia => mesmo id (rebip vira upsert)."""
        from app.scan_ids import scan_db_id

        assert scan_db_id("PKG1", "H28_PM1", "2026-09-09") == scan_db_id(
            "pkg1 ", "h28_pm1", "09/09/2026"
        )
        assert scan_db_id("PKG1", "H28_PM1", "2026-09-09") != scan_db_id(
            "PKG1", "H28_PM1", "2026-09-08"
        )

    def test_api_upload_scans_invalido(self, client):
        """Testa API upload com dados inválidos."""
        response = client.post("/api/scans", json="not a list")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_api_pendentes(self, client, mock_supabase, sample_pendente):
        """Testa API de pendências."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[sample_pendente])
        )

        response = client.get("/api/pendentes")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_api_pendentes_com_filtro(self, client, mock_supabase):
        """Testa API pendências com filtro de motorista."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        response = client.get("/api/pendentes?motorista_id=m1&data=2026-01-01")
        assert response.status_code == 200

    def test_api_dashboard(self, client, mock_supabase):
        """Testa API dashboard (conta pacotes únicos do dia)."""
        from app.timezone import hoje_sp_iso

        hoje = hoje_sp_iso()
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(
                data=[  # scans do dia
                    {
                        "code": "A",
                        "route": "R1",
                        "operator_name": "Joao",
                        "motorista_id": None,
                        "session_date": hoje,
                    },
                    {
                        "code": "B",
                        "route": "R1",
                        "operator_name": "Joao",
                        "motorista_id": None,
                        "session_date": hoje,
                    },
                    {
                        "code": "A",
                        "route": "R1",
                        "operator_name": "Joao",
                        "motorista_id": None,
                        "session_date": hoje,
                    },  # rebip: não conta 2x
                ]
            ),
            MagicMock(data=[{"id": "m1", "nome": "Joao"}]),  # motoristas
            MagicMock(data=[]),  # pendentes
        ]

        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.get_json()
        assert data["entregadores_ativos"] == 1
        assert data["pacotes_entregues"] == 2
        assert data["pacotes_pendentes"] == 0
        assert data["data"] == hoje

    def test_api_entregador_stats(self, client, mock_supabase):
        """Testa API stats do entregador (id ou nome do operador)."""
        from app.timezone import hoje_sp_iso

        hoje = hoje_sp_iso()
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[{"id": "motorista-123", "nome": "Joao"}]),  # motorista
            MagicMock(
                data=[{"id": "motorista-123", "nome": "Joao"}]
            ),  # mapa motoristas
            MagicMock(
                data=[  # scans (total)
                    {"code": "A", "operator_name": "Joao", "motorista_id": None},
                    {"code": "B", "operator_name": "Joao", "motorista_id": None},
                ]
            ),
            MagicMock(
                data=[  # scans hoje
                    {
                        "code": "A",
                        "operator_name": "Joao",
                        "motorista_id": None,
                        "session_date": hoje,
                    },
                ]
            ),
            MagicMock(data=[], count=0),  # pendentes
        ]

        response = client.get("/api/entregadores/motorista-123/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_geral"] == 2
        assert data["total_hoje"] == 1
        assert data["pendentes"] == 0


class TestAPIRateLimit:
    """Testes de rate limiting (simulado)."""

    def test_api_aceita_requisicoes_normais(self, client, mock_supabase):
        """APIs aceitam requisições normais."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        for _ in range(5):
            response = client.get("/api/rotas")
            assert response.status_code == 200

    def test_api_content_type_json(self, client, mock_supabase):
        """APIs retornam JSON."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        response = client.get("/api/rotas")
        assert response.content_type == "application/json"
