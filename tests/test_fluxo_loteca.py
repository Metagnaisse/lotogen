import unittest
from unittest.mock import patch

import gera_loteca
import lotogen


def jogos_validos(prefixo="ATUAL"):
    return [
        {
            "odds": [2.0, 3.0, 4.0],
            "mandante": f"{prefixo} M{indice}",
            "visitante": f"{prefixo} V{indice}",
        }
        for indice in range(14)
    ]


class FluxoLotecaTest(unittest.TestCase):
    @patch("lotogen.le_sim_nao", return_value=False)
    @patch("lotogen.buscar_programacao_loteca", return_value=[{"nuConcurso": 200}])
    @patch("lotogen.loteca_local_pronta", side_effect=lambda concurso: concurso == 100)
    @patch("lotogen.concursos_loteca", return_value=[{"concurso": 100}])
    def test_recusar_atualizacao_retorna_concurso_atual_sem_escolher_antigo(
        self,
        _concursos,
        _pronta,
        _programacao,
        _resposta,
    ):
        atuais = lotogen.checa_bancos_historicos(["loteca"])
        self.assertEqual(atuais, [200])

        with patch("lotogen.jogos_loteca") as buscar_jogos:
            concurso, jogos = lotogen.escolhe_concurso_loteca_local(atuais)
        self.assertIsNone(concurso)
        self.assertEqual(jogos, [])
        buscar_jogos.assert_not_called()

    @patch("lotogen.le_modo_loteca", return_value="razao")
    @patch("lotogen.le_inteiro", side_effect=[1, 0])
    @patch("lotogen.le_sim_nao", return_value=True)
    @patch("lotogen.jogos_loteca", return_value=jogos_validos("ANTIGO"))
    @patch("lotogen.loteca_local_pronta", side_effect=lambda concurso: concurso == 100)
    @patch("lotogen.concursos_loteca", return_value=[{"concurso": 100, "data_proximo_concurso": None}])
    def test_concurso_anterior_exige_confirmacao_explicita(
        self,
        _concursos,
        _pronta,
        _jogos,
        confirmar,
        _inteiros,
        _modo,
    ):
        configuracao = lotogen.configura_loteca([200])
        confirmar.assert_called_once()
        self.assertTrue(configuracao["jogos"][0]["mandante"].startswith("ANTIGO"))

    @patch("lotogen.le_modo_loteca", return_value="razao")
    @patch("lotogen.le_inteiro", side_effect=[1, 0])
    @patch("lotogen.solicita_planilha_loteca", return_value=jogos_validos("MANUAL"))
    @patch("lotogen.os.path.exists", return_value=False)
    @patch("lotogen.le_sim_nao", return_value=False)
    @patch("lotogen.jogos_loteca", return_value=jogos_validos("ANTIGO"))
    @patch("lotogen.loteca_local_pronta", side_effect=lambda concurso: concurso == 100)
    @patch("lotogen.concursos_loteca", return_value=[{"concurso": 100, "data_proximo_concurso": None}])
    def test_recusa_do_concurso_anterior_nao_usa_dados_antigos_silenciosamente(
        self,
        _concursos,
        _pronta,
        _jogos,
        _confirmar,
        _existe,
        _planilha,
        _inteiros,
        _modo,
    ):
        configuracao = lotogen.configura_loteca([200])
        self.assertTrue(configuracao["jogos"][0]["mandante"].startswith("MANUAL"))

    @patch.object(gera_loteca, "atualizar_loteca")
    @patch("lotogen.le_sim_nao", return_value=True)
    @patch("lotogen.buscar_programacao_loteca", return_value=[{"nuConcurso": 200, "listaJogos": []}])
    @patch("lotogen.loteca_local_pronta", return_value=False)
    @patch("lotogen.concursos_loteca", return_value=[{"concurso": 200}])
    def test_concurso_incompleto_e_atualizado_com_programacao_ja_consultada(
        self,
        _concursos,
        _pronta,
        _programacao,
        _resposta,
        atualizar,
    ):
        atuais = lotogen.checa_bancos_historicos(["loteca"])
        self.assertEqual(atuais, [200])
        atualizar.assert_called_once()
        self.assertEqual(atualizar.call_args.kwargs["dados_concurso"]["nuConcurso"], 200)


if __name__ == "__main__":
    unittest.main()
