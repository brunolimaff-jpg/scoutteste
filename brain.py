from google import genai
from google.genai import types
import json
import re
import streamlit as st

# ==============================================================================
# 1. HELPER: LIMPEZA DE JSON (A Correção do Erro 400)
# ==============================================================================
def clean_and_parse_json(text):
    """
    Remove blocos de código markdown (```json ... ```) e tenta parsear.
    Essencial porque não podemos usar response_mime_type='application/json' com Tools.
    """
    try:
        # Remove marcadores de código se existirem
        clean_text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        clean_text = re.sub(r'```\s*$', '', clean_text, flags=re.IGNORECASE)
        clean_text = clean_text.strip()
        return json.loads(clean_text)
    except Exception:
        # Fallback agressivo: tenta achar o primeiro '{' e o último '}'
        try:
            start = clean_text.find('{')
            end = clean_text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(clean_text[start:end])
            return None
        except:
            return None

# ==============================================================================
# 2. PERSONALIDADE E PROMPTS
# ==============================================================================

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
    
    O QUE VOCÊ VAI RECEBER: Um JSON com dados brutos da empresa (Faturamento, Cultura, Verticalização, Notícias).
    O QUE VOCÊ DEVE ENTREGAR: 4 BLOCOS de texto distintos, escritos em PROSA FLUIDA, DIRETA e ANALÍTICA.
    
    REGRAS DE TOM E ESTILO:
    1. ZERO CORPORATÊS: Não use frases vazias.
    2. REALPOLITIK: Fale da verdade nua e crua.
    3. CAUSA & EFEITO: Conecte os dados.
    4. ESPECIFICIDADE: Use os números do JSON.

    REGRAS DE OURO DO PORTFÓLIO:
    - Agroindústria: Venda GAtec (Originação/Indústria) + ERP (Backoffice).
    - Produtor: Venda GAtec (Campo) + ERP (Fiscal).

    SAÍDA STRICT (RÍGIDA):
    1. NÃO use Introduções ("Aqui está...", "Com base nos dados...").
    2. NÃO use Títulos Markdown (como '# Seção 1: Perfil').
    3. Retorne OBRIGATORIAMENTE 4 blocos de texto separados pela string delimitadora '|||'.
    
    ESTRUTURA EXATA DA RESPOSTA:
    [Texto do Perfil e Mercado] ||| [Texto da Complexidade Operacional e Dores] ||| [Texto da Proposta de Valor / Fit Senior] ||| [Texto dos Insights de Ataque e Abordagem]
