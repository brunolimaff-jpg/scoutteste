"""
services/cnpj_service.py — Wrapper BrasilAPI
Equivalente ao cnpjService.ts.
Consulta CNPJ com cache, retry automático e fallback.
"""
import re
import requests
import time
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from scout_types import DadosCNPJ
from services import cache


# =============================================================================
# HELPERS
# =============================================================================

def limpar_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ."""
    return re.sub(r'\D', '', cnpj.strip())


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ: XX.XXX.XXX/XXXX-XX"""
    cnpj = limpar_cnpj(cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def validar_cnpj(cnpj: str) -> bool:
    """Validação básica de CNPJ (tamanho + não tudo igual)."""
    cnpj = limpar_cnpj(cnpj)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False
    return True


# =============================================================================
# API CALLS (com retry)
# =============================================================================

class CNPJServiceError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
)
def _consultar_brasilapi(cnpj: str) -> dict:
    """Consulta a BrasilAPI com retry automático."""
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    resp = requests.get(url, timeout=15)
    
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 404:
        raise CNPJServiceError(f"CNPJ {cnpj} não encontrado")
    elif resp.status_code == 429:
        time.sleep(5)  # Rate limit — espera e tenta de novo
        raise requests.ConnectionError("Rate limited, retrying")
    else:
        raise CNPJServiceError(f"Erro na BrasilAPI: HTTP {resp.status_code}")


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
)
def _consultar_receitaws(cnpj: str) -> dict:
    """Fallback: ReceitaWS."""
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "ERROR":
            raise CNPJServiceError(data.get("message", "Erro ReceitaWS"))
        return data
    raise CNPJServiceError(f"ReceitaWS: HTTP {resp.status_code}")


# =============================================================================
# SERVIÇO PRINCIPAL
# =============================================================================

def _parse_brasilapi_response(data: dict) -> DadosCNPJ:
    """Converte resposta da BrasilAPI para DadosCNPJ."""
    qsa = []
    for socio in data.get("qsa", []):
        qsa.append({
            "nome": socio.get("nome_socio", ""),
            "qualificacao": socio.get("qualificacao_socio", ""),
            "data_entrada": socio.get("data_entrada_sociedade", ""),
            "cpf_cnpj": socio.get("cnpj_cpf_do_socio", ""),
            "faixa_etaria": socio.get("faixa_etaria", ""),
        })
    
    cnaes_sec = []
    for cnae in data.get("cnaes_secundarios", []):
        if cnae.get("codigo"):
            cnaes_sec.append(f"{cnae['codigo']} - {cnae.get('descricao', '')}")
    
    return DadosCNPJ(
        cnpj=data.get("cnpj", ""),
        razao_social=data.get("razao_social", ""),
        nome_fantasia=data.get("nome_fantasia", ""),
        situacao_cadastral=data.get("descricao_situacao_cadastral", ""),
        data_abertura=data.get("data_inicio_atividade", ""),
        natureza_juridica=data.get("descricao_natureza_juridica", ""),
        capital_social=float(data.get("capital_social", 0)),
        porte=data.get("descricao_porte", ""),
        cnae_principal=str(data.get("cnae_fiscal", "")),
        cnae_descricao=data.get("cnae_fiscal_descricao", ""),
        cnaes_secundarios=cnaes_sec,
        municipio=data.get("municipio", ""),
        uf=data.get("uf", ""),
        cep=data.get("cep", ""),
        logradouro=data.get("logradouro", ""),
        numero=data.get("numero", ""),
        complemento=data.get("complemento", ""),
        bairro=data.get("bairro", ""),
        telefone=data.get("ddd_telefone_1", ""),
        email=data.get("email", ""),
        qsa=qsa,
        fonte="brasilapi",
        timestamp=str(time.time()),
    )


def consultar_cnpj(cnpj: str) -> Optional[DadosCNPJ]:
    """
    Consulta CNPJ com cache + retry + fallback.
    Pipeline: Cache → BrasilAPI → ReceitaWS
    """
    cnpj_limpo = limpar_cnpj(cnpj)
    
    if not validar_cnpj(cnpj_limpo):
        return None
    
    # Check cache
    cached = cache.get("cnpj", {"cnpj": cnpj_limpo})
    if cached is not None:
        return cached
    
    # Tenta BrasilAPI
    try:
        raw = _consultar_brasilapi(cnpj_limpo)
        resultado = _parse_brasilapi_response(raw)
        cache.set("cnpj", {"cnpj": cnpj_limpo}, resultado, ttl=86400)  # 24h
        return resultado
    except Exception:
        pass
    
    # Fallback ReceitaWS
    try:
        raw = _consultar_receitaws(cnpj_limpo)
        # ReceitaWS tem formato ligeiramente diferente, adaptamos
        resultado = DadosCNPJ(
            cnpj=cnpj_limpo,
            razao_social=raw.get("nome", ""),
            nome_fantasia=raw.get("fantasia", ""),
            situacao_cadastral=raw.get("situacao", ""),
            capital_social=float(str(raw.get("capital_social", "0")).replace(".", "").replace(",", ".")),
            cnae_principal=raw.get("atividade_principal", [{}])[0].get("code", ""),
            cnae_descricao=raw.get("atividade_principal", [{}])[0].get("text", ""),
            municipio=raw.get("municipio", ""),
            uf=raw.get("uf", ""),
            fonte="receitaws",
            timestamp=str(time.time()),
        )
        cache.set("cnpj", {"cnpj": cnpj_limpo}, resultado, ttl=86400)
        return resultado
    except Exception:
        return None
