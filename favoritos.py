"""Gerenciador de bilhetes favoritos do Lotogen."""

import argparse
import json
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
    quantidade = regra["min"]
    dezenas = valores[:quantidade]
    extra = " ".join(valores[quantidade:]).strip() or None
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

    return normalizadas


def valida_dezenas(modalidade, dezenas):
    if modalidade == "super-sete" and dezenas and isinstance(dezenas[0], list):
        return valida_colunas_super_sete(dezenas)

    regra = MODALIDADES[modalidade]

    if len(dezenas) != regra["min"]:
        raise ValueError(f"{modalidade} precisa de {regra['min']} dezenas.")

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
        for trevo in extra.split():
            try:
                numero = int(trevo.strip("{}"))
            except ValueError:
                raise ValueError(f"Trevo inválido: {trevo}")

            if not 1 <= numero <= 6:
                raise ValueError(f"Trevo fora do intervalo 1 a 6: {trevo}")

            trevos.append(numero)

        if len(trevos) != 2 or len(set(trevos)) != 2:
            raise ValueError("+Milionária precisa de 2 trevos diferentes.")

        return " ".join(str(trevo) for trevo in sorted(trevos))

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
    favorito_id, modalidade, dezenas, extra = cria_favorito(
        args.modalidade,
        args.valores,
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
            valores = input("Dezenas e extra, se houver: ").strip().split()
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
