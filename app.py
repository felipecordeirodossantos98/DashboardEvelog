"""Entrada do Dashboard Evelog.

A UI fica intencionalmente pequena: leitura da base, filtro global e roteamento
para as três views. Regras de negócio e componentes reutilizáveis vivem no
pacote ``evelog_dashboard``.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from evelog_dashboard.config import (
    LOGO_PATH,
    OCORRENCIAS_JUSTIFICADAS,
    PAGE_ICON,
    PAGE_TITLE,
)
from evelog_dashboard.data import (
    carregar_planilha_bytes,
    preparar_base_global,
    separar_bases,
    unificar_bases,
    filtrar_periodo_datas,
    preparar_entregues,
)
from evelog_dashboard.summaries import aplicar_regras_otd
from evelog_dashboard.ui import (
    botao_exportar_excel,
    instalar_confirmacao_saida,
    renderizar_resumo_sidebar,
)
from evelog_dashboard.views import delivered, not_delivered, open_orders


# Deve ser a primeira chamada Streamlit da aplicação.
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)


@st.cache_data(show_spinner="📥 Processando planilha...")
def _carregar_planilha_cached(conteudo: bytes, data_referencia: date) -> pd.DataFrame:
    """Cache por conteúdo + dia para não congelar o cálculo de pedidos em aberto."""
    return carregar_planilha_bytes(
        conteudo,
        hoje=pd.Timestamp(data_referencia),
    )


def _carregar_uploads(uploaded_files) -> pd.DataFrame | None:
    if not uploaded_files:
        return None

    dataframes: list[pd.DataFrame] = []
    hoje = date.today()

    with st.spinner("🔄 Unificando bases..."):
        for arquivo in uploaded_files:
            try:
                df = _carregar_planilha_cached(arquivo.getvalue(), hoje)
            except Exception as exc:
                st.sidebar.error(f"Erro ao processar {arquivo.name}: {exc}")
                continue

            if df.empty:
                st.sidebar.warning(f"{arquivo.name}: planilha sem dados válidos.")
                continue

            dataframes.append(df)
            mes_ref = df["Arquivo_Origem"].iloc[0] if "Arquivo_Origem" in df else "Mês desconhecido"
            cliente = df["Cliente"].iloc[0] if "Cliente" in df else "Cliente desconhecido"
            st.sidebar.write(f"**{arquivo.name}** carregado → {mes_ref} | {cliente}")

    base = unificar_bases(dataframes)
    if base is not None:
        st.sidebar.success(f"{len(dataframes)} planilha(s) carregada(s)")
    return base


def _aplicar_filtro_global_emissao(base: pd.DataFrame) -> pd.DataFrame:
    """Renderiza e aplica o filtro global por data de emissão."""
    if "Dt Emissao" not in base.columns:
        st.warning("A coluna 'Dt Emissao' não foi encontrada. O filtro global foi ignorado.")
        return base.copy()

    datas_validas = base["Dt Emissao"].dropna()
    if datas_validas.empty:
        st.warning("Não há datas de emissão válidas para aplicar o filtro global.")
        return base.copy()

    min_emissao = datas_validas.min().date()
    max_emissao = datas_validas.max().date()
    assinatura = (len(base), min_emissao, max_emissao)

    if st.session_state.get("global_base_signature") != assinatura:
        st.session_state["filtro_global_emissao"] = (min_emissao, max_emissao)
        st.session_state["global_base_signature"] = assinatura

    # Como o valor do widget já é controlado pelo Session State, não passamos
    # ``value`` ao date_input. Isso evita o aviso do Streamlit sobre definir o
    # mesmo widget simultaneamente pelo parâmetro padrão e pela Session State API.
    col_filtro, _, col_metrica = st.columns([1, 2, 1])
    with col_filtro:
        periodo = st.date_input(
            "📅 Período de emissão dos pedidos",
            min_value=min_emissao,
            max_value=max_emissao,
            key="filtro_global_emissao",
        )

    filtrada = base.copy()
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
        filtrada = filtrada[
            filtrada["Dt Emissao"].notna()
            & filtrada["Dt Emissao"].dt.date.ge(inicio)
            & filtrada["Dt Emissao"].dt.date.le(fim)
        ].copy()

    with col_metrica:
        st.metric(
            "Pedidos no período",
            f"{len(filtrada):,}".replace(",", "."),
        )

    return filtrada


def _opcoes_justificativas_resumo(base: pd.DataFrame) -> list[str]:
    """Replica as opções válidas de justificativa usadas na aba de OTD."""
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


def _aplicar_filtros_otd_ao_resumo(df_entregues: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica ao resumo exatamente as regras ativas da aba Performance OTD.

    O resumo acompanha:
    - período de entrega;
    - dias extras;
    - baixas indevidas;
    - justificativas consideradas.

    Ordenação e visualização (UF/Região) são apenas controles de apresentação e
    não alteram os totais do resumo.
    """
    base = preparar_entregues(df_entregues)

    periodo = st.session_state.get("entregues_periodo_entrega")
    if (
        not base.empty
        and "Dt Evento" in base.columns
        and isinstance(periodo, (tuple, list))
        and len(periodo) == 2
    ):
        inicio, fim = periodo
        base = filtrar_periodo_datas(
            base,
            "Dt Evento",
            inicio,
            fim,
            incluir_dia_final=True,
        )

    dias_extra = int(st.session_state.get("entregues_dias_extra", 0) or 0)
    usar_baixa_indevida = bool(
        st.session_state.get("entregues_baixas_indevidas", False)
    )

    # Primeiro aplica apenas as regras do OTD base. Isso reproduz a mesma lista
    # de ocorrências elegíveis que alimenta o multiselect da aba de Entregues.
    base_sem_justificativas = aplicar_regras_otd(
        base,
        dias_extra=dias_extra,
        justificativas=(),
        usar_baixa_indevida=usar_baixa_indevida,
    )
    opcoes_justificativas = _opcoes_justificativas_resumo(base_sem_justificativas)

    chave_justificativas = "entregues_justificativas"
    if chave_justificativas in st.session_state:
        justificativas = [
            valor
            for valor in st.session_state.get(chave_justificativas, [])
            if valor in opcoes_justificativas
        ]
    else:
        # No primeiro carregamento, usa o mesmo padrão da aba Performance OTD
        # para o resumo já nascer coerente, sem depender de um segundo rerun.
        justificativas = [
            ocorrencia
            for ocorrencia in OCORRENCIAS_JUSTIFICADAS
            if ocorrencia in opcoes_justificativas
        ]

    base_parametrizada = aplicar_regras_otd(
        base,
        dias_extra=dias_extra,
        justificativas=justificativas,
        usar_baixa_indevida=usar_baixa_indevida,
    )

    regras = {
        "periodo": periodo,
        "dias_extra": dias_extra,
        "baixas_indevidas": usar_baixa_indevida,
        "justificativas": justificativas,
    }
    return base_parametrizada, regras


