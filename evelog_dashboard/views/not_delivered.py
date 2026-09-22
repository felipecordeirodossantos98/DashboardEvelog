"""Aba de Pedidos Não Entregues."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import barras_com_rotulo
from ..ui import (
    botao_exportar_excel,
    extrair_primeiro_ponto_selecionado,
    nome_seguro_arquivo,
    renderizar_download_selecao,
    renderizar_plotly_selecionavel,
)


_PREFIX = "nao_entregues_"


def _key(nome: str) -> str:
    return f"{_PREFIX}{nome}"


def render(df_encerrados: pd.DataFrame) -> None:
    """Renderiza a aba de pedidos não entregues."""
    if df_encerrados.empty:
        st.info("Não há pedidos não entregues na base.")
        return

    base = df_encerrados.copy()
    base["Status_plot"] = base["Status"]
    base.loc[base["Status"].eq("CUSTODIA"), "Status_plot"] = base["Ocorrencias"]

    status_opcoes = sorted(base["Status_plot"].dropna().unique())

    st.header("Pedidos Não Entregues")
    st.caption(f"Total de pedidos não entregues: {len(df_encerrados)}")

    col_form, _, col_metric = st.columns([1, 2, 1])
    with col_form:
        status_selecionados = st.multiselect(
            "Status",
            options=status_opcoes,
            key=_key("status"),
        )

    filtrado = (
        base[base["Status_plot"].isin(status_selecionados)].copy()
        if status_selecionados
        else base.copy()
    )

    with col_metric:
        st.metric(
            "Total de pedidos",
            f"{len(df_encerrados):,}".replace(",", "."),
        )

    status_counts = filtrado["Status_plot"].value_counts().reset_index()
    status_counts.columns = ["Status", "Quantidade"]

    if not status_counts.empty:
        st.subheader("Status")
        evento = renderizar_plotly_selecionavel(
            barras_com_rotulo(
                status_counts,
                categoria="Status",
                valor="Quantidade",
                horizontal=True,
                titulo_categoria="Status",
                titulo_valor="Quantidade de pedidos",
            ),
            key=_key("grafico_status"),
        )
        ponto = extrair_primeiro_ponto_selecionado(evento)
        if ponto and ponto.get("y") is not None:
            status_clicado = str(ponto["y"])
            base_selecionada = filtrado[
                filtrado["Status_plot"].astype(str).eq(status_clicado)
            ].copy()
            renderizar_download_selecao(
                base_selecionada,
                descricao=f"Status: {status_clicado}",
                nome_arquivo=(
                    f"base_nao_entregues_{nome_seguro_arquivo(status_clicado)}.xlsx"
                ),
                key=_key("download_status"),
            )

    st.subheader("Pedidos filtrados")
    st.caption(f"Total: {len(filtrado)}")
    st.dataframe(filtrado, width="stretch", hide_index=True)
    botao_exportar_excel(
        filtrado,
        nome_arquivo="base_nao_entregues.xlsx",
        usar_sidebar=False,
        key=_key("exportar"),
    )
