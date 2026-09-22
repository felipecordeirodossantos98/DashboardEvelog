"""Agregações e regras reutilizáveis usadas nas tabelas e gráficos."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from .data import faixa_atraso_por_dia, localizar_coluna


def garantir_colunas_status(df: pd.DataFrame) -> pd.DataFrame:
    """Garante as duas colunas de prazo esperadas após um unstack."""
    resultado = df.copy()
    for coluna in ("NO PRAZO", "FORA DO PRAZO"):
        if coluna not in resultado.columns:
            resultado[coluna] = 0
    return resultado


def aplicar_regras_otd(
    df: pd.DataFrame,
    *,
    dias_extra: int = 0,
    justificativas: Iterable[str] = (),
    usar_baixa_indevida: bool = False,
) -> pd.DataFrame:
    """Aplica, uma única vez, todas as regras parametrizáveis do OTD.

    A base retornada é a fonte de verdade da aba de entregues. Dessa forma,
    gráficos, tabelas e exportações passam a usar exatamente a mesma regra.

    ``Prazo Base Ajustado`` considera os dias extras e, quando habilitada, a
    correção de baixa indevida. ``Prazo Ajustado`` parte desse OTD base e
    acrescenta somente as justificativas por ocorrência selecionadas pelo usuário.
    """
    base = df.copy()
    if base.empty:
        for coluna in (
            "Previsao Ajustada",
            "Dias Atraso",
            "Prazo Base Ajustado",
            "Baixa Indevida",
            "Justificado",
            "Justificativa Aplicada",
            "Prazo Ajustado",
            "No Prazo Ajustado",
        ):
            base[coluna] = pd.Series(dtype="object")
        return base

    base["Ocorrencias"] = base["Ocorrencias"].fillna("").astype(str).str.strip()
    base["Previsao Ajustada"] = base["Previsao"] + pd.to_timedelta(
        int(dias_extra), unit="D"
    )
    base["Dias Atraso"] = (
        base["Dt Evento"].dt.normalize()
        - base["Previsao Ajustada"].dt.normalize()
    ).dt.days

    # Preserva registros com datas inválidas usando o prazo já calculado na
    # carga. Para datas válidas, a regra parametrizada substitui esse valor.
    base["Prazo Base Ajustado"] = base.get(
        "Prazo", pd.Series(index=base.index, dtype="object")
    )
    datas_validas = base["Dt Evento"].notna() & base["Previsao Ajustada"].notna()
    base.loc[
        datas_validas & base["Dias Atraso"].le(0), "Prazo Base Ajustado"
    ] = "NO PRAZO"
    base.loc[
        datas_validas & base["Dias Atraso"].gt(0), "Prazo Base Ajustado"
    ] = "FORA DO PRAZO"

    # Baixa indevida é uma correção do OTD base, e não uma justificativa.
    # Como Descricao vazia é padronizada como LAST MILE durante a carga, a
    # identificação precisa consultar diretamente a coluna original Descricao.
    col_descricao = localizar_coluna(base, "descricao")
    if col_descricao:
        descricao_vazia = (
            base[col_descricao]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
        )
    else:
        descricao_vazia = pd.Series(False, index=base.index)

    atraso_base = base["Prazo Base Ajustado"].eq("FORA DO PRAZO")
    cond_baixa_indevida = (
        atraso_base
        & base["Dias Atraso"].eq(1)
        & descricao_vazia
    )

    base["Baixa Indevida"] = False
    if usar_baixa_indevida:
        base.loc[cond_baixa_indevida, "Baixa Indevida"] = True
        base.loc[cond_baixa_indevida, "Prazo Base Ajustado"] = "NO PRAZO"

    # As justificativas por ocorrência entram somente depois do OTD base já
    # corrigido por dias extras e, se habilitada, por baixa indevida.
    selecionadas = list(
        dict.fromkeys(str(v).strip() for v in justificativas if str(v).strip())
    )
    ocorrencias_justificadas = {valor.upper() for valor in selecionadas}
    ocorrencias_upper = base["Ocorrencias"].str.upper()
    atraso_para_justificar = base["Prazo Base Ajustado"].eq("FORA DO PRAZO")
    cond_ocorrencia = (
        atraso_para_justificar
        & ocorrencias_upper.isin(ocorrencias_justificadas)
    )

    base["Justificado"] = cond_ocorrencia
    base["Justificativa Aplicada"] = ""
    base.loc[cond_ocorrencia, "Justificativa Aplicada"] = base.loc[
        cond_ocorrencia, "Ocorrencias"
    ]

    base["Prazo Ajustado"] = "FORA DO PRAZO"
    base.loc[
        base["Prazo Base Ajustado"].eq("NO PRAZO") | base["Justificado"],
        "Prazo Ajustado",
    ] = "NO PRAZO"
    base["No Prazo Ajustado"] = base["Prazo Ajustado"].eq("NO PRAZO").astype(int)
    return base


def resumo_otd_por_grupo(
    df: pd.DataFrame,
    tipo_ordem: str,
    *,
    prazo_col: str = "Prazo",
) -> pd.DataFrame:
    """Cria o resumo usado no gráfico principal de OTD."""
    agrupado = (
        df.groupby(["Grupo", prazo_col])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    agrupado = garantir_colunas_status(agrupado)
    agrupado.columns.name = None
    agrupado["Total"] = agrupado["NO PRAZO"] + agrupado["FORA DO PRAZO"]

    denominador = agrupado["Total"].replace(0, pd.NA)
    agrupado["Percentual No Prazo"] = (agrupado["NO PRAZO"] / denominador) * 100
    agrupado["Percentual Atrasado"] = (agrupado["FORA DO PRAZO"] / denominador) * 100

    if tipo_ordem == "Percentual":
        agrupado = agrupado.sort_values(
            ["Percentual No Prazo", "Total"], ascending=[True, True]
        )
    else:
        agrupado = agrupado.sort_values("Total", ascending=True)

    total = pd.DataFrame(
        {
            "Grupo": ["Total"],
            "NO PRAZO": [agrupado["NO PRAZO"].sum()],
            "FORA DO PRAZO": [agrupado["FORA DO PRAZO"].sum()],
        }
    )
    total["Total"] = total["NO PRAZO"] + total["FORA DO PRAZO"]
    total_den = total["Total"].replace(0, pd.NA)
    total["Percentual No Prazo"] = (total["NO PRAZO"] / total_den) * 100
    total["Percentual Atrasado"] = (total["FORA DO PRAZO"] / total_den) * 100

    return pd.concat([agrupado, total], ignore_index=True)


def resumo_otd_pizza(df: pd.DataFrame, *, prazo_col: str = "Prazo") -> pd.DataFrame:
    """Retorna as duas fatias usadas nos gráficos de OTD."""
    no_prazo = int(df[prazo_col].eq("NO PRAZO").sum())
    fora_prazo = int(df[prazo_col].eq("FORA DO PRAZO").sum())
    return pd.DataFrame(
        {
            "Status": ["No Prazo", "Fora do Prazo"],
            "Quantidade": [no_prazo, fora_prazo],
        }
    )


def adicionar_periodo_otd(df: pd.DataFrame, tipo_periodo: str) -> pd.DataFrame:
    """Adiciona a mesma chave temporal usada no gráfico de evolução do OTD."""
    base = df[df["Dt Evento"].notna()].copy()
    if base.empty:
        base["Periodo"] = pd.Series(dtype="datetime64[ns]")
        return base

    evento = pd.to_datetime(base["Dt Evento"], errors="coerce")
    if tipo_periodo == "Diário":
        base["Periodo"] = evento.dt.normalize()
    elif tipo_periodo == "Semanal":
        base["Periodo"] = evento.dt.to_period("W").apply(lambda r: r.start_time)
    else:
        base["Periodo"] = evento.dt.to_period("M").apply(lambda r: r.start_time)
    return base


def evolucao_otd(
    df: pd.DataFrame,
    tipo_periodo: str,
    *,
    prazo_col: str = "Prazo",
) -> pd.DataFrame:
    """Agrupa OTD por dia, semana ou mês."""
    base = adicionar_periodo_otd(df, tipo_periodo)
    if base.empty:
        return pd.DataFrame(columns=["Periodo", "NO PRAZO", "FORA DO PRAZO", "Total", "OTD"])

    agrupado = (
        base.groupby(["Periodo", prazo_col])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    agrupado = garantir_colunas_status(agrupado)
    agrupado.columns.name = None
    agrupado["Total"] = agrupado["NO PRAZO"] + agrupado["FORA DO PRAZO"]
    agrupado["OTD"] = (agrupado["NO PRAZO"] / agrupado["Total"].replace(0, pd.NA)) * 100
    return agrupado.sort_values("Periodo")


def resumo_otd_detalhado(
    df: pd.DataFrame,
    *,
    tipo_ordem: str,
) -> pd.DataFrame:
    """Resume OTD base e OTD justificado usando a mesma base parametrizada.

    OTD considera dias extras e a correção opcional de baixa indevida.
    OTD Justificado parte desse OTD base e acrescenta as justificativas
    escolhidas no painel.
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "Grupo",
                "NO PRAZO",
                "FORA DO PRAZO",
                "Total geral",
                "Share",
                "OTD",
                "OTD Justificado",
            ]
        )

    resumo = (
        df.groupby(["Grupo", "Prazo Base Ajustado"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    resumo = garantir_colunas_status(resumo)
    resumo.columns.name = None
    resumo["Total geral"] = resumo["NO PRAZO"] + resumo["FORA DO PRAZO"]

    total_base = int(resumo["Total geral"].sum())
    resumo["Share"] = (
        resumo["Total geral"] / total_base * 100 if total_base else 0.0
    )
    resumo["OTD"] = (
        resumo["NO PRAZO"] / resumo["Total geral"].replace(0, pd.NA) * 100
    )

    justificado = (
        df.groupby("Grupo")["No Prazo Ajustado"]
        .sum()
        .reset_index(name="No Prazo Final")
    )
    resumo = resumo.merge(justificado, on="Grupo", how="left")
    resumo["OTD Justificado"] = (
        resumo["No Prazo Final"] / resumo["Total geral"].replace(0, pd.NA) * 100
    )

    # A tabela acompanha o seletor "Ordenar por" do painel.
    # Quantidade: maior Total geral primeiro.
    # Percentual: maior OTD primeiro, usando Total geral como desempate.
    # A linha Total geral é criada somente depois da ordenação para permanecer
    # fixa no final da tabela.
    if tipo_ordem == "Percentual":
        resumo = resumo.sort_values(
            ["OTD", "Total geral"],
            ascending=[False, False],
        )
    else:
        resumo = resumo.sort_values("Total geral", ascending=False)

    total = pd.DataFrame(
        {
            "Grupo": ["Total geral"],
            "NO PRAZO": [int(resumo["NO PRAZO"].sum())],
            "FORA DO PRAZO": [int(resumo["FORA DO PRAZO"].sum())],
            "Total geral": [int(resumo["Total geral"].sum())],
            "Share": [100.0 if total_base else 0.0],
            "No Prazo Final": [int(resumo["No Prazo Final"].sum())],
        }
    )
    total_den = total["Total geral"].replace(0, pd.NA)
    total["OTD"] = total["NO PRAZO"] / total_den * 100
    total["OTD Justificado"] = total["No Prazo Final"] / total_den * 100
    return pd.concat([resumo, total], ignore_index=True)


def formatar_resumo_otd_detalhado(df: pd.DataFrame, tipo_visao: str) -> pd.DataFrame:
    """Aplica os rótulos e formatos da tabela detalhada sob o gráfico principal."""
    resultado = df.copy()
    for coluna in ("Share", "OTD", "OTD Justificado"):
        resultado[coluna] = resultado[coluna].map(
            lambda valor: "-" if pd.isna(valor) else f"{valor:.2f}%"
        )

    primeira_coluna = "UF" if tipo_visao == "UF" else "Região"
    resultado = resultado.rename(
        columns={
            "Grupo": primeira_coluna,
            "NO PRAZO": "No prazo",
            "FORA DO PRAZO": "Fora do prazo",
        }
    )
    return resultado[
        [
            primeira_coluna,
            "No prazo",
            "Fora do prazo",
            "Total geral",
            "Share",
            "OTD",
            "OTD Justificado",
        ]
    ]


def normalizar_ocorrencia_atraso(serie: pd.Series) -> pd.Series:
    """Padroniza ocorrências vazias para a descrição usada nas tabelas de atraso."""
    resultado = serie.fillna("").astype(str).str.strip()
    mask = (
        resultado.eq("")
        | resultado.str.upper().eq("SEM OCORRENCIA")
        | resultado.str.upper().eq("NAN")
    )
    resultado = resultado.copy()
    resultado.loc[mask] = "Atraso sem ocorrência"
    return resultado


def _texto_ocorrencias(grupo: pd.DataFrame) -> str:
    ordenado = grupo.sort_values("Qtd", ascending=False)
    return ", ".join(
        f"{row['Ocorrencias']} ({row['Qtd']})"
        for _, row in ordenado.iterrows()
    )


def resumo_grupo_com_ocorrencias(
    df: pd.DataFrame,
    grupo_col: str,
    *,
    ordem_numerica: bool = False,
    nome_grupo_saida: str | None = None,
) -> pd.DataFrame:
    """Resume quantidade, percentual e composição de ocorrências por grupo."""
    if df.empty:
        return pd.DataFrame(
            columns=[nome_grupo_saida or grupo_col, "Ocorrências", "Quantidade", "Percentual (%)"]
        )

    base = df.copy()
    base["Ocorrencias"] = normalizar_ocorrencia_atraso(base["Ocorrencias"])

    ocorrencias = (
        base.groupby([grupo_col, "Ocorrencias"])
        .size()
        .reset_index(name="Qtd")
    )

    # Evita GroupBy.apply sobre as colunas de agrupamento, comportamento que
    # foi depreciado pelo pandas. A ordenação continua sendo por maior Qtd
    # dentro de cada grupo, exatamente como antes.
    ocorrencias = ocorrencias.sort_values(
        [grupo_col, "Qtd"],
        ascending=[True, False],
    )
    ocorrencias["_texto_ocorrencia"] = (
        ocorrencias["Ocorrencias"].astype(str)
        + " ("
        + ocorrencias["Qtd"].astype(str)
        + ")"
    )
    texto = (
        ocorrencias.groupby(grupo_col, sort=ordem_numerica)["_texto_ocorrencia"]
        .agg(", ".join)
        .reset_index(name="Ocorrências")
    )
    quantidades = base.groupby(grupo_col).size().reset_index(name="Quantidade")
    resultado = texto.merge(quantidades, on=grupo_col)

    total = int(resultado["Quantidade"].sum())
    resultado["Percentual (%)"] = (
        resultado["Quantidade"] / total * 100 if total else 0.0
    )

    if ordem_numerica:
        resultado = resultado.sort_values(grupo_col)
    else:
        resultado = resultado.sort_values("Quantidade", ascending=False)

    if nome_grupo_saida:
        resultado = resultado.rename(columns={grupo_col: nome_grupo_saida})
        grupo_saida = nome_grupo_saida
    else:
        grupo_saida = grupo_col

    linha_total = pd.DataFrame(
        {
            grupo_saida: ["Total"],
            "Ocorrências": [""],
            "Quantidade": [total],
            "Percentual (%)": [100.0 if total else 0.0],
        }
    )
    resultado["Percentual (%)"] = resultado["Percentual (%)"].round(2)
    return pd.concat([resultado, linha_total], ignore_index=True)


def resumo_faixas_atraso(df_atrasos: pd.DataFrame) -> pd.DataFrame:
    """Monta uma linha por dia de atraso, com ocorrências detalhadas."""
    if df_atrasos.empty:
        return pd.DataFrame(
            columns=["Faixa de atraso", "Ocorrências", "Quantidade", "Percentual (%)"]
        )

    base = df_atrasos.copy()
    base["Dias Atraso"] = base["Dias Atraso"].astype(int)

    resumo = resumo_grupo_com_ocorrencias(
        base,
        "Dias Atraso",
        ordem_numerica=True,
        nome_grupo_saida="Dias Atraso",
    )

    mask_total = resumo["Dias Atraso"].eq("Total")
    resumo.loc[~mask_total, "Faixa de atraso"] = resumo.loc[
        ~mask_total, "Dias Atraso"
    ].apply(faixa_atraso_por_dia)
    resumo.loc[mask_total, "Faixa de atraso"] = "Total"

    return resumo[
        ["Faixa de atraso", "Ocorrências", "Quantidade", "Percentual (%)"]
    ]


def resumo_ocorrencias_gerais(df_atrasos: pd.DataFrame) -> pd.DataFrame:
    """Resume as ocorrências dos atrasos sem transformar vazios em categorias."""
    base = df_atrasos[
        df_atrasos["Ocorrencias"].notna()
        & df_atrasos["Ocorrencias"].astype(str).str.strip().ne("")
    ].copy()
    if base.empty:
        return pd.DataFrame(columns=["Ocorrencias", "Quantidade", "Percentual (%)"])

    resumo = (
        base.groupby("Ocorrencias").size().reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    total = int(resumo["Quantidade"].sum())
    resumo["Percentual (%)"] = (resumo["Quantidade"] / total * 100).round(2)
    total_row = pd.DataFrame(
        {"Ocorrencias": ["Total"], "Quantidade": [total], "Percentual (%)": [100.0]}
    )
    return pd.concat([resumo, total_row], ignore_index=True)
