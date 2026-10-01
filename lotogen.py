"""Gerador de bilhetes e manutenção dos bancos locais do Lotogen."""

import argparse
import csv
import os
import zipfile
from math import isfinite
from xml.etree import ElementTree
from random import sample
from unicodedata import normalize

from algoritmo_loteca import (
    COLUNAS_LOTECA,
    capacidade_bilhetes_loteca,
    combinacao_loteca_por_variante,
    distribuir_multiplos_loteca,
    equilibrio_loteca,
    gera_bilhete_loteca,
    opcoes_colunas_loteca,
    probabilidades_por_odds,
    ranking_colunas_loteca,
)
from banco_lotogen import (
    concursos_loteca,
    intervalo_concursos_numericos,
    jogos_loteca,
    total_resultados_numericos,
)
from consulta_loteca import buscar_programacao_loteca, numero_concurso as numero_concurso_loteca
from historico_loterias import (
    cobertura_historico,
    ranking_dezenas_por_frequencia,
    ranking_super_sete_por_frequencia,
    sincronizar_historico,
)


lista_times = [
    "ABC/RN",
    "Altos/PI",
    "Amazonas/AM",
    "America/MG",
    "America/RN",
    "Aparecidense/GO",
    "Athletic Club/MG",
    "Athletico/PR",
    "Atletico/GO",
    "Atletico Mineiro/MG",
    "Avai/SC",
    "Bahia/BA",
    "Bahia de Feira/BA",
    "Botafogo/PB",
    "Botafogo/RJ",
    "Botafogo/SP",
    "Bragantino/SP",
    "Brasil/RS",
    "Brasiliense/DF",
    "Brusque/SC",
    "Campinense/PB",
    "Cascavel/PR",
    "Caxias/RS",
    "Ceara/CE",
    "Ceilandia/DF",
    "Chapecoense/SC",
    "Confianca/SE",
    "Corinthians/SP",
    "Coritiba/PR",
    "CRB/AL",
    "Criciuma/SC",
    "Cruzeiro/MG",
    "CSA/AL",
    "Cuiaba/MT",
    "Ferroviaria/SP",
    "Ferroviario/CE",
    "Figueirense/SC",
    "Flamengo/RJ",
    "Floresta/CE",
    "Fluminense/RJ",
    "Fortaleza/CE",
    "Goias/GO",
    "Gremio/RS",
    "Guarani/SP",
    "Internacional/RS",
    "Ituano/SP",
    "Jacuipense/BA",
    "Juazeirense/BA",
    "Juventude/RS",
    "Londrina/PR",
    "Manaus/AM",
    "Mirassol/SP",
    "Nautico/PE",
    "Nova Iguacu/RJ",
    "Novorizontino/SP",
    "Oeste/SP",
    "Operario/PR",
    "Palmeiras/SP",
    "Parana/PR",
    "Paysandu/PA",
    "Ponte Preta/SP",
    "Portuguesa/RJ",
    "Pouso Alegre/MG",
    "Remo/PA",
    "Retro/PE",
    "Sampaio Correa/MA",
    "Santa Cruz/PE",
    "Santos/SP",
    "Sao Bernardo/SP",
    "Sao Jose/RS",
    "Sao Paulo/SP",
    "Sao Raimundo/RR",
    "Sport/PE",
    "Tocantinopolis/TO",
    "Tombense/MG",
    "Vasco/RJ",
    "Vila Nova/GO",
    "Vitoria/BA",
    "Volta Redonda/RJ",
    "Ypiranga/RS",
]

lista_meses = [
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


MODALIDADES = {
    "mega-sena": {"min": 6, "max": 20, "inicio": 1, "fim": 60},
    "lotofacil": {"min": 15, "max": 20, "inicio": 1, "fim": 25},
    "quina": {"min": 5, "max": 15, "inicio": 1, "fim": 80},
    "lotomania": {"min": 50, "max": 50, "inicio": 1, "fim": 100, "zero_final": True},
    "timemania": {"min": 10, "max": 10, "inicio": 1, "fim": 80, "extra": lista_times},
    "dupla-sena": {"min": 6, "max": 15, "inicio": 1, "fim": 50},
    "dia-de-sorte": {"min": 7, "max": 15, "inicio": 1, "fim": 31, "extra": lista_meses},
    "super-sete": {"min": 7, "max": 21, "inicio": 0, "fim": 9},
    "mais-milionaria": {
        "min": 6,
        "max": 12,
        "inicio": 1,
        "fim": 50,
        "trevos": True,
        "trevos_min": 2,
        "trevos_max": 6,
    },
}

ALIASES = {
    "mega": "mega-sena",
    "mega sena": "mega-sena",
    "mega-sena": "mega-sena",
    "lotofacil": "lotofacil",
    "lotofácil": "lotofacil",
    "quina": "quina",
    "lotomania": "lotomania",
    "timemania": "timemania",
    "dupla": "dupla-sena",
    "dupla sena": "dupla-sena",
    "dupla-sena": "dupla-sena",
    "dia de sorte": "dia-de-sorte",
    "dia-de-sorte": "dia-de-sorte",
    "super sete": "super-sete",
    "super-sete": "super-sete",
    "+milionaria": "mais-milionaria",
    "+milionária": "mais-milionaria",
    "mais milionaria": "mais-milionaria",
    "mais milionária": "mais-milionaria",
    "mais-milionaria": "mais-milionaria",
    "loteca": "loteca",
}

def normaliza_nome(nome):
    """Remove diferenças simples de acento, maiúsculas e espaços duplicados."""
    texto = normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().strip().split())


