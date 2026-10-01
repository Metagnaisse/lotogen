import math
import os
import tempfile
import unittest
from itertools import combinations
from unittest.mock import patch

from lotogen import (
    COLUNAS_LOTECA,
    gera_bilhete_loteca,
    gera_bilhetes_historicos,
    gera_mais_milionaria,
    gera_super_sete,
    le_planilha_loteca,
    probabilidades_por_odds,
)


class GeracaoLotecaTest(unittest.TestCase):
    def setUp(self):
        self.jogos = [
            {"odds": [1.55 + indice * 0.08, 2.75 + indice * 0.03, 5.4 - indice * 0.1]}
            for indice in range(14)
        ]

    def probabilidade_coberta(self, bilhete):
        total = 1.0
        for jogo, palpite in zip(self.jogos, bilhete):
            probabilidades = probabilidades_por_odds(jogo["odds"])
            indices = [COLUNAS_LOTECA.index(coluna) for coluna in palpite["colunas"]]
            total *= sum(probabilidades[indice] for indice in indices)
        return total

    def test_probabilidades_sao_normalizadas(self):
        probabilidades = probabilidades_por_odds([2.0, 3.0, 4.0])
        self.assertAlmostEqual(sum(probabilidades), 1.0)
        self.assertGreater(probabilidades[0], probabilidades[1])
        self.assertGreater(probabilidades[1], probabilidades[2])

    def test_odds_nao_finitas_sao_rejeitadas(self):
        for odds in ([math.nan, 2, 3], [math.inf, 2, 3], [1, 2, 3]):
            with self.subTest(odds=odds), self.assertRaises(ValueError):
                probabilidades_por_odds(odds)

    def test_quantidades_de_duplos_e_triplos_sao_exatas(self):
        bilhete = gera_bilhete_loteca(self.jogos, duplos=3, triplos=2, modo="razao")
        self.assertEqual(sum(len(jogo["colunas"]) == 2 for jogo in bilhete), 3)
        self.assertEqual(sum(len(jogo["colunas"]) == 3 for jogo in bilhete), 2)
        self.assertEqual(sum(len(jogo["colunas"]) == 1 for jogo in bilhete), 9)

    def test_alocacao_maximiza_cobertura_conjunta(self):
        bilhete = gera_bilhete_loteca(self.jogos, duplos=2, triplos=1, modo="razao")
        obtida = self.probabilidade_coberta(bilhete)
        probabilidades = [probabilidades_por_odds(jogo["odds"]) for jogo in self.jogos]
        melhor = 0.0

        for triplo in range(14):
            restantes = [indice for indice in range(14) if indice != triplo]
            for duplos in combinations(restantes, 2):
                cobertura = 1.0
                for indice, probs in enumerate(probabilidades):
                    quantidade = 3 if indice == triplo else 2 if indice in duplos else 1
                    cobertura *= sum(sorted(probs, reverse=True)[:quantidade])
                melhor = max(melhor, cobertura)

        self.assertAlmostEqual(obtida, melhor)

    def test_variantes_racionais_sao_distintas_e_ordenadas(self):
        bilhetes = [
            gera_bilhete_loteca(self.jogos, duplos=1, triplos=1, modo="razao", variante=i)
            for i in range(3)
        ]
        assinaturas = {
            tuple(tuple(jogo["colunas"]) for jogo in bilhete)
            for bilhete in bilhetes
        }
        self.assertEqual(len(assinaturas), 3)
        coberturas = [self.probabilidade_coberta(bilhete) for bilhete in bilhetes]
        self.assertGreaterEqual(coberturas[0], coberturas[1])
        self.assertGreaterEqual(coberturas[1], coberturas[2])

    def test_zero_duplos_e_permitido(self):
        bilhete = gera_bilhete_loteca(self.jogos, duplos=0, triplos=0, modo="razao")
        self.assertTrue(all(len(jogo["colunas"]) == 1 for jogo in bilhete))


class GeracaoNumericaTest(unittest.TestCase):
    def test_mais_milionaria_aceita_aposta_multipla(self):
        bilhete = gera_mais_milionaria(12, 6)
        dezenas = [valor for valor in bilhete if not valor.startswith("{")]
        trevos = [valor for valor in bilhete if valor.startswith("{")]
        self.assertEqual(len(dezenas), 12)
        self.assertEqual(len(trevos), 6)
        self.assertEqual(len(set(dezenas)), 12)
        self.assertEqual(len(set(trevos)), 6)

    def test_mais_milionaria_historica_respeita_duas_quantidades(self):
        retorno = (list(range(1, 51)), ["1", "2", "3", "4", "5", "6"], 100)
        with patch("lotogen.ranking_dezenas_por_frequencia", return_value=retorno):
            bilhetes, consultados = gera_bilhetes_historicos(
                "mais-milionaria",
                {"numeros": 8, "trevos": 4},
                "mais",
                total=2,
                atualizar_historico=False,
            )

        self.assertEqual(consultados, 100)
        for bilhete in bilhetes:
            self.assertEqual(sum(not valor.startswith("{") for valor in bilhete), 8)
            self.assertEqual(sum(valor.startswith("{") for valor in bilhete), 4)

    def test_super_sete_respeita_limites_por_coluna(self):
        for quantidade in (7, 8, 14, 15, 21):
            with self.subTest(quantidade=quantidade):
                colunas = gera_super_sete(quantidade)
                limites = (1, 2) if quantidade <= 14 else (2, 3)
                self.assertEqual(sum(map(len, colunas)), quantidade)
                self.assertTrue(all(limites[0] <= len(coluna) <= limites[1] for coluna in colunas))


class LeituraLotecaTest(unittest.TestCase):
    def test_csv_com_metadado_de_concurso(self):
        linhas = [
            "# concurso;1255",
            "odd_mandante;odd_empate;odd_visitante;time_mandante;time_visitante",
        ]
        linhas.extend(f"2.0;3.0;4.0;MANDANTE {i};VISITANTE {i}" for i in range(14))

        with tempfile.TemporaryDirectory() as diretorio:
            caminho = os.path.join(diretorio, "loteca.csv")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write("\n".join(linhas))
            jogos = le_planilha_loteca(caminho)

        self.assertEqual(len(jogos), 14)
        self.assertEqual(jogos[0]["odds"], [2.0, 3.0, 4.0])


if __name__ == "__main__":
    unittest.main()
