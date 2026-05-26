"""Persistência local do Lotogen em SQLite."""

import json
import os
import sqlite3
from datetime import datetime


CAMINHO_BANCO = "lotogen.db"


def agora_iso():
    return datetime.now().isoformat(timespec="seconds")


def conectar(caminho=CAMINHO_BANCO):
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    inicializar(conexao)
    return conexao


def inicializar(conexao):
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS resultados_numericos (
            modalidade TEXT NOT NULL,
            concurso INTEGER NOT NULL,
            data_sorteio TEXT,
            dezenas_json TEXT NOT NULL,
            extra TEXT,
            atualizado_em TEXT NOT NULL,
            PRIMARY KEY (modalidade, concurso)
        );

        CREATE TABLE IF NOT EXISTS frequencias_numericas (
            modalidade TEXT NOT NULL,
            tipo TEXT NOT NULL,
            item TEXT NOT NULL,
            frequencia INTEGER NOT NULL,
            concurso_inicial INTEGER NOT NULL,
            concurso_final INTEGER NOT NULL,
            atualizado_em TEXT NOT NULL,
            PRIMARY KEY (modalidade, tipo, item, concurso_inicial, concurso_final)
        );

        CREATE TABLE IF NOT EXISTS loteca_concursos (
            concurso INTEGER PRIMARY KEY,
            data_proximo_concurso TEXT,
            atualizado_em TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS loteca_jogos (
            concurso INTEGER NOT NULL,
            sequencial INTEGER NOT NULL,
            mandante TEXT NOT NULL,
            visitante TEXT NOT NULL,
            dia_semana TEXT,
            data_jogo TEXT,
            competicao TEXT,
            odd_mandante REAL,
            odd_empate REAL,
            odd_visitante REAL,
            atualizado_em TEXT NOT NULL,
            PRIMARY KEY (concurso, sequencial),
            FOREIGN KEY (concurso) REFERENCES loteca_concursos(concurso)
        );

        CREATE TABLE IF NOT EXISTS bilhetes_favoritos (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            modalidade TEXT NOT NULL,
            dezenas_json TEXT NOT NULL,
            extra TEXT,
            criado_em TEXT NOT NULL
        );
        """
    )
    migrar_loteca_jogos(conexao)
    conexao.commit()


def coluna_existe(conexao, tabela, coluna):
    linhas = conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    return any(linha["name"] == coluna for linha in linhas)


def migrar_loteca_jogos(conexao):
    if not coluna_existe(conexao, "loteca_jogos", "competicao"):
        conexao.execute("ALTER TABLE loteca_jogos ADD COLUMN competicao TEXT")


def maior_concurso_numerico(modalidade):
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT MAX(concurso) AS concurso FROM resultados_numericos WHERE modalidade = ?",
            (modalidade,),
        ).fetchone()
        return linha["concurso"] if linha and linha["concurso"] is not None else None


def salvar_resultado_numerico(modalidade, concurso, dezenas, data_sorteio=None, extra=None):
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT OR REPLACE INTO resultados_numericos
                (modalidade, concurso, data_sorteio, dezenas_json, extra, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                modalidade,
                int(concurso),
                data_sorteio,
                json.dumps([str(dezena) for dezena in dezenas], ensure_ascii=False),
                extra,
                agora_iso(),
            ),
        )
        conexao.commit()


def resultados_numericos(modalidade, concurso_inicial=None):
    sql = "SELECT * FROM resultados_numericos WHERE modalidade = ?"
    parametros = [modalidade]

    if concurso_inicial is not None:
        sql += " AND concurso >= ?"
        parametros.append(int(concurso_inicial))

    sql += " ORDER BY concurso"

    with conectar() as conexao:
        return list(conexao.execute(sql, parametros))


def intervalo_concursos_numericos(modalidade):
    with conectar() as conexao:
        linha = conexao.execute(
            """
            SELECT MIN(concurso) AS inicio, MAX(concurso) AS fim
            FROM resultados_numericos
            WHERE modalidade = ?
            """,
            (modalidade,),
        ).fetchone()

    if not linha or linha["inicio"] is None or linha["fim"] is None:
        return None, None

    return int(linha["inicio"]), int(linha["fim"])


def total_resultados_numericos(modalidade):
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT COUNT(*) AS total FROM resultados_numericos WHERE modalidade = ?",
            (modalidade,),
        ).fetchone()
        return int(linha["total"] or 0)


def salvar_frequencias(modalidade, frequencias_dezenas, frequencias_extra, concurso_inicial, concurso_final):
    atualizado_em = agora_iso()

    with conectar() as conexao:
        conexao.execute(
            """
            DELETE FROM frequencias_numericas
            WHERE modalidade = ? AND concurso_inicial = ? AND concurso_final = ?
            """,
            (modalidade, int(concurso_inicial), int(concurso_final)),
        )

        for tipo, frequencias in (("dezena", frequencias_dezenas), ("extra", frequencias_extra)):
            for item, frequencia in frequencias.items():
                conexao.execute(
                    """
                    INSERT INTO frequencias_numericas
                        (modalidade, tipo, item, frequencia, concurso_inicial, concurso_final, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        modalidade,
                        tipo,
                        str(item),
                        int(frequencia),
                        int(concurso_inicial),
                        int(concurso_final),
                        atualizado_em,
                    ),
                )

        conexao.commit()


