"""Aba de Pedidos Entregues / Performance OTD."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import (
    barras_com_rotulo,
    grafico_evolucao_otd,
    grafico_otd_empilhado,
)
from ..config import (
    COLUNAS_EXPORT_ATRASOS,
    OCORRENCIAS_JUSTIFICADAS,
)
from ..data import (
    adicionar_grupo_geografico,
    faixa_atraso_por_dia,
    filtrar_periodo_datas,
    preparar_atrasos_entregues,
    preparar_entregues,
)
from ..summaries import (
    adicionar_periodo_otd,
    aplicar_regras_otd,
    evolucao_otd,
    formatar_resumo_otd_detalhado,
    resumo_faixas_atraso,
    resumo_grupo_com_ocorrencias,
    resumo_ocorrencias_gerais,
    resumo_otd_detalhado,
    resumo_otd_por_grupo,
)
from ..ui import (
    botao_exportar_excel,
    extrair_primeiro_ponto_selecionado,
    nome_seguro_arquivo,
    renderizar_download_selecao,
    renderizar_imagens_complementares,
    renderizar_plotly_selecionavel,
)


_PREFIX = "entregues_"


def _key(nome: str) -> str:
    return f"{_PREFIX}{nome}"


def _opcoes_justificativas(base: pd.DataFrame) -> list[str]:
    """Lista ocorrências atrasadas disponíveis para uso como justificativa."""
    if base.empty or "Ocorrencias" not in base.columns:
        return []

    atrasados = base[base["Prazo Base Ajustado"].eq("FORA DO PRAZO")]
    ocorrencias = (
        atrasados["Ocorrencias"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    return sorted(
        valor
        for valor in ocorrencias.unique().tolist()
        if valor and valor.upper() != "NAN"
    )


def _render_resumo_principal(
    df: pd.DataFrame,
    *,
    tipo_ordem: str,
    tipo_visao: str,
) -> None:
    """Renderiza gráfico principal e a visão detalhada correspondente."""
    base = adicionar_grupo_geografico(df, tipo_visao)
    resumo = resumo_otd_por_grupo(
        base,
        tipo_ordem,
        prazo_col="Prazo Ajustado",
    )

    if resumo.empty:
        st.info("Não há dados de UF/Região para montar o gráfico de OTD.")
        return

    evento = renderizar_plotly_selecionavel(
        grafico_otd_empilhado(resumo),
        key=_key("grafico_principal"),
    )

    detalhado = resumo_otd_detalhado(base, tipo_ordem=tipo_ordem)
    with st.expander("Detalhes"):
        st.subheader("OTD — Visão Detalhada")
        st.dataframe(
            formatar_resumo_otd_detalhado(detalhado, tipo_visao),
            width="stretch",
            hide_index=True,
        )

        st.subheader("OTD — Visão diária, semanal e mensal")
        _render_evolucao_conteudo(df)

    ponto = extrair_primeiro_ponto_selecionado(evento)
    if ponto:
        grupo = ponto.get("x")
        curva = ponto.get("curve_number")
        customdata = ponto.get("customdata")
        prazo_custom = (
            customdata[0]
            if isinstance(customdata, (list, tuple)) and customdata
            else None
        )
        if grupo is not None and (curva in (0, 1) or prazo_custom in ("NO PRAZO", "FORA DO PRAZO")):
            prazo = prazo_custom or ("NO PRAZO" if curva == 0 else "FORA DO PRAZO")
            rotulo_prazo = "No prazo" if prazo == "NO PRAZO" else "Fora do prazo"
            selecionada = base.copy()
            if str(grupo) != "Total":
                selecionada = selecionada[selecionada["Grupo"].astype(str).eq(str(grupo))]
            selecionada = selecionada[selecionada["Prazo Ajustado"].eq(prazo)].copy()

            renderizar_download_selecao(
                selecionada,
                descricao=f"{tipo_visao}: {grupo} · {rotulo_prazo}",
                nome_arquivo=(
                    f"base_otd_{nome_seguro_arquivo(grupo)}_"
                    f"{nome_seguro_arquivo(rotulo_prazo)}.xlsx"
                ),
                key=_key("download_grafico_principal"),
            )


def _render_evolucao_conteudo(df: pd.DataFrame) -> None:
    """Renderiza a evolução temporal e o drill-down por período dentro da visão detalhada."""
    tipo_periodo = st.radio(
        "Período",
        ["Diário", "Semanal", "Mensal"],
        horizontal=True,
        key=_key("periodicidade"),
    )
    evolucao = evolucao_otd(
        df,
        tipo_periodo,
        prazo_col="Prazo Ajustado",
    )
    if evolucao.empty:
        st.info("Não há dados suficientes para a evolução do OTD.")
        return

    evento = renderizar_plotly_selecionavel(
        grafico_evolucao_otd(evolucao),
        key=_key("grafico_evolucao"),
    )

    ponto = extrair_primeiro_ponto_selecionado(evento)
    if not ponto or ponto.get("x") is None:
        return

    periodo_clicado = pd.to_datetime(ponto["x"], errors="coerce")
    if pd.isna(periodo_clicado):
        return

    base_periodos = adicionar_periodo_otd(df, tipo_periodo)
    periodo_serie = pd.to_datetime(base_periodos["Periodo"], errors="coerce")
    selecionada = base_periodos[periodo_serie.eq(periodo_clicado)].copy()
    selecionada = selecionada.drop(columns=["Periodo"], errors="ignore")

    renderizar_download_selecao(
        selecionada,
        descricao=(
            f"{tipo_periodo}: {periodo_clicado.strftime('%d/%m/%Y')}"
        ),
        nome_arquivo=(
            f"base_otd_{nome_seguro_arquivo(tipo_periodo)}_"
            f"{periodo_clicado.strftime('%Y-%m-%d')}.xlsx"
        ),
        key=_key("download_evolucao"),
    )


def _render_analise_atrasos(df_entregues: pd.DataFrame) -> None:
    """Renderiza somente os atrasos que restaram após todas as regras ativas."""
    atrasos = preparar_atrasos_entregues(
        df_entregues,
        prazo_col="Prazo Ajustado",
    )

    distribuicao = (
        atrasos.groupby("Dias Atraso")
        .size()
        .reset_index(name="Pedidos")
        .sort_values("Dias Atraso")
    )

    if distribuicao.empty:
        st.info("Não há atrasos na base com as regras selecionadas.")
    else:
        st.subheader("Distribuição de atrasos (dias)")
        st.caption(f"Total de pedidos em atraso: {int(distribuicao['Pedidos'].sum())}")
        distribuicao["Dias_str"] = distribuicao["Dias Atraso"].astype(int).astype(str)
        ordem = distribuicao["Dias_str"].tolist()
        evento = renderizar_plotly_selecionavel(
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
            key=_key("grafico_distribuicao_atrasos"),
        )
        ponto = extrair_primeiro_ponto_selecionado(evento)
        if ponto and ponto.get("x") is not None:
            dia = pd.to_numeric(pd.Series([ponto["x"]]), errors="coerce").iloc[0]
            if pd.notna(dia):
                dia_int = int(dia)
                selecionada = atrasos[
                    atrasos["Dias Atraso"].astype(int).eq(dia_int)
                ].copy()
                renderizar_download_selecao(
                    selecionada,
                    descricao=f"{dia_int} dia(s) de atraso",
                    nome_arquivo=f"base_atrasos_{dia_int}_dias.xlsx",
                    key=_key("download_distribuicao_atrasos"),
                )

    resumo_oc = resumo_ocorrencias_gerais(atrasos)
    if resumo_oc.empty:
        st.info("Não há ocorrências na base.")
    else:
        st.subheader("Ocorrências")
        st.dataframe(resumo_oc, width="stretch", hide_index=True)

    if atrasos.empty:
        st.info("Não há atrasos para montar as faixas.")
    else:
        st.subheader("Faixas de atraso e ocorrências")
        st.dataframe(
            resumo_faixas_atraso(atrasos),
            width="stretch",
            hide_index=True,
        )

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
        st.dataframe(unidades, width="stretch", hide_index=True)

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

    # ------------------------------------------------------------------
    # PAINEL PRINCIPAL DE REGRAS
    # Tudo abaixo deste bloco usa a mesma base parametrizada.
    # ------------------------------------------------------------------
    col_data, col_ordem, col_visao, _, col_total = st.columns(
        [1.45, 1.25, 1.05, 0.95, 0.9]
    )

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

    # Segunda linha: mantém os controles de regra agrupados. A coluna de
    # justificativas usa a mesma largura do campo de período da primeira linha.
    # Mantém o campo "Dias extras" alinhado horizontalmente com
    # "Visualização" da linha acima. As duas primeiras larguras repetem
    # Período de entrega + Ordenar por.
    col_justificativas, col_baixa, col_dias, _ = st.columns(
        [1.45, 1.25, 0.55, 2.35]
    )

    with col_baixa:
        usar_baixa_indevida = st.checkbox(
            "Baixas indevidas",
            value=False,
            key=_key("baixas_indevidas"),
        )

    with col_dias:
        dias_extra = st.number_input(
            "Dias extras",
            min_value=0,
            max_value=30,
            value=0,
            step=1,
            key=_key("dias_extra"),
        )

    # Calcula o OTD base com dias extras + baixa indevida para descobrir quais
    # ocorrências ainda estão atrasadas e podem ser usadas como justificativa.
    base_sem_justificativas = aplicar_regras_otd(
        filtrado,
        dias_extra=int(dias_extra),
        justificativas=(),
        usar_baixa_indevida=usar_baixa_indevida,
    )
    opcoes_justificativas = _opcoes_justificativas(base_sem_justificativas)
    padrao_justificativas = [
        ocorrencia
        for ocorrencia in OCORRENCIAS_JUSTIFICADAS
        if ocorrencia in opcoes_justificativas
    ]

    key_justificativas = _key("justificativas")
    if key_justificativas not in st.session_state:
        st.session_state[key_justificativas] = padrao_justificativas
    else:
        st.session_state[key_justificativas] = [
            valor
            for valor in st.session_state[key_justificativas]
            if valor in opcoes_justificativas
        ]

    with col_justificativas:
        justificativas = st.multiselect(
            "Justificativas consideradas",
            options=opcoes_justificativas,
            key=key_justificativas,
        )

    base_parametrizada = aplicar_regras_otd(
        filtrado,
        dias_extra=int(dias_extra),
        justificativas=justificativas,
        usar_baixa_indevida=usar_baixa_indevida,
    )

    regras_txt = ", ".join(justificativas) if justificativas else "nenhuma"
    st.caption(
        f"OTD base: +{int(dias_extra)} dia(s) · "
        f"Baixas indevidas: {'sim' if usar_baixa_indevida else 'não'} · "
        f"Justificativas do OTD Justificado: {regras_txt}"
    )

    # A partir daqui todos os componentes usam a MESMA base parametrizada.
    _render_resumo_principal(
        base_parametrizada,
        tipo_ordem=tipo_ordem,
        tipo_visao=tipo_visao,
    )
    _render_analise_atrasos(base_parametrizada)
    renderizar_imagens_complementares()
