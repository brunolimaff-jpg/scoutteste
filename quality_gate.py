"""
services/quality_gate.py — Auditor de Qualidade
Equivalente ao qualityGateService.ts.
Executa verificações determinísticas + IA sobre o dossiê gerado.
"""
import time
from scout_types import (
    QualityReport, QualityCheck, QualityLevel, DossieCompleto,
)


def _check_dados_cadastrais(dossie: DossieCompleto) -> QualityCheck:
    """Verifica se dados cadastrais básicos existem."""
    tem_cnpj = dossie.dados_cnpj is not None
    tem_razao = bool(dossie.dados_cnpj and dossie.dados_cnpj.razao_social)
    tem_cnae = bool(dossie.dados_cnpj and dossie.dados_cnpj.cnae_principal)
    
    total = sum([tem_cnpj, tem_razao, tem_cnae])
    passou = total >= 2
    
    return QualityCheck(
        criterio="Dados Cadastrais (CNPJ, Razão Social, CNAE)",
        passou=passou,
        nota=f"{total}/3 campos preenchidos",
        peso=1.0,
    )


def _check_dados_operacionais(dossie: DossieCompleto) -> QualityCheck:
    """Verifica se dados operacionais foram coletados."""
    ops = dossie.dados_operacionais
    tem_hectares = ops.hectares_total > 0
    tem_culturas = len(ops.culturas) > 0
    tem_regioes = len(ops.regioes_atuacao) > 0
    confianca_ok = ops.confianca >= 0.5
    
    total = sum([tem_hectares, tem_culturas, tem_regioes, confianca_ok])
    passou = total >= 2
    
    return QualityCheck(
        criterio="Dados Operacionais (Hectares, Culturas, Regiões)",
        passou=passou,
        nota=f"{total}/4 indicadores OK | Confiança: {ops.confianca:.0%}",
        peso=1.5,
    )


def _check_dados_financeiros(dossie: DossieCompleto) -> QualityCheck:
    """Verifica se dados financeiros foram coletados."""
    fin = dossie.dados_financeiros
    tem_capital = fin.capital_social_estimado > 0
    tem_funcs = fin.funcionarios_estimados > 0
    tem_movimentos = len(fin.movimentos_financeiros) > 0
    tem_governanca = fin.governanca_corporativa or len(fin.auditorias) > 0
    
    total = sum([tem_capital, tem_funcs, tem_movimentos, tem_governanca])
    passou = total >= 2
    
    return QualityCheck(
        criterio="Dados Financeiros (Capital, Funcionários, Movimentos)",
        passou=passou,
        nota=f"{total}/4 indicadores | {len(fin.movimentos_financeiros)} movimentos detectados",
        peso=1.5,
    )


def _check_analise_gerada(dossie: DossieCompleto) -> QualityCheck:
    """Verifica se a análise estratégica foi gerada adequadamente."""
    secoes = dossie.secoes_analise
    tem_secoes = len(secoes) >= 3
    
    total_palavras = sum(len(s.conteudo.split()) for s in secoes)
    palavras_ok = total_palavras >= 400
    
    passou = tem_secoes and palavras_ok
    
    return QualityCheck(
        criterio="Análise Estratégica (4 seções, profundidade)",
        passou=passou,
        nota=f"{len(secoes)} seções | {total_palavras} palavras total",
        peso=2.0,
    )


def _check_score_calculado(dossie: DossieCompleto) -> QualityCheck:
    """Verifica se o score foi calculado."""
    tem_score = dossie.sas_result.score > 0
    tem_breakdown = dossie.sas_result.breakdown.total > 0
    
    return QualityCheck(
        criterio="Score SAS 4.0 Calculado",
        passou=tem_score and tem_breakdown,
        nota=f"Score: {dossie.sas_result.score}/1000 ({dossie.sas_result.tier.value})",
        peso=1.0,
    )


def executar_quality_gate(dossie: DossieCompleto) -> QualityReport:
    """
    Executa todas as verificações de qualidade (determinísticas).
    O audit pela IA é feito separadamente via agent_auditor_qualidade.
    """
    checks = [
        _check_dados_cadastrais(dossie),
        _check_dados_operacionais(dossie),
        _check_dados_financeiros(dossie),
        _check_analise_gerada(dossie),
        _check_score_calculado(dossie),
    ]
    
    # Calcular score ponderado
    total_peso = sum(c.peso for c in checks)
    score_ponderado = sum(c.peso * (1.0 if c.passou else 0.0) for c in checks) / total_peso
    score_percentual = score_ponderado * 100
    
    # Determinar nível
    if score_percentual >= 85:
        nivel = QualityLevel.EXCELENTE
    elif score_percentual >= 65:
        nivel = QualityLevel.BOM
    elif score_percentual >= 45:
        nivel = QualityLevel.ACEITAVEL
    else:
        nivel = QualityLevel.INSUFICIENTE
    
    # Gerar recomendações
    recomendacoes = []
    for check in checks:
        if not check.passou:
            recomendacoes.append(f"⚠️ {check.criterio}: {check.nota}")
    
    return QualityReport(
        nivel=nivel,
        score_qualidade=score_percentual,
        checks=checks,
        recomendacoes=recomendacoes,
        timestamp=str(time.time()),
    )
