"""Consulta resultados historicos das loterias numericas da Caixa."""

import json
from collections import Counter

import requests

from banco_lotogen import (
    intervalo_concursos_numericos,
    ler_frequencias,
    maior_concurso_numerico,
    resultados_numericos,
    salvar_frequencias,
    salvar_resultado_numerico,
    total_resultados_numericos,
)
from progresso import mostrar_progresso

CAIXA_API_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api"

SLUGS_CAIXA = {
    "mega-sena": "megasena",
    "lotofacil": "lotofacil",
    "quina": "quina",
    "lotomania": "lotomania",
    "timemania": "timemania",
    "dupla-sena": "duplasena",
    "dia-de-sorte": "diadesorte",
    "super-sete": "supersete",
    "mais-milionaria": "maismilionaria",
}


def slug_modalidade(modalidade):
    return SLUGS_CAIXA.get(modalidade)


def requisicao_caixa(caminho):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    resposta = requests.get(f"{CAIXA_API_BASE}/{caminho}", headers=headers, timeout=20)
    resposta.raise_for_status()
    return resposta.json()


def ultimo_concurso(modalidade):
    slug = slug_modalidade(modalidade)

    if not slug:
        raise ValueError("Modalidade sem consulta historica configurada.")

    dados = requisicao_caixa(slug)
    return numero_concurso(dados)


def resultado_concurso(modalidade, concurso):
    slug = slug_modalidade(modalidade)

    if not slug:
        raise ValueError("Modalidade sem consulta historica configurada.")

    return requisicao_caixa(f"{slug}/{concurso}")


def data_sorteio(dados):
    return dados.get("dataApuracao") or dados.get("dtApuracao") or dados.get("dataSorteio")


def numero_concurso(dados):
    for chave in ("nuConcurso", "numero", "numeroConcurso"):
        if chave in dados and dados[chave] is not None:
            return int(dados[chave])

    raise KeyError("numero do concurso")


def dezenas_resultado(dados):
    if isinstance(dados.get("listaDezenas"), list):
        return [str(dezena) for dezena in dados["listaDezenas"]]

    dezenas = []
    for chave, valor in dados.items():
        if "dezena" not in chave.lower():
            continue

        if isinstance(valor, list):
            dezenas.extend(str(dezena) for dezena in valor)

    return dezenas


def normaliza_dezena(dezena, zero_final=False):
    numero = int(str(dezena))

    if zero_final and numero == 0:
        numero = 100

    return numero


def concursos_para_consulta(ultimo, quantidade):
    if quantidade <= 0 or quantidade > ultimo:
        quantidade = ultimo

    primeiro = ultimo - quantidade + 1
    return range(primeiro, ultimo + 1)


def frequencias_historicas(modalidade, quantidade_concursos=200, zero_final=False):
    sincronizar_historico(modalidade)
    inicio_banco, fim_banco = intervalo_concursos_numericos(modalidade)

    if fim_banco is None:
        raise RuntimeError("Nao ha historico local para esta modalidade.")

    if quantidade_concursos and quantidade_concursos > 0:
        concurso_inicial = max(inicio_banco, fim_banco - quantidade_concursos + 1)
    else:
        concurso_inicial = inicio_banco

    dezenas_cache, extras_cache = ler_frequencias(modalidade, concurso_inicial, fim_banco)

    if dezenas_cache:
        return (
            Counter({int(item): frequencia for item, frequencia in dezenas_cache.items()}),
            Counter(extras_cache),
            fim_banco - concurso_inicial + 1,
        )

    frequencias = Counter()
    frequencias_extra = Counter()
    consultados = 0

    for linha in resultados_numericos(modalidade, concurso_inicial):
        dezenas = json.loads(linha["dezenas_json"])

        for dezena in dezenas:
            try:
                frequencias[normaliza_dezena(dezena, zero_final)] += 1
            except ValueError:
                continue

        extra = linha["extra"]

        if extra:
            frequencias_extra[normaliza_extra(extra)] += 1

        consultados += 1

    if not frequencias:
        raise RuntimeError("Nao encontrei dezenas no historico consultado.")

    salvar_frequencias(modalidade, frequencias, frequencias_extra, concurso_inicial, fim_banco)
    return frequencias, frequencias_extra, consultados


