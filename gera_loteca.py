"""Atualiza o loteca_atual.csv com jogos e odds da Loteca.

Os jogos oficiais são descobertos pela API da Caixa via consulta_loteca.py.
Quando THE_ODDS_API_KEY estiver configurada, as odds 1X2 são buscadas
automaticamente. Odds faltantes são solicitadas manualmente.
"""

import argparse
import csv
import os
from dataclasses import dataclass

from banco_lotogen import concurso_loteca_existe, jogos_loteca as jogos_loteca_banco, salvar_loteca
from consulta_loteca import (
    buscar_programacao_loteca,
    completar_odds_the_odds_api,
    concurso_por_numero,
    jogos_do_concurso,
    numero_concurso as numero_concurso_caixa,
    the_odds_api_key,
)


ARQUIVO_PADRAO = "loteca_atual.csv"
CABECALHO = ["odd_mandante", "odd_empate", "odd_visitante", "time_mandante", "time_visitante"]
METADADO_CONCURSO = "# concurso"


@dataclass
class JogoLoteca:
    mandante: str
    visitante: str
    odd_mandante: float | None = None
    odd_empate: float | None = None
    odd_visitante: float | None = None
    concurso: int | None = None
    data: str | None = None
    sequencial: int | None = None
    dia_semana: str | None = None
    competicao: str | None = None


def normaliza_nome(nome):
    return " ".join(nome.strip().upper().split())


def le_decimal(mensagem):
    while True:
        resposta = input(mensagem).strip().replace(",", ".")

        try:
            valor = float(resposta)
        except ValueError:
            print("Informe um numero decimal. Exemplo: 1.80")
            continue

        if valor <= 1:
            print("A odd precisa ser maior que 1.")
            continue

        return valor


def le_texto_obrigatorio(mensagem):
    while True:
        resposta = input(mensagem).strip()

        if resposta:
            return normaliza_nome(resposta)

        print("Informe um valor.")


def jogos_oficiais_do_concurso(concurso):
    numero_concurso = concurso.get("nuConcurso")
    jogos = jogos_do_concurso(concurso)

    if the_odds_api_key():
        print("Buscando odds 1X2 na The Odds API...")
        try:
            jogos = completar_odds_the_odds_api(jogos)
        except Exception as erro:
            print(f"Nao consegui buscar odds na The Odds API: {erro}")
        else:
            total = sum(1 for jogo in jogos if jogo.get("odds_encontradas"))
            print(f"The Odds API encontrou odds para {total} de {len(jogos)} jogos.")

    if not the_odds_api_key():
        print("Nenhuma API de odds configurada; as odds serao preenchidas manualmente.")

    pendentes = [
        jogo
        for jogo in jogos
        if not (jogo.get("odd_mandante") and jogo.get("odd_empate") and jogo.get("odd_visitante"))
    ]

    if pendentes:
        print("Jogos sem odds automaticas:")

        for jogo in pendentes:
            candidato = jogo.get("odds_melhor_candidato") or "nenhum candidato"
            score = jogo.get("odds_match_score") or 0
            status = jogo.get("odds_status") or jogo.get("the_odds_status") or "nao encontrada"
            data = jogo.get("data") or "sem data"
            print(
                f"- {jogo['mandante']} x {jogo['visitante']} "
                f"({status}; data {data}; melhor: {candidato}, score {score:.2f})"
            )

    return [
        JogoLoteca(
            jogo["mandante"],
            jogo["visitante"],
            odd_mandante=jogo.get("odd_mandante"),
            odd_empate=jogo.get("odd_empate"),
            odd_visitante=jogo.get("odd_visitante"),
            concurso=numero_concurso,
            data=jogo.get("data"),
            sequencial=jogo.get("sequencial"),
            dia_semana=jogo.get("dia_semana"),
            competicao=jogo.get("competicao"),
        )
        for jogo in jogos
    ]


def descricao_concurso(concurso):
    numero = numero_concurso_caixa(concurso) or "?"
    data = concurso.get("dataProximoConcurso") or "sem data"
    total_jogos = len(jogos_do_concurso(concurso))
    return f"{numero} - {data} - {total_jogos} jogos"


def escolher_concurso_caixa(numero=None):
    if numero:
        return concurso_por_numero(numero)

    concursos = buscar_programacao_loteca()

    if not concursos:
        raise RuntimeError("A API da Caixa nao retornou programacao da Loteca.")

    if len(concursos) == 1:
        return concursos[0]

    print("Concursos da Loteca disponiveis na Caixa:")

    for indice, concurso in enumerate(concursos, start=1):
        print(f"{indice}. {descricao_concurso(concurso)}")

    while True:
        resposta = input("Qual concurso deseja atualizar? [ENTER para o primeiro] ").strip()

        if not resposta:
            return concursos[0]

        try:
            indice = int(resposta)
        except ValueError:
            print("Informe o numero da opcao.")
            continue

        if 1 <= indice <= len(concursos):
            return concursos[indice - 1]

        print("Opcao invalida.")


def descobrir_jogos_oficiais():
    try:
        concurso = escolher_concurso_caixa()
    except Exception as erro:
        print(f"Nao consegui buscar os jogos oficiais: {erro}")
        return []

    return jogos_oficiais_do_concurso(concurso)


def ler_jogos_manualmente():
    jogos = []

    print()
    print("Informe os 14 jogos da Loteca.")

    for indice in range(1, 15):
        print()
        mandante = le_texto_obrigatorio(f"Jogo {indice:02d} - mandante: ")
        visitante = le_texto_obrigatorio(f"Jogo {indice:02d} - visitante: ")
        jogos.append(JogoLoteca(mandante, visitante))

    return jogos


