"""Fábrica de gráficos Plotly reutilizáveis do dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def barras_com_rotulo(
    df: pd.DataFrame,
    *,
    categoria: str,
    valor: str = "Quantidade",
    horizontal: bool = False,
    titulo_categoria: str | None = None,
    titulo_valor: str | None = None,
    ordenar=None,
    altura: int | None = None,
    cor: str | None = None,
):
    """Cria um gráfico Plotly de barras com rótulos e seleção por clique."""
    dados = df.copy()
    categorias = (
        list(ordenar)
        if ordenar is not None
        else dados[categoria].tolist()
    )

    marker = {"color": cor} if cor else None
    customdata = [
        [cat, val]
        for cat, val in zip(dados[categoria].tolist(), dados[valor].tolist())
    ]

    if horizontal:
        trace = go.Bar(
            x=dados[valor],
            y=dados[categoria],
            orientation="h",
            text=dados[valor],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            customdata=customdata,
            marker=marker,
            hovertemplate=(
                f"{titulo_categoria or categoria}: %{{y}}<br>"
                f"{titulo_valor or valor}: %{{x:,.0f}}<extra></extra>"
            ),
        )
        fig = go.Figure(trace)
        fig.update_yaxes(
            title=titulo_categoria,
            categoryorder="array",
            categoryarray=categorias,
            autorange="reversed",
        )
        max_valor = pd.to_numeric(dados[valor], errors="coerce").fillna(0).max()
        eixo_valor = {
            "title": titulo_valor,
            "rangemode": "tozero",
            "tickformat": ",.0f",
        }
        if max_valor <= 10:
            eixo_valor["dtick"] = 1
        fig.update_xaxes(**eixo_valor)
    else:
        trace = go.Bar(
            x=dados[categoria],
            y=dados[valor],
            text=dados[valor],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            customdata=customdata,
            marker=marker,
            hovertemplate=(
                f"{titulo_categoria or categoria}: %{{x}}<br>"
                f"{titulo_valor or valor}: %{{y:,.0f}}<extra></extra>"
            ),
        )
        fig = go.Figure(trace)
        fig.update_xaxes(
            title=titulo_categoria,
            type="category",
            categoryorder="array",
            categoryarray=categorias,
        )
        max_valor = pd.to_numeric(dados[valor], errors="coerce").fillna(0).max()
        eixo_valor = {
            "title": titulo_valor,
            "rangemode": "tozero",
            "tickformat": ",.0f",
        }
        if max_valor <= 10:
            eixo_valor["dtick"] = 1
        fig.update_yaxes(**eixo_valor)

    fig.update_layout(
        clickmode="event+select",
        showlegend=False,
        margin=dict(t=20, r=30, b=40, l=40),
    )
    if altura:
        fig.update_layout(height=altura)
    return fig


def grafico_otd_empilhado(df: pd.DataFrame):
    """Cria o gráfico principal de OTD por grupo, 100% empilhado."""
    fig = go.Figure()

    fig.add_bar(
        name="No prazo",
        x=df["Grupo"],
        y=df["Percentual No Prazo"],
        marker_color="#2ca02c",
        text=df["Percentual No Prazo"],
        texttemplate="%{text:.0f}%",
        textposition="inside",
        customdata=[
            ["NO PRAZO", int(qtd)] for qtd in df["NO PRAZO"].fillna(0)
        ],
        hovertemplate=(
            "Grupo: %{x}<br>No prazo<br>Percentual: %{y:.1f}%<br>"
            "Qtd: %{customdata[1]:,.0f}<extra></extra>"
        ),
    )
    fig.add_bar(
        name="Fora do prazo",
        x=df["Grupo"],
        y=df["Percentual Atrasado"],
        marker_color="#d62728",
        text=df["Percentual Atrasado"],
        texttemplate="%{text:.0f}%",
        textposition="inside",
        customdata=[
            ["FORA DO PRAZO", int(qtd)] for qtd in df["FORA DO PRAZO"].fillna(0)
        ],
        hovertemplate=(
            "Grupo: %{x}<br>Fora do prazo<br>Percentual: %{y:.1f}%<br>"
            "Qtd: %{customdata[1]:,.0f}<extra></extra>"
        ),
    )

    # Total no topo via annotation, para não criar uma terceira série selecionável.
    for _, row in df.iterrows():
        fig.add_annotation(
            x=row["Grupo"],
            y=102,
            text=f"{int(row['Total'])}",
            showarrow=False,
            yanchor="bottom",
        )

    fig.update_layout(
        barmode="stack",
        clickmode="event+select",
        yaxis=dict(range=[0, 110], ticksuffix="%", title="Percentual (%)"),
        xaxis=dict(title="Grupo", type="category"),
        legend_title_text="",
        margin=dict(t=35, r=20, b=40, l=40),
    )
    return fig


def grafico_evolucao_otd(df: pd.DataFrame):
    """Cria a linha de evolução do OTD com seleção por ponto."""
    fig = go.Figure()
    fig.add_scatter(
        x=df["Periodo"],
        y=df["OTD"],
        mode="lines+markers",
        name="OTD",
        customdata=[
            [str(periodo), int(total)]
            for periodo, total in zip(df["Periodo"], df["Total"])
        ],
        hovertemplate=(
            "Período: %{x}<br>OTD: %{y:.1f}%<br>"
            "Pedidos: %{customdata[1]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(
        clickmode="event+select",
        yaxis=dict(ticksuffix="%", title="OTD (%)"),
        xaxis_title="",
        showlegend=False,
        margin=dict(t=20, r=20, b=40, l=40),
    )
    return fig
