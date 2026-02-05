"""
services/gemini_service.py — Motor Híbrido de IA
Equivalente ao geminiService.ts.
Centraliza toda comunicação com Gemini API.
Usa modelo certo para cada tarefa:
  - Flash: busca rápida com Google Search
  - Pro: raciocínio profundo, análise estratégica, auditoria
"""
import json
import re
import time
from typing import Optional, Any
from google import genai
from google.genai import types

from services import cache
from services.request_queue import request_queue, Priority


# =============================================================================
# CONSTANTES
# =============================================================================

MODEL_FLASH = "gemini-2.5-flash"
MODEL_PRO = "gemini-2.5-pro"
MODEL_FLASH_LITE = "gemini-2.5-flash-lite"


# =============================================================================
# HELPERS
# =============================================================================

def _clean_json(text: str) -> Optional[dict]:
    """Extrai e parseia JSON de resposta do Gemini."""
    if not text:
        return None
    
    # Tenta extrair bloco JSON
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Tenta limpar markdown
    try:
        clean = text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        pass
    
    return None


def _clean_json_array(text: str) -> Optional[list]:
    """Extrai e parseia JSON array de resposta do Gemini."""
    if not text:
        return None
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def _safe_call(client, model: str, contents: str, config: types.GenerateContentConfig,
               priority: Priority = Priority.NORMAL) -> Optional[str]:
    """Wrapper seguro para chamada ao Gemini com rate limiting."""
    def _do_call():
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return resp.text
    
    try:
        return request_queue.execute(_do_call, priority=priority)
    except Exception as e:
        return None


# =============================================================================
# AGENTE 1: RECON OPERACIONAL (Flash + Search)
# =============================================================================

def agent_recon_operacional(client, empresa: str) -> dict:
    """
    Agente de Reconhecimento Operacional.
    Usa Flash + Google Search para mapear a estrutura física.
    """
    cache_key = {"agent": "recon", "empresa": empresa}
    cached = cache.get("agent_recon", cache_key)
    if cached:
        return cached
    
    prompt = f"""ATUE COMO: Investigador Agrícola Sênior com 20 anos de experiência.
ALVO: "{empresa}"

Você deve descobrir a ESTRUTURA FÍSICA E OPERACIONAL do grupo econômico.
Busque em múltiplas fontes (site oficial, LinkedIn, notícias, Econodata, etc).

INVESTIGUE:
1. Nome oficial do grupo econômico (pode ser diferente do nome fantasia)
2. Área TOTAL em hectares — se encontrar números diferentes, pegue o MAIS RECENTE
3. TODAS as culturas cultivadas (soja, milho, algodão, cana, café, HF, pecuária, etc)
4. Infraestrutura vertical: tem agroindústria? Silos? Sementeira? Algodoeira? Usina? Frigorífico?
5. Regiões onde opera (estados, municípios, biomas)
6. Número aproximado de fazendas/unidades
7. Tecnologias que usa (agricultura de precisão, drones, ERP, etc)

REGRAS:
- Seja FACTUAL. Não invente dados. Se não encontrar, diga 0.
- Se encontrar faixa (ex: "20 a 30 mil hectares"), use o valor MÉDIO.
- Atribua confiança de 0.0 a 1.0 aos dados encontrados.

Retorne APENAS JSON válido:
{{
    "nome_grupo": "Nome Real do Grupo",
    "hectares_total": numero,
    "culturas": ["lista", "de", "culturas"],
    "verticalizacao": {{
        "agroindustria": bool,
        "sementeira": bool,
        "silos": bool,
        "algodoeira": bool,
        "usina": bool,
        "frigorifico": bool,
        "fabrica_racao": bool
    }},
    "regioes_atuacao": ["MT", "GO"],
    "numero_fazendas": numero,
    "tecnologias_identificadas": ["lista"],
    "confianca": 0.8
}}"""

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.1,
        # Para modelos com thinking, budget de tokens para raciocínio
        thinking_config=types.ThinkingConfig(thinking_budget=2048),
    )
    
    text = _safe_call(client, MODEL_FLASH, prompt, config, Priority.HIGH)
    result = _clean_json(text) or {
        "nome_grupo": empresa,
        "hectares_total": 0,
        "confianca": 0.0,
    }
    
    cache.set("agent_recon", cache_key, result, ttl=7200)
    return result