def nome_modalidade(nome):
    chave = normaliza_nome(nome)
    modalidade = ALIASES.get(chave)

    if modalidade is None:
        opcoes = ", ".join(sorted(set(ALIASES.values())))
        raise ValueError(f"Modalidade inválida. Opções: {opcoes}")

    return modalidade


def valida_quantidade(quantidade, minimo, maximo):
    if quantidade is None:
        return minimo

    if not minimo <= quantidade <= maximo:
        raise ValueError(f"Quantidade deve ficar entre {minimo} e {maximo}.")

    return quantidade


def valor_decimal(valor):
    if isinstance(valor, (int, float)):
        return float(valor)

    return float(str(valor).strip().replace(",", "."))


def formata_numero(numero, zero_final=False):
    if zero_final and numero == 100:
        return "00"

    return f"{numero:02d}"


def gera_num(quantidade, inicio, fim, zero_final=False):
    numeros = sorted(sample(range(inicio, fim + 1), quantidade))
    return [formata_numero(numero, zero_final) for numero in numeros]


def escolhe_nome(nomes):
    return sample(nomes, 1)[0]


def chave_extra_atual(nome):
    return normaliza_nome(str(nome).replace(" /", "/").replace("/ ", "/"))


def filtra_ranking_extra_atual(ranking_extra, opcoes_atuais):
    atuais_por_chave = {
        chave_extra_atual(opcao): opcao
        for opcao in opcoes_atuais
    }
    vistos = set()
    filtrados = []

    for extra in ranking_extra:
        chave = chave_extra_atual(extra)

        if chave in atuais_por_chave and chave not in vistos:
            filtrados.append(atuais_por_chave[chave])
            vistos.add(chave)

    return filtrados


def gera_bilhete_comum(modalidade, quantidade=None):
    regra = MODALIDADES[modalidade]
    quantidade = valida_quantidade(quantidade, regra["min"], regra["max"])
    numeros = gera_num(
        quantidade,
        regra["inicio"],
        regra["fim"],
        zero_final=regra.get("zero_final", False),
    )

    if "extra" in regra:
        numeros.append(f"{{{escolhe_nome(regra['extra'])}}}")

    return numeros


def gera_bilhete_historico(modalidade, quantidade, estrategia, concursos=0):
    bilhetes, consultados = gera_bilhetes_historicos(
        modalidade,
        quantidade,
        estrategia,
        total=1,
        concursos=concursos,
    )
    return bilhetes[0], consultados


def gera_bilhetes_historicos(
    modalidade,
    quantidade,
    estrategia,
    total,
    concursos=0,
    atualizar_historico=True,
):
    regra = MODALIDADES[modalidade]
    quantidade_trevos = regra.get("trevos_min", 0)

    if modalidade == "mais-milionaria" and isinstance(quantidade, dict):
        quantidade_trevos = quantidade.get("trevos", quantidade_trevos)
        quantidade = quantidade.get("numeros")

    quantidade = valida_quantidade(quantidade, regra["min"], regra["max"])

    if modalidade == "super-sete":
        rankings, consultados = ranking_super_sete_por_frequencia(
            estrategia,
            concursos,
            atualizar=atualizar_historico,
        )
        bilhetes = []

        for indice in range(total):
            colunas = []

            for ranking, cota in zip(rankings, cotas_super_sete(quantidade)):
                inicio = (indice * cota) % len(ranking)
                numeros = [
                    ranking[(inicio + posicao) % len(ranking)]
                    for posicao in range(cota)
                ]
                colunas.append([str(numero) for numero in sorted(numeros)])

            bilhetes.append(colunas)

        return bilhetes, consultados

    ranking, ranking_extra, consultados = ranking_dezenas_por_frequencia(
        modalidade,
        estrategia,
        regra["inicio"],
        regra["fim"],
        quantidade_concursos=concursos,
        zero_final=regra.get("zero_final", False),
        atualizar=atualizar_historico,
    )
    bilhetes = []
    if "extra" in regra:
        ranking_extra_atual = filtra_ranking_extra_atual(ranking_extra, regra["extra"])
    else:
        ranking_extra_atual = []

    for indice in range(total):
        inicio = (indice * quantidade) % len(ranking)
        numeros = [ranking[(inicio + posicao) % len(ranking)] for posicao in range(quantidade)]
        bilhete = [formata_numero(numero, regra.get("zero_final", False)) for numero in sorted(numeros)]

        if "extra" in regra:
            if ranking_extra_atual:
                extra = ranking_extra_atual[indice % len(ranking_extra_atual)]
            else:
                extra = escolhe_nome(regra["extra"])

            bilhete.append(f"{{{extra}}}")

        if regra.get("trevos"):
            quantidade_trevos = valida_quantidade(
                quantidade_trevos,
                regra["trevos_min"],
                regra["trevos_max"],
            )
            if len(ranking_extra) >= quantidade_trevos:
                trevos = [
                    ranking_extra[(indice + posicao) % len(ranking_extra)]
                    for posicao in range(quantidade_trevos)
                ]
            else:
                trevos = sorted(sample(range(1, 7), quantidade_trevos))

            bilhete.extend(f"{{{trevo}}}" for trevo in sorted(trevos, key=int))

        bilhetes.append(bilhete)

    return bilhetes, consultados


def cotas_super_sete(quantidade):
    quantidade = valida_quantidade(quantidade, 7, 21)

    if quantidade <= 14:
        cotas = [1] * 7
        extras = quantidade - 7
    else:
        cotas = [2] * 7
        extras = quantidade - 14

    for coluna in sample(range(7), extras):
        cotas[coluna] += 1

    return cotas


