"""Componentes de interface compartilhados entre as views."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .excel import exportar_excel


def instalar_confirmacao_saida() -> None:
    """Mantém o aviso de saída existente no dashboard atual."""
    components.html(
        """
        <script>
            window.parent.addEventListener("beforeunload", function (event) {
                event.preventDefault();
                event.returnValue = "";
            });
        </script>
        """,
        height=0,
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
) -> None:
    """Renderiza o botão de exportação de maneira consistente."""
    container = st.sidebar if usar_sidebar else st
    habilitado = df is not None and not df.empty
    data = _exportar_excel_cached(df) if habilitado else b""

    container.download_button(
        label="⬇️ Exportar base (.xlsx)",
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
    nao_entregues: int,
) -> None:
    """Mostra a árvore-resumo da sidebar."""
    pct_abertos = abertos / total if total else 0
    pct_entregues = entregues / total if total else 0
    pct_nao_entregues = nao_entregues / total if total else 0
    pct_atrasados = atrasados / abertos if abertos else 0
    pct_no_prazo = no_prazo / abertos if abertos else 0

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
                use_container_width=True,
            )