def preencher_odds_manualmente(jogos):
    pendentes = [
        jogo
        for jogo in jogos
        if not (jogo.odd_mandante and jogo.odd_empate and jogo.odd_visitante)
    ]

    if not pendentes:
        print("Todas as odds foram preenchidas automaticamente.")
        return jogos

    print()
    print("Informe as odds 1X2 dos jogos sem odds automaticas.")

    for indice, jogo in enumerate(jogos, start=1):
        if jogo.odd_mandante and jogo.odd_empate and jogo.odd_visitante:
            continue

        print()
        print(f"Jogo {indice:02d}: {jogo.mandante} x {jogo.visitante}")
        jogo.odd_mandante = le_decimal("Odd mandante: ")
        jogo.odd_empate = le_decimal("Odd empate: ")
        jogo.odd_visitante = le_decimal("Odd visitante: ")

    return jogos


def validar_jogos(jogos):
    if len(jogos) != 14:
        raise ValueError("A Loteca precisa de exatamente 14 jogos.")

    for indice, jogo in enumerate(jogos, start=1):
        if not jogo.mandante or not jogo.visitante:
            raise ValueError(f"Jogo {indice:02d}: informe mandante e visitante.")

        odds = (jogo.odd_mandante, jogo.odd_empate, jogo.odd_visitante)

        if any(odd is None or odd <= 1 for odd in odds):
            raise ValueError(f"Jogo {indice:02d}: informe odds validas maiores que 1.")


def concurso_csv(caminho):
    if not os.path.exists(caminho):
        return None

    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        primeira_linha = arquivo.readline().strip()

    if not primeira_linha.startswith(METADADO_CONCURSO):
        return None

    try:
        return int(primeira_linha.split(";", 1)[1])
    except (IndexError, ValueError):
        return None


def escrever_csv(jogos, caminho, concurso=None):
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")

        if concurso:
            escritor.writerow([METADADO_CONCURSO, concurso])

        escritor.writerow(CABECALHO)

        for jogo in jogos:
            escritor.writerow(
                [
                    jogo.odd_mandante,
                    jogo.odd_empate,
                    jogo.odd_visitante,
                    jogo.mandante,
                    jogo.visitante,
                ]
            )


def jogos_salvos_do_banco(concurso):
    return [
        JogoLoteca(
            jogo.get("mandante"),
            jogo.get("visitante"),
            odd_mandante=jogo["odds"][0],
            odd_empate=jogo["odds"][1],
            odd_visitante=jogo["odds"][2],
            competicao=jogo.get("competicao"),
        )
        for jogo in jogos_loteca_banco(concurso)
    ]


def atualizar_loteca(saida=ARQUIVO_PADRAO, manual=False, concurso=None):
    caminho_saida = os.path.abspath(saida)

    if manual:
        jogos = []
        numero_concurso = concurso
        data_proximo_concurso = None
    else:
        try:
            concurso_atual_caixa = escolher_concurso_caixa(concurso)
        except Exception as erro:
            print(f"Nao consegui buscar os jogos oficiais: {erro}")
            concurso_atual_caixa = None

        numero_concurso = numero_concurso_caixa(concurso_atual_caixa) if concurso_atual_caixa else concurso
        data_proximo_concurso = (
            concurso_atual_caixa.get("dataProximoConcurso") if concurso_atual_caixa else None
        )

        if numero_concurso and concurso_loteca_existe(numero_concurso):
            if concurso_csv(caminho_saida) == int(numero_concurso):
                print(f"A Loteca local ja esta atualizada para o concurso {numero_concurso}.")
                return caminho_saida

            jogos_salvos = jogos_salvos_do_banco(numero_concurso)
            if jogos_salvos:
                escrever_csv(jogos_salvos, caminho_saida, numero_concurso)
                print(f"Banco ja tinha o concurso {numero_concurso}.")
                print(f"Arquivo atualizado: {caminho_saida}")
                return caminho_saida

        jogos = jogos_oficiais_do_concurso(concurso_atual_caixa) if concurso_atual_caixa else []

    if not jogos:
        print("Nao foi possivel descobrir os jogos automaticamente.")
        jogos = ler_jogos_manualmente()

    jogos = preencher_odds_manualmente(jogos)
    validar_jogos(jogos)

    numero_concurso = numero_concurso or next((jogo.concurso for jogo in jogos if jogo.concurso), None)
    if numero_concurso:
        salvar_loteca(numero_concurso, jogos, data_proximo_concurso=data_proximo_concurso)

    escrever_csv(jogos, caminho_saida, numero_concurso)

    if numero_concurso:
        print(f"Banco atualizado: concurso {numero_concurso}")
    print(f"Arquivo atualizado: {caminho_saida}")
    return caminho_saida


def parse_args():
    parser = argparse.ArgumentParser(description="Atualiza o loteca_atual.csv com jogos e odds.")
    parser.add_argument(
        "--saida",
        default=ARQUIVO_PADRAO,
        help="Arquivo CSV de saida. Padrao: loteca_atual.csv",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Ignora fontes/API e solicita os 14 jogos manualmente.",
    )
    parser.add_argument(
        "--concurso",
        type=int,
        help="Numero do concurso da Loteca a atualizar ou usar em modo manual.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    atualizar_loteca(
        saida=args.saida,
        manual=args.manual,
        concurso=args.concurso,
    )


if __name__ == "__main__":
    main()
