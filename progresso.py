"""Barra de progresso simples para o terminal."""

import os
import shutil
import sys


def largura_padrao():
    try:
        return int(os.getenv("LOTOGEN_LARGURA_PROGRESSO", "60"))
    except ValueError:
        return 60


def largura_disponivel(prefixo=""):
    """Calcula uma largura que nao provoque quebra da linha no terminal."""
    colunas = shutil.get_terminal_size(fallback=(80, 24)).columns
    texto_prefixo = f"{prefixo} " if prefixo else ""
    caracteres_fixos = len(f"{texto_prefixo}|| - {100:3d}% completo")
    return max(1, colunas - caracteres_fixos - 1)


def mostrar_progresso(atual, total, largura=None, prefixo=""):
    if total <= 0:
        return

    if largura is None:
        largura = largura_padrao()

    largura = max(1, min(largura, largura_disponivel(prefixo)))

    atual = min(max(atual, 0), total)
    proporcao = atual / total
    preenchidos = int(largura * proporcao)
    vazios = largura - preenchidos
    percentual = int(proporcao * 100)
    barra = "#" * preenchidos + "=" * vazios
    texto_prefixo = f"{prefixo} " if prefixo else ""
    limpa_linha = "\033[2K" if sys.stdout.isatty() else ""
    print(
        f"\r{limpa_linha}{texto_prefixo}|{barra}| - {percentual:3d}% completo",
        end="",
        flush=True,
    )

    if atual >= total:
        print()
