import unittest
from unittest.mock import patch

import gera_loteca
import lotogen


class AtualizacaoBancosTest(unittest.TestCase):
    def test_sem_modalidades_seleciona_todos_os_bancos(self):
        modalidades = lotogen.modalidades_para_atualizacao()
        self.assertEqual(set(lotogen.MODALIDADES), set(modalidades) - {"loteca"})
        self.assertIn("loteca", modalidades)

    @patch("lotogen.total_resultados_numericos", return_value=10)
    @patch("lotogen.intervalo_concursos_numericos", return_value=(1, 10))
    @patch("lotogen.sincronizar_historico", return_value=True)
    def test_atualiza_modalidade_numerica_sem_gerar_bilhetes(
        self,
        sincronizar,
        _intervalo,
        _total,
    ):
        self.assertTrue(lotogen.atualizar_bancos(["mega-sena"]))
        sincronizar.assert_called_once_with("mega-sena")

    @patch.object(gera_loteca, "atualizar_loteca")
    @patch(
        "lotogen.buscar_programacao_loteca",
        return_value=[{"nuConcurso": 200}, {"nuConcurso": 201}],
    )
    def test_atualiza_todos_os_concursos_atuais_da_loteca(
        self,
        _programacao,
        atualizar,
    ):
        self.assertTrue(lotogen.atualizar_bancos(["loteca"], force_loteca=True))
        self.assertEqual(atualizar.call_count, 2)
        self.assertEqual(
            [chamada.kwargs["concurso"] for chamada in atualizar.call_args_list],
            [200, 201],
        )
        self.assertTrue(all(chamada.kwargs["force"] for chamada in atualizar.call_args_list))

    @patch("lotogen.gerar_bilhetes", side_effect=AssertionError("não deveria gerar"))
    @patch("lotogen.atualizar_bancos", return_value=True)
    def test_subcomando_atualizar_nao_entra_no_fluxo_de_bilhetes(
        self,
        atualizar,
        _gerar,
    ):
        lotogen.main(["atualizar", "mega"])
        atualizar.assert_called_once_with(
            ["mega-sena"],
            concurso_loteca=None,
            force_loteca=False,
        )

    @patch("lotogen.sincronizar_historico", return_value=False)
    @patch("lotogen.intervalo_concursos_numericos", return_value=(1, 5))
    @patch("lotogen.total_resultados_numericos", return_value=5)
    def test_atualizacao_parcial_retorna_falha(
        self,
        _total,
        _intervalo,
        _sincronizar,
    ):
        self.assertFalse(lotogen.atualizar_bancos(["quina"]))


if __name__ == "__main__":
    unittest.main()
