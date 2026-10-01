import os
import unittest
from unittest.mock import patch

import consulta_loteca


class OddsApiTest(unittest.TestCase):
    def test_data_distante_impede_associacao_automatica(self):
        jogo = {"mandante": "TIME A", "visitante": "TIME B", "data": "2026-10-01"}
        evento = {
            "home_team": "TIME A",
            "away_team": "TIME B",
            "commence_time": "2026-10-03T20:00:00Z",
        }
        encontrado, score, _invertido, _nome = consulta_loteca.encontrar_evento(jogo, [evento])
        self.assertIsNone(encontrado)
        self.assertLess(score, 0.78)

    def test_evento_nao_e_reutilizado_em_dois_jogos(self):
        jogos = [
            {"mandante": "TIME A", "visitante": "TIME B"},
            {"mandante": "TIME A", "visitante": "TIME B"},
        ]
        evento = {
            "home_team": "TIME A",
            "away_team": "TIME B",
            "sport_key": "soccer_teste",
            "bookmakers": [
                {
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "TIME A", "price": 2.0},
                                {"name": "Draw", "price": 3.0},
                                {"name": "TIME B", "price": 4.0},
                            ],
                        }
                    ]
                }
            ],
        }

        with patch.dict(os.environ, {"THE_ODDS_API_KEY": "teste"}):
            with patch.object(consulta_loteca, "buscar_eventos_the_odds_api", return_value=[evento]):
                consulta_loteca.completar_odds_the_odds_api(jogos)

        self.assertTrue(jogos[0]["odds_encontradas"])
        self.assertFalse(jogos[1]["odds_encontradas"])

    def test_descarta_odds_invalidas(self):
        evento = {
            "home_team": "A",
            "away_team": "B",
            "bookmakers": [
                {
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "A", "price": "nan"},
                                {"name": "Draw", "price": 3.0},
                                {"name": "B", "price": 4.0},
                            ],
                        }
                    ]
                }
            ],
        }
        self.assertIsNone(consulta_loteca.odds_1x2_the_odds_api(evento))


if __name__ == "__main__":
    unittest.main()
