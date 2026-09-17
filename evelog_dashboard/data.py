"""Leitura, limpeza e transformação das bases do Dashboard Evelog."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Iterable, Sequence
import unicodedata

import pandas as pd

from .config import (
    DESCRICOES_EXCLUIDAS_CUSTODIA,
    MAPA_OCORRENCIAS,
    MAPA_REGIAO,
    STATUS_EXCLUIDOS,
)


@dataclass(frozen=True)
class DashboardBases:
    """Recortes principais usados pelas abas do dashboard."""

    completa: pd.DataFrame
    abertos: pd.DataFrame
    entregues: pd.DataFrame
    encerrados: pd.DataFrame
    abertos_atrasados: pd.DataFrame
    abertos_no_prazo: pd.DataFrame


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Remove acentos e espaços extras dos nomes de coluna."""
    resultado = df.copy()
    resultado.columns = [
        unicodedata.normalize("NFKD", str(col))
        .encode("ASCII", "ignore")
        .decode("ASCII")
        .strip()
        for col in resultado.columns
    ]
    return resultado


def localizar_coluna(df: pd.DataFrame, termo: str) -> str | None:
    """Localiza a primeira coluna cujo nome contém ``termo``."""
    termo = termo.lower()
    return next((col for col in df.columns if termo in str(col).lower()), None)


def parse_data_br(serie: pd.Series) -> pd.Series:
    """Converte datas brasileiras com ou sem horário.

    Mantém a compatibilidade com os dois formatos usados no dashboard original.
    """
    texto = serie.astype(str).str.strip()
    com_hora = pd.to_datetime(
        texto,
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )
    somente_data = pd.to_datetime(
        texto,
        format="%d/%m/%Y",
        errors="coerce",
    )
    return com_hora.fillna(somente_data)


def _extrair_referencia_arquivo(
    df_raw: pd.DataFrame,
    df: pd.DataFrame,
) -> tuple[str, str]:
    """Extrai mês de referência e cliente, preservando a lógica do app original.

    Primeiro tenta a posição usada anteriormente na planilha bruta. Se a base tiver
    outro espaçamento, usa os primeiros valores válidos da tabela já carregada.
    """
    mes_ref = "Mês desconhecido"
    cliente = "Cliente desconhecido"

    if "Dt Emissao" in df.columns:
        try:
            col_emissao = df.columns.get_loc("Dt Emissao")
            data_ref = pd.to_datetime(df_raw.iloc[2, col_emissao], dayfirst=True)
            if pd.notna(data_ref):
                mes_ref = data_ref.strftime("%m/%Y")
        except (IndexError, KeyError, TypeError, ValueError):
            serie = pd.to_datetime(df["Dt Emissao"], dayfirst=True, errors="coerce").dropna()
            if not serie.empty:
                mes_ref = serie.iloc[0].strftime("%m/%Y")

    if "Cliente" in df.columns:
        try:
            col_cliente = df.columns.get_loc("Cliente")
            valor = str(df_raw.iloc[2, col_cliente]).strip()
            if valor and valor.lower() != "nan":
                cliente = valor
        except (IndexError, KeyError, TypeError, ValueError):
            serie = df["Cliente"].dropna().astype(str).str.strip()
            serie = serie[serie.ne("") & serie.str.lower().ne("nan")]
            if not serie.empty:
                cliente = serie.iloc[0]

    return mes_ref, cliente


