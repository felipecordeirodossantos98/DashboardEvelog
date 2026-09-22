"""Componentes de interface compartilhados entre as views."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .excel import exportar_excel


def instalar_confirmacao_saida() -> None:
    """Mantém o aviso de saída usando a API atual de iframe do Streamlit."""
    st.iframe(
        """
        <style>
            html, body { margin: 0; padding: 0; overflow: hidden; }
        </style>
        <script>
            window.parent.addEventListener("beforeunload", function (event) {
                event.preventDefault();
                event.returnValue = "";
            });
        </script>
        """,
        height=1,
        width="stretch",
        tab_index=-1,
    )


@st.cache_data(show_spinner=False)
def _exportar_excel_cached(df: pd.DataFrame) -> bytes:
    return exportar_excel(df)


def botao_exportar_excel(
    df: pd.DataFrame | None,
    nome_arquivo: str = "base_unificada.xlsx",
    *,
    usar_sidebar: bool = True,
    key: str | None = None,
    label: str = "⬇️ Exportar base (.xlsx)",
) -> None:
    """Renderiza o botão de exportação de maneira consistente."""
    container = st.sidebar if usar_sidebar else st
    habilitado = df is not None and not df.empty
    data = _exportar_excel_cached(df) if habilitado else b""

    container.download_button(
        label=label,
        data=data,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not habilitado,
        key=key,
    )


def renderizar_resumo_sidebar(
    *,
    total: int,
    abertos: int,
    atrasados: int,
    no_prazo: int,
    entregues: int,
    entregues_no_prazo: int,
    entregues_fora_prazo: int,
    nao_entregues: int,
) -> None:
    """Mostra a árvore-resumo da sidebar."""
    pct_abertos = abertos / total if total else 0
    pct_entregues = entregues / total if total else 0
    pct_nao_entregues = nao_entregues / total if total else 0
    pct_atrasados = atrasados / abertos if abertos else 0
    pct_no_prazo = no_prazo / abertos if abertos else 0
    pct_entregues_no_prazo = entregues_no_prazo / entregues if entregues else 0
    pct_entregues_fora_prazo = entregues_fora_prazo / entregues if entregues else 0

    st.sidebar.subheader("Resumo")
    st.sidebar.markdown(
        f"""
<style>
.tabela-resumo {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.tabela-resumo td {{
    padding: 4px 6px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
.tree {{ font-family: monospace; white-space: pre; }}
.bold {{ font-weight: 600; }}
</style>
<table class="tabela-resumo">
<tr><td class="tree bold">Total do Período</td><td>{total}</td><td>100.00%</td></tr>
<tr><td class="tree">├─ Em aberto</td><td>{abertos}</td><td>{pct_abertos:.2%}</td></tr>
<tr><td class="tree">│  ├─ Em atraso</td><td>{atrasados}</td><td>{pct_atrasados:.2%}</td></tr>
<tr><td class="tree">│  └─ No prazo</td><td>{no_prazo}</td><td>{pct_no_prazo:.2%}</td></tr>
<tr><td class="tree">├─ Entregues</td><td>{entregues}</td><td>{pct_entregues:.2%}</td></tr>
<tr><td class="tree">│  ├─ No prazo</td><td>{entregues_no_prazo}</td><td>{pct_entregues_no_prazo:.2%}</td></tr>
<tr><td class="tree">│  └─ Fora do prazo</td><td>{entregues_fora_prazo}</td><td>{pct_entregues_fora_prazo:.2%}</td></tr>
<tr><td class="tree">└─ Não entregues</td><td>{nao_entregues}</td><td>{pct_nao_entregues:.2%}</td></tr>
</table>
""",
        unsafe_allow_html=True,
    )


def renderizar_imagens_complementares() -> None:
    """Upload opcional das imagens usadas para apresentação."""
    with st.expander("🖼️ Imagens complementares"):
        imagens = st.file_uploader(
            "Importar imagens",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="imgs_apresentacao",
        )
        for indice, imagem in enumerate(imagens or [], start=1):
            st.image(
                imagem,
                caption=f"Imagem {indice}",
                width="stretch",
            )


def renderizar_plotly_selecionavel(fig, *, key: str):
    """Renderiza um Plotly com seleção simples por clique em pontos/barras."""
    return st.plotly_chart(
        fig,
        width="stretch",
        key=key,
        on_select="rerun",
        selection_mode="points",
        config={"displaylogo": False},
    )


def extrair_primeiro_ponto_selecionado(evento) -> dict | None:
    """Extrai o primeiro ponto selecionado de forma tolerante à API do Streamlit."""
    if evento is None:
        return None

    selecao = getattr(evento, "selection", None)
    if selecao is None and isinstance(evento, dict):
        selecao = evento.get("selection")
    if selecao is None:
        return None

    pontos = getattr(selecao, "points", None)
    if pontos is None and isinstance(selecao, dict):
        pontos = selecao.get("points")
    if not pontos:
        return None

    ponto = pontos[0]
    try:
        return dict(ponto)
    except (TypeError, ValueError):
        return ponto if isinstance(ponto, dict) else None


def renderizar_tabela_grafico(
    df: pd.DataFrame,
    *,
    titulo: str = "📋 Ver dados do gráfico",
    hide_index: bool = True,
) -> None:
    """Mostra a tabela-resumo que alimenta um gráfico."""
    with st.expander(titulo):
        st.dataframe(
            df,
            width="stretch",
            hide_index=hide_index,
        )


def nome_seguro_arquivo(valor: object) -> str:
    """Cria um fragmento simples e seguro para nomes de arquivos exportados."""
    import re
    import unicodedata

    texto = str(valor).strip() or "selecao"
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9_-]+", "_", texto).strip("_")
    return texto.lower() or "selecao"


def renderizar_download_selecao(
    df: pd.DataFrame,
    *,
    descricao: str,
    nome_arquivo: str,
    key: str,
) -> None:
    """Exibe contexto da seleção e exporta exatamente a base que gerou o ponto."""
    if df is None or df.empty:
        st.caption(f"Seleção: {descricao} · nenhum pedido encontrado.")
        return

    st.caption(f"Seleção: {descricao} · {len(df):,} pedido(s)".replace(",", "."))
    botao_exportar_excel(
        df,
        nome_arquivo=nome_arquivo,
        usar_sidebar=False,
        key=key,
        label="⬇️ Baixar base selecionada",
    )