def gera_super_sete(quantidade=None):
    colunas = []

    for cota in cotas_super_sete(quantidade):
        numeros = sorted(sample(range(10), cota))
        colunas.append([str(numero) for numero in numeros])

    return colunas


def gera_mais_milionaria(quantidade_numeros=6, quantidade_trevos=2):
    regra = MODALIDADES["mais-milionaria"]
    quantidade_numeros = valida_quantidade(quantidade_numeros, regra["min"], regra["max"])
    quantidade_trevos = valida_quantidade(
        quantidade_trevos,
        regra["trevos_min"],
        regra["trevos_max"],
    )
    numeros = gera_num(quantidade_numeros, regra["inicio"], regra["fim"])
    trevos = [
        f"{{{trevo}}}"
        for trevo in sorted(sample(range(1, 7), quantidade_trevos))
    ]
    return numeros + trevos


def gera_bilhete(modalidade, quantidade=None):
    modalidade = nome_modalidade(modalidade)

    if modalidade == "super-sete":
        return gera_super_sete(quantidade)

    if modalidade == "mais-milionaria":
        if isinstance(quantidade, dict):
            return gera_mais_milionaria(
                quantidade.get("numeros", 6),
                quantidade.get("trevos", 2),
            )
        return gera_mais_milionaria(quantidade or 6)

    return gera_bilhete_comum(modalidade, quantidade)


def formata_bilhete(bilhete):
    if bilhete and isinstance(bilhete[0], dict):
        ordem = {coluna: indice for indice, coluna in enumerate(COLUNAS_LOTECA)}
        jogos = []

        for indice, jogo in enumerate(bilhete, start=1):
            colunas = "/".join(sorted(jogo["colunas"], key=ordem.get))
            mandante = jogo.get("mandante")
            visitante = jogo.get("visitante")

            if mandante and visitante:
                jogos.append(f"{indice:02d}: {mandante} x {visitante} -> {colunas}")
            else:
                jogos.append(f"{indice:02d}: {colunas}")

        return "\n" + "\n".join(jogos)

    if bilhete and isinstance(bilhete[0], list):
        if len(bilhete) == 14 and all(set(coluna) <= set(COLUNAS_LOTECA) for coluna in bilhete):
            ordem = {coluna: indice for indice, coluna in enumerate(COLUNAS_LOTECA)}
            jogos = [
                f"{indice:02d}: {'/'.join(sorted(coluna, key=ordem.get))}"
                for indice, coluna in enumerate(bilhete, start=1)
            ]
            return " | ".join(jogos)

        colunas = ["|" + ", ".join(coluna) + "|" for coluna in bilhete]
        return "[" + " ".join(colunas) + "]"

    return "[" + " ".join(bilhete) + "]"


def valores_favorito(modalidade, bilhete):
    modalidade = nome_modalidade(modalidade)

    if modalidade == "loteca":
        return [
            {
                "colunas": jogo.get("colunas", []),
                "mandante": jogo.get("mandante"),
                "visitante": jogo.get("visitante"),
            }
            for jogo in bilhete
        ]

    if modalidade == "super-sete":
        return bilhete

    if modalidade == "mais-milionaria":
        dezenas = [valor for valor in bilhete if not str(valor).startswith("{")]
        trevos = [str(valor).strip("{}") for valor in bilhete if str(valor).startswith("{")]
        return {"dezenas": dezenas, "extra": trevos}

    regra = MODALIDADES[modalidade]
    dezenas = [str(valor) for valor in bilhete if not str(valor).startswith("{")]
    extras = [str(valor).strip("{}") for valor in bilhete if str(valor).startswith("{")]
    return {
        "dezenas": dezenas,
        "extra": " ".join(extras) if extras and "extra" in regra else None,
    }


def seleciona_bilhetes_para_salvar(bilhetes):
    opcoes = []

    for indice, (modalidade, numero, bilhete) in enumerate(bilhetes, start=1):
        if valores_favorito(modalidade, bilhete) is not None:
            opcoes.append((indice, modalidade, numero, bilhete))

    if not opcoes:
        print("Nenhum bilhete gerado pode ser salvo nos favoritos por enquanto.")
        return []

    while True:
        resposta = normaliza_nome(
            input("Qual bilhete deseja salvar? [números, todos ou ENTER para nenhum] ")
        )

        if not resposta:
            return []

        if resposta in ("todos", "t"):
            return opcoes

        selecionados = []
        partes = resposta.replace(",", " ").split()

        try:
            indices = [int(parte) for parte in partes]
        except ValueError:
            print("Informe números separados por espaço, todos ou ENTER.")
            continue

        invalidos = [indice for indice in indices if not 1 <= indice <= len(bilhetes)]

        if invalidos:
            print(f"Bilhete inválido: {invalidos[0]}.")
            continue

        indices_opcoes = {indice for indice, _modalidade, _numero, _bilhete in opcoes}
        nao_suportados = [indice for indice in indices if indice not in indices_opcoes]

        if nao_suportados:
            print(f"Bilhete {nao_suportados[0]} ainda não pode ser salvo nos favoritos.")
            continue

        vistos = set()
        for opcao in opcoes:
            indice = opcao[0]

            if indice in indices and indice not in vistos:
                selecionados.append(opcao)
                vistos.add(indice)

        return selecionados


def salvar_bilhetes_favoritos(bilhetes):
    from favoritos import cria_favorito

    if not bilhetes:
        return

    if not le_sim_nao("Deseja salvar algum bilhete nos favoritos? [S/N ou 1/0] "):
        return

    for _indice, modalidade, numero, bilhete in seleciona_bilhetes_para_salvar(bilhetes):
        valores = valores_favorito(modalidade, bilhete)

        nome = input(f"Nome opcional para {modalidade} #{numero}: ").strip() or None

        try:
            favorito_id, _modalidade, _dezenas, _extra = cria_favorito(
                modalidade,
                valores,
                nome=nome,
            )
        except ValueError as erro:
            print(f"Não consegui salvar favorito: {erro}")
        else:
            print(f"Favorito {favorito_id} salvo.")


