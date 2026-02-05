"""
services/dossier_orchestrator.py — O Maestro
Equivalente ao dossierOrchestrator.ts.
Pipeline de 6 passos para gerar um dossiê completo.
"""
import json
import time
from typing import Optional, Callable
from google import genai

from scout_types import (
    DossieCompleto, DadosCNPJ, DadosOperacionais, DadosFinanceiros,
    IntelMercado, SecaoAnalise, Verticalizacao, SASResult,
)
from services.gemini_service import (
    agent_recon_operacional,
    agent_sniper_financeiro,
    agent_intel_mercado,
    agent_analise_estrategica,
    agent_auditor_qualidade,
    buscar_cnpj_por_nome,
)
from services.cnpj_service import consultar_cnpj, limpar_cnpj, validar_cnpj
from services.market_estimator import calcular_sas
from services.quality_gate import executar_quality_gate
from utils.market_intelligence import enriquecer_prompt_com_contexto


# =============================================================================
# HELPERS
# =============================================================================

def _parse_operacional(raw: dict) -> DadosOperacionais:
    """Converte dict bruto do agente em DadosOperacionais tipado."""
    vert_raw = raw.get('verticalizacao', {})
    vert = Verticalizacao(
        agroindustria=vert_raw.get('agroindustria', False),
        sementeira=vert_raw.get('sementeira', False),
        silos=vert_raw.get('silos', False),
        algodoeira=vert_raw.get('algodoeira', False),
        usina=vert_raw.get('usina', False),
        frigorifico=vert_raw.get('frigorifico', False),
        fabrica_racao=vert_raw.get('fabrica_racao', False),
    )
    
    return DadosOperacionais(
        nome_grupo=raw.get('nome_grupo', ''),
        hectares_total=int(raw.get('hectares_total', 0) or 0),
        culturas=raw.get('culturas', []) or [],
        verticalizacao=vert,
        regioes_atuacao=raw.get('regioes_atuacao', []) or [],
        numero_fazendas=int(raw.get('numero_fazendas', 0) or 0),
        tecnologias_identificadas=raw.get('tecnologias_identificadas', []) or [],
        confianca=float(raw.get('confianca', 0) or 0),
    )


def _parse_financeiro(raw: dict) -> DadosFinanceiros:
    """Converte dict bruto do agente em DadosFinanceiros tipado."""
    return DadosFinanceiros(
        capital_social_estimado=float(raw.get('capital_social_estimado', 0) or 0),
        funcionarios_estimados=int(raw.get('funcionarios_estimados', 0) or 0),
        faturamento_estimado=float(raw.get('faturamento_estimado', 0) or 0),
        movimentos_financeiros=raw.get('movimentos_financeiros', []) or [],
        fiagros_relacionados=raw.get('fiagros_relacionados', []) or [],
        cras_emitidos=raw.get('cras_emitidos', []) or [],
        parceiros_financeiros=raw.get('parceiros_financeiros', []) or [],
        auditorias=raw.get('auditorias', []) or [],
        governanca_corporativa=bool(raw.get('governanca_corporativa', False)),
        resumo_financeiro=raw.get('resumo_financeiro', ''),
        confianca=float(raw.get('confianca', 0) or 0),
    )


def _parse_intel(raw: dict) -> IntelMercado:
    """Converte dict bruto do agente em IntelMercado tipado."""
    return IntelMercado(
        noticias_recentes=raw.get('noticias_recentes', []) or [],
        concorrentes=raw.get('concorrentes', []) or [],
        tendencias_setor=raw.get('tendencias_setor', []) or [],
        dores_identificadas=raw.get('dores_identificadas', []) or [],
        oportunidades=raw.get('oportunidades', []) or [],
        sinais_compra=raw.get('sinais_compra', []) or [],
        riscos=raw.get('riscos', []) or [],
        confianca=float(raw.get('confianca', 0) or 0),
    )