def sincronizar_historico(modalidade):
    ultimo_local = maior_concurso_numerico(modalidade)

    try:
        ultimo_remoto = ultimo_concurso(modalidade)
    except (requests.RequestException, KeyError, ValueError) as erro:
        if ultimo_local is None:
            raise RuntimeError(f"Nao consegui consultar a Caixa e nao ha historico local: {erro}")

        print(f"Nao consegui verificar novos concursos na Caixa. Usando historico local ate {ultimo_local}.")
        return

    inicio = 1 if ultimo_local is None else ultimo_local + 1

    if inicio > ultimo_remoto:
        return

    print(f"Atualizando historico de {modalidade}: concursos {inicio} a {ultimo_remoto}.")
    total = ultimo_remoto - inicio + 1

    for posicao, concurso in enumerate(range(inicio, ultimo_remoto + 1), start=1):
        try:
            dados = resultado_concurso(modalidade, concurso)
        except requests.RequestException:
            mostrar_progresso(posicao, total, prefixo="Historico")
            continue

        dezenas = dezenas_resultado(dados)

        if not dezenas:
            mostrar_progresso(posicao, total, prefixo="Historico")
            continue

        salvar_resultado_numerico(
            modalidade,
            numero_concurso(dados),
            dezenas,
            data_sorteio=data_sorteio(dados),
            extra=extra_resultado(dados),
        )
        mostrar_progresso(posicao, total, prefixo="Historico")


def cobertura_historico(modalidade):
    total_local = total_resultados_numericos(modalidade)
    ultimo_local = maior_concurso_numerico(modalidade)

    try:
        ultimo_remoto = ultimo_concurso(modalidade)
    except (requests.RequestException, KeyError, ValueError) as erro:
        return {
            "modalidade": modalidade,
            "total_local": total_local,
            "ultimo_local": ultimo_local,
            "ultimo_remoto": None,
            "percentual": None,
            "erro": erro,
        }

    percentual = total_local / ultimo_remoto if ultimo_remoto else 0
    return {
        "modalidade": modalidade,
        "total_local": total_local,
        "ultimo_local": ultimo_local,
        "ultimo_remoto": ultimo_remoto,
        "percentual": percentual,
        "erro": None,
    }


def extra_resultado(dados):
    return dados.get("nomeTimeCoracaoMesSorte")


def normaliza_extra(valor):
    return " ".join(str(valor).strip().split())


def ranking_dezenas_por_frequencia(
    modalidade,
    estrategia,
    inicio,
    fim,
    quantidade_concursos=200,
    zero_final=False,
):
    frequencias, frequencias_extra, consultados = frequencias_historicas(
        modalidade,
        quantidade_concursos=quantidade_concursos,
        zero_final=zero_final,
    )
    universo = range(inicio, fim + 1)
    reverso = estrategia == "mais"
    ordenadas = sorted(
        universo,
        key=lambda numero: (frequencias.get(numero, 0), -numero if reverso else numero),
        reverse=reverso,
    )
    return ordenadas, ranking_extra_por_frequencia(frequencias_extra, estrategia), consultados


def ranking_extra_por_frequencia(frequencias, estrategia):
    reverso = estrategia == "mais"
    return [
        extra
        for extra, _frequencia in sorted(
            frequencias.items(),
            key=lambda item: (item[1], item[0]),
            reverse=reverso,
        )
    ]


def dezenas_por_frequencia(
    modalidade,
    quantidade,
    estrategia,
    inicio,
    fim,
    quantidade_concursos=200,
    zero_final=False,
):
    ordenadas, _extras, consultados = ranking_dezenas_por_frequencia(
        modalidade,
        estrategia,
        inicio,
        fim,
        quantidade_concursos=quantidade_concursos,
        zero_final=zero_final,
    )
    return sorted(ordenadas[:quantidade]), consultados
