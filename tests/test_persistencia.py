import json
import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import banco_lotogen
import historico_loterias
from favoritos import cria_favorito, valida_colunas_super_sete
from lotogen import gera_mais_milionaria, valores_favorito


class BancoTemporarioTest(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.caminho = os.path.join(self.diretorio.name, "lotogen.db")
        self.caminho_original = banco_lotogen.CAMINHO_BANCO
        banco_lotogen.CAMINHO_BANCO = self.caminho

    def tearDown(self):
        banco_lotogen.CAMINHO_BANCO = self.caminho_original
        self.diretorio.cleanup()

    def test_favorito_preserva_aposta_multipla(self):
        cria_favorito("mega-sena", ["01", "02", "03", "04", "05", "06", "07"])
        favorito = banco_lotogen.listar_favoritos("mega-sena")[0]
        self.assertEqual(len(json.loads(favorito["dezenas_json"])), 7)
        self.assertIsNone(favorito["extra"])

    def test_favorito_preserva_mais_milionaria_multipla(self):
        bilhete = gera_mais_milionaria(8, 4)
        cria_favorito("mais-milionaria", valores_favorito("mais-milionaria", bilhete))
        favorito = banco_lotogen.listar_favoritos("mais-milionaria")[0]
        self.assertEqual(len(json.loads(favorito["dezenas_json"])), 8)
        self.assertEqual(len(favorito["extra"].split()), 4)

    def test_favorito_preserva_dia_de_sorte_multiplo(self):
        cria_favorito(
            "dia-de-sorte",
            {
                "dezenas": ["01", "02", "03", "04", "05", "06", "07", "08"],
                "extra": "março",
            },
        )
        favorito = banco_lotogen.listar_favoritos("dia-de-sorte")[0]
        self.assertEqual(len(json.loads(favorito["dezenas_json"])), 8)
        self.assertEqual(favorito["extra"], "marco")

    def test_substituir_loteca_remove_jogos_antigos(self):
        jogos = [
            SimpleNamespace(
                sequencial=indice,
                mandante=f"M{indice}",
                visitante=f"V{indice}",
                odd_mandante=2.0,
                odd_empate=3.0,
                odd_visitante=4.0,
            )
            for indice in range(1, 15)
        ]
        banco_lotogen.salvar_loteca(100, jogos)
        banco_lotogen.salvar_loteca(100, jogos[:1])
        self.assertEqual(len(banco_lotogen.jogos_loteca(100)), 1)

    def test_calculo_offline_nao_sincroniza(self):
        with patch.object(historico_loterias, "sincronizar_historico") as sincronizar:
            with self.assertRaises(RuntimeError):
                historico_loterias.frequencias_historicas("mega-sena", atualizar=False)
        sincronizar.assert_not_called()


class ValidacaoFavoritosTest(unittest.TestCase):
    def test_super_sete_rejeita_distribuicao_invalida(self):
        with self.assertRaises(ValueError):
            valida_colunas_super_sete([["1", "2", "3"]] + [["1"]] * 6)


class MigracaoFavoritosTest(unittest.TestCase):
    def test_recupera_dezenas_salvas_como_extra(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = os.path.join(diretorio, "antigo.db")
            conexao = sqlite3.connect(caminho)
            conexao.execute(
                """
                CREATE TABLE bilhetes_favoritos (
                    id INTEGER PRIMARY KEY, nome TEXT, modalidade TEXT NOT NULL,
                    dezenas_json TEXT NOT NULL, extra TEXT, criado_em TEXT NOT NULL
                )
                """
            )
            conexao.execute(
                """
                INSERT INTO bilhetes_favoritos
                    (modalidade, dezenas_json, extra, criado_em)
                VALUES ('mega-sena', '["01", "02", "03", "04", "05", "06"]', '07', 'agora')
                """
            )
            conexao.commit()
            conexao.close()

            with banco_lotogen.conectar(caminho) as migrado:
                favorito = migrado.execute("SELECT * FROM bilhetes_favoritos").fetchone()

            self.assertEqual(len(json.loads(favorito["dezenas_json"])), 7)
            self.assertIsNone(favorito["extra"])


if __name__ == "__main__":
    unittest.main()