def le_inteiro(mensagem, minimo=1, maximo=None, padrao=None):
    while True:
        resposta = input(mensagem).strip()

        if resposta == "" and padrao is not None:
            return padrao

        try:
            valor = int(resposta)
        except ValueError:
            print("Informe um número inteiro.")
            continue

        if valor < minimo:
            print(f"Informe um número maior ou igual a {minimo}.")
            continue

        if maximo is not None and valor > maximo:
            print(f"Informe um número menor ou igual a {maximo}.")
            continue

        return valor


def le_sim_nao(mensagem):
    while True:
        resposta = normaliza_nome(input(mensagem))

        if resposta in ("1", "s", "sim"):
            return True

        if resposta in ("0", "n", "nao"):
            return False

        print("Responda com S/1 ou N/0.")


def le_modo_loteca():
    while True:
        resposta = normaliza_nome(input("Decidir bilhete com razão ou emoção? [0=razão/1=emoção] "))

        if resposta in ("0", "r", "razao"):
            return "razao"

        if resposta in ("1", "e", "emocao"):
            return "emocao"

        print("Informe 0/razão ou 1/emoção.")


def le_estrategia_numerica():
    while True:
        resposta = normaliza_nome(
            input("Gerar como? [0=aleatório/1=mais sorteados/2=menos sorteados] ")
        )

        if resposta in ("", "0", "a", "aleatorio"):
            return "aleatorio"

        if resposta in ("1", "mais", "mais sorteados"):
            return "mais"

        if resposta in ("2", "menos", "menos sorteados"):
            return "menos"

        print("Informe 0, 1 ou 2.")


def le_quantidade_concursos():
    return le_inteiro("Consultar quantos concursos históricos? [Informe um número ou ENTER para todos] ", 0, padrao=0)


def opcoes_modalidades():
    return [
        "loteca",
        "mega-sena",
        "timemania",
        "lotofacil",
        "quina",
        "lotomania",
        "dupla-sena",
        "dia-de-sorte",
        "super-sete",
        "+milionaria",
    ]


def le_modalidades(opcoes):
    while True:
        resposta = normaliza_nome(input("Jogos desejados: "))
        partes = resposta.replace(",", " ").replace(" e ", " ").split()
        escolhidos = []

        for parte in partes:
            try:
                indice = int(parte)
            except ValueError:
                print("Informe os números dos jogos, por exemplo: 1 e 2")
                break

            if not 0 <= indice < len(opcoes):
                print(f"Opção inválida: {indice}.")
                break

            modalidade = opcoes[indice]
            if modalidade not in escolhidos:
                escolhidos.append(modalidade)
        else:
            if escolhidos:
                return escolhidos

        print("Tente novamente.")


def quantidade_aposta(modalidade):
    modalidade = nome_modalidade(modalidade)
    regra = MODALIDADES.get(modalidade)

    if regra is None:
        return None

    if modalidade == "mais-milionaria":
        multipla = le_sim_nao("Quer aposta múltipla? [S/N ou 1/0] ")
        if not multipla:
            return None

        numeros = le_inteiro(
            f"Quantos números por bilhete ({regra['min']} a {regra['max']})? ",
            regra["min"],
            regra["max"],
        )
        trevos = le_inteiro(
            f"Quantos trevos por bilhete ({regra['trevos_min']} a {regra['trevos_max']})? ",
            regra["trevos_min"],
            regra["trevos_max"],
        )
        return {"numeros": numeros, "trevos": trevos}

    if regra["min"] == regra["max"]:
        return None

    multipla = le_sim_nao("Quer aposta múltipla? [S/N ou 1/0] ")

    if not multipla:
        return None

    minimo = regra["min"]
    maximo = regra["max"]
    return le_inteiro(f"Quantos números por bilhete ({minimo} a {maximo})? ", minimo, maximo)


def jogo_loteca_da_linha(linha, numero):
    try:
        odds = [valor_decimal(linha[indice]) for indice in range(3)]
    except (IndexError, TypeError, ValueError):
        raise ValueError(f"Linha {numero}: informe odds válidas nas colunas A, B e C.")

    if any(not isfinite(odd) or odd <= 1 for odd in odds):
        raise ValueError(f"Linha {numero}: as odds precisam ser finitas e maiores que 1.")

    mandante = str(linha[3]).strip() if len(linha) > 3 and linha[3] not in (None, "") else None
    visitante = str(linha[4]).strip() if len(linha) > 4 and linha[4] not in (None, "") else None

    return {"odds": odds, "mandante": mandante, "visitante": visitante}


def le_loteca_csv(caminho):
    jogos = []

    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        amostra = arquivo.read(2048)
        arquivo.seek(0)
        amostra_dados = "\n".join(
            linha for linha in amostra.splitlines() if not linha.lstrip().startswith("#")
        )

        try:
            dialeto = csv.Sniffer().sniff(amostra_dados, delimiters=";\t,")
        except csv.Error:
            leitor = csv.reader(arquivo, delimiter=";")
        else:
            leitor = csv.reader(arquivo, dialeto)

        linhas = [
            linha
            for linha in leitor
            if linha and not str(linha[0]).lstrip().startswith("#")
        ]

    for indice, linha in enumerate(linhas[1:15], start=2):
        jogos.append(jogo_loteca_da_linha(linha, indice))

    return jogos


