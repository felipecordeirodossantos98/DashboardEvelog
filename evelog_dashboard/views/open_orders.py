"""Aba de Pedidos Em Aberto."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import barras_com_rotulo
from ..data import aplicar_filtros_abertos, preparar_abertos
from ..ui import (
    botao_exportar_excel,
    extrair_primeiro_ponto_selecionado,
    nome_seguro_arquivo,
    renderizar_download_selecao,
    renderizar_plotly_selecionavel,
)


_PREFIX = "abertos_"


def _key(nome: str) -> str:
    return f"{_PREFIX}{nome}"


def _inicializar_estado() -> None:
    defaults = {
        _key("dias"): [],
        _key("status"): [],
        _key("ocorrencias"): [],
        _key("dias_sem_mov"): [],
        _key("dias_widget"): [],
        _key("tipo_anterior"): None,
    }
    for chave, valor in defaults.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def _limpar_filtros() -> None:
    for nome in ("dias", "status", "ocorrencias", "dias_sem_mov", "dias_widget"):
        st.session_state[_key(nome)] = []


def _rotulo_dia(valor: float, tipo: str) -> str:
    dia = int(valor)
    if tipo == "Em atraso":
        return "1 dia em atraso" if dia == 1 else f"{dia} dias em atraso"
    if dia == 0:
        return "Vence hoje"
    return "1 dia para vencer" if dia == 1 else f"{dia} dias para vencer"


def _sanitizar_estado(chave: str, opcoes) -> None:
    permitidos = set(opcoes)
    st.session_state[chave] = [
        valor for valor in st.session_state.get(chave, []) if valor in permitidos
    ]


def render(df_abertos: pd.DataFrame) -> None:
    """Renderiza a aba de pedidos em aberto."""
    if df_abertos.empty:
        st.info("Não há pedidos em aberto na base.")
        return

    _inicializar_estado()

    st.header("Pedidos Em Aberto")
    st.caption(f"Total de pedidos em aberto: {len(df_abertos)}")

    col_tipo, col_metrica = st.columns([3, 1])
    with col_tipo:
        tipo = st.radio(
            "Visualização",
            ["Em atraso", "No prazo"],
            horizontal=True,
            key=_key("tipo"),
        )

    # Ao trocar de visão, valores da visão anterior não são reaproveitados por engano.
    if st.session_state[_key("tipo_anterior")] != tipo:
        _limpar_filtros()
        st.session_state[_key("tipo_anterior")] = tipo

    total_tipo = (
        df_abertos["Prazo"].astype(str).str.contains("ATRASADO", na=False).sum()
        if tipo == "Em atraso"
        else df_abertos["Prazo"].astype(str).str.contains("FALTAM", na=False).sum()
    )
    with col_metrica:
        st.metric(
            "Total de pedidos em atraso" if tipo == "Em atraso" else "Total de pedidos no prazo",
            int(total_tipo),
        )

    base = preparar_abertos(df_abertos, tipo)

    titulos = {
        "Em atraso": {
            "dias": "Distribuição de Pedidos em Atraso por Dias de Atraso",
            "status": "Status (Pedidos em atraso)",
            "ocorrencias": "Ocorrencias (Pedidos em atraso)",
            "mov": "Dias sem movimentação (Pedidos em atraso)",
            "tabela": "Pedidos filtrados (Pedidos em atraso)",
            "eixo_dias": "Dias em Atraso",
            "arquivo": "em_atraso",
        },
        "No prazo": {
            "dias": "Distribuição de Pedidos no Prazo por Dias Restantes",
            "status": "Status (Pedidos no Prazo)",
            "ocorrencias": "Ocorrencias (Pedidos no Prazo)",
            "mov": "Dias sem movimentação (Pedidos no Prazo)",
            "tabela": "Pedidos filtrados (Pedidos no Prazo)",
            "eixo_dias": "Dias até o Vencimento",
            "arquivo": "no_prazo",
        },
    }[tipo]

    col_dias, col_status, col_oc, col_mov = st.columns(4)

    with col_dias:
        temp = aplicar_filtros_abertos(
            base,
            status=st.session_state[_key("status")],
            ocorrencias=st.session_state[_key("ocorrencias")],
            dias_sem_mov=st.session_state[_key("dias_sem_mov")],
        )
        dias_opcoes = sorted(temp["Dias"].dropna().unique())
        _sanitizar_estado(_key("dias"), dias_opcoes)

        mapa_valor_label = {valor: _rotulo_dia(valor, tipo) for valor in dias_opcoes}
        mapa_label_valor = {label: valor for valor, label in mapa_valor_label.items()}
        labels = list(mapa_label_valor)

        # Mantém o widget sincronizado com a seleção numérica real.
        labels_atuais = [
            mapa_valor_label[dia]
            for dia in st.session_state[_key("dias")]
            if dia in mapa_valor_label
        ]
        if any(label not in labels for label in st.session_state[_key("dias_widget")]):
            st.session_state[_key("dias_widget")] = labels_atuais

        selecionados = st.multiselect(
            "Dias em atraso" if tipo == "Em atraso" else "Dias até o vencimento",
            labels,
            key=_key("dias_widget"),
        )
        st.session_state[_key("dias")] = [
            mapa_label_valor[label] for label in selecionados if label in mapa_label_valor
        ]

    with col_status:
        temp = aplicar_filtros_abertos(
            base,
            dias=st.session_state[_key("dias")],
            ocorrencias=st.session_state[_key("ocorrencias")],
            dias_sem_mov=st.session_state[_key("dias_sem_mov")],
        )
        status_opcoes = sorted(
            temp["Status"].dropna().astype(str).str.strip().unique()
        )
        _sanitizar_estado(_key("status"), status_opcoes)
        st.multiselect("Status", status_opcoes, key=_key("status"))

    with col_oc:
        temp = aplicar_filtros_abertos(
            base,
            dias=st.session_state[_key("dias")],
            status=st.session_state[_key("status")],
            dias_sem_mov=st.session_state[_key("dias_sem_mov")],
        )
        ocorrencias_opcoes = sorted(
            temp["Ocorrencias"]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda serie: serie.ne("")]
            .unique()
        )
        _sanitizar_estado(_key("ocorrencias"), ocorrencias_opcoes)
        st.multiselect("Ocorrências", ocorrencias_opcoes, key=_key("ocorrencias"))

    with col_mov:
        temp = aplicar_filtros_abertos(
            base,
            dias=st.session_state[_key("dias")],
            status=st.session_state[_key("status")],
            ocorrencias=st.session_state[_key("ocorrencias")],
        )
        dias_sem_mov_opcoes = sorted(
            temp["Dias_sem_mov"].dropna().astype(int).unique()
        )
        _sanitizar_estado(_key("dias_sem_mov"), dias_sem_mov_opcoes)
        st.multiselect(
            "Dias sem movimentação",
            dias_sem_mov_opcoes,
            key=_key("dias_sem_mov"),
        )

    st.button("Limpar filtros", on_click=_limpar_filtros, key=_key("limpar"))

    filtrado = aplicar_filtros_abertos(
        base,
        dias=st.session_state[_key("dias")],
        status=st.session_state[_key("status")],
        ocorrencias=st.session_state[_key("ocorrencias")],
        dias_sem_mov=st.session_state[_key("dias_sem_mov")],
    )

    if filtrado.empty:
        st.info("Nenhum pedido corresponde aos filtros selecionados.")
        return

    def renderizar_agregado(
        resumo: pd.DataFrame,
        *,
        titulo: str,
        categoria: str,
        filtro_col: str,
        grafico_key: str,
        arquivo_prefixo: str,
        horizontal: bool = False,
        titulo_categoria: str | None = None,
        titulo_valor: str | None = None,
        numerico: bool = False,
    ) -> None:
        if resumo.empty:
            return

        st.subheader(titulo)
        evento = renderizar_plotly_selecionavel(
            barras_com_rotulo(
                resumo,
                categoria=categoria,
                valor="Quantidade",
                horizontal=horizontal,
                titulo_categoria=titulo_categoria or categoria,
                titulo_valor=titulo_valor or "Quantidade",
            ),
            key=_key(grafico_key),
        )
        ponto = extrair_primeiro_ponto_selecionado(evento)
        if not ponto:
            return

        selecionado = ponto.get("y" if horizontal else "x")
        if selecionado is None:
            return

        if numerico:
            valor_num = pd.to_numeric(pd.Series([selecionado]), errors="coerce").iloc[0]
            if pd.isna(valor_num):
                return
            serie = pd.to_numeric(filtrado[filtro_col], errors="coerce")
            base_selecionada = filtrado[serie.eq(valor_num)].copy()
            descricao = f"{titulo_categoria or filtro_col}: {int(valor_num) if float(valor_num).is_integer() else valor_num}"
        else:
            valor_txt = str(selecionado)
            base_selecionada = filtrado[
                filtrado[filtro_col].astype(str).eq(valor_txt)
            ].copy()
            descricao = f"{titulo_categoria or filtro_col}: {valor_txt}"

        renderizar_download_selecao(
            base_selecionada,
            descricao=descricao,
            nome_arquivo=(
                f"{arquivo_prefixo}_{nome_seguro_arquivo(selecionado)}.xlsx"
            ),
            key=_key(f"download_{grafico_key}"),
        )

    distribuicao = (
        filtrado.groupby("Dias").size().reset_index(name="Quantidade").sort_values("Dias")
    )
    renderizar_agregado(
        distribuicao,
        titulo=titulos["dias"],
        categoria="Dias",
        filtro_col="Dias",
        grafico_key="grafico_dias",
        arquivo_prefixo=f"base_{titulos['arquivo']}_dias",
        titulo_categoria=titulos["eixo_dias"],
        numerico=True,
    )

    status_df = (
        filtrado.groupby("Status").size().reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    renderizar_agregado(
        status_df,
        titulo=titulos["status"],
        categoria="Status",
        filtro_col="Status",
        grafico_key="grafico_status",
        arquivo_prefixo=f"base_{titulos['arquivo']}_status",
        horizontal=True,
        titulo_categoria="Status",
    )

    ocorrencias_validas = filtrado[
        filtrado["Ocorrencias"].notna()
        & filtrado["Ocorrencias"].astype(str).str.strip().ne("")
    ]
    ocorrencias_df = (
        ocorrencias_validas.groupby("Ocorrencias")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    renderizar_agregado(
        ocorrencias_df,
        titulo=titulos["ocorrencias"],
        categoria="Ocorrencias",
        filtro_col="Ocorrencias",
        grafico_key="grafico_ocorrencias",
        arquivo_prefixo=f"base_{titulos['arquivo']}_ocorrencia",
        horizontal=True,
        titulo_categoria="Ocorrências",
    )

    mov_df = (
        filtrado.groupby("Dias_sem_mov")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Dias_sem_mov")
    )
    renderizar_agregado(
        mov_df,
        titulo=titulos["mov"],
        categoria="Dias_sem_mov",
        filtro_col="Dias_sem_mov",
        grafico_key="grafico_movimentacao",
        arquivo_prefixo=f"base_{titulos['arquivo']}_sem_movimentacao",
        titulo_categoria="Dias sem movimentação",
        titulo_valor="Quantidade de pedidos",
        numerico=True,
    )

    st.subheader(titulos["tabela"])
    st.caption(f"Total: {len(filtrado)}")
    st.dataframe(filtrado, width="stretch", hide_index=True)
    botao_exportar_excel(
        filtrado,
        nome_arquivo=f"base_em_aberto_{titulos['arquivo']}.xlsx",
        usar_sidebar=False,
        key=_key("exportar"),
    )
