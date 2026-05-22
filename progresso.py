"""Barra de progresso simples para o terminal."""

import os


def largura_padrao():
    try:
        return int(os.getenv("LOTOGEN_LARGURA_PROGRESSO", "60"))
    except ValueError:
        return 60


def mostrar_progresso(atual, total, largura=None, prefixo=""):
    if total <= 0:
        return

    if largura is None:
        largura = largura_padrao()

    atual = min(max(atual, 0), total)
    proporcao = atual / total
    preenchidos = int(largura * proporcao)
    vazios = largura - preenchidos
    percentual = int(proporcao * 100)
    barra = "#" * preenchidos + "=" * vazios
    texto_prefixo = f"{prefixo} " if prefixo else ""
    print(f"\r{texto_prefixo}|{barra}| - {percentual:3d}% completo", end="", flush=True)

    if atual >= total:
        print()
