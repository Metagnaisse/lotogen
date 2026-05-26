"""Consulta a programação atual da Loteca e odds 1X2 pela The Odds API."""

import os
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from unicodedata import normalize

import requests


CAIXA_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/loteca/programacao"
THE_ODDS_API_SPORTS_URL = "https://api.the-odds-api.com/v4/sports"
THE_ODDS_API_ODDS_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"
THE_ODDS_API_DEFAULT_SPORTS = (
    "soccer_brazil_campeonato",
    "soccer_brazil_serie_b",
    "soccer_epl",
)

APELIDOS_TIMES = {
    "ATLETICO": "ATLETICO MINEIRO",
    "ATLETICO MG": "ATLETICO MINEIRO",
    "ATLETICO GO": "ATLETICO GOIANIENSE",
    "ATHLETICO": "ATHLETICO PARANAENSE",
    "ATHLETICO PR": "ATHLETICO PARANAENSE",
    "BRAGANTINO": "RB BRAGANTINO",
    "BOTAFOGO RJ": "BOTAFOGO",
    "BOTAFOGO SP": "BOTAFOGO SP",
    "OPERARIO": "OPERARIO PR",
    "SAO PAULO FC": "SAO PAULO",
    "SPORT RECIFE": "SPORT",
    "VASCO DA GAMA": "VASCO",
}

PALAVRAS_IGNORADAS = {
    "AC",
    "ASSOCIACAO",
    "CLUB",
    "CLUBE",
    "DA",
    "DE",
    "DO",
    "DOS",
    "EC",
    "FC",
    "FUTEBOL",
    "REGATAS",
    "SAF",
    "SC",
    "SOCIEDADE",
}

UF_TIMES = {
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
}


def the_odds_api_key():
    return os.getenv("THE_ODDS_API_KEY")


def depuracao_ativa():
    return os.getenv("THE_ODDS_API_DEBUG", "").strip().lower() in (
        "1",
        "s",
        "sim",
        "true",
        "yes",
    )


def depurar(mensagem):
    if depuracao_ativa():
        print(f"[the-odds-api] {mensagem}")


def buscar_programacao_loteca():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    resposta = requests.get(CAIXA_URL, headers=headers, timeout=20)
    resposta.raise_for_status()

    dados = resposta.json()
    concursos = dados if isinstance(dados, list) else [dados]
    return [concurso for concurso in concursos if isinstance(concurso, dict)]


def concurso_atual():
    concursos = buscar_programacao_loteca()

    if not concursos:
        raise RuntimeError("A API da Caixa nao retornou programacao da Loteca.")

    return concursos[0]


def data_iso(valor):
    if not valor:
        return None

    texto = str(valor).strip()

    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return None


def primeira_data_jogo(jogo, concurso):
    campos = (
        "dtJogo",
        "dataJogo",
        "dataPartida",
        "data",
        "dataRealizacao",
        "dataProximoConcurso",
    )

    for campo in campos:
        data = data_iso(jogo.get(campo) or concurso.get(campo))

        if data:
            return data

    return None


def formatar_time(nome, uf):
    time = nome.strip()

    if uf:
        time = f"{time}/{uf}"

    return time


def jogos_do_concurso(concurso):
    jogos = concurso.get("listaJogos") or concurso.get("listaResultadoEquipeEsportiva", [])
    resultado = []

    for indice, jogo in enumerate(jogos, start=1):
        if "mandante" in jogo and "visitante" in jogo:
            resultado.append(jogo)
            continue

        resultado.append(
            {
                "sequencial": jogo.get("nuSequencial") or indice,
                "mandante": formatar_time(jogo.get("nomeEquipeUm", ""), jogo.get("siglaUFUm", "")),
                "visitante": formatar_time(jogo.get("nomeEquipeDois", ""), jogo.get("siglaUFDois", "")),
                "dia_semana": jogo.get("diaSemana", ""),
                "data": primeira_data_jogo(jogo, concurso),
            }
        )

    return resultado


def nome_base_time(nome):
    texto = str(nome).split("/", 1)[0]
    texto = normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.upper()

    for caractere in ".-'()":
        texto = texto.replace(caractere, " ")

    texto = " ".join(texto.split())

    if texto in APELIDOS_TIMES:
        return APELIDOS_TIMES[texto]

    palavras = [palavra for palavra in texto.split() if palavra not in PALAVRAS_IGNORADAS]

    if palavras and palavras[-1] in UF_TIMES:
        palavras = palavras[:-1]

    texto = " ".join(palavras) or texto
    return APELIDOS_TIMES.get(texto, texto)