# =============================================================================
# AGENTE 2: SNIPER FINANCEIRO (Flash + Search)
# =============================================================================

def agent_sniper_financeiro(client, empresa: str, nome_grupo: str = "") -> dict:
    """
    Agente Sniper Financeiro.
    Deep dive em movimentações financeiras, Fiagro, CRA, governança.
    """
    alvo = nome_grupo or empresa
    cache_key = {"agent": "financeiro", "empresa": alvo}
    cached = cache.get("agent_fin", cache_key)
    if cached:
        return cached
    
    prompt = f"""ATUE COMO: Analista Sênior de Mercado de Capitais especializado em Agro.
ALVO: "{alvo}" (também pesquise como "{empresa}" se for diferente)

Você é um detective financeiro. Vasculhe a web procurando ESPECIFICAMENTE:

1. EMISSÕES DE CRA (Certificados de Recebíveis do Agronegócio):
   - Valor, data, estruturador (Itaú BBA, BTG, XP, etc)
   - Séries, ratings

2. FIAGRO (Fundos de Investimento das Cadeias Produtivas Agroindustriais):
   - Fundos que investiram neles ou que eles criaram
   - Gestoras (Suno, XP, Valora, Capitânia, etc)
   - Ticker (ex: SNFZ11, VGIA11)

3. GOVERNANÇA CORPORATIVA:
   - Auditoria externa (Big 4: Deloitte, PwC, EY, KPMG)
   - Conselho de administração
   - Natureza jurídica (S.A. vs Ltda)
   
4. M&A (Fusões e Aquisições):
   - Compraram ou foram comprados?
   - Parcerias estratégicas

5. DADOS FINANCEIROS:
   - Capital social (Econodata, Casa dos Dados, Sócios Brasil)
   - Faturamento estimado
   - Número de funcionários (LinkedIn, RAIS)
   
6. PARCEIROS FINANCEIROS:
   - Bancos, gestoras, seguradoras com relacionamento

Retorne APENAS JSON válido:
{{
    "capital_social_estimado": numero,
    "funcionarios_estimados": numero,
    "faturamento_estimado": numero,
    "movimentos_financeiros": ["Fato 1: Emissão de CRA de R$50M via Itaú BBA em 2023", "Fato 2: ..."],
    "fiagros_relacionados": ["SNFZ11 (Suno)", "..."],
    "cras_emitidos": ["CRA Série X - R$YM - Estruturador Z"],
    "parceiros_financeiros": ["Itaú BBA", "XP", "..."],
    "auditorias": ["Deloitte", "..."],
    "governanca_corporativa": bool,
    "resumo_financeiro": "Texto curto sobre a robustez financeira do grupo.",
    "confianca": 0.7
}}"""

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.1,
        thinking_config=types.ThinkingConfig(thinking_budget=2048),
    )
    
    text = _safe_call(client, MODEL_FLASH, prompt, config, Priority.HIGH)
    result = _clean_json(text) or {"confianca": 0.0}
    
    cache.set("agent_fin", cache_key, result, ttl=7200)
    return result


# =============================================================================
# AGENTE 3: INTEL DE MERCADO (Flash + Search)
# =============================================================================

