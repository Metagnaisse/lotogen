"""Algoritmo puro de geração de palpites da Loteca a partir de odds 1X2."""

from heapq import heappop, heappush
from itertools import combinations
from math import isfinite, log
from random import choices


COLUNAS_LOTECA = ("1", "X", "2")


def _valida_quantidade(quantidade, minimo, maximo):
    if not minimo <= quantidade <= maximo:
        raise ValueError(f"Quantidade deve ficar entre {minimo} e {maximo}.")
    return quantidade


def probabilidades_por_odds(odds):
    """Remove a margem proporcional das odds e devolve probabilidades que somam 1."""
    if len(odds) != 3:
        raise ValueError("Cada jogo da Loteca precisa de três odds 1X2.")

    try:
        odds = [float(odd) for odd in odds]
    except (TypeError, ValueError):
        raise ValueError("As odds da Loteca precisam ser numéricas.")

    if any(not isfinite(odd) or odd <= 1 for odd in odds):
        raise ValueError("As odds da Loteca precisam ser finitas e maiores que 1.")

    inversos = [1 / odd for odd in odds]
    total = sum(inversos)
    return [inverso / total for inverso in inversos]


def ranking_colunas_loteca(probabilidades):
    indices = sorted(range(3), key=lambda indice: probabilidades[indice], reverse=True)
    return [COLUNAS_LOTECA[indice] for indice in indices]


def equilibrio_loteca(probabilidades):
    ordenadas = sorted(probabilidades, reverse=True)
    return ordenadas[1] / ordenadas[0]


def opcoes_colunas_loteca(probabilidades, quantidade):
    """Retorna as combinações possíveis, ordenadas pela cobertura probabilística."""
    opcoes = []

    for indices in combinations(range(3), quantidade):
        cobertura = sum(probabilidades[indice] for indice in indices)
        colunas = [COLUNAS_LOTECA[indice] for indice in indices]
        opcoes.append((cobertura, colunas))

    return sorted(opcoes, key=lambda item: item[0], reverse=True)


def distribuir_multiplos_loteca(probabilidades_jogos, duplos, triplos):
    """Maximiza a probabilidade conjunta coberta com quantidades exatas de múltiplos."""
    estados = {(0, 0): (0.0, [])}

    for probabilidades in probabilidades_jogos:
        coberturas = {
            "simples": opcoes_colunas_loteca(probabilidades, 1)[0][0],
            "duplo": opcoes_colunas_loteca(probabilidades, 2)[0][0],
            "triplo": 1.0,
        }
        proximos = {}

        for (usados_duplos, usados_triplos), (pontuacao, tipos) in estados.items():
            for tipo, incremento_duplo, incremento_triplo in (
                ("simples", 0, 0),
                ("duplo", 1, 0),
                ("triplo", 0, 1),
            ):
                novos_duplos = usados_duplos + incremento_duplo
                novos_triplos = usados_triplos + incremento_triplo

                if novos_duplos > duplos or novos_triplos > triplos:
                    continue

                nova_pontuacao = pontuacao + log(coberturas[tipo])
                chave = (novos_duplos, novos_triplos)
                anterior = proximos.get(chave)

                if anterior is None or nova_pontuacao > anterior[0]:
                    proximos[chave] = (nova_pontuacao, tipos + [tipo])

        estados = proximos

    return estados[(duplos, triplos)][1]


def combinacao_loteca_por_variante(candidatos, variante):
    """Obtém a enésima melhor combinação conjunta sem enumerar todo o produto."""
    capacidade = 1
    for opcoes in candidatos:
        capacidade *= len(opcoes)

    if not 0 <= variante < capacidade:
        raise ValueError(f"A variante deve ficar entre 0 e {capacidade - 1}.")

    inicial = tuple(0 for _opcoes in candidatos)
    fila = [(0.0, inicial)]
    visitados = {inicial}

    for _indice in range(variante + 1):
        _penalidade, posicoes = heappop(fila)

        for jogo, opcoes in enumerate(candidatos):
            atual = posicoes[jogo]
            if atual + 1 >= len(opcoes):
                continue

            vizinho = list(posicoes)
            vizinho[jogo] += 1
            vizinho = tuple(vizinho)
            if vizinho in visitados:
                continue

            visitados.add(vizinho)
            penalidade = sum(
                log(opcoes_jogo[0][0] / opcoes_jogo[posicao][0])
                for opcoes_jogo, posicao in zip(candidatos, vizinho)
            )
            heappush(fila, (penalidade, vizinho))

    return [
        candidatos[jogo][posicao][1]
        for jogo, posicao in enumerate(posicoes)
    ]


def capacidade_bilhetes_loteca(triplos):
    return 3 ** (14 - triplos)


def gera_bilhete_loteca(jogos, duplos=1, triplos=0, modo="emocao", variante=0):
    if len(jogos) != 14:
        raise ValueError("A Loteca precisa de odds para 14 jogos.")

    duplos = _valida_quantidade(duplos, 0, 14)
    triplos = _valida_quantidade(triplos, 0, 14)

    if duplos + triplos > 14:
        raise ValueError("A soma de duplos e triplos não pode passar de 14.")

    if modo not in ("razao", "emocao"):
        raise ValueError("Modo da Loteca deve ser 'razao' ou 'emocao'.")

    probabilidades_jogos = [probabilidades_por_odds(jogo["odds"]) for jogo in jogos]
    tipos = distribuir_multiplos_loteca(probabilidades_jogos, duplos, triplos)
    quantidades = {"simples": 1, "duplo": 2, "triplo": 3}
    candidatos = [
        opcoes_colunas_loteca(probabilidades, quantidades[tipo])
        for probabilidades, tipo in zip(probabilidades_jogos, tipos)
    ]

    if modo == "razao":
        colunas_por_jogo = combinacao_loteca_por_variante(candidatos, variante)
    else:
        colunas_por_jogo = [
            choices(
                opcoes,
                weights=[cobertura for cobertura, _colunas in opcoes],
                k=1,
            )[0][1]
            for opcoes in candidatos
        ]

    return [
        {
            "colunas": colunas_por_jogo[indice],
            "mandante": jogos[indice].get("mandante"),
            "visitante": jogos[indice].get("visitante"),
        }
        for indice in range(14)
    ]
