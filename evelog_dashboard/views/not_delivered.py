"""Aba de Pedidos Não Entregues."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import barras_com_rotulo
from ..ui import botao_exportar_excel


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
        st.altair_chart(
            barras_com_rotulo(
                status_counts,
                categoria="Status",
                valor="Quantidade",
                horizontal=True,
                titulo_categoria="Status",
                titulo_valor="Quantidade de pedidos",
            ),
            use_container_width=True,
        )

    st.subheader("Pedidos filtrados")
    st.caption(f"Total: {len(filtrado)}")
    st.dataframe(filtrado, use_container_width=True, hide_index=True)
    botao_exportar_excel(
        filtrado,
        nome_arquivo="base_nao_entregues.xlsx",
        usar_sidebar=False,
        key=_key("exportar"),
    )