"""

# ==============================================================================
# 3. MOTOR SAS 4.0 - FÓRMULA EXATA
# ==============================================================================

def calculate_sas_score(lead):
    # Lookup Tables
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
        txt = str(txt).lower() if txt else ""
        if 'bioenergia' in txt or 'cana' in txt: return 150
        if 'semente' in txt or 'seed' in txt: return 130
        if 'algod' in txt or 'cotton' in txt: return 120
        if 'café' in txt or 'coffee' in txt: return 110
        if 'soja' in txt or 'milho' in txt or 'gr' in txt: return 80
        if 'gado' in txt or 'boi' in txt or 'pecu' in txt: return 30
        return 50

    def lookup_funcionarios(val):
        if val >= 500: return 120
        if val >= 200: return 90
        if val >= 100: return 60
        if val >= 50: return 30
        return 0
    
    def lookup_natureza(txt):
        txt = str(txt).lower() if txt else ""
        if 's.a' in txt or 'anônima' in txt: return 50
        if 'cooperativa' in txt: return 15
        if 'ltda' in txt: return 20
        return 10

    # Extração de dados (com defaults seguros)
    capital = lead.get('capital_social', 0)
    hectares = lead.get('hectares', 0)
    cultura = lead.get('cultura_principal', '')
    funcionarios = lead.get('funcionarios', 0)
    natureza = lead.get('natureza_juridica', '')
    
    # --- CÁLCULO DOS PILARES ---
    pilar_musculo = min(lookup_capital(capital) + lookup_hectares(hectares), 400)
    
    cultura_pts = lookup_cultura(cultura)
    verticalizacao_pts = 0
    if lead.get('agroindustria'): verticalizacao_pts += 50
    if lead.get('silos'): verticalizacao_pts += 30
    
    complexidade_bruto = min(cultura_pts + verticalizacao_pts, 250)
    if 'semente' in str(cultura).lower():
        complexidade_bruto = min(complexidade_bruto * 1.15, 250)
    pilar_complexidade = int(complexidade_bruto)
    
    pilar_gente = min(lookup_funcionarios(funcionarios), 200)
    
    natureza_pts = lookup_natureza(natureza)
    presenca_pts = 40 
    if lead.get('vagas_ti'): presenca_pts += 25
    pilar_momento = min(natureza_pts + presenca_pts, 150)
    
    bonus = 50 if lookup_natureza(natureza) == 50 else 0
    
    sas_final = pilar_musculo + pilar_complexidade + pilar_gente + pilar_momento + bonus
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

# ==============================================================================
# 3. MOTOR DE IA (GOOGLE GENAI SDK - CORRIGIDO)
# ==============================================================================

def investigate_company(query_input, api_key):
    client = genai.Client(api_key=api_key)
    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    
    # --------------------------------------------------------------------------
    # PASSO 1: RECONHECIMENTO DE GRUPO (SEM response_mime_type)
    # --------------------------------------------------------------------------
    recon_prompt = f"""
    ATUE COMO: Investigador Corporativo Sênior.
    ALVO: "{query_input}"
    
    TAREFA CRÍTICA: Identificar se este alvo faz parte de um GRUPO ECONÔMICO ou FAMILIAR maior.
    
    Pesquise profundamente na web (notícias, LinkedIn, relatórios).
    Retorne APENAS um JSON válido (sem texto antes ou depois) com estes campos:
    
    {{
        "nome_grupo": "Nome do Grupo",
        "hectares_total": numero (estimativa do grupo todo, SOMENTE NUMEROS),
        "funcionarios_estimados": numero,
        "capital_social_estimado": numero (soma aproximada),
        "culturas": ["Soja", "Milho", "Algodão", etc],
        "verticalizacao": {{
            "agroindustria": boolean,
            "sementeira": boolean,
            "silos": boolean,
            "algodoeira": boolean
        }},
        "resumo_operacao": "Texto curto explicando quem é o grupo."
    }}
    """
    
    try:
        # AQUI MUDOU: Removemos response_mime_type='application/json'
        response_recon = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=recon_prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                temperature=0.1 
            )
        )
        # Parse Manual usando a função helper
        data = clean_and_parse_json(response_recon.text)
        
        # Se falhar o parse, lança erro para cair no except
        if not data: raise ValueError("Falha no Parse JSON")

    except Exception as e:
        # Fallback de segurança se a IA não retornar JSON ou a busca falhar
        data = {
            "nome_grupo": query_input, "hectares_total": 0, "funcionarios_estimados": 0,
            "capital_social_estimado": 0, "culturas": [], 
            "verticalizacao": {"agroindustria": False}, 
            "resumo_operacao": f"Erro na extração de dados: {str(e)}"
        }

    # --------------------------------------------------------------------------
    # PASSO 2: CÁLCULO DO SCORE
    # --------------------------------------------------------------------------
    lead_formatado = {
        'capital_social': data.get('capital_social_estimado', 0),
        'hectares': data.get('hectares_total', 0),
        'cultura_principal': ', '.join(data.get('culturas', [])),
        'funcionarios': data.get('funcionarios_estimados', 0),
        'agroindustria': data.get('verticalizacao', {}).get('agroindustria', False),
        'silos': data.get('verticalizacao', {}).get('silos', False),
        'natureza_juridica': 'Ltda'
    }
    
    score_result = calculate_sas_score(lead_formatado)
    
    # --------------------------------------------------------------------------
    # PASSO 3: GERAÇÃO DA NARRATIVA SARA
    # --------------------------------------------------------------------------
    analysis_prompt = f"""
    CONTEXTO DO CLIENTE (JSON): {json.dumps(data)}
    SCORE CALCULADO: {score_result['score']} ({score_result['tier']})
    
    {SYSTEM_PROMPT_SARA}
    """
    
    response_analysis = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=analysis_prompt,
        config=types.GenerateContentConfig(
            tools=[google_search_tool]
        )
    )
    
    full_text = response_analysis.text
    sections = full_text.split('|||')
    
    if len(sections) < 2:
        sections = [full_text, "", "", ""]
        
    return data, score_result, sections