def coluna_referencia_xlsx(referencia):
    return "".join(caractere for caractere in referencia if caractere.isalpha())


def indice_coluna_xlsx(coluna):
    indice = 0

    for caractere in coluna:
        indice = indice * 26 + ord(caractere.upper()) - ord("A") + 1

    return indice - 1


def textos_compartilhados_xlsx(arquivo):
    try:
        conteudo = arquivo.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    raiz = ElementTree.fromstring(conteudo)
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    textos = []

    for item in raiz.findall("x:si", ns):
        partes = [texto.text or "" for texto in item.findall(".//x:t", ns)]
        textos.append("".join(partes))

    return textos


def valor_celula_xlsx(celula, textos):
    tipo = celula.attrib.get("t")
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    if tipo == "inlineStr":
        partes = [texto.text or "" for texto in celula.findall(".//x:t", ns)]
        return "".join(partes)

    valor = celula.find("x:v", ns)

    if valor is None or valor.text is None:
        return ""

    if tipo == "s":
        return textos[int(valor.text)]

    return valor.text


def le_loteca_xlsx(caminho):
    jogos = []
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    with zipfile.ZipFile(caminho) as arquivo:
        textos = textos_compartilhados_xlsx(arquivo)
        planilha = ElementTree.fromstring(arquivo.read("xl/worksheets/sheet1.xml"))

        linhas = {}
        for linha in planilha.findall(".//x:row", ns):
            numero = int(linha.attrib["r"])

            if not 2 <= numero <= 15:
                continue

            valores = [""] * 5

            for celula in linha.findall("x:c", ns):
                coluna = coluna_referencia_xlsx(celula.attrib["r"])
                indice = indice_coluna_xlsx(coluna)

                if 0 <= indice < 5:
                    valores[indice] = valor_celula_xlsx(celula, textos)

            linhas[numero] = valores

    for numero in range(2, 16):
        jogos.append(jogo_loteca_da_linha(linhas.get(numero, []), numero))

    return jogos


def texto_celula_ods(celula):
    ns = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    }

    valor = (
        celula.attrib.get(f"{{{ns['office']}}}value")
        or celula.attrib.get(f"{{{ns['office']}}}string-value")
    )

    if valor is not None:
        return valor

    partes = [
        "".join(paragrafo.itertext())
        for paragrafo in celula.findall("text:p", ns)
    ]
    return "\n".join(parte for parte in partes if parte)


def repeticoes_ods(elemento, atributo):
    try:
        return int(elemento.attrib.get(atributo, "1"))
    except ValueError:
        return 1


def valores_linha_ods(linha, limite_colunas=5):
    ns_table = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    valores = []

    for celula in linha:
        celula_normal = celula.tag == f"{{{ns_table}}}table-cell"
        celula_coberta = celula.tag == f"{{{ns_table}}}covered-table-cell"

        if not (celula_normal or celula_coberta):
            continue

        repeticoes = repeticoes_ods(celula, f"{{{ns_table}}}number-columns-repeated")
        valor = texto_celula_ods(celula) if celula_normal else ""

        for _indice in range(repeticoes):
            if len(valores) >= limite_colunas:
                return valores

            valores.append(valor)

    return valores


def le_loteca_ods(caminho):
    jogos = []
    ns = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    }
    linhas_por_numero = {}

    with zipfile.ZipFile(caminho) as arquivo:
        conteudo = ElementTree.fromstring(arquivo.read("content.xml"))
        planilha = conteudo.find(".//table:table", ns)

        if planilha is None:
            raise ValueError("Planilha ODS sem tabela.")

        numero_linha = 1

        for linha in planilha.findall("table:table-row", ns):
            repeticoes = repeticoes_ods(
                linha,
                f"{{{ns['table']}}}number-rows-repeated",
            )
            valores = valores_linha_ods(linha)

            for _indice in range(repeticoes):
                if 2 <= numero_linha <= 15:
                    linhas_por_numero[numero_linha] = valores

                numero_linha += 1

                if numero_linha > 15:
                    break

            if numero_linha > 15:
                break

    for numero in range(2, 16):
        jogos.append(jogo_loteca_da_linha(linhas_por_numero.get(numero, []), numero))

    return jogos


def le_planilha_loteca(caminho):
    extensao = os.path.splitext(caminho)[1].lower()

    if extensao == ".csv":
        return le_loteca_csv(caminho)

    if extensao == ".xlsx":
        return le_loteca_xlsx(caminho)

    if extensao == ".ods":
        return le_loteca_ods(caminho)

    raise ValueError("Use uma planilha .csv, .xlsx ou .ods.")


