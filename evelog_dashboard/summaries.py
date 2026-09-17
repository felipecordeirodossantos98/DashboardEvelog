"""Agregações reutilizáveis usadas nas tabelas e gráficos."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from .config import OCORRENCIAS_JUSTIFICADAS
from .data import faixa_atraso_por_dia


def garantir_colunas_status(df: pd.DataFrame) -> pd.DataFrame:
    """Garante as duas colunas de prazo esperadas após um unstack."""
    resultado = df.copy()
    for coluna in ("NO PRAZO", "FORA DO PRAZO"):
        if coluna not in resultado.columns:
            resultado[coluna] = 0
    return resultado


def resumo_otd_por_grupo(df: pd.DataFrame, tipo_ordem: str) -> pd.DataFrame:
    """Cria o resumo usado no gráfico principal de OTD."""
    agrupado = (
        df.groupby(["Grupo", "Prazo"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    agrupado = garantir_colunas_status(agrupado)
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


def resumo_otd_pizza(df: pd.DataFrame, justificado: bool = False) -> pd.DataFrame:
    """Retorna as duas fatias usadas nos gráficos de OTD."""
    if justificado:
        ocorrencias = (
            df["Ocorrencias"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )
        padrao = "|".join(oc.replace(".", r"\.") for oc in OCORRENCIAS_JUSTIFICADAS)
        cond_justificado = (
            df["Prazo"].eq("FORA DO PRAZO")
            & ocorrencias.str.contains(padrao, regex=True)
        )
        no_prazo = (df["Prazo"].eq("NO PRAZO") | cond_justificado).sum()
    else:
        no_prazo = df["Prazo"].eq("NO PRAZO").sum()

    fora_prazo = len(df) - int(no_prazo)
    return pd.DataFrame(
        {
            "Status": ["No Prazo", "Fora do Prazo"],
            "Quantidade": [int(no_prazo), int(fora_prazo)],
        }
    )


def evolucao_otd(df: pd.DataFrame, tipo_periodo: str) -> pd.DataFrame:
    """Agrupa OTD por dia, semana ou mês."""
    base = df[df["Dt Evento"].notna()].copy()
    if base.empty:
        return pd.DataFrame(columns=["Periodo", "NO PRAZO", "FORA DO PRAZO", "Total", "OTD"])

    if tipo_periodo == "Diário":
        base["Periodo"] = base["Dt Evento"].dt.date
    elif tipo_periodo == "Semanal":
        base["Periodo"] = base["Dt Evento"].dt.to_period("W").apply(lambda r: r.start_time)
    else:
        base["Periodo"] = base["Dt Evento"].dt.to_period("M").apply(lambda r: r.start_time)

    agrupado = (
        base.groupby(["Periodo", "Prazo"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    agrupado = garantir_colunas_status(agrupado)
    agrupado["Total"] = agrupado["NO PRAZO"] + agrupado["FORA DO PRAZO"]
    agrupado["OTD"] = (agrupado["NO PRAZO"] / agrupado["Total"].replace(0, pd.NA)) * 100
    return agrupado.sort_values("Periodo")


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
    """Resume quantidade, percentual e composição de ocorrências por grupo.

    É a mesma regra usada tanto em "Faixas de atraso" quanto em
    "Unidades ofensoras", eliminando duas implementações quase idênticas.
    """
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
    texto = (
        ocorrencias.groupby(grupo_col, sort=ordem_numerica)
        .apply(_texto_ocorrencias)
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


def preparar_otd_detalhado(
    df: pd.DataFrame,
    *,
    tipo_visao: str,
    tipo_ordem: str,
    dias_extra: int,
    usar_justificados: bool,
    usar_baixa_indevida: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula a visão detalhada do OTD e devolve resumo + base calculada."""
    base = df.copy()
    base["Ocorrencias"] = base["Ocorrencias"].astype(str).str.strip()
    base["Previsao Ajustada"] = base["Previsao"] + pd.to_timedelta(dias_extra, unit="D")
    base["Dias Atraso"] = (
        base["Dt Evento"].dt.normalize() - base["Previsao Ajustada"].dt.normalize()
    ).dt.days
    base["Prazo Ajustado"] = base["Dias Atraso"].apply(
        lambda valor: "NO PRAZO" if valor <= 0 else "FORA DO PRAZO"
    )

    cond_justificado = (
        base["Prazo Ajustado"].eq("FORA DO PRAZO")
        & base["Ocorrencias"].apply(
            lambda texto: any(oc in texto for oc in OCORRENCIAS_JUSTIFICADAS)
        )
    )
    cond_baixa_indevida = (
        base["Prazo Ajustado"].eq("FORA DO PRAZO")
        & base["Dias Atraso"].eq(1)
        & base["Ocorrencias"].eq("SEM OCORRENCIA")
    )

    base["Justificado"] = False
    if usar_justificados:
        base.loc[cond_justificado, "Justificado"] = True
    if usar_baixa_indevida:
        base.loc[cond_baixa_indevida, "Justificado"] = True

    base["No Prazo Ajustado"] = (
        base["Prazo Ajustado"].eq("NO PRAZO") | base["Justificado"]
    ).astype(int)

    if tipo_visao == "Região":
        from .config import MAPA_REGIAO
        base["Grupo"] = base["UF"].map(MAPA_REGIAO)
    else:
        base["Grupo"] = base["UF"]

    resumo = (
        base.groupby(["Grupo", "Prazo Ajustado"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    resumo = garantir_colunas_status(resumo)
    resumo["Total geral"] = resumo["NO PRAZO"] + resumo["FORA DO PRAZO"]
    total_base = resumo["Total geral"].sum()
    resumo["Share"] = resumo["Total geral"] / total_base * 100 if total_base else 0.0
    resumo["OTD"] = resumo["NO PRAZO"] / resumo["Total geral"].replace(0, pd.NA) * 100

    justificados = (
        base.groupby("Grupo")["No Prazo Ajustado"].sum().reset_index()
    )
    resumo = resumo.merge(justificados, on="Grupo", how="left")
    resumo["OTD Justificado"] = (
        resumo["No Prazo Ajustado"] / resumo["Total geral"].replace(0, pd.NA) * 100
    )

    if tipo_ordem == "Percentual":
        resumo = resumo.sort_values(["OTD", "Total geral"], ascending=[False, False])
    else:
        resumo = resumo.sort_values("Total geral", ascending=False)

    total = pd.DataFrame(
        {
            "Grupo": ["Total geral"],
            "NO PRAZO": [resumo["NO PRAZO"].sum()],
            "FORA DO PRAZO": [resumo["FORA DO PRAZO"].sum()],
            "No Prazo Ajustado": [resumo["No Prazo Ajustado"].sum()],
        }
    )
    total["Total geral"] = total["NO PRAZO"] + total["FORA DO PRAZO"]
    total["Share"] = 100.0
    total_den = total["Total geral"].replace(0, pd.NA)
    total["OTD"] = total["NO PRAZO"] / total_den * 100
    total["OTD Justificado"] = total["No Prazo Ajustado"] / total_den * 100

    resumo = pd.concat([resumo, total], ignore_index=True)
    return resumo, base


def formatar_resumo_otd_detalhado(df: pd.DataFrame, tipo_visao: str) -> pd.DataFrame:
    """Aplica os rótulos e formatos usados na tabela de OTD detalhado."""
    resultado = df.copy()
    for coluna in ("Share", "OTD", "OTD Justificado"):
        resultado[coluna] = resultado[coluna].map("{:.2f}%".format)

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
