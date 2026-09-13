"""
Testes de Entregadores (CRUD).
"""

from unittest.mock import MagicMock


class TestEntregadores:
    """Testes para CRUD de entregadores."""

    def test_listar_entregadores(self, client, mock_supabase, sample_motorista):
        """Testa listagem de entregadores."""
        mock_supabase.table.return_value.select.return_value.execute.side_effect = [
            MagicMock(data=[sample_motorista]),  # motoristas
            MagicMock(count=10),  # total geral
            MagicMock(count=5),  # total hoje
            MagicMock(count=2),  # pendentes
        ]

        response = client.get("/entregadores")
        assert response.status_code == 200
        assert b"Entregadores" in response.data
        assert sample_motorista["nome"].encode() in response.data

    def test_novo_entregador_get(self, client):
        """Testa formulário de novo entregador (GET)."""
        response = client.get("/entregadores/novo")
        assert response.status_code == 200
        assert b"Novo Entregador" in response.data or b"novo" in response.data.lower()

    def test_novo_entregador_post_valido(self, client, mock_supabase):
        """Testa criação de entregador válido."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{"id": "new-id", "nome": "Novo", "telefone": "123"}])
        )

        response = client.post(
            "/entregadores/novo",
            data={"nome": "Novo Entregador", "telefone": "(77) 99999-9999"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verifica se foi redirecionado para lista

    def test_novo_entregador_post_invalido(self, client):
        """Testa criação com nome vazio."""
        response = client.post(
            "/entregadores/novo", data={"nome": "", "telefone": "123"}
        )
        assert response.status_code == 200  # Retorna formulário com erro
        assert b"obrigat" in response.data.lower()

    def test_editar_entregador_get(self, client, mock_supabase, sample_motorista):
        """Testa formulário de edição (GET)."""
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[sample_motorista])
        )

        response = client.get(f"/entregadores/{sample_motorista['id']}/editar")
        assert response.status_code == 200
        assert sample_motorista["nome"].encode() in response.data

    def test_editar_entregador_post(self, client, mock_supabase, sample_motorista):
        """Testa atualização de entregador."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": sample_motorista["id"], "nome": "Nome Atualizado"}]
        )

        response = client.post(
            f"/entregadores/{sample_motorista['id']}/editar",
            data={"nome": "Nome Atualizado", "telefone": "(77) 88888-8888"},
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_excluir_entregador(self, client, mock_supabase, sample_motorista):
        """Testa exclusão de entregador."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        response = client.post(
            f"/entregadores/{sample_motorista['id']}/excluir", follow_redirects=True
        )
        assert response.status_code == 200

    def test_detalhe_entregador(
        self, client, mock_supabase, sample_motorista, sample_scan
    ):
        """Testa detalhes do entregador."""
        scan_hoje = dict(
            sample_scan, operator_name="João Silva", session_date="2026-09-09"
        )
        calls = [0]

        def execute_side_effect(*args, **kwargs):
            calls[0] += 1
            # ordem do serviço: motorista, scans do dia, rota_motoristas,
            # rotas (se houver vínculo), pendentes, total, dias x7
            if calls[0] == 1:
                return MagicMock(data=[sample_motorista])  # motorista
            if calls[0] == 2:
                return MagicMock(data=[scan_hoje])  # scans do dia
            return MagicMock(data=[], count=0)

        mock_supabase.table.return_value.select.return_value.execute.side_effect = (
            execute_side_effect
        )

        response = client.get(f"/entregador/{sample_motorista['id']}")
        assert response.status_code == 200
        assert sample_motorista["nome"].encode() in response.data


class TestEntregadoresValidation:
    """Testes de validação."""

    def test_nome_obrigatorio(self, client):
        """Nome é obrigatório."""
        response = client.post(
            "/entregadores/novo", data={"nome": "   ", "telefone": "123"}
        )
        assert b"obrigat" in response.data.lower()

    def test_telefone_opcional(self, client, mock_supabase):
        """Telefone é opcional."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{"id": "new-id", "nome": "Sem Telefone"}])
        )

        response = client.post(
            "/entregadores/novo",
            data={"nome": "Sem Telefone", "telefone": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
