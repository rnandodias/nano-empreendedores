"""Harmonização de classificações entre fontes.

CNAE (versões 2.0 vs 2.3), categorias de cor/raça, escolaridade e ocupação.
Mantém um único vocabulário interno do projeto, documentado em
``docs/dicionario-dados.md``.

As funções recebem o DataFrame e a coluna de origem e **adicionam** uma coluna
nova com o nome harmonizado (cor_raca, escolaridade, posicao_ocupacao).
A coluna original é mantida para rastreabilidade.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Tabelas de-para
# ---------------------------------------------------------------------------

# PNADC V2010 — cor ou raça
COR_RACA_PNADC: dict[str, str] = {
    "1": "branca",
    "2": "preta",
    "3": "amarela",
    "4": "parda",
    "5": "indigena",
    "9": "ignorada",
}

# Censo Demográfico (V0606 / V0606A no Censo 2010-2022) — mesmos códigos, ordem
# diferente: amarela=4, parda=3. Mantemos rótulo final igual.
COR_RACA_CENSO: dict[str, str] = {
    "1": "branca",
    "2": "preta",
    "3": "parda",
    "4": "amarela",
    "5": "indigena",
    "9": "ignorada",
}

# PNADC VD3004 — Nível de instrução mais elevado alcançado.
# Categorias colapsadas para o vocabulário interno do projeto:
#  - sem_instrucao: 1
#  - fundamental:   2 (fund. incompleto), 3 (fund. completo)
#  - medio:         4 (médio incompleto), 5 (médio completo)
#  - superior:      6 (sup. incompleto), 7 (sup. completo)
ESCOLARIDADE_PNADC: dict[str, str] = {
    "1": "sem_instrucao",
    "2": "fundamental",
    "3": "fundamental",
    "4": "medio",
    "5": "medio",
    "6": "superior",
    "7": "superior",
}

# PNADC VD4009 — Posição na ocupação e categoria do emprego (consolidada),
# para a pessoa ocupada na semana de referência. Códigos oficiais IBGE:
#   01 = Empregado no setor privado com carteira de trabalho assinada
#   02 = Empregado no setor privado sem carteira de trabalho assinada
#   03 = Trabalhador doméstico com carteira de trabalho assinada
#   04 = Trabalhador doméstico sem carteira de trabalho assinada
#   05 = Empregado no setor público com carteira de trabalho assinada
#   06 = Militar e servidor estatutário
#   07 = Empregado no setor público sem carteira de trabalho assinada
#   08 = Empregador
#   09 = Conta-própria
#   10 = Trabalhador familiar auxiliar
POSICAO_OCUPACAO_PNADC: dict[str, str] = {
    "01": "empregado",
    "02": "empregado",
    "03": "domestico",
    "04": "domestico",
    "05": "empregado",
    "06": "empregado",
    "07": "empregado",
    "08": "empregador",
    "09": "conta_propria",
    "10": "outro",
}


# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------

def harmonize_cor_raca(df: pd.DataFrame, col: str, fonte: str) -> pd.DataFrame:
    """Padroniza categorias de cor/raça entre PNADC, Censo e MEI.

    Adiciona a coluna ``cor_raca`` com o vocabulário interno.
    """
    fonte = fonte.lower()
    if fonte == "pnadc":
        mapa = COR_RACA_PNADC
    elif fonte == "censo":
        mapa = COR_RACA_CENSO
    else:
        raise ValueError(f"Fonte desconhecida para cor_raca: {fonte!r}")

    df = df.copy()
    df["cor_raca"] = (
        df[col].astype(str).str.strip().map(mapa).fillna("ignorada").astype("category")
    )
    return df


def harmonize_escolaridade(df: pd.DataFrame, col: str, fonte: str) -> pd.DataFrame:
    """Padroniza escolaridade em: sem_instrucao, fundamental, medio, superior."""
    fonte = fonte.lower()
    if fonte == "pnadc":
        mapa = ESCOLARIDADE_PNADC
    else:
        raise ValueError(f"Fonte ainda não implementada para escolaridade: {fonte!r}")

    df = df.copy()
    df["escolaridade"] = (
        df[col].astype(str).str.strip().map(mapa).astype("category")
    )
    return df


def harmonize_posicao_ocupacao(df: pd.DataFrame, col: str, fonte: str) -> pd.DataFrame:
    """Padroniza posição na ocupação, marcando claramente 'conta_propria'.

    Vocabulário interno: ``conta_propria`` | ``empregado`` | ``empregador`` |
    ``domestico`` | ``outro``. Não-ocupados ficam como ``NaN``.
    """
    fonte = fonte.lower()
    if fonte == "pnadc":
        mapa = POSICAO_OCUPACAO_PNADC
    else:
        raise ValueError(f"Fonte ainda não implementada para posicao_ocupacao: {fonte!r}")

    df = df.copy()
    # Códigos PNADC vêm com 2 dígitos (ex: '01', '09'). Garantir zero-padding.
    serie = df[col].astype(str).str.strip()
    serie = serie.where(serie.str.len() != 1, "0" + serie)
    df["posicao_ocupacao"] = serie.map(mapa).astype("category")
    return df


def harmonize_cnae(df: pd.DataFrame, col: str, versao_origem: str = "2.0") -> pd.DataFrame:
    """Converte CNAE da versão de origem para o vocabulário interno do projeto.

    PENDÊNCIA Etapa 1: implementação completa requer tabela de-para CNAE 2.0 ↔
    CNAE 2.3 (publicada pelo CONCLA) e mapeamento das classes 5-dígitos para
    seções A-U. Para a PNADC trimestral vigente (V4013 + V40132), o IBGE já
    devolve a seção em ``V40132`` (1 caractere alfabético), o que nos atende
    para os recortes da Etapa 1. Conversão entre versões CNAE será necessária
    quando integrarmos o dump CNPJ/MEI (CNAE 2.3) com PNADC/Censo (CNAE 2.0).
    """
    raise NotImplementedError(
        "TODO Etapa 1+: tabela de-para CNAE 2.0 ↔ 2.3. "
        "Para PNADC use diretamente V40132 (já vem como seção)."
    )
