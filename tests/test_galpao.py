"""
Testes do Galpão (Conferência).
"""

from unittest.mock import MagicMock


class TestGalpao:
    """Testes para conferência do galpão."""

    def test_conferencia_galpao_get(self, client):
        """Testa página de conferência."""
        response = client.get("/galpao")
        assert response.status_code == 200
        assert b"Confer" in response.data or b"galp" in response.data.lower()
        # Verifica se tem sessao_id
        assert b"sessao" in response.data.lower() or b"session" in response.data.lower()

    def test_galpao_scan_valido(self, client, mock_supabase):
        """Testa scan de pacote encontrado."""
        # Mock da função identificar_pacote
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "encontrado": True,
                    "rota_id": "rota-123",
                    "rota_nome": "ROTA-001",
                    "motorista_id": "motorista-123",
                    "motorista_nome": "João Silva",
                    "endereco": "Rua Teste, 123",
                }
            ]
        )
        # Mock motoristas select single
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"nome": "João Silva"}
        )
        # Mock rotas select single
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"rota": "ROTA-001"}
        )
        # Mock galpao_scans insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{"id": "scan-1"}])
        )

        response = client.post(
            "/galpao/scan", json={"codigo_pacote": "PKG001", "sessao_id": "abc12345"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["encontrado"] is True
        assert data["rota_nome"] == "ROTA-001"

    def test_galpao_scan_nao_encontrado(self, client, mock_supabase):
        """Testa scan de pacote não encontrado."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{"encontrado": False}]
        )

        response = client.post(
            "/galpao/scan",
            json={"codigo_pacote": "INEXISTENTE", "sessao_id": "abc12345"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["encontrado"] is False

    def test_galpao_scan_codigo_vazio(self, client):
        """Testa scan com código vazio."""
        response = client.post(
            "/galpao/scan", json={"codigo_pacote": "", "sessao_id": "abc12345"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_galpao_finalizar(self, client, mock_supabase):
        """Testa finalização da conferência."""
        # Mock RPC gerar_pendencias_diarias
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=5)

        # Mock galpao_scans select chain - the service calls:
        # supabase.table('galpao_scans').select('codigo_pacote, motorista_id').eq('sessao_id', sessao_id).execute()
        mock_galpao_scans_table = MagicMock()
        mock_galpao_scans_select = MagicMock()
        mock_galpao_scans_eq = MagicMock()
        mock_galpao_scans_table.select.return_value = mock_galpao_scans_select
        mock_galpao_scans_select.eq.return_value = mock_galpao_scans_eq
        mock_galpao_scans_eq.execute.return_value = MagicMock(
            data=[
                {"codigo_pacote": "PKG001", "motorista_id": "m1"},
                {"codigo_pacote": "PKG002", "motorista_id": "m1"},
            ]
        )

        # Mock motoristas table for name lookup
        mock_motoristas_table = MagicMock()
        mock_motoristas_select = MagicMock()
        mock_motoristas_eq = MagicMock()
        mock_motoristas_single = MagicMock()
        mock_motoristas_table.select.return_value = mock_motoristas_select
        mock_motoristas_select.eq.return_value = mock_motoristas_eq
        mock_motoristas_eq.single.return_value = mock_motoristas_single
        mock_motoristas_single.execute.return_value = MagicMock(
            data={"nome": "João Silva"}
        )

        # Configure table() to return different mocks based on table name
        def table_side_effect(table_name):
            if table_name == "galpao_scans":
                return mock_galpao_scans_table
            elif table_name == "motoristas":
                return mock_motoristas_table
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        response = client.post("/galpao/finalizar", json={"sessao_id": "abc12345"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["pendencias_criadas"] == 5
        assert "por_motorista" in data


class TestGalpaoValidation:
    """Testes de validação do galpão."""

    def test_pagina_abre_ultima_sessao(self, client, mock_supabase):
        """Sem ?sessao=, abre a última com dados e lista os pacotes restantes."""
        from unittest.mock import patch

        with (
            patch(
                "app.services.resolver_sessao",
                return_value=(
                    "09-09-2026",
                    [
                        {"sessao_id": "09-09-2026", "total": 6},
                        {"sessao_id": "06-09-2026", "total": 71},
                    ],
                ),
            ),
            patch(
                "app.services.get_session_scans_enriquecidos",
                return_value=[
                    {
                        "code": "PKG1",
                        "rota_nome": "H28_PM1",
                        "motorista_nome": "Eric",
                        "endereco": "Rua A, 1",
                        "escaneado_em": "2026-09-09T20:00:00",
                    },
                ],
            ),
        ):
            response = client.get("/galpao")
            assert response.status_code == 200
            assert b"09-09-2026" in response.data
            assert b"PKG1" in response.data
            assert b"Eric" in response.data

    def test_scan_requer_json(self, client):
        """Scan requer JSON."""
        response = client.post(
            "/galpao/scan",
            data="codigo=PKG001",
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code in (400, 415)

    def test_finalizar_requer_sessao(self, client, mock_supabase):
        """Finalizar aceita sessao_id vazio."""
        # Mock RPC para retornar 0 pendências
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=0)
        # Mock galpao_scans vazio
        mock_galpao_scans_table = MagicMock()
        mock_galpao_scans_select = MagicMock()
        mock_galpao_scans_eq = MagicMock()
        mock_galpao_scans_table.select.return_value = mock_galpao_scans_select
        mock_galpao_scans_select.eq.return_value = mock_galpao_scans_eq
        mock_galpao_scans_eq.execute.return_value = MagicMock(data=[])

        def table_side_effect(table_name):
            if table_name == "galpao_scans":
                return mock_galpao_scans_table
            return MagicMock()

        mock_supabase.table.side_effect = table_side_effect

        response = client.post("/galpao/finalizar", json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["pendencias_criadas"] == 0


def _q(rows):
    """Mock de query encadeável que retorna rows no execute."""
    q = MagicMock()
    for ch in ("select", "eq", "in_", "limit", "order"):
        getattr(q, ch).return_value = q
    q.execute.return_value = MagicMock(data=rows)
    return q


class TestGerarPendentesSessao:
    """Geração real de pendentes (retornados ao galpão viram pendentes)."""

    def test_gera_retornados_como_pendentes(self, mock_supabase):
        """Retornados ao galpão (não entregues) viram pendentes, COM ou SEM motorista."""
        from app.services.galpao_service import gerar_pendentes_sessao

        por_tabela = {
            # 2 retornados com motorista+rota; 1 sem motorista (tambem vira pendente)
            "galpao_scans": [
                {"codigo_pacote": "P1", "rota_id": "r1", "motorista_id": "m1"},
                {"codigo_pacote": "P2", "rota_id": "r1", "motorista_id": "m1"},
                {"codigo_pacote": "P9", "rota_id": "r1", "motorista_id": None},
            ],
            "paradas": [{"id": "pa1", "rota_id": "r1", "endereco": "Rua X"}],
            "pacotes": [{"codigo_pacote": "P2", "parada_id": "pa1"}],
            # P1 já pendente hoje -> P2 e P9 são criados (P2 com endereço)
            "pacotes_pendentes": [{"codigo_pacote": "P1", "motorista_id": "m1"}],
        }
        inseridos = []

        def table_side_effect(name):
            t = MagicMock()
            t.select.return_value = _q(por_tabela.get(name, []))

            def _insert(payload):
                inseridos.append(payload)
                qq = MagicMock()
                qq.execute.return_value = MagicMock(data=[{"id": "x"}])
                return qq

            t.insert.side_effect = _insert
            return t

        mock_supabase.table.side_effect = table_side_effect
        try:
            n = gerar_pendentes_sessao(mock_supabase, "09-09-2026")
        finally:
            mock_supabase.table.side_effect = None

        assert n == 2
        # insert e' em lote: cada item de `inseridos` e' uma lista
        todos = [
            d
            for lote in inseridos
            for d in (lote if isinstance(lote, list) else [lote])
        ]
        cods = sorted(d["codigo_pacote"] for d in todos)
        assert cods == ["P2", "P9"]
        p2 = next(d for d in todos if d["codigo_pacote"] == "P2")
        assert p2["motorista_id"] == "m1"
        assert p2["status"] == "pendente"
        assert p2["endereco"] == "Rua X"
        p9 = next(d for d in todos if d["codigo_pacote"] == "P9")
        assert p9["motorista_id"] is None
        assert p9["status"] == "pendente"

    def test_sem_retorno_nao_gera(self, mock_supabase):
        from app.services.galpao_service import gerar_pendentes_sessao

        def table_side_effect(name):
            t = MagicMock()
            t.select.return_value = _q([])
            return t

        mock_supabase.table.side_effect = table_side_effect
        try:
            assert gerar_pendentes_sessao(mock_supabase, "09-09-2026") == 0
        finally:
            mock_supabase.table.side_effect = None


class TestForaNaRua:
    """Pacotes do romaneio sem bip na rua nem no galpão."""

    def test_aponta_quem_falta(self, mock_supabase):
        import app.services.galpao_service as gs
        from app.services.galpao_service import fora_na_rua

        por_tabela = {
            "galpao_scans": [
                {"codigo_pacote": "G1", "rota_id": "r1", "motorista_id": "m1"}
            ],
            "paradas": [{"id": "pa1", "rota_id": "r1", "endereco": "Rua X"}],
            "pacotes": [
                {"codigo_pacote": "G1", "parada_id": "pa1"},
                {"codigo_pacote": "F1", "parada_id": "pa1"},
            ],
            "scans": [],
            "rota_motoristas": [{"rota_id": "r1", "motorista_id": "m1"}],
            "motoristas": [{"id": "m1", "nome": "Eric"}],
        }

        def table_side_effect(name):
            t = MagicMock()
            t.select.return_value = _q(por_tabela.get(name, []))
            return t

        mock_supabase.table.side_effect = table_side_effect
        orig = gs.get_supabase
        gs.get_supabase = lambda: mock_supabase
        try:
            r = fora_na_rua("09-09-2026")
        finally:
            gs.get_supabase = orig
            mock_supabase.table.side_effect = None

        assert r["total"] == 1
        assert r["por_motorista"][0]["nome"] == "Eric"
        assert r["por_motorista"][0]["exemplos"][0]["code"] == "F1"

    def test_vazio_sem_retorno(self, mock_supabase):
        import app.services.galpao_service as gs
        from app.services.galpao_service import fora_na_rua

        def table_side_effect(name):
            t = MagicMock()
            t.select.return_value = _q([])
            return t

        mock_supabase.table.side_effect = table_side_effect
        orig = gs.get_supabase
        gs.get_supabase = lambda: mock_supabase
        try:
            assert fora_na_rua("09-09-2026") == {"total": 0, "por_motorista": []}
        finally:
            gs.get_supabase = orig
            mock_supabase.table.side_effect = None


class TestRankingDevolucao:
    def test_ranking_ordena_e_deduplica(self, mock_supabase):
        from app.services.galpao_service import ranking_devolucao

        # fora_na_rua usa get_supabase interno; aqui testamos ranking direto
        def table_side_effect(name):
            t = MagicMock()
            if name == "galpao_scans":
                t.select.return_value = _q(
                    [
                        {
                            "codigo_pacote": "A",
                            "motorista_id": "m1",
                            "escaneado_em": "2026-09-09T10:00:00",
                        },
                        {
                            "codigo_pacote": "A",
                            "motorista_id": "m1",
                            "escaneado_em": "2026-09-09T11:00:00",
                        },
                        {
                            "codigo_pacote": "B",
                            "motorista_id": "m2",
                            "escaneado_em": "2026-09-09T10:00:00",
                        },
                    ]
                )
            elif name == "motoristas":
                t.select.return_value = _q(
                    [{"id": "m1", "nome": "Eric"}, {"id": "m2", "nome": "Thiago"}]
                )
            else:
                t.select.return_value = _q([])
            return t

        mock_supabase.table.side_effect = table_side_effect
        try:
            # injeta o mock direto (ranking chama get_supabase interno)
            import app.services.galpao_service as gs

            orig = gs.get_supabase
            gs.get_supabase = lambda: mock_supabase
            try:
                rank = ranking_devolucao(dias=365)
            finally:
                gs.get_supabase = orig
        finally:
            mock_supabase.table.side_effect = None

        assert [(r["nome"], r["total"]) for r in rank] == [("Eric", 1), ("Thiago", 1)]