def similaridade_time(nome_caixa, nome_api):
    caixa = nome_base_time(nome_caixa)
    api = nome_base_time(nome_api)

    if caixa == api:
        return 1.0

    if caixa in api or api in caixa:
        return 0.92

    tokens_caixa = set(caixa.split())
    tokens_api = set(api.split())
    intersecao = tokens_caixa & tokens_api
    uniao = tokens_caixa | tokens_api
    token_score = len(intersecao) / len(uniao) if uniao else 0
    texto_score = SequenceMatcher(None, caixa, api).ratio()
    return max(token_score, texto_score)


def similaridade_jogo(jogo_loteca, evento):
    home = evento.get("home_team", "")
    away = evento.get("away_team", "")
    direto = (
        similaridade_time(jogo_loteca["mandante"], home)
        + similaridade_time(jogo_loteca["visitante"], away)
    ) / 2
    invertido = (
        similaridade_time(jogo_loteca["mandante"], away)
        + similaridade_time(jogo_loteca["visitante"], home)
    ) / 2

    if direto >= invertido:
        return direto, False

    return invertido, True


def encontrar_evento(jogo_loteca, eventos):
    melhor_evento = None
    melhor_score = 0
    melhor_invertido = False
    melhor_nome = ""

    for evento in eventos:
        score, invertido = similaridade_jogo(jogo_loteca, evento)

        if score > melhor_score:
            melhor_evento = evento
            melhor_score = score
            melhor_invertido = invertido
            melhor_nome = f"{evento.get('home_team', '')} x {evento.get('away_team', '')}"

    minimo = float(os.getenv("THE_ODDS_API_MATCH_MIN_SCORE", "0.78"))

    if melhor_score < minimo:
        return None, melhor_score, melhor_invertido, melhor_nome

    return melhor_evento, melhor_score, melhor_invertido, melhor_nome


def periodo_dos_jogos(jogos):
    datas = sorted({jogo.get("data") for jogo in jogos if jogo.get("data")})

    if not datas:
        return None, None

    return datas[0], datas[-1]


def periodo_the_odds_api(jogos):
    inicio, fim = periodo_dos_jogos(jogos)

    if not inicio or not fim:
        return None, None

    data_inicio = datetime.strptime(inicio, "%Y-%m-%d")
    data_fim = datetime.strptime(fim, "%Y-%m-%d") + timedelta(days=1)
    return f"{data_inicio:%Y-%m-%d}T00:00:00Z", f"{data_fim:%Y-%m-%d}T03:00:00Z"


def sport_keys_the_odds_api():
    valor = os.getenv("THE_ODDS_API_SPORT_KEYS", "").strip()

    if valor:
        return [item.strip() for item in valor.split(",") if item.strip()]

    if os.getenv("THE_ODDS_API_ALL_SOCCER", "").strip().lower() in ("1", "s", "sim", "true", "yes"):
        try:
            resposta = requests.get(
                THE_ODDS_API_SPORTS_URL,
                params={"apiKey": the_odds_api_key(), "all": "false"},
                timeout=30,
            )
            resposta.raise_for_status()
            esportes = resposta.json()
        except requests.RequestException:
            return list(THE_ODDS_API_DEFAULT_SPORTS)

        chaves = [
            esporte["key"]
            for esporte in esportes
            if esporte.get("group") == "Soccer" and not esporte.get("has_outrights")
        ]
        depurar(f"esportes de futebol ativos: {len(chaves)}")
        return chaves or list(THE_ODDS_API_DEFAULT_SPORTS)

    return list(THE_ODDS_API_DEFAULT_SPORTS)