def calcular_prazo(df: pd.DataFrame, hoje: pd.Timestamp | None = None) -> pd.DataFrame:
    """Calcula a classificação de prazo e padroniza ocorrências."""
    resultado = df.copy()

    col_previsao = localizar_coluna(resultado, "previsao")
    col_evento = localizar_coluna(resultado, "evento")
    col_status = localizar_coluna(resultado, "status")
    col_descricao = localizar_coluna(resultado, "descricao")

    if not col_previsao or not col_status:
        return resultado

    previsao = pd.to_datetime(
        resultado[col_previsao], dayfirst=True, errors="coerce"
    ).dt.normalize()
    status = resultado[col_status].astype(str).str.strip().str.upper()

    descricao = None
    if col_descricao:
        descricao = (
            resultado[col_descricao]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    data_hoje = (hoje if hoje is not None else pd.Timestamp.today()).normalize()
    resultado["Prazo"] = ""

    mask_excluir = status.isin(STATUS_EXCLUIDOS)
    if descricao is not None:
        mask_excluir |= (
            status.eq("CUSTODIA")
            & descricao.isin(DESCRICOES_EXCLUIDAS_CUSTODIA)
        )

    if col_evento:
        evento = pd.to_datetime(
            resultado[col_evento], dayfirst=True, errors="coerce"
        ).dt.normalize()
        mask_entregue = status.eq("ENTREGUE") & ~mask_excluir
        resultado.loc[mask_entregue & evento.le(previsao), "Prazo"] = "NO PRAZO"
        resultado.loc[mask_entregue & evento.gt(previsao), "Prazo"] = "FORA DO PRAZO"

    mask_abertos = status.ne("ENTREGUE") & ~mask_excluir & previsao.notna()
    diff = (previsao - data_hoje).dt.days

    resultado.loc[mask_abertos & diff.ge(0), "Prazo"] = (
        "FALTAM " + diff.astype(str).str.zfill(3) + " DIAS"
    )
    resultado.loc[mask_abertos & diff.lt(0), "Prazo"] = (
        "ATRASADO " + diff.abs().astype(str).str.zfill(3) + " DIAS"
    )
    resultado["Prazo"] = resultado["Prazo"].replace("", None)

    if descricao is not None:
        resultado["Ocorrencias"] = descricao.map(MAPA_OCORRENCIAS).fillna(descricao)
    elif "Ocorrencias" not in resultado.columns:
        resultado["Ocorrencias"] = ""

    return resultado


def carregar_planilha_bytes(
    conteudo: bytes, hoje: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Lê uma planilha enviada pelo Streamlit a partir dos bytes do arquivo."""
    arquivo = BytesIO(conteudo)
    df_raw = pd.read_excel(arquivo, header=None)
    if df_raw.empty:
        return pd.DataFrame()

    linha_cabecalho = int(df_raw.notna().sum(axis=1).idxmax())

    arquivo.seek(0)
    df = pd.read_excel(arquivo, skiprows=linha_cabecalho)
    df = normalizar_colunas(df)

    mes_ref, cliente = _extrair_referencia_arquivo(df_raw, df)
    df["Arquivo_Origem"] = mes_ref
    df["Cliente"] = cliente

    return calcular_prazo(df, hoje=hoje)


def unificar_bases(dfs: Sequence[pd.DataFrame]) -> pd.DataFrame | None:
    """Concatena as planilhas válidas em uma única base."""
    validas = [df for df in dfs if df is not None and not df.empty]
    if not validas:
        return None
    return pd.concat(validas, ignore_index=True)


def filtrar_periodo_datas(
    df: pd.DataFrame,
    coluna: str,
    inicio,
    fim,
    *,
    incluir_dia_final: bool = True,
) -> pd.DataFrame:
    """Filtra uma coluna datetime entre duas datas sem mutar a base original."""
    if df.empty or coluna not in df.columns:
        return df.copy()

    resultado = df.copy()
    serie = pd.to_datetime(resultado[coluna], errors="coerce")
    inicio_ts = pd.to_datetime(inicio)
    fim_ts = pd.to_datetime(fim)

    if incluir_dia_final:
        fim_ts += pd.Timedelta(days=1)
        mask = serie.notna() & serie.ge(inicio_ts) & serie.lt(fim_ts)
    else:
        mask = serie.notna() & serie.ge(inicio_ts) & serie.le(fim_ts)

    return resultado.loc[mask].copy()


def preparar_base_global(base: pd.DataFrame) -> pd.DataFrame:
    """Normaliza os campos comuns usados por todas as abas."""
    resultado = base.copy()

    if "Dt Emissao" in resultado.columns:
        resultado["Dt Emissao"] = pd.to_datetime(
            resultado["Dt Emissao"].astype(str).str.strip(),
            dayfirst=True,
            errors="coerce",
        )

    if "Ocorrencias" not in resultado.columns:
        resultado["Ocorrencias"] = ""

    return resultado


def separar_bases(base: pd.DataFrame) -> DashboardBases:
    """Cria os recortes usados pelo dashboard a partir da base filtrada."""
    df = base.copy()

    prazo = df.get("Prazo", pd.Series(index=df.index, dtype="object"))
    prazo_txt = prazo.astype(str).str.strip()

    abertos = df[
        ~prazo.isin(["NO PRAZO", "FORA DO PRAZO"])
        & prazo.notna()
        & prazo_txt.ne("")
    ].copy()

    abertos_atrasados = abertos[
        abertos["Prazo"].astype(str).str.contains("ATRASADO", na=False)
    ].copy()
    abertos_no_prazo = abertos[
        abertos["Prazo"].astype(str).str.contains("FALTAM", na=False)
    ].copy()

    entregues = df[prazo.isin(["NO PRAZO", "FORA DO PRAZO"])].copy()
    encerrados = df[prazo.isna() | prazo_txt.eq("")].copy()

    return DashboardBases(
        completa=df,
        abertos=abertos,
        entregues=entregues,
        encerrados=encerrados,
        abertos_atrasados=abertos_atrasados,
        abertos_no_prazo=abertos_no_prazo,
    )


def preparar_abertos(df_abertos: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Prepara a base de pedidos em aberto para filtros e gráficos."""
    if tipo == "Em atraso":
        mask = df_abertos["Prazo"].astype(str).str.contains("ATRASADO", na=False)
    else:
        mask = df_abertos["Prazo"].astype(str).str.contains("FALTAM", na=False)

    resultado = df_abertos.loc[mask].copy()
    resultado["Dias"] = pd.to_numeric(
        resultado["Prazo"].astype(str).str.extract(r"(\d+)", expand=False),
        errors="coerce",
    )

    if "Dt Evento" in resultado.columns:
        resultado["Dt Evento"] = parse_data_br(resultado["Dt Evento"])
        hoje = pd.Timestamp.now().normalize()
        resultado["Dias_sem_mov"] = (
            hoje - resultado["Dt Evento"].dt.normalize()
        ).dt.days.clip(lower=0)
    else:
        resultado["Dias_sem_mov"] = pd.NA

    return resultado


def aplicar_filtros_abertos(
    df: pd.DataFrame,
    *,
    dias: Sequence | None = None,
    status: Sequence | None = None,
    ocorrencias: Sequence | None = None,
    dias_sem_mov: Sequence | None = None,
) -> pd.DataFrame:
    """Aplica os quatro filtros encadeados da aba de pedidos em aberto."""
    resultado = df
    if dias:
        resultado = resultado[resultado["Dias"].isin(dias)]
    if status:
        resultado = resultado[resultado["Status"].isin(status)]
    if ocorrencias:
        resultado = resultado[resultado["Ocorrencias"].isin(ocorrencias)]
    if dias_sem_mov:
        resultado = resultado[resultado["Dias_sem_mov"].isin(dias_sem_mov)]
    return resultado.copy()


def preparar_entregues(df: pd.DataFrame) -> pd.DataFrame:
    """Converte as datas da base de entregues uma única vez."""
    resultado = df.copy()
    if "Dt Evento" in resultado.columns:
        resultado["Dt Evento"] = parse_data_br(resultado["Dt Evento"])
    if "Previsao" in resultado.columns:
        resultado["Previsao"] = pd.to_datetime(
            resultado["Previsao"].astype(str).str.strip(),
            format="%d/%m/%Y",
            errors="coerce",
        )
    return resultado


def adicionar_grupo_geografico(df: pd.DataFrame, tipo_visao: str) -> pd.DataFrame:
    """Adiciona a coluna Grupo usando UF ou Região."""
    resultado = df.copy()
    if tipo_visao == "Região":
        resultado["Grupo"] = resultado["UF"].map(MAPA_REGIAO)
    else:
        resultado["Grupo"] = resultado["UF"]
    return resultado


def preparar_atrasos_entregues(df_entregues: pd.DataFrame) -> pd.DataFrame:
    """Retorna apenas entregas atrasadas com a coluna ``Dias Atraso``."""
    resultado = df_entregues.copy()
    if resultado.empty:
        resultado["Dias Atraso"] = pd.Series(dtype="int64")
        return resultado

    if "Dt Evento" not in resultado.columns or "Previsao" not in resultado.columns:
        resultado["Dias Atraso"] = pd.Series(index=resultado.index, dtype="float64")
        return resultado.iloc[0:0].copy()

    resultado = resultado.dropna(subset=["Dt Evento", "Previsao"]).copy()
    resultado["Dias Atraso"] = (
        resultado["Dt Evento"].dt.normalize()
        - resultado["Previsao"].dt.normalize()
    ).dt.days
    return resultado[resultado["Dias Atraso"].gt(0)].copy()


def faixa_atraso_por_dia(dias: int | float) -> str:
    """Gera o rótulo detalhado solicitado: uma faixa para cada dia."""
    valor = int(dias)
    return "1 dia" if valor == 1 else f"{valor} dias"