def main() -> None:
    instalar_confirmacao_saida()

    # Logo é opcional: se o arquivo não existir, o dashboard continua abrindo.
    if LOGO_PATH.is_file():
        st.sidebar.image(str(LOGO_PATH), width=180)

    st.title(PAGE_TITLE)

    st.sidebar.header("Importar Planilhas")
    uploaded_files = st.sidebar.file_uploader(
        "Selecione uma ou mais planilhas Excel",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="arquivos_entrada",
    )

    base = _carregar_uploads(uploaded_files)
    st.sidebar.divider()

    if base is None or base.empty:
        st.info("Importe planilhas no menu lateral para visualizar o dashboard.")
        return

    base = preparar_base_global(base)
    base_filtrada = _aplicar_filtro_global_emissao(base)
    bases = separar_bases(base_filtrada)

    # O bloco de Entregues do resumo usa a MESMA base parametrizada da aba
    # Performance OTD. Assim, período, dias extras, baixas indevidas e
    # justificativas alteram os números/percentuais do resumo imediatamente.
    entregues_resumo, regras_resumo = _aplicar_filtros_otd_ao_resumo(
        bases.entregues
    )

    renderizar_resumo_sidebar(
        total=len(bases.completa),
        abertos=len(bases.abertos),
        atrasados=len(bases.abertos_atrasados),
        no_prazo=len(bases.abertos_no_prazo),
        entregues=len(entregues_resumo),
        entregues_no_prazo=int(
            entregues_resumo["Prazo Ajustado"].eq("NO PRAZO").sum()
        ),
        entregues_fora_prazo=int(
            entregues_resumo["Prazo Ajustado"].eq("FORA DO PRAZO").sum()
        ),
        nao_entregues=len(bases.encerrados),
    )

    periodo_entrega = regras_resumo["periodo"]
    if isinstance(periodo_entrega, (tuple, list)) and len(periodo_entrega) == 2:
        inicio, fim = periodo_entrega
        justificativas_txt = (
            ", ".join(regras_resumo["justificativas"])
            if regras_resumo["justificativas"]
            else "nenhuma"
        )
    botao_exportar_excel(
        bases.completa,
        nome_arquivo="base_completa.xlsx",
        usar_sidebar=True,
        key="exportar_base_completa",
    )

    tab_abertos, tab_entregues, tab_nao_entregues = st.tabs(
        ["Pedidos Em Aberto", "Pedidos Entregues", "Pedidos Não Entregues"]
    )

    with tab_abertos:
        open_orders.render(bases.abertos)

    with tab_entregues:
        delivered.render(bases.entregues)

    with tab_nao_entregues:
        not_delivered.render(bases.encerrados)


if __name__ == "__main__":
    main()
