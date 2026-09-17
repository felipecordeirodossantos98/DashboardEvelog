"""Fábrica de gráficos reutilizáveis do dashboard."""

from __future__ import annotations

import altair as alt
import pandas as pd
import plotly.express as px


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
    """Cria um gráfico Altair de barras com o valor escrito junto à barra."""
    if horizontal:
        base = alt.Chart(df).encode(
            y=alt.Y(
                f"{categoria}:N",
                sort=ordenar if ordenar is not None else "-x",
                title=titulo_categoria,
            ),
            x=alt.X(
                f"{valor}:Q",
                title=titulo_valor,
                axis=alt.Axis(tickMinStep=1),
            ),
        )
        mark_kwargs = {"color": cor} if cor else {}
        barras = base.mark_bar(**mark_kwargs)
        texto = base.mark_text(
            align="left",
            dx=6,
            color="white",
        ).encode(text=alt.Text(f"{valor}:Q", format=",.0f"))
    else:
        base = alt.Chart(df).encode(
            x=alt.X(
                f"{categoria}:N",
                sort=ordenar,
                title=titulo_categoria,
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                f"{valor}:Q",
                title=titulo_valor,
                axis=alt.Axis(tickMinStep=1),
            ),
        )
        mark_kwargs = {"color": cor} if cor else {}
        barras = base.mark_bar(**mark_kwargs)
        texto = base.mark_text(dy=-8, color="white").encode(
            text=alt.Text(f"{valor}:Q", format=",.0f")
        )

    grafico = barras + texto
    if altura:
        grafico = grafico.properties(height=altura)
    return grafico


def grafico_otd_empilhado(df: pd.DataFrame):
    """Cria o gráfico principal de OTD por grupo."""
    fig = px.bar(
        df,
        x="Grupo",
        y=["Percentual No Prazo", "Percentual Atrasado"],
        labels={"value": "Percentual (%)", "variable": ""},
        color_discrete_map={
            "Percentual No Prazo": "#2ca02c",
            "Percentual Atrasado": "#d62728",
        },
    )

    if len(fig.data) >= 2:
        fig.data[0].customdata = df["NO PRAZO"]
        fig.data[1].customdata = df["FORA DO PRAZO"]
        fig.data[0].hovertemplate = (
            "Grupo: %{x}<br>No prazo<br>Percentual: %{y:.1f}%<br>"
            "Qtd: %{customdata}<extra></extra>"
        )
        fig.data[1].hovertemplate = (
            "Grupo: %{x}<br>Fora do prazo<br>Percentual: %{y:.1f}%<br>"
            "Qtd: %{customdata}<extra></extra>"
        )

    fig.update_traces(texttemplate="%{y:.0f}%", textposition="inside", textangle=0)
    fig.add_scatter(
        x=df["Grupo"],
        y=[100] * len(df),
        mode="text",
        text=df["Total"],
        textposition="top center",
        showlegend=False,
        hoverinfo="skip",
    )
    fig.update_layout(
        barmode="stack",
        yaxis=dict(range=[0, 110], ticksuffix="%"),
        legend_title_text="",
    )
    return fig


def grafico_otd_pizza(df: pd.DataFrame):
    """Cria o gráfico de rosca de OTD."""
    return px.pie(df, names="Status", values="Quantidade", hole=0.4)


def grafico_evolucao_otd(df: pd.DataFrame):
    """Cria a linha de evolução do OTD."""
    fig = px.line(df, x="Periodo", y="OTD", markers=True)
    fig.update_traces(
        hovertemplate=(
            "Período: %{x}<br>OTD: %{y:.1f}%<br>"
            "Pedidos: %{customdata}<extra></extra>"
        ),
        customdata=df["Total"],
    )
    fig.update_layout(
        yaxis=dict(ticksuffix="%"),
        xaxis_title="",
        yaxis_title="OTD (%)",
    )
    return fig
