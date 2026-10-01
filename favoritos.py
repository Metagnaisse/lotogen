"""Gerenciador de bilhetes favoritos do Lotogen."""

import argparse
import json
from collections.abc import Mapping
from unicodedata import normalize

from banco_lotogen import listar_favoritos, remover_favorito, salvar_favorito
from lotogen import COLUNAS_LOTECA, MODALIDADES, formata_numero, lista_times, nome_modalidade, opcoes_modalidades


def normaliza_texto(texto):
    texto = normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().strip().split())


def normaliza_time(time):
    return normaliza_texto(str(time).replace(" /", "/").replace("/ ", "/"))


def time_atual(time):
    times_por_chave = {
        normaliza_time(time_atual): time_atual
        for time_atual in lista_times
    }
    return times_por_chave.get(normaliza_time(time))


def separa_dezenas_e_extra(modalidade, valores):
    regra = MODALIDADES[modalidade]

    if isinstance(valores, Mapping):
        return list(valores.get("dezenas", [])), valores.get("extra")

    valores = list(valores)

    if modalidade == "super-sete":
        colunas = [
            valor if isinstance(valor, list) else str(valor).replace(",", "/").split("/")
            for valor in valores
        ]
        return colunas, None

    if modalidade == "mais-milionaria":
        dezenas = [valor for valor in valores if not str(valor).strip().startswith("{")]
        trevos = [str(valor).strip().strip("{}") for valor in valores if str(valor).strip().startswith("{")]

        if trevos:
            return dezenas, trevos

        # Compatibilidade com a sintaxe antiga: 6 dezenas seguidas dos trevos.
        return valores[: regra["min"]], valores[regra["min"] :]

    if "extra" not in regra:
        return valores, None

    dezenas = []
    restantes = []
    for valor in valores:
        if len(dezenas) < regra["max"]:
            try:
                int(valor)
            except (TypeError, ValueError):
                restantes.append(valor)
            else:
                if not restantes:
                    dezenas.append(valor)
                    continue
                restantes.append(valor)
        else:
            restantes.append(valor)

    extra = " ".join(str(valor) for valor in restantes).strip() or None
    return dezenas, extra


def valida_colunas_super_sete(colunas):
    if len(colunas) != 7:
        raise ValueError("Super Sete precisa de 7 colunas.")

    normalizadas = []

    for indice, coluna in enumerate(colunas, start=1):
        if not coluna:
            raise ValueError(f"Coluna {indice}: informe ao menos um número.")

        numeros = []
        for dezena in coluna:
            try:
                numero = int(dezena)
            except ValueError:
                raise ValueError(f"Coluna {indice}: número inválido: {dezena}")

            if not 0 <= numero <= 9:
                raise ValueError(f"Coluna {indice}: número fora do intervalo 0 a 9: {dezena}")

            numeros.append(numero)

        if len(set(numeros)) != len(numeros):
            raise ValueError(f"Coluna {indice}: números repetidos.")

        normalizadas.append("/".join(str(numero) for numero in sorted(numeros)))

    total = sum(len(coluna.split("/")) for coluna in normalizadas)

    if not 7 <= total <= 21:
        raise ValueError("Super Sete precisa ter entre 7 e 21 números no total.")

    minimo_coluna, maximo_coluna = ((1, 2) if total <= 14 else (2, 3))
    for indice, coluna in enumerate(normalizadas, start=1):
        quantidade = len(coluna.split("/"))
        if not minimo_coluna <= quantidade <= maximo_coluna:
            raise ValueError(
                f"Coluna {indice}: use de {minimo_coluna} a {maximo_coluna} números "
                f"quando a aposta tiver {total} números."
            )

    return normalizadas


def valida_dezenas(modalidade, dezenas):
    if modalidade == "super-sete" and dezenas and isinstance(dezenas[0], list):
        return valida_colunas_super_sete(dezenas)

    regra = MODALIDADES[modalidade]

    if not regra["min"] <= len(dezenas) <= regra["max"]:
        raise ValueError(
            f"{modalidade} precisa ter entre {regra['min']} e {regra['max']} dezenas."
        )

    numeros = []
    for dezena in dezenas:
        try:
            numero = int(dezena)
        except ValueError:
            raise ValueError(f"Dezena inválida: {dezena}")

        if regra.get("zero_final") and numero == 0:
            numero = 100

        if not regra["inicio"] <= numero <= regra["fim"]:
            raise ValueError(
                f"Dezena fora do intervalo {regra['inicio']} a {regra['fim']}: {dezena}"
            )

        numeros.append(numero)

    if len(set(numeros)) != len(numeros):
        raise ValueError("O bilhete não pode ter dezenas repetidas.")

    return [
        formata_numero(numero, regra.get("zero_final", False))
        for numero in sorted(numeros)
    ]