def agent_intel_mercado(client, empresa: str, setor_info: str = "") -> dict:
    """
    Agente de Inteligência de Mercado.
    Busca notícias recentes, sinais de compra, riscos e oportunidades.
    """
    cache_key = {"agent": "intel", "empresa": empresa}
    cached = cache.get("agent_intel", cache_key)
    if cached:
        return cached
    
    prompt = f"""ATUE COMO: Analista de Inteligência Competitiva focado em Agronegócio.
ALVO: "{empresa}"
{f'CONTEXTO DO SETOR: {setor_info}' if setor_info else ''}

Busque as NOTÍCIAS E SINAIS mais recentes (últimos 12 meses) sobre esta empresa.

INVESTIGUE:
1. NOTÍCIAS RECENTES: Expansão? Crise? Investimento? Novo projeto?
2. SINAIS DE COMPRA para ERP/tecnologia:
   - Expansão de área ou de operações
   - Contratação de C-level (CFO, CTO, CIO)
   - Problemas operacionais reportados
   - Auditoria ou IPO (precisam de sistemas)
3. RISCOS: Processos judiciais, problemas ambientais, inadimplência
4. CONCORRENTES: Quem mais atua no mesmo segmento/região?
5. OPORTUNIDADES: Janelas de venda, dores explícitas

Retorne APENAS JSON válido:
{{
    "noticias_recentes": [
        {{"titulo": "...", "resumo": "...", "data_aprox": "2024-XX", "relevancia": "alta/media/baixa"}},
    ],
    "sinais_compra": ["Sinal 1: ...", "Sinal 2: ..."],
    "riscos": ["Risco 1: ...", "Risco 2: ..."],
    "oportunidades": ["Oportunidade 1: ...", "Oportunidade 2: ..."],
    "concorrentes": ["Empresa X", "Empresa Y"],
    "dores_identificadas": ["Dor 1: ...", "Dor 2: ..."],
    "confianca": 0.7
}}"""

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=1024),
    )
    
    text = _safe_call(client, MODEL_FLASH, prompt, config, Priority.NORMAL)
    result = _clean_json(text) or {"confianca": 0.0}
    
    cache.set("agent_intel", cache_key, result, ttl=3600)
    return result


# =============================================================================
# AGENTE 4: ANÁLISE ESTRATÉGICA (Pro — Raciocínio Profundo)
# =============================================================================

def agent_analise_estrategica(client, dados_completos: dict, sas_result: dict,
                               contexto_mercado: str = "") -> str:
    """
    Agente Analista Estratégico.
    Usa Gemini Pro para análise profunda e redação do dossiê.
    """
    prompt = f"""VOCÊ É: Sara, Analista Sênior de Inteligência de Vendas para o Agronegócio.
Você trabalha na Senior Sistemas e prepara briefings estratégicos ("off-the-record") 
para Executivos de Contas que vão prospectar grandes operações agrícolas.

DADOS COLETADOS SOBRE O ALVO:
{json.dumps(dados_completos, indent=2, ensure_ascii=False, default=str)}

SCORE SAS 4.0: {sas_result.get('score', 0)}/1000 — Classificação: {sas_result.get('tier', 'N/D')}
BREAKDOWN: {json.dumps(sas_result.get('breakdown', {}), ensure_ascii=False)}

{contexto_mercado}

=== ESTRUTURA OBRIGATÓRIA DO BRIEFING ===

Escreva 4 seções, separadas EXATAMENTE por '|||':

SEÇÃO 1 — PERFIL E MERCADO:
- Quem é esse grupo? Qual o tamanho REAL da operação?
- Se emitiu CRA ou tem Fiagro, isso indica que é uma CORPORAÇÃO, não "fazendeiro"
- Contexto regional: o que está acontecendo na região deles?
- Se tem S.A. ou auditoria: trate como empresa com governança

SEÇÃO 2 — COMPLEXIDADE OPERACIONAL E DORES:
- Mapeie a complexidade: múltiplas culturas? Verticalização? Multisite?
- Quais as dores ESPECÍFICAS deste tipo de operação?
- Onde eles provavelmente têm gaps de gestão?
- NUNCA use dores genéricas — conecte com os dados reais

SEÇÃO 3 — FIT SENIOR (O PITCH):
- Quais módulos Senior resolvem as dores identificadas?
- Qual o argumento matador para esta conta específica?
- Se usa concorrente (TOTVS, SAP, Siagri), qual o argumento de troca?
- ROI estimado: onde Senior gera economia?

SEÇÃO 4 — PLANO DE ATAQUE:
- Quem é o decisor provável? (CFO? CEO? Dir. Operações?)
- Qual o timing ideal? (Safra? Entressafra? Pós-CRA?)
- Qual o gatilho de entrada? (Evento, dor aguda, expansão?)
- Estratégia de abordagem: primeiro contato, demo, proposta
- Red flags: o que pode dar errado?

=== REGRAS ===
1. Seja DIRETO e PRÁTICO. O executivo vai ler isso antes de uma reunião.
2. USE OS DADOS FINANCEIROS: Se tem CRA, Fiagro, auditoria — MENCIONE. Isso é ouro.
3. REALPOLITIK: 35k hectares + auditoria = corporação. Trate assim.
4. Separe as 4 seções com ||| (três pipes)
5. Mínimo 300 palavras por seção. Máximo 600.
6. Tom: profissional mas direto, como um briefing militar.
"""

    config = types.GenerateContentConfig(
        temperature=0.4,
        thinking_config=types.ThinkingConfig(thinking_budget=8192),
        max_output_tokens=16000,
    )
    
    text = _safe_call(client, MODEL_PRO, prompt, config, Priority.CRITICAL)
    return text or "Erro ao gerar análise estratégica."