def solicita_planilha_loteca():
    while True:
        caminho = input("Caminho da planilha da Loteca (.csv, .xlsx ou .ods): ").strip().strip('"')

        if not caminho:
            print("Informe o caminho da planilha.")
            continue

        if not os.path.isabs(caminho):
            caminho = os.path.abspath(caminho)

        if not os.path.exists(caminho):
            print("Arquivo não encontrado.")
            continue

        try:
            jogos = le_planilha_loteca(caminho)
        except (ValueError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as erro:
            print(f"Não consegui ler a planilha: {erro}")
            continue

        if len(jogos) != 14:
            print("A planilha precisa ter 14 jogos nas linhas 2 a 15.")
            continue

        return jogos


def loteca_local_pronta(concurso):
    jogos = jogos_loteca(concurso)

    if len(jogos) != 14:
        return False

    try:
        for jogo in jogos:
            probabilidades_por_odds(jogo["odds"])
    except (KeyError, TypeError, ValueError):
        return False

    return True


def escolhe_concurso_loteca_local(preferidos=None):
    concursos = [
        item
        for item in concursos_loteca()
        if (preferidos is None or item["concurso"] in preferidos)
        and loteca_local_pronta(item["concurso"])
    ]

    if not concursos:
        return None, []

    if len(concursos) == 1:
        concurso = concursos[0]["concurso"]
        return concurso, jogos_loteca(concurso)

    print("Concursos da Loteca salvos no banco local:")

    for indice, item in enumerate(concursos, start=1):
        data = item["data_proximo_concurso"] or "sem data"
        print(f"{indice}. concurso {item['concurso']} - {data}")

    while True:
        resposta = input("Qual concurso deseja usar? [ENTER para o mais recente] ").strip()

        if not resposta:
            concurso = concursos[0]["concurso"]
            return concurso, jogos_loteca(concurso)

        try:
            indice = int(resposta)
        except ValueError:
            print("Informe o número da opção.")
            continue

        if 1 <= indice <= len(concursos):
            concurso = concursos[indice - 1]["concurso"]
            return concurso, jogos_loteca(concurso)

        print("Opção inválida.")


def configura_loteca(concursos_preferidos=None):
    print()
    caminho_padrao = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loteca_atual.csv")
    concurso, jogos = escolhe_concurso_loteca_local(concursos_preferidos)

    if not jogos and concursos_preferidos:
        concursos_anteriores = [
            item["concurso"]
            for item in concursos_loteca()
            if item["concurso"] not in concursos_preferidos
            and loteca_local_pronta(item["concurso"])
        ]
        print("Nenhum concurso atual da Caixa está pronto no banco local.")

        if concursos_anteriores and le_sim_nao(
            "Deseja usar explicitamente um concurso local anterior? [S/N ou 1/0] "
        ):
            concurso, jogos = escolhe_concurso_loteca_local(concursos_anteriores)

    if jogos:
        print(f"Usando Loteca salva no banco local: concurso {concurso}.")
    elif os.path.exists(caminho_padrao):
        from gera_loteca import concurso_csv

        concurso_arquivo = concurso_csv(caminho_padrao)
        descricao_arquivo = (
            f"concurso {concurso_arquivo}" if concurso_arquivo else "concurso não identificado"
        )
        print(f"Arquivo alternativo disponível: loteca_atual.csv ({descricao_arquivo}).")
        usar_csv = le_sim_nao(
            "Deseja usar o loteca_atual.csv como fonte alternativa? [S/N ou 1/0] "
        )
        if usar_csv:
            print("Usando arquivo loteca_atual.csv encontrado na pasta do programa.")
            jogos = le_planilha_loteca(caminho_padrao)
        else:
            jogos = solicita_planilha_loteca()
    else:
        print("Arquivo loteca_atual.csv não encontrado na pasta do programa.")
        print("A planilha da Loteca deve ter:")
        print("A: odd mandante | B: odd empate | C: odd visitante | D/E: times opcionais")
        print("Use as linhas 2 a 15 para os 14 jogos.")
        jogos = solicita_planilha_loteca()

    duplos = le_inteiro("Quantos duplos por bilhete? [1] ", 0, 14, padrao=1)
    triplos = le_inteiro("Quantos triplos por bilhete? [0] ", 0, 14 - duplos, padrao=0)
    modo = le_modo_loteca()
    return {"jogos": jogos, "duplos": duplos, "triplos": triplos, "modo": modo}


def imprime_menu(opcoes):
    print("LOTOGEN - gerador de bilhetes para as Loterias da Caixa")
    print("Informe para quais jogos deseja gerar bilhetes")
    print("Separe múltiplas opções com espaço. Exemplo: X Y Z")
    print()

    indices = list(range(1, len(opcoes))) + [0]

    for indice in indices:
        modalidade = opcoes[indice]
        print(f"{indice}. {modalidade}")

    print()


def formata_percentual_cobertura(percentual):
    if percentual >= 1:
        return "100%"

    return f"{percentual:.2%}"


def banco_historico_defasado(cobertura, limite):
    percentual = cobertura["percentual"]
    ultimo_local = cobertura["ultimo_local"] or 0
    ultimo_remoto = cobertura["ultimo_remoto"] or 0
    total_local = cobertura["total_local"]

    if percentual is None:
        return total_local == 0

    return (
        percentual < limite
        or total_local < ultimo_remoto
        or ultimo_local < ultimo_remoto
    )


def checa_bancos_historicos(escolhidos):
    modalidades = [
        nome_modalidade(modalidade)
        for modalidade in escolhidos
        if nome_modalidade(modalidade) in MODALIDADES
    ]

    limite = float(os.getenv("LOTOGEN_COBERTURA_MINIMA", "0.75"))
    defasados = []
    loteca_defasada = False
    faltantes_loteca = []
    concursos_remotos = None
    concursos_remotos_por_numero = {}

    print("Verificando bancos locais...")

    for modalidade in modalidades:
        cobertura = cobertura_historico(modalidade)
        percentual = cobertura["percentual"]
        ultimo_local = cobertura["ultimo_local"] or 0

        if percentual is None:
            texto = f"{cobertura['total_local']} concursos locais; não consegui comparar com a Caixa"
            if cobertura["total_local"] == 0:
                defasados.append((modalidade, cobertura))
        else:
            faltantes = max(0, cobertura["ultimo_remoto"] - cobertura["total_local"])
            detalhe_faltantes = f"; faltam {faltantes}" if faltantes else ""
            texto = (
                f"{cobertura['total_local']} de {cobertura['ultimo_remoto']} concursos "
                f"({formata_percentual_cobertura(percentual)}); ultimo local: {ultimo_local}"
                f"{detalhe_faltantes}"
            )

            if banco_historico_defasado(cobertura, limite):
                defasados.append((modalidade, cobertura))

        print(f"- {modalidade}: {texto}")

    if "loteca" in escolhidos:
        todos_concursos_locais = {item["concurso"] for item in concursos_loteca()}
        concursos_locais = {
            concurso for concurso in todos_concursos_locais if loteca_local_pronta(concurso)
        }
        concursos_invalidos = todos_concursos_locais - concursos_locais

        try:
            programacoes = buscar_programacao_loteca()
        except Exception as erro:
            estado_local = (
                f"{len(concursos_locais)} concurso(s) válido(s)"
                if concursos_locais
                else "nenhum concurso válido"
            )
            print(f"- loteca: concursos atuais desconhecidos; local: {estado_local} ({erro})")
        else:
            concursos_remotos_por_numero = {
                numero: concurso
                for concurso in programacoes
                if (numero := numero_concurso_loteca(concurso)) is not None
            }
            concursos_remotos = list(concursos_remotos_por_numero)
            if not concursos_remotos:
                print("- loteca: a Caixa não informou concursos atuais.")
                concursos_remotos = None
                return concursos_remotos

            concursos_atuais_locais = concursos_locais & set(concursos_remotos)
            concursos_invalidos_atuais = concursos_invalidos & set(concursos_remotos)
            faltantes_loteca = [
                numero for numero in concursos_remotos if numero not in concursos_atuais_locais
            ]
            lista_remotos = ", ".join(str(numero) for numero in concursos_remotos) or "nenhum"
            lista_locais = (
                ", ".join(str(numero) for numero in sorted(concursos_atuais_locais, reverse=True))
                or "nenhum"
            )
            estado_local = (
                "presente"
                if not faltantes_loteca
                else f"faltando {', '.join(str(numero) for numero in faltantes_loteca)}"
            )
            print(
                f"- loteca: concursos atuais {lista_remotos}; "
                f"atuais prontos no banco: {lista_locais}; {estado_local}"
            )

            if not faltantes_loteca:
                print(
                    "- loteca: a checagem confirma presença e integridade; "
                    "não recota odds já salvas."
                )

            if concursos_invalidos_atuais:
                lista_invalidos = ", ".join(
                    str(numero) for numero in sorted(concursos_invalidos_atuais)
                )
                print(f"- loteca: concursos atuais incompletos ou com odds inválidas: {lista_invalidos}")

            if faltantes_loteca:
                loteca_defasada = True

    if not defasados and not loteca_defasada:
        return concursos_remotos

    if loteca_defasada and not defasados:
        mensagem_atualizacao = "Deseja baixar os concursos atuais da Loteca agora? [S/N ou 1/0] "
    else:
        mensagem_atualizacao = "Deseja atualizar os bancos defasados agora? [S/N ou 1/0] "

    if not le_sim_nao(mensagem_atualizacao):
        return concursos_remotos

    for modalidade, _cobertura in defasados:
        try:
            sincronizar_historico(modalidade)
        except Exception as erro:
            print(f"Não consegui atualizar histórico de {modalidade}: {erro}")

    if loteca_defasada:
        from gera_loteca import atualizar_loteca

        caminho_padrao = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loteca_atual.csv")
        for concurso in faltantes_loteca:
            try:
                atualizar_loteca(
                    saida=caminho_padrao,
                    concurso=concurso,
                    dados_concurso=concursos_remotos_por_numero.get(concurso),
                )
            except Exception as erro:
                print(f"Não consegui atualizar a Loteca {concurso}: {erro}")

    return concursos_remotos


def gerar_bilhetes():
    opcoes = opcoes_modalidades()
    imprime_menu(opcoes)
    escolhidos = le_modalidades(opcoes)
    bilhetes = []

    for modalidade in escolhidos:
        print()

        if modalidade == "loteca":
            concursos_atuais = checa_bancos_historicos(["loteca"])
            config_loteca = configura_loteca(concursos_atuais)
            total = le_inteiro(f"Quantos bilhetes de {modalidade}? ")
            capacidade = capacidade_bilhetes_loteca(config_loteca["triplos"])
            if total > capacidade:
                print(
                    f"Com essa configuração existem {capacidade} bilhetes distintos; "
                    f"serão gerados {capacidade}."
                )
                total = capacidade

            assinaturas = set()
            tentativas = 0
            variante_reserva = 0
            while len(assinaturas) < total:
                variante = len(assinaturas) if config_loteca["modo"] == "razao" else 0
                bilhete = gera_bilhete_loteca(**config_loteca, variante=variante)
                assinatura = tuple(tuple(jogo["colunas"]) for jogo in bilhete)
                tentativas += 1

                if assinatura in assinaturas:
                    if tentativas < max(100, total * 50):
                        continue
                    # Evita laço longo em configurações quase esgotadas.
                    while variante_reserva < capacidade:
                        bilhete = gera_bilhete_loteca(
                            **{**config_loteca, "modo": "razao"},
                            variante=variante_reserva,
                        )
                        variante_reserva += 1
                        assinatura = tuple(tuple(jogo["colunas"]) for jogo in bilhete)
                        if assinatura not in assinaturas:
                            break
                    else:
                        break

                assinaturas.add(assinatura)
                bilhetes.append((modalidade, len(assinaturas), bilhete))

            continue

        total = le_inteiro(f"Quantos bilhetes de {modalidade}? ")
        quantidade = quantidade_aposta(modalidade)
        modalidade_normalizada = nome_modalidade(modalidade)
        estrategia = le_estrategia_numerica()
        concursos_historicos = None

        if estrategia != "aleatorio":
            checa_bancos_historicos([modalidade])
            concursos_historicos = le_quantidade_concursos()
            try:
                bilhetes_historicos, consultados = gera_bilhetes_historicos(
                    modalidade_normalizada,
                    quantidade,
                    estrategia,
                    total,
                    concursos_historicos,
                    atualizar_historico=False,
                )
            except Exception as erro:
                print(f"Não consegui consultar histórico de {modalidade}: {erro}")
                print("Gerando bilhetes aleatórios.")
                bilhetes_historicos = None
            else:
                print(f"Histórico consultado: {consultados} concursos.")
        else:
            bilhetes_historicos = None

        for numero in range(1, total + 1):
            if bilhetes_historicos is not None:
                bilhete = bilhetes_historicos[numero - 1]
            elif estrategia == "aleatorio":
                bilhete = gera_bilhete(modalidade, quantidade)
            else:
                bilhete = gera_bilhete(modalidade, quantidade)

            bilhetes.append((modalidade, numero, bilhete))

    print()
    print("BILHETES GERADOS")

    for modalidade, numero, bilhete in bilhetes:
        bilhete_formatado = formata_bilhete(bilhete)

        if bilhete_formatado.startswith("\n"):
            print(f"{modalidade} #{numero}:{bilhete_formatado}")
        else:
            print(f"{modalidade} #{numero}: {bilhete_formatado}")

    salvar_bilhetes_favoritos(bilhetes)


def modalidades_para_atualizacao(valores=None):
    valores = list(valores or [])

    if not valores or any(normaliza_nome(valor) in ("todos", "todas") for valor in valores):
        return list(MODALIDADES) + ["loteca"]

    modalidades = []
    for valor in valores:
        modalidade = nome_modalidade(valor)
        if modalidade not in modalidades:
            modalidades.append(modalidade)

    return modalidades


def atualizar_bancos(modalidades=None, concurso_loteca=None, force_loteca=False):
    modalidades = modalidades_para_atualizacao(modalidades)
    sucesso = True

    for modalidade in (item for item in modalidades if item in MODALIDADES):
        print(f"Atualizando histórico de {modalidade}...")
        try:
            atualizacao_completa = sincronizar_historico(modalidade)
        except Exception as erro:
            print(f"Falha ao atualizar {modalidade}: {erro}")
            sucesso = False
            continue

        if atualizacao_completa is False:
            print(f"{modalidade}: atualização não foi concluída integralmente.")
            sucesso = False

        inicio, fim = intervalo_concursos_numericos(modalidade)
        total = total_resultados_numericos(modalidade)
        intervalo = f"{inicio} a {fim}" if inicio is not None else "sem concursos"
        print(f"{modalidade}: {total} concursos no banco ({intervalo}).")

    if "loteca" in modalidades:
        from gera_loteca import ARQUIVO_PADRAO, atualizar_loteca

        if concurso_loteca is not None:
            try:
                atualizar_loteca(
                    saida=ARQUIVO_PADRAO,
                    concurso=concurso_loteca,
                    force=force_loteca,
                )
            except Exception as erro:
                print(f"Falha ao atualizar Loteca {concurso_loteca}: {erro}")
                sucesso = False
        else:
            try:
                programacoes = buscar_programacao_loteca()
            except Exception as erro:
                print(f"Falha ao consultar concursos atuais da Loteca: {erro}")
                sucesso = False
            else:
                if not programacoes:
                    print("A Caixa não informou concursos atuais da Loteca.")
                    sucesso = False

                for dados_concurso in programacoes:
                    numero = numero_concurso_loteca(dados_concurso)
                    if numero is None:
                        print("Ignorando programação da Loteca sem número de concurso.")
                        sucesso = False
                        continue

                    try:
                        atualizar_loteca(
                            saida=ARQUIVO_PADRAO,
                            concurso=numero,
                            force=force_loteca,
                            dados_concurso=dados_concurso,
                        )
                    except Exception as erro:
                        print(f"Falha ao atualizar Loteca {numero}: {erro}")
                        sucesso = False

    return sucesso


def criar_parser():
    parser = argparse.ArgumentParser(
        description="Gera bilhetes ou atualiza os bancos locais do Lotogen."
    )
    subcomandos = parser.add_subparsers(dest="comando")
    atualizar = subcomandos.add_parser(
        "atualizar",
        help="Atualiza bancos sem gerar bilhetes.",
    )
    atualizar.add_argument(
        "modalidades",
        nargs="*",
        help="Modalidades desejadas; sem valores, atualiza todas.",
    )
    atualizar.add_argument(
        "--concurso",
        type=int,
        help="Atualiza somente este concurso da Loteca.",
    )
    atualizar.add_argument(
        "--force",
        action="store_true",
        help="Recota a Loteca mesmo quando o concurso já está salvo.",
    )
    return parser


def main(argv=None):
    parser = criar_parser()
    args = parser.parse_args(argv)

    if args.comando == "atualizar":
        modalidades = args.modalidades
        if not modalidades and (args.concurso is not None or args.force):
            modalidades = ["loteca"]

        try:
            normalizadas = modalidades_para_atualizacao(modalidades)
        except ValueError as erro:
            parser.error(str(erro))

        if (args.concurso is not None or args.force) and "loteca" not in normalizadas:
            parser.error("--concurso e --force só podem ser usados ao atualizar a Loteca.")

        if not atualizar_bancos(
            normalizadas,
            concurso_loteca=args.concurso,
            force_loteca=args.force,
        ):
            raise SystemExit(1)
        return

    while True:
        gerar_bilhetes()

        if not le_sim_nao("Deseja gerar novos bilhetes? [S/N ou 1/0] "):
            return


if __name__ == "__main__":
    main()