def valida_extra(modalidade, extra):
    if modalidade == "mais-milionaria":
        if not extra:
            raise ValueError("+Milionária precisa de 2 trevos.")

        trevos = []
        valores = extra if isinstance(extra, (list, tuple)) else str(extra).split()
        for trevo in valores:
            try:
                numero = int(trevo.strip("{}"))
            except ValueError:
                raise ValueError(f"Trevo inválido: {trevo}")

            if not 1 <= numero <= 6:
                raise ValueError(f"Trevo fora do intervalo 1 a 6: {trevo}")

            trevos.append(numero)

        minimo = MODALIDADES[modalidade]["trevos_min"]
        maximo = MODALIDADES[modalidade]["trevos_max"]
        if not minimo <= len(trevos) <= maximo or len(set(trevos)) != len(trevos):
            raise ValueError(
                f"+Milionária precisa de {minimo} a {maximo} trevos diferentes."
            )

        return " ".join(str(trevo) for trevo in sorted(trevos))

    if modalidade == "dia-de-sorte":
        if not extra:
            raise ValueError("Dia de Sorte precisa de um Mês da Sorte.")

        meses = {normaliza_texto(mes): mes for mes in MODALIDADES[modalidade]["extra"]}
        mes = meses.get(normaliza_texto(extra))
        if not mes:
            raise ValueError("Informe um Mês da Sorte válido.")
        return mes

    if modalidade != "timemania":
        return extra

    if not extra:
        raise ValueError("Timemania precisa de um Time do Coração.")

    time = time_atual(extra)

    if not time:
        raise ValueError("Informe um Time do Coração da lista atual da Timemania.")

    return time


def normaliza_colunas_loteca(colunas):
    if isinstance(colunas, str):
        colunas = colunas.replace(",", "/").replace("-", "/").split("/")

    ordem = {coluna: indice for indice, coluna in enumerate(COLUNAS_LOTECA)}
    normalizadas = []

    for coluna in colunas:
        coluna = str(coluna).strip().upper()

        if coluna not in COLUNAS_LOTECA:
            raise ValueError(f"Coluna inválida da Loteca: {coluna}")

        if coluna not in normalizadas:
            normalizadas.append(coluna)

    if not normalizadas:
        raise ValueError("Cada jogo da Loteca precisa de ao menos uma coluna.")

    return sorted(normalizadas, key=ordem.get)


def valida_loteca(valores):
    if len(valores) != 14:
        raise ValueError("Loteca precisa de 14 jogos.")

    jogos = []

    for indice, valor in enumerate(valores, start=1):
        if isinstance(valor, dict):
            colunas = normaliza_colunas_loteca(valor.get("colunas", []))
            mandante = valor.get("mandante")
            visitante = valor.get("visitante")
        else:
            colunas = normaliza_colunas_loteca(valor)
            mandante = None
            visitante = None

        jogos.append(
            {
                "jogo": indice,
                "colunas": colunas,
                "mandante": mandante,
                "visitante": visitante,
            }
        )

    return jogos


def cria_favorito(modalidade, valores, nome=None):
    modalidade = nome_modalidade(modalidade)

    if modalidade == "loteca":
        jogos = valida_loteca(valores)
        favorito_id = salvar_favorito(modalidade, jogos, nome=nome)
        return favorito_id, modalidade, jogos, None

    if modalidade not in MODALIDADES:
        raise ValueError("Esta modalidade ainda não é suportada nos favoritos.")

    dezenas, extra = separa_dezenas_e_extra(modalidade, valores)
    dezenas = valida_dezenas(modalidade, dezenas)
    extra = valida_extra(modalidade, extra)
    favorito_id = salvar_favorito(modalidade, dezenas, extra=extra, nome=nome)
    return favorito_id, modalidade, dezenas, extra


def formata_favorito(favorito):
    dezenas = json.loads(favorito["dezenas_json"])
    cabecalho = f"{favorito['id']}. {favorito['modalidade']}"

    if favorito["nome"]:
        cabecalho += f" - {favorito['nome']}"

    if favorito["modalidade"] == "loteca":
        linhas = [f"{cabecalho}:"]

        for indice, jogo in enumerate(dezenas, start=1):
            if isinstance(jogo, dict):
                numero = int(jogo.get("jogo") or indice)
                colunas = "/".join(jogo.get("colunas", []))
                mandante = jogo.get("mandante")
                visitante = jogo.get("visitante")

                if mandante and visitante:
                    linhas.append(f"{numero:02d}: {mandante} x {visitante} -> {colunas}")
                else:
                    linhas.append(f"{numero:02d}: {colunas}")
            else:
                linhas.append(f"{indice:02d}: {jogo}")

        return "\n".join(linhas)

    partes = [f"{cabecalho}:", " ".join(dezenas)]

    if favorito["extra"]:
        partes.append(f"{{{favorito['extra']}}}")

    return " ".join(partes)