def ler_frequencias(modalidade, concurso_inicial, concurso_final):
    with conectar() as conexao:
        linhas = list(
            conexao.execute(
                """
                SELECT tipo, item, frequencia
                FROM frequencias_numericas
                WHERE modalidade = ? AND concurso_inicial = ? AND concurso_final = ?
                """,
                (modalidade, int(concurso_inicial), int(concurso_final)),
            )
        )

    dezenas = {}
    extras = {}

    for linha in linhas:
        destino = dezenas if linha["tipo"] == "dezena" else extras
        destino[linha["item"]] = int(linha["frequencia"])

    return dezenas, extras


def salvar_loteca(concurso, jogos, data_proximo_concurso=None):
    atualizado_em = agora_iso()

    with conectar() as conexao:
        conexao.execute(
            """
            INSERT OR REPLACE INTO loteca_concursos
                (concurso, data_proximo_concurso, atualizado_em)
            VALUES (?, ?, ?)
            """,
            (int(concurso), data_proximo_concurso, atualizado_em),
        )

        for indice, jogo in enumerate(jogos, start=1):
            sequencial = int(getattr(jogo, "sequencial", indice) or indice)
            conexao.execute(
                """
                INSERT OR REPLACE INTO loteca_jogos
                    (
                        concurso, sequencial, mandante, visitante, dia_semana, data_jogo,
                        competicao, odd_mandante, odd_empate, odd_visitante, atualizado_em
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(concurso),
                    sequencial,
                    jogo.mandante,
                    jogo.visitante,
                    getattr(jogo, "dia_semana", None),
                    getattr(jogo, "data", None),
                    getattr(jogo, "competicao", None),
                    jogo.odd_mandante,
                    jogo.odd_empate,
                    jogo.odd_visitante,
                    atualizado_em,
                ),
            )

        conexao.commit()


def concurso_loteca_atual():
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT concurso FROM loteca_concursos ORDER BY concurso DESC LIMIT 1"
        ).fetchone()
        return int(linha["concurso"]) if linha else None


def jogos_loteca(concurso=None):
    if concurso is None:
        concurso = concurso_loteca_atual()

    if concurso is None:
        return []

    with conectar() as conexao:
        linhas = list(
            conexao.execute(
                """
                SELECT *
                FROM loteca_jogos
                WHERE concurso = ?
                ORDER BY sequencial
                """,
                (int(concurso),),
            )
        )

    return [
        {
            "odds": [linha["odd_mandante"], linha["odd_empate"], linha["odd_visitante"]],
            "mandante": linha["mandante"],
            "visitante": linha["visitante"],
            "competicao": linha["competicao"],
        }
        for linha in linhas
    ]


def competicoes_loteca():
    with conectar() as conexao:
        return list(
            conexao.execute(
                """
                SELECT competicao, COUNT(*) AS total
                FROM loteca_jogos
                WHERE competicao IS NOT NULL AND TRIM(competicao) <> ''
                GROUP BY competicao
                ORDER BY total DESC, competicao
                """
            )
        )


def salvar_favorito(modalidade, dezenas, extra=None, nome=None):
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO bilhetes_favoritos
                (nome, modalidade, dezenas_json, extra, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                nome,
                modalidade,
                json.dumps([str(dezena) for dezena in dezenas], ensure_ascii=False),
                extra,
                agora_iso(),
            ),
        )
        conexao.commit()
        return int(cursor.lastrowid)


def listar_favoritos(modalidade=None):
    sql = "SELECT * FROM bilhetes_favoritos"
    parametros = []

    if modalidade:
        sql += " WHERE modalidade = ?"
        parametros.append(modalidade)

    sql += " ORDER BY modalidade, id"

    with conectar() as conexao:
        return list(conexao.execute(sql, parametros))


def remover_favorito(favorito_id):
    with conectar() as conexao:
        cursor = conexao.execute(
            "DELETE FROM bilhetes_favoritos WHERE id = ?",
            (int(favorito_id),),
        )
        conexao.commit()
        return cursor.rowcount > 0
