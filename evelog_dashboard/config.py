"""Configurações e regras de negócio do Dashboard Evelog.

Manter os valores de negócio neste módulo evita duplicação nas views e
facilita alterações futuras sem precisar procurar regras espalhadas pela UI.
"""

from pathlib import Path


# Caminhos sempre relativos à pasta do projeto, e não ao diretório de onde
# o comando ``streamlit run`` foi executado. Isso evita erros ao iniciar o app
# a partir da pasta pai, VS Code, systemd, Streamlit Cloud etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJECT_ROOT / "images"
LOGO_PATH = IMAGES_DIR / "logo.svg"
PAGE_ICON = IMAGES_DIR / "evelog-favicon.svg"

PAGE_TITLE = "Dashboard Evelog"
# O Streamlit aceita emoji como ícone. Se o SVG não estiver no projeto, o app
# continua funcionando em vez de falhar por causa de um recurso visual.

STATUS_EXCLUIDOS = {
    "DEVOLVIDO",
    "EM DEVOLUCAO",
    "ENCERRADO",
    "LISTA DEVOLUCAO",
    "SINISTRO",
    "TRAVADO",
    "UNITIZADO",
}

DESCRICOES_EXCLUIDAS_CUSTODIA = {
    "AVARIA / DANO PARCIAL",
    "AVARIA / DANO TOTAL",
    "ERRO DO EMISSOR",
    "EXTRAVIO PARCIAL",
    "EXTRAVIO TOTAL",
    "FALTA DE ACAREAÇÃO / TOTAL",
    "FALTA DE COMPROVANTE DE ENTREGA / TOTAL",
    "INDENIZACAO RECUSADA",
    "INDICIO VIOLACAO",
    "LIBERADO",
    "PERDA POR PRAZO SLA / TOTAL",
}

MAPA_OCORRENCIAS = {
    # Destinatário ausente
    "AUSENTE": "DEST. AUSENTE",
    "AUSENTE 2": "DEST. AUSENTE",
    "AUSENTE 3": "DEST. AUSENTE",
    "FECHADO": "DEST. AUSENTE",
    "FECHADO 2": "DEST. AUSENTE",
    "TEMPO DE ESPERA EXCEDIDO NO DESTINATARIO": "DEST. AUSENTE",
    "AUSENTE EM FERIAS": "DEST. AUSENTE",

    # Pedido avariado
    "AVARIA / DANO PARCIAL": "PEDIDO AVARIADO",
    "AVARIA / DANO TOTAL": "PEDIDO AVARIADO",
    "INDICIO VIOLACAO": "PEDIDO AVARIADO",

    # Problema de endereço
    "DESTINATARIO DESCONHECIDO": "PROB. ENDEREÇO",
    "ENDERECO INSUFICIENTE": "PROB. ENDEREÇO",
    "ENDERECO NAO LOCALIZADO": "PROB. ENDEREÇO",
    "MUDOU-SE": "PROB. ENDEREÇO",
    "NUMERO NAO LOCALIZADO": "PROB. ENDEREÇO",
    "CEP ERRADO": "PROB. ENDEREÇO",
    "ENDERECO EM ZONA RURAL": "PROB. ENDEREÇO",

    # Agência
    "DESTINATARIO SOLICITOU RETIRAR NA UNIDADE": "AG. RETIRADA AGÊNCIA",

    # Last Mile
    "ATRASO TRANSPORTE": "LAST MILE",
    "FALHA ENTREGA": "LAST MILE",
    "SOLICITACAO ENTREGA FUTURA": "LAST MILE",

    # Fiscal
    "EM ANÁLISE NO POSTO FISCAL": "PROB. FISCAL",
    "RETENCAO FISCAL DE DOCUMENTO E/OU MERCADORIA": "PROB. FISCAL",
    "SAIDA FISCALIZACAO": "PROB. FISCAL",

    # Zona rural
    #"ENDERECO EM ZONA RURAL": "ZONA RURAL",

    # Middle Mile
    "BUSCA": "MIDDLE MILE",
    "NAO ENTROU NA UNIDADE": "MIDDLE MILE",

    # Feriado
    "FECHADO EM VESPERA OU APOS FERIADO": "FERIADO",

    # Rodovia
    "TRAFEGO INTERROMPIDO": "RODOVIA INTERDITADA",

    # Clima
    "TEMPORAL": "PROB. CLIMÁTICO",

    # Triagem
    "ERRO DE TRIAGEM / SEPARACAO": "ERRO DE TRIAGEM",

    # Acareação
    "FALTA DE ACAREAÇÃO / TOTAL": "ACAREAÇÃO",
    "FALTA DE COMPROVANTE DE ENTREGA / TOTAL": "ACAREAÇÃO",

    # Área de risco
    "RESTRICAO DE ACESSO / MOVIMENTACAO": "ÁREA DE RISCO",

    # Sinistro
    "SINISTRO / ACIDENTE TRANSPORTE": "SINISTRO",
    "FURTO / ROUBO": "SINISTRO",

    # Tentativa de furto
    "PARADO B.O POLICIAL": "TENTATIVA DE FURTO",

    # Pedido recusado
    "RECUSADO": "PEDIDO RECUSADO",
    "RECUSADO - DIVERGENCIA DE PEDIDO": "PEDIDO RECUSADO",
    "RECUSADO - NAO PAGA FRETE": "PEDIDO RECUSADO",

    # Extravio
    "EXTRAVIO PARCIAL": "EXTRAVIO",
    "EXTRAVIO TOTAL": "EXTRAVIO",
    "PERDA POR PRAZO SLA / TOTAL": "EXTRAVIO",

    # Devolução
    "DEVOLUCAO POR INSTRUCAO MATRIZ": "DEVOLUCAO",
    "DEVOLUCAO POR INSTRUCAO REMETENTE": "DEVOLUCAO",
    "DEVOLUCAO RECUSADA": "DEVOLUCAO",

    # Mantido igual ao comportamento atual do dashboard.
    "": "LAST MILE",
}

MAPA_REGIAO = {
    # Norte
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",

    # Nordeste
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste",
    "RN": "Nordeste", "SE": "Nordeste",

    # Centro-Oeste
    "DF": "Centro-Oeste", "GO": "Centro-Oeste",
    "MT": "Centro-Oeste", "MS": "Centro-Oeste",

    # Sudeste
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",

    # Sul
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

OCORRENCIAS_JUSTIFICADAS = ("DEST. AUSENTE", "PROB. ENDEREÇO")
OPCAO_BAIXAS_INDEVIDAS = "Baixas indevidas"

COLUNAS_EXPORT_ATRASOS = [
    "Codigo",
    "Destino",
    "Dt Evento",
    "Previsao",
    "Previsao Ajustada",
    "Dias Atraso",
    "Faixa Atraso",
    "Ocorrencias",
]