def buscar_odds_the_odds_api_por_sport(sport, inicio, fim):
    chave = the_odds_api_key()

    if not chave:
        return []

    params = {
        "apiKey": chave,
        "regions": os.getenv("THE_ODDS_API_REGIONS", "eu,uk"),
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    if inicio and fim:
        params["commenceTimeFrom"] = inicio
        params["commenceTimeTo"] = fim

    casas_aposta = os.getenv("THE_ODDS_API_BOOKMAKERS", "").strip()
    if casas_aposta:
        params.pop("regions", None)
        params["bookmakers"] = casas_aposta

    resposta = requests.get(
        THE_ODDS_API_ODDS_URL.format(sport=sport),
        params=params,
        timeout=30,
    )

    if resposta.status_code == 404:
        depurar(f"{sport}: esporte indisponivel")
        return []

    resposta.raise_for_status()
    eventos = resposta.json()
    depurar(f"{sport}: {len(eventos)} eventos")
    return eventos


def buscar_eventos_the_odds_api(jogos):
    inicio, fim = periodo_the_odds_api(jogos)
    eventos = []

    for sport in sport_keys_the_odds_api():
        try:
            eventos.extend(buscar_odds_the_odds_api_por_sport(sport, inicio, fim))
        except requests.RequestException as erro:
            depurar(f"{sport}: erro {erro}")

    return eventos


def odds_1x2_the_odds_api(evento):
    home = evento.get("home_team", "")
    away = evento.get("away_team", "")
    odds = {"Home": [], "Draw": [], "Away": []}

    for casa_aposta in evento.get("bookmakers", []):
        for market in casa_aposta.get("markets", []):
            if market.get("key") != "h2h":
                continue

            for outcome in market.get("outcomes", []):
                nome = outcome.get("name", "")

                if nome_base_time(nome) == nome_base_time(home):
                    coluna = "Home"
                elif nome_base_time(nome) == nome_base_time(away):
                    coluna = "Away"
                elif nome_base_time(nome) in ("DRAW", "TIE") or str(nome).strip().lower() in (
                    "draw",
                    "tie",
                    "empate",
                    "x",
                ):
                    coluna = "Draw"
                else:
                    continue

                try:
                    odds[coluna].append(float(outcome["price"]))
                except (KeyError, TypeError, ValueError):
                    continue

    if not all(odds.values()):
        return None

    return {nome: sum(valores) / len(valores) for nome, valores in odds.items()}


def completar_odds_the_odds_api(jogos):
    if not the_odds_api_key():
        return jogos

    eventos = buscar_eventos_the_odds_api(jogos)

    for jogo in jogos:
        evento, score, invertido, nome = encontrar_evento(jogo, eventos)

        if evento is None:
            jogo["odds_encontradas"] = False
            jogo["odds_status"] = "jogo nao encontrado"
            jogo["odds_match_score"] = score
            jogo["odds_melhor_candidato"] = nome
            continue

        odds = odds_1x2_the_odds_api(evento)

        if odds is None:
            jogo["odds_encontradas"] = False
            jogo["odds_status"] = "mercado h2h sem empate/odds"
            jogo["odds_match_score"] = score
            jogo["odds_melhor_candidato"] = nome
            continue

        if invertido:
            jogo["odd_mandante"] = odds["Away"]
            jogo["odd_empate"] = odds["Draw"]
            jogo["odd_visitante"] = odds["Home"]
        else:
            jogo["odd_mandante"] = odds["Home"]
            jogo["odd_empate"] = odds["Draw"]
            jogo["odd_visitante"] = odds["Away"]

        jogo["odds_encontradas"] = True
        jogo["odds_status"] = "ok"
        jogo["odds_match_score"] = score
        jogo["odds_melhor_candidato"] = nome

    return jogos


def imprimir_concurso(concurso):
    print("Concurso:", concurso.get("nuConcurso"))
    print("Data:", concurso.get("dataProximoConcurso"))

    for indice, jogo in enumerate(jogos_do_concurso(concurso), start=1):
        try:
            numero = f"{int(jogo['sequencial']):02d}"
        except (TypeError, ValueError):
            numero = str(indice).zfill(2)

        partes = [f"{numero} - {jogo['mandante']} x {jogo['visitante']} - {jogo['dia_semana']}"]

        if jogo.get("odd_mandante") and jogo.get("odd_empate") and jogo.get("odd_visitante"):
            partes.append(
                f"odds: {jogo['odd_mandante']:.2f} | {jogo['odd_empate']:.2f} | {jogo['odd_visitante']:.2f}"
            )

        print(" - ".join(partes))


def main():
    for concurso in buscar_programacao_loteca():
        jogos = jogos_do_concurso(concurso)

        if the_odds_api_key():
            completar_odds_the_odds_api(jogos)

        concurso = dict(concurso)
        concurso["listaJogos"] = jogos
        imprimir_concurso(concurso)


if __name__ == "__main__":
    main()
