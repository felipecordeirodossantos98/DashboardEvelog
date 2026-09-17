"""Aba de Pedidos Entregues / Performance OTD."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import (
    barras_com_rotulo,
    grafico_evolucao_otd,
    grafico_otd_empilhado,
    grafico_otd_pizza,
)
from ..config import COLUNAS_EXPORT_ATRASOS
from ..data import (
    adicionar_grupo_geografico,
    faixa_atraso_por_dia,
    filtrar_periodo_datas,
    preparar_atrasos_entregues,
    preparar_entregues,
)
from ..summaries import (
    evolucao_otd,
    formatar_resumo_otd_detalhado,
    preparar_otd_detalhado,
    resumo_faixas_atraso,
    resumo_grupo_com_ocorrencias,
    resumo_ocorrencias_gerais,
    resumo_otd_pizza,
    resumo_otd_por_grupo,
)
from ..ui import (
    botao_exportar_excel,
    renderizar_imagens_complementares,
)


_PREFIX = "entregues_"


def _key(nome: str) -> str:
    return f"{_PREFIX}{nome}"


def _render_resumo_principal(
    df: pd.DataFrame,
    *,
    tipo_ordem: str,
    tipo_visao: str,
) -> None:
    base = adicionar_grupo_geografico(df, tipo_visao)
    resumo = resumo_otd_por_grupo(base, tipo_ordem)

    if resumo.empty:
        st.info("Não há dados de UF/Região para montar o gráfico de OTD.")
        return

    st.plotly_chart(
        grafico_otd_empilhado(resumo),
        use_container_width=True,
        key=_key("grafico_principal"),
    )


def _render_pizzas(df: pd.DataFrame) -> None:
    original = resumo_otd_pizza(df, justificado=False)
    justificado = resumo_otd_pizza(df, justificado=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### OTD Original")
        st.plotly_chart(
            grafico_otd_pizza(original),
            use_container_width=True,
            key=_key("grafico_pizza_original"),
        )
    with col2:
        st.markdown("##### OTD Justificado")
        st.plotly_chart(
            grafico_otd_pizza(justificado),
            use_container_width=True,
            key=_key("grafico_pizza_justificado"),
        )


def _render_evolucao(df: pd.DataFrame) -> None:
    st.subheader("Evolução do OTD")
    tipo_periodo = st.radio(
        "Período",
        ["Diário", "Semanal", "Mensal"],
        horizontal=True,
        key=_key("periodicidade"),
    )
    evolucao = evolucao_otd(df, tipo_periodo)
    if evolucao.empty:
        st.info("Não há dados suficientes para a evolução do OTD.")
        return

    st.plotly_chart(
        grafico_evolucao_otd(evolucao),
        use_container_width=True,
        key=_key("grafico_evolucao"),
    )


def _render_analise_atrasos(df_entregues: pd.DataFrame) -> None:
    atrasos = preparar_atrasos_entregues(df_entregues)

    distribuicao = (
        atrasos.groupby("Dias Atraso")
        .size()
        .reset_index(name="Pedidos")
        .sort_values("Dias Atraso")
    )

    if distribuicao.empty:
        st.info("Não há atrasos na base.")
    else:
        st.subheader("Distribuição de atrasos (dias)")
        st.caption(f"Total de pedidos em atraso: {int(distribuicao['Pedidos'].sum())}")
        distribuicao["Dias_str"] = distribuicao["Dias Atraso"].astype(int).astype(str)
        ordem = distribuicao["Dias_str"].tolist()
        st.altair_chart(
            barras_com_rotulo(
                distribuicao,
                categoria="Dias_str",
                valor="Pedidos",
                titulo_categoria="Dias de atraso",
                titulo_valor="Quantidade",
                ordenar=ordem,
                altura=400,
                cor="#6baed6",
            ),
            use_container_width=True,
        )

    # Tabela detalhada: uma linha por dia de atraso.
    if atrasos.empty:
        st.info("Não há atrasos para montar as faixas.")
    else:
        st.subheader("Faixas de atraso e ocorrências")
        st.dataframe(
            resumo_faixas_atraso(atrasos),
            use_container_width=True,
            hide_index=True,
        )

    resumo_oc = resumo_ocorrencias_gerais(atrasos)
    if resumo_oc.empty:
        st.info("Não há ocorrências na base.")
    else:
        st.subheader("Ocorrências")
        st.dataframe(resumo_oc, use_container_width=True, hide_index=True)

    unidades_base = atrasos[atrasos["Destino"].notna()].copy()
    if unidades_base.empty:
        st.info("Não há unidades ofensoras base.")
    else:
        st.subheader("Unidades ofensores")
        unidades = resumo_grupo_com_ocorrencias(
            unidades_base,
            "Destino",
            nome_grupo_saida="Unidade",
        )
        st.dataframe(unidades, use_container_width=True, hide_index=True)

    exportacao = atrasos.copy()
    if not exportacao.empty:
        exportacao["Dias Atraso"] = exportacao["Dias Atraso"].astype(int)
        exportacao["Faixa Atraso"] = exportacao["Dias Atraso"].apply(faixa_atraso_por_dia)

    colunas = [col for col in COLUNAS_EXPORT_ATRASOS if col in exportacao.columns]
    exportacao = exportacao[colunas]
    botao_exportar_excel(
        exportacao,
        nome_arquivo="base_atrasos.xlsx",
        usar_sidebar=False,
        key=_key("exportar_atrasos"),
    )


def _render_otd_detalhado(
    df: pd.DataFrame,
    *,
    tipo_visao: str,
    tipo_ordem: str,
) -> None:
    st.subheader("Performance OTD – Visão Detalhada")

    col5, col6, _, col7 = st.columns([1, 1, 1, 1])
    with col5:
        usar_justificados = st.checkbox(
            "Atrasos justificados",
            value=True,
            key=_key("usar_justificados"),
        )
    with col6:
        usar_baixa_indevida = st.checkbox(
            "Baixas indevidas",
            value=False,
            key=_key("usar_baixa_indevida"),
        )
    with col7:
        dias_extra = st.number_input(
            "Dias extras",
            min_value=0,
            max_value=10,
            value=0,
            key=_key("dias_extra"),
        )

    base_valida = df.dropna(subset=["Dt Evento", "Previsao"]).copy()
    if base_valida.empty:
        st.info("Não há datas válidas para calcular a visão detalhada do OTD.")
        renderizar_imagens_complementares()
        return

    resumo, _ = preparar_otd_detalhado(
        base_valida,
        tipo_visao=tipo_visao,
        tipo_ordem=tipo_ordem,
        dias_extra=int(dias_extra),
        usar_justificados=usar_justificados,
        usar_baixa_indevida=usar_baixa_indevida,
    )
    st.dataframe(
        formatar_resumo_otd_detalhado(resumo, tipo_visao),
        use_container_width=True,
        hide_index=True,
    )
    renderizar_imagens_complementares()


def render(df_entregues: pd.DataFrame) -> None:
    """Renderiza toda a aba de pedidos entregues."""
    if df_entregues.empty:
        st.info("Não há pedidos entregues na base.")
        return

    st.header("Performance OTD")
    st.caption(f"Total de pedidos entregues: {len(df_entregues)}")

    base = preparar_entregues(df_entregues)
    datas_validas = base["Dt Evento"].dropna()
    if datas_validas.empty:
        st.warning("A base de entregues não possui datas de evento válidas.")
        return

    min_data = datas_validas.min().date()
    max_data = datas_validas.max().date()

    col_data, col_ordem, col_visao, col_total = st.columns(4)
    with col_data:
        data_evento = st.date_input(
            "Período de entrega",
            value=(min_data, max_data),
            min_value=min_data,
            max_value=max_data,
            key=_key("periodo_entrega"),
        )
    with col_ordem:
        tipo_ordem = st.radio(
            "Ordenar por",
            ["Quantidade", "Percentual"],
            horizontal=True,
            key=_key("tipo_ordem"),
        )
    with col_visao:
        tipo_visao = st.radio(
            "Visualização",
            ["UF", "Região"],
            horizontal=True,
            key=_key("tipo_visao"),
        )

    filtrado = base
    if isinstance(data_evento, tuple) and len(data_evento) == 2:
        filtrado = filtrar_periodo_datas(
            base,
            "Dt Evento",
            data_evento[0],
            data_evento[1],
            incluir_dia_final=True,
        )

    with col_total:
        st.metric("Total de pedidos entregues", len(filtrado))

    if filtrado.empty:
        st.info("Não há pedidos entregues no período selecionado.")
        return

    _render_resumo_principal(
        filtrado,
        tipo_ordem=tipo_ordem,
        tipo_visao=tipo_visao,
    )
    _render_pizzas(filtrado)
    _render_evolucao(filtrado)
    _render_analise_atrasos(filtrado)
    _render_otd_detalhado(
        filtrado,
        tipo_visao=tipo_visao,
        tipo_ordem=tipo_ordem,
    )
