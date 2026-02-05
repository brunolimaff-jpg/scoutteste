from google import genai
from google.genai import types
import json
import streamlit as st
import random

# ==========================================
# 1. CONFIGURAÇÃO DA SARA (PERSONALIDADE)
# ==========================================
SARA_PHRASES = [
    "☕ Enchendo a garrafa de café e calibrando o GPS...",
    "🚜 Ligando os motores e verificando o óleo da inteligência...",
    "👢 Calçando a botina para entrar no mato digital...",
    "🤠 Ajeitando o chapéu: hora de caçar oportunidades...",
    "📡 Ajustando a antena da Starlink para achar sinal de dinheiro..."
]

SYSTEM_PROMPT_SARA = """
VOCÊ É: Sara, Analista Sênior de Inteligência de Vendas (Agro).
SUA MISSÃO: Escrever um briefing estratégico ("off-the-record") para um Executivo de Contas da Senior Sistemas.

O QUE VOCÊ VAI RECEBER: Dados da empresa e contexto de mercado.
O QUE VOCÊ DEVE ENTREGAR: 4 BLOCOS de texto distintos, escritos em PROSA FLUIDA, DIRETA e ANALÍTICA.

REGRAS DE TOM E ESTILO:
1. ZERO CORPORATÊS: Não use frases vazias.
2. REALPOLITIK: Fale da verdade nua e crua.
3. CAUSA & EFEITO: Conecte os dados.
4. ESPECIFICIDADE: Use os números fornecidos.

ESTRUTURA DA RESPOSTA (Use Markdown):
## 🏢 Perfil e Mercado
(Texto analítico aqui)

## 🚜 Complexidade Operacional e Dores
(Foque em gargalos de safra, logística e gestão)

## 💡 Fit com Soluções Senior (Gatec/ERP)
(Por que eles precisam de nós?)

## ⚔️ Plano de Ataque
(Abordagem sugerida)
"""

# ==========================================
# 2. MOTOR SAS 4.0 (A MATEMÁTICA)
# ==========================================
def calculate_sas_score(data):
    def lookup_capital(val):
        if val >= 100_000_000: return 200
        if val >= 50_000_000: return 150
        if val >= 10_000_000: return 100
        if val >= 1_000_000: return 50
        return 0

    def lookup_hectares(val):
        if val >= 50_000: return 200
        if val >= 10_000: return 150
        if val >= 3_000: return 100
        if val >= 500: return 50
        return 0
    
    def lookup_cultura(txt):
        txt = txt.lower() if txt else ""
        if 'bioenergia' in txt or 'cana' in txt: return 150
        if 'semente' in txt or 'seed' in txt: return 130
        if 'algod' in txt or 'cotton' in txt: return 120
        if 'café' in txt or 'coffee' in txt: return 110
        if 'soja' in txt or 'milho' in txt: return 80
        if 'gado' in txt or 'boi' in txt: return 30
        return 50

    def lookup_funcionarios(val):
        if val >= 500: return 120
        if val >= 200: return 90
        if val >= 100: return 60
        if val >= 50: return 30
        return 0

    capital = data.get('capital_social', 0)
    hectares = data.get('hectares', 0)
    cultura = data.get('cultura_principal', '')
    funcionarios = data.get('funcionarios', 0)
    
    pilar_musculo = min(lookup_capital(capital) + lookup_hectares(hectares), 400)
    
    cultura_pts = lookup_cultura(cultura)
    verticalizacao_pts = 50 if data.get('agroindustria') else 0
    pilar_complexidade = min(cultura_pts + verticalizacao_pts, 250)
    
    pilar_gente = min(lookup_funcionarios(funcionarios), 200)
    pilar_momento = 80 
    
    sas_final = pilar_musculo + pilar_complexidade + pilar_gente + pilar_momento
    sas_final = min(sas_final, 1000)
    
    if sas_final >= 751: tier = "DIAMANTE 💎"
    elif sas_final >= 501: tier = "OURO 🥇"
    elif sas_final >= 251: tier = "PRATA 🥈"
    else: tier = "BRONZE 🥉"
    
    return {
        "score": sas_final,
        "tier": tier,
        "breakdown": {
            "Músculo": pilar_musculo,
            "Complexidade": pilar_complexidade,
            "Gente": pilar_gente,
            "Momento": pilar_momento
        }
    }

# ==========================================
# 3. MOTOR DE IA (NOVA SDK: GOOGLE-GENAI)
# ==========================================
def investigate_company(company_name, api_key):
    # Inicializa o Cliente da Nova SDK
    client = genai.Client(api_key=api_key)
    
    # Configuração da Ferramenta de Busca
    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    
    # Passo 1: Buscar Dados Reais (JSON Mode + Search)
    search_prompt = f"""
    Investigue a empresa agrícola: "{company_name}".
    Procure dados exatos ou estimados na web sobre:
    1. Hectares plantados (aprox).
    2. Quantidade de funcionários.
    3. Capital Social estimado.
    4. Principais culturas (Soja, Milho, Algodão, Cana).
    5. Se possui agroindústria própria.
    
    Retorne APENAS um JSON neste formato:
    {{
        "capital_social": numero,
        "hectares": numero,
        "funcionarios": numero,
        "cultura_principal": "texto",
        "agroindustria": boolean,
        "resumo_operacao": "texto curto"
    }}
    """
    
    # Chamada para buscar dados (JSON)
    try:
        response_data = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=search_prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                response_mime_type='application/json'
            )
        )
        hard_data = json.loads(response_data.text)
    except Exception as e:
        print(f"Erro JSON: {e}")
        hard_data = {
            "capital_social": 1000000, "hectares": 1000, 
            "funcionarios": 50, "cultura_principal": "Grãos", 
            "agroindustria": False, "resumo_operacao": "Dados estimados (Falha na extração)"
        }

    # Passo 2: Calcular Score
    score_result = calculate_sas_score(hard_data)
    
    # Passo 3: Gerar Narrativa Estratégica (Sara)
    analysis_prompt = f"""
    CONTEXTO DA EMPRESA: {json.dumps(hard_data)}
    SCORE CALCULADO: {score_result['score']} ({score_result['tier']})
    
    {SYSTEM_PROMPT_SARA}
    """
    
    # Chamada para análise textual (Sem JSON mode, com Search)
    response_analysis = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=analysis_prompt,
        config=types.GenerateContentConfig(
            tools=[google_search_tool]
        )
    )
    
    return hard_data, score_result, response_analysis.text