# =============================================================================
# AGENTE 5: AUDITOR DE QUALIDADE (Pro)
# =============================================================================

def agent_auditor_qualidade(client, texto_dossie: str, dados: dict) -> dict:
    """
    Agente Auditor de Qualidade.
    Revisa o dossiê e pontua qualidade. Equivalente ao qualityGateService.ts.
    """
    prompt = f"""ATUE COMO: Editor-Chefe de um relatório de inteligência de vendas.
Você está revisando o dossiê abaixo antes de ser entregue ao Executivo de Contas.

=== DOSSIÊ A SER AUDITADO ===
{texto_dossie[:8000]}

=== DADOS BASE ===
{json.dumps(dados, indent=2, ensure_ascii=False, default=str)[:4000]}

=== AUDITORIA ===
Avalie o dossiê em cada critério (0 a 10) e justifique brevemente:

1. PRECISÃO: Os dados mencionados no texto correspondem ao JSON base?
2. PROFUNDIDADE: A análise vai além do óbvio? Cita dados financeiros específicos?
3. ACIONABILIDADE: O executivo sabe EXATAMENTE o que fazer depois de ler?
4. PERSONALIZAÇÃO: O texto é específico para ESTA empresa ou poderia ser genérico?
5. COMPLETUDE: As 4 seções estão presentes e completas?
6. DADOS_FINANCEIROS: Fiagro, CRA, auditoria foram MENCIONADOS se existem nos dados?

Retorne APENAS JSON:
{{
    "scores": {{
        "precisao": {{"nota": 8, "justificativa": "..."}},
        "profundidade": {{"nota": 7, "justificativa": "..."}},
        "acionabilidade": {{"nota": 9, "justificativa": "..."}},
        "personalizacao": {{"nota": 8, "justificativa": "..."}},
        "completude": {{"nota": 7, "justificativa": "..."}},
        "dados_financeiros": {{"nota": 9, "justificativa": "..."}}
    }},
    "nota_final": 8.0,
    "nivel": "EXCELENTE|BOM|ACEITAVEL|INSUFICIENTE",
    "recomendacoes": ["Recomendação 1", "Recomendação 2"]
}}"""

    config = types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=4096),
    )
    
    text = _safe_call(client, MODEL_PRO, prompt, config, Priority.NORMAL)
    result = _clean_json(text) or {
        "nota_final": 0,
        "nivel": "INSUFICIENTE",
        "recomendacoes": ["Erro na auditoria automática"],
    }
    return result


# =============================================================================
# BUSCA MÁGICA DE CNPJ (Flash + Search)
# =============================================================================

def buscar_cnpj_por_nome(client, nome_empresa: str) -> Optional[str]:
    """
    Busca Mágica: encontra CNPJ a partir do nome da empresa.
    """
    cache_key = {"busca_cnpj": nome_empresa}
    cached = cache.get("busca_cnpj", cache_key)
    if cached:
        return cached
    
    prompt = f"""Encontre o CNPJ principal da empresa/grupo "{nome_empresa}" do agronegócio brasileiro.
Busque em sites como Econodata, Casa dos Dados, Sócios Brasil, ou site oficial.
Retorne APENAS o CNPJ no formato XX.XXX.XXX/XXXX-XX ou "NAO_ENCONTRADO"."""

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.0,
    )
    
    text = _safe_call(client, MODEL_FLASH, prompt, config, Priority.HIGH)
    if text and "NAO_ENCONTRADO" not in text:
        # Tenta extrair CNPJ do texto
        match = re.search(r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}', text)
        if match:
            cnpj = match.group(0)
            cache.set("busca_cnpj", cache_key, cnpj, ttl=86400)
            return cnpj
    
    return None