def texto_favorito_salvo(favorito_id, modalidade, dezenas, extra=None):
    if modalidade == "loteca":
        return f"Favorito {favorito_id} salvo: loteca com {len(dezenas)} jogos"

    texto = f"Favorito {favorito_id} salvo: {modalidade} {' '.join(dezenas)}"

    if extra:
        texto += f" {{{extra}}}"

    return texto


def cmd_adicionar(args):
    valores = args.valores
    if getattr(args, "trevos", None):
        valores = {"dezenas": valores, "extra": args.trevos}

    favorito_id, modalidade, dezenas, extra = cria_favorito(
        args.modalidade,
        valores,
        nome=args.nome,
    )
    print(texto_favorito_salvo(favorito_id, modalidade, dezenas, extra))


def cmd_listar(args):
    modalidade = nome_modalidade(args.modalidade) if args.modalidade else None
    favoritos = listar_favoritos(modalidade)

    if not favoritos:
        print("Nenhum favorito cadastrado.")
        return

    for favorito in favoritos:
        print(formata_favorito(favorito))


def le_filtro_listagem():
    while True:
        resposta = normaliza_texto(input("Listar todos ou alguma modalidade? [T/M] "))

        if resposta in ("", "t", "todos", "todo"):
            return None

        if resposta in ("m", "modalidade", "alguma"):
            return le_modalidade()

        print("Informe T/todos ou M/modalidade.")


def cmd_remover(args):
    if remover_favorito(args.id):
        print(f"Favorito {args.id} removido.")
    else:
        print(f"Favorito {args.id} não encontrado.")


def imprime_menu_modalidades():
    opcoes = opcoes_modalidades()
    indices = list(range(1, len(opcoes))) + [0]

    print("Modalidade:")
    for indice in indices:
        print(f"{indice}. {opcoes[indice]}")


def le_modalidade():
    opcoes = opcoes_modalidades()

    while True:
        imprime_menu_modalidades()
        resposta = input("Escolha: ").strip()

        try:
            indice = int(resposta)
        except ValueError:
            print("Informe o número da modalidade.")
            continue

        if 0 <= indice < len(opcoes):
            return opcoes[indice]

        print("Opção inválida.")


def modo_interativo():
    while True:
        print()
        print("FAVORITOS")
        print("1. listar")
        print("2. adicionar")
        print("3. remover")
        print("0. sair")
        opcao = input("Escolha: ").strip()

        if opcao == "0":
            return

        if opcao == "1":
            modalidade = le_filtro_listagem()
            cmd_listar(argparse.Namespace(modalidade=modalidade))
            continue

        if opcao == "2":
            modalidade = le_modalidade()
            dezenas = input("Dezenas: ").strip().split()
            if modalidade == "mais-milionaria":
                valores = {
                    "dezenas": dezenas,
                    "extra": input("Trevos: ").strip().split(),
                }
            elif modalidade in ("timemania", "dia-de-sorte"):
                valores = {
                    "dezenas": dezenas,
                    "extra": input("Time/Mês da Sorte: ").strip(),
                }
            else:
                valores = dezenas
            nome = input("Nome opcional: ").strip() or None

            try:
                favorito_id, modalidade, dezenas, extra = cria_favorito(
                    modalidade,
                    valores,
                    nome=nome,
                )
            except ValueError as erro:
                print(f"Não consegui salvar: {erro}")
                continue

            print(texto_favorito_salvo(favorito_id, modalidade, dezenas, extra))
            continue

        if opcao == "3":
            try:
                favorito_id = int(input("ID do favorito: ").strip())
            except ValueError:
                print("Informe um ID numérico.")
                continue

            cmd_remover(argparse.Namespace(id=favorito_id))
            continue

        print("Opção inválida.")


def parse_args():
    parser = argparse.ArgumentParser(description="Gerencia bilhetes favoritos do Lotogen.")
    subparsers = parser.add_subparsers(dest="comando")

    adicionar = subparsers.add_parser("adicionar", help="Cadastra um bilhete favorito.")
    adicionar.add_argument("modalidade")
    adicionar.add_argument("valores", nargs="+")
    adicionar.add_argument(
        "--trevos",
        nargs="+",
        help="Trevos da +Milionária, separados das dezenas.",
    )
    adicionar.add_argument("--nome")
    adicionar.set_defaults(func=cmd_adicionar)

    listar = subparsers.add_parser("listar", help="Lista bilhetes favoritos.")
    listar.add_argument("--modalidade")
    listar.set_defaults(func=cmd_listar)

    remover = subparsers.add_parser("remover", help="Remove um favorito pelo ID.")
    remover.add_argument("id", type=int)
    remover.set_defaults(func=cmd_remover)

    return parser.parse_args()


def main():
    args = parse_args()

    if not args.comando:
        modo_interativo()
        return

    args.func(args)


if __name__ == "__main__":
    main()