def _parse_secoes(texto: str) -> list[SecaoAnalise]:
    """Divide a análise em seções usando |||."""
    TITULOS = [
        ("🏢", "Perfil e Mercado"),
        ("🚜", "Complexidade e Dores"),
        ("💡", "Fit Senior (O Pitch)"),
        ("⚔️", "Plano de Ataque"),
    ]
    
    partes = texto.split('|||')
    secoes = []
    
    for i, parte in enumerate(partes):
        parte = parte.strip()
        if not parte:
            continue
        
        if i < len(TITULOS):
            icone, titulo = TITULOS[i]
        else:
            icone, titulo = "📄", f"Seção {i+1}"
        
        secoes.append(SecaoAnalise(
            titulo=titulo,
            conteudo=parte,
            icone=icone,
        ))
    
    # Fallback: se não conseguiu dividir
    if len(secoes) < 2:
        secoes = [SecaoAnalise(
            titulo="Análise Completa",
            conteudo=texto,
            icone="🧠",
        )]
    
    return secoes


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def gerar_dossie_completo(
    empresa_alvo: str,
    api_key: str,
    cnpj: str = "",
    log_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> DossieCompleto:
    """
    Pipeline de 6 passos para gerar um dossiê completo.
    
    Passo 1: Consulta CNPJ (BrasilAPI)
    Passo 2: Recon Operacional (Flash + Search)
    Passo 3: Sniper Financeiro (Flash + Search)
    Passo 4: Intel de Mercado (Flash + Search)
    Passo 5: Análise Estratégica (Pro — Deep Thinking)
    Passo 6: Quality Gate (Determinístico + Pro)
    """
    start_time = time.time()
    client = genai.Client(api_key=api_key)
    
    dossie = DossieCompleto(empresa_alvo=empresa_alvo, cnpj=cnpj)
    
    def _log(msg: str):
        dossie.pipeline_log.append(msg)
        if log_callback:
            log_callback(msg)
    
    def _progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)
    
    # =========================================================================
    # PASSO 1: CONSULTA CNPJ
    # =========================================================================
    _progress(0.05, "🔍 Passo 1/6: Consultando CNPJ...")
    _log("Passo 1: Consulta CNPJ")
    
    if cnpj and validar_cnpj(limpar_cnpj(cnpj)):
        dados_cnpj = consultar_cnpj(cnpj)
        if dados_cnpj:
            dossie.dados_cnpj = dados_cnpj
            dossie.cnpj = cnpj
            _log(f"  ✅ CNPJ encontrado: {dados_cnpj.razao_social}")
        else:
            _log(f"  ⚠️ CNPJ {cnpj} não encontrado na BrasilAPI")
    else:
        # Busca mágica: tenta encontrar CNPJ pelo nome
        _log("  🔮 Tentando Busca Mágica de CNPJ...")
        cnpj_encontrado = buscar_cnpj_por_nome(client, empresa_alvo)
        if cnpj_encontrado:
            _log(f"  ✅ CNPJ encontrado via IA: {cnpj_encontrado}")
            dados_cnpj = consultar_cnpj(cnpj_encontrado)
            if dados_cnpj:
                dossie.dados_cnpj = dados_cnpj
                dossie.cnpj = cnpj_encontrado
        else:
            _log("  ℹ️ CNPJ não encontrado — continuando sem dados cadastrais")
    
    # =========================================================================
    # PASSO 2: RECON OPERACIONAL
    # =========================================================================
    _progress(0.20, "🛰️ Passo 2/6: Reconhecimento Operacional...")
    _log("Passo 2: Agente Recon Operacional (Flash + Search)")
    
    raw_ops = agent_recon_operacional(client, empresa_alvo)
    dossie.dados_operacionais = _parse_operacional(raw_ops)
    
    nome_grupo = dossie.dados_operacionais.nome_grupo or empresa_alvo
    _log(f"  ✅ Grupo: {nome_grupo} | {dossie.dados_operacionais.hectares_total:,} ha | "
         f"Culturas: {', '.join(dossie.dados_operacionais.culturas)} | "
         f"Confiança: {dossie.dados_operacionais.confianca:.0%}")
    
    # =========================================================================
    # PASSO 3: SNIPER FINANCEIRO
    # =========================================================================
    _progress(0.40, "💰 Passo 3/6: Deep Dive Financeiro...")
    _log("Passo 3: Agente Sniper Financeiro (Flash + Search)")
    
    raw_fin = agent_sniper_financeiro(client, empresa_alvo, nome_grupo)
    dossie.dados_financeiros = _parse_financeiro(raw_fin)
    
    n_mov = len(dossie.dados_financeiros.movimentos_financeiros)
    n_fiagro = len(dossie.dados_financeiros.fiagros_relacionados)
    _log(f"  ✅ {n_mov} movimentos financeiros | {n_fiagro} Fiagros | "
         f"Capital: R${dossie.dados_financeiros.capital_social_estimado/1e6:.1f}M | "
         f"Confiança: {dossie.dados_financeiros.confianca:.0%}")
    
    # =========================================================================
    # PASSO 4: INTEL DE MERCADO
    # =========================================================================
    _progress(0.55, "📡 Passo 4/6: Inteligência de Mercado...")
    _log("Passo 4: Agente Intel de Mercado (Flash + Search)")
    
    # Enriquece com contexto estático
    cnae = ""
    uf = ""
    if dossie.dados_cnpj:
        cnae = dossie.dados_cnpj.cnae_principal
        uf = dossie.dados_cnpj.uf
    elif dossie.dados_operacionais.regioes_atuacao:
        uf = dossie.dados_operacionais.regioes_atuacao[0]
    
    contexto_setor = enriquecer_prompt_com_contexto(cnae, uf)
    
    raw_intel = agent_intel_mercado(client, empresa_alvo, contexto_setor)
    dossie.intel_mercado = _parse_intel(raw_intel)
    
    n_noticias = len(dossie.intel_mercado.noticias_recentes)
    n_sinais = len(dossie.intel_mercado.sinais_compra)
    _log(f"  ✅ {n_noticias} notícias | {n_sinais} sinais de compra | "
         f"Confiança: {dossie.intel_mercado.confianca:.0%}")
    
    # =========================================================================
    # PASSO 4.5: CÁLCULO DO SCORE SAS 4.0
    # =========================================================================
    _progress(0.65, "📊 Calculando Score SAS 4.0...")
    _log("Passo 4.5: Cálculo do Score SAS 4.0")
    
    dados_merged = dossie.merge_dados()
    dossie.sas_result = calcular_sas(dados_merged)
    
    _log(f"  ✅ Score: {dossie.sas_result.score}/1000 — {dossie.sas_result.tier.value}")
    for j in dossie.sas_result.justificativas:
        _log(f"    → {j}")
    
    # =========================================================================
    # PASSO 5: ANÁLISE ESTRATÉGICA (PRO — Deep Thinking)
    # =========================================================================
    _progress(0.75, "🧠 Passo 5/6: Análise Estratégica (Gemini Pro)...")
    _log("Passo 5: Agente Analista Estratégico (Gemini Pro — Deep Thinking)")
    
    # Monta dict completo para o prompt
    dados_para_analise = dados_merged.copy()
    dados_para_analise['intel_mercado'] = {
        'noticias': dossie.intel_mercado.noticias_recentes,
        'sinais_compra': dossie.intel_mercado.sinais_compra,
        'dores': dossie.intel_mercado.dores_identificadas,
        'oportunidades': dossie.intel_mercado.oportunidades,
        'riscos': dossie.intel_mercado.riscos,
        'concorrentes': dossie.intel_mercado.concorrentes,
    }
    
    sas_dict = {
        'score': dossie.sas_result.score,
        'tier': dossie.sas_result.tier.value,
        'breakdown': dossie.sas_result.breakdown.to_dict(),
    }
    
    texto_analise = agent_analise_estrategica(
        client, dados_para_analise, sas_dict, contexto_setor,
    )
    
    dossie.analise_bruta = texto_analise
    dossie.secoes_analise = _parse_secoes(texto_analise)
    dossie.modelo_usado = "gemini-2.5-pro (análise) + gemini-2.5-flash (recon/search)"
    
    n_secoes = len(dossie.secoes_analise)
    n_palavras = sum(len(s.conteudo.split()) for s in dossie.secoes_analise)
    _log(f"  ✅ {n_secoes} seções geradas | {n_palavras} palavras")
    
    # =========================================================================
    # PASSO 6: QUALITY GATE
    # =========================================================================
    _progress(0.90, "✅ Passo 6/6: Auditoria de Qualidade...")
    _log("Passo 6: Quality Gate")
    
    # Quality Gate determinístico
    dossie.quality_report = executar_quality_gate(dossie)
    _log(f"  ✅ Nível: {dossie.quality_report.nivel.value} "
         f"({dossie.quality_report.score_qualidade:.0f}%)")
    
    # Auditoria por IA (Pro) — opcional, adiciona profundidade
    try:
        audit_ia = agent_auditor_qualidade(client, texto_analise, dados_para_analise)
        dossie.quality_report.recomendacoes.extend(
            audit_ia.get('recomendacoes', [])
        )
        ia_nota = audit_ia.get('nota_final', 0)
        _log(f"  ✅ Auditoria IA: nota {ia_nota}/10")
    except Exception as e:
        _log(f"  ⚠️ Auditoria IA falhou: {e}")
    
    # Finalização
    dossie.tempo_total_segundos = time.time() - start_time
    dossie.timestamp_geracao = time.strftime("%Y-%m-%d %H:%M:%S")
    
    _progress(1.0, "🎯 Dossiê completo!")
    _log(f"Pipeline completo em {dossie.tempo_total_segundos:.1f}s")
    
    return dossie
