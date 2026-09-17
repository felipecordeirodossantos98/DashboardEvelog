"""Exportação de DataFrames para Excel."""

from io import BytesIO

import pandas as pd


def exportar_excel(df: pd.DataFrame, sheet_name: str = "Base_Unificada") -> bytes:
    """Serializa um DataFrame em XLSX e retorna os bytes do arquivo."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()
