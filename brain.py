from google import genai
from google.genai import types
import json
import re
import math

# ==============================================================================
# 1. HELPER: EXTRAÇÃO E LIMPEZA
# ==============================================================================
def clean_and_parse_json(text):
    if not text: return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    try:
        clean_text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except: return None

# ==============================================================================
# 2. PERSONALIDADE E PROMPTS
# ==============================================================================

# AQUI ESTÁ A LISTA QUE FALTAVA
SARA_PHRASES = [
    "☕ Enchendo a garrafa de café e calibrando o GPS...",
    "🚜 Ligando os motores e verificando o óleo da inteligência...",
    "👢 Calçando a botina para entrar no mato digital...",
    "🤠 Ajeitando o chapéu: hora de caçar oportunidades...",
    "📡 Ajustando a antena da Starlink para achar sinal de dinheiro...",
    "📊 Cruzando dados de satélite com balanços financeiros...",
    "🚁 Sobrevoando a operação em busca de gargalos..."
]

SYSTEM_PROMPT_SARA = """
    VOCÊ É: Sara, Analista Sênior de Inteligência de Vendas (Agro).
    SUA MISSÃO: Escrever um briefing estratégico ("off-the-record") para um Executivo de Contas da Senior Sistemas.
    
    ESTRUTURA OBRIGATÓRIA DA RESPOSTA (Separada por '|||'):
    [Perfil e Mercado] ||| [Complexidade e Dores] ||| [Fit Senior] ||| [Plano de Ataque]
    
    DIRETRIZES DE CONTEÚDO:
    1. USE OS DADOS FINANCEIROS: Se o JSON diz que eles emitiram Fiagro ou CRA, você TEM que mencionar isso. Isso indica governança e dinheiro.
    2. REALPOLITIK: Se eles têm 35k hectares e auditoria, eles não são "produtores rurais", são uma CORPORAÇÃO. Trate-os assim.
    3. FALE DE DINHEIRO: Mencione os fundos, parceiros financeiros (Suno, XP, etc) se aparecerem nos dados.
"""

# ==============================================================================
# 3. MOTOR SAS 4.0 (COM HEURÍSTICAS DE CORREÇÃO)
# ==============================================================================
def heuristic_fill(lead):
    """
    Se a busca na web falhar em trazer números exatos, usamos heurísticas de mercado
    para não zerar o score de uma operação gigante.
    """
    hectares = lead.get('hectares_total', 0)
    
    # HEURÍSTICA 1: Estimativa de Funcionários (se for 0)
    if lead.get('funcionarios_estimados', 0) == 0 and hectares > 0:
        fator = 350 # Padrão Grãos
        culturas_str = str(lead.get('culturas', [])).lower()
        if 'cana' in culturas_str or 'batata' in culturas_str or 'alho' in culturas_str or 'semente' in culturas_str:
            fator = 150 # Culturas intensivas exigem mais gente
        
        lead['funcionarios_estimados'] = math.ceil(hectares / fator)
        lead['dados_inferidos'] = True # Flag para avisar no front

    # HEURÍSTICA 2: Estimativa de Capital Operacional (se for 0)
    if lead.get('capital_social_estimado', 0) == 0 and hectares > 0:
        lead['capital_social_estimado'] = hectares * 2000 # Estimativa conservadora
        lead['dados_inferidos'] = True

    return lead

def calculate_sas_score(lead):
    # Aplica correções antes de calcular
    lead = heuristic_fill(lead)

    # Tabelas de Pontuação
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
        if 'cana' in txt: return 150
        if 'semente' in txt: return 130
        if 'algod' in txt: return 120
        if 'café' in txt or 'alho' in txt or 'batata' in txt: return 110
        if 'soja' in txt or 'milho' in txt: return 80
        return 50

    def lookup_funcionarios(val):
        if val >= 500: return 120
        if val >= 200: return 90
        if val >= 100: return 60
        if val >= 50: return 30
        return 0
    
    # Extração
    capital = lead.get('capital_social_estimado', 0)
    hectares = lead.get('hectares_total', 0)
    cultura = ', '.join(lead.get('culturas', []))
    funcionarios = lead.get('funcionarios_estimados', 0)
    
    # Cálculo
    pilar_musculo = min(lookup_capital(capital) + lookup_hectares(hectares), 400)
    
    cultura_pts = lookup_cultura(cultura)
    vert_pts = 0
    vert = lead.get('verticalizacao', {})
    if vert.get('agroindustria'): vert_pts += 50
    if vert.get('silos'): vert_pts += 30
    if vert.get('sementeira'): vert_pts += 30
    
    pilar_complexidade = min(cultura_pts + vert_pts, 250)
    
    pilar_gente = min(lookup_funcionarios(funcionarios), 200)
    
    # Momento: Se tem Fiagro/CRA, ganha pontos de "S.A." (Governança)
    movimentos = str(lead.get('movimentos_financeiros', '')).lower()
    tem_gov = 'fiagro' in movimentos or 'cra' in movimentos or 'auditoria' in movimentos
    pilar_momento = 100 if tem_gov else 60

    sas_final = pilar_musculo + pilar_complexidade + pilar_gente + pilar_momento
    
    if sas_final >= 751: tier = "DIAMANTE 💎"
    elif sas_final >= 501: tier = "OURO 🥇"
    elif sas_final >= 251: tier = "PRATA 🥈"
    else: tier = "BRONZE 🥉"
    
    return {
        "score": int(sas_final),
        "tier": tier,
        "breakdown": {
            "Músculo": pilar_musculo,
            "Complexidade": pilar_complexidade,
            "Gente": pilar_gente,
            "Momento": pilar_momento
        }
    }

# ==============================================================================
# 4. AGENTES DE INVESTIGAÇÃO (PIPELINE DUPLO)
# ==============================================================================

def investigate_company(query_input, api_key):
    client = genai.Client(api_key=api_key)
    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    
    # --- AGENTE 1: RECONHECIMENTO OPERACIONAL ---
    recon_prompt = f"""
    ATUE COMO: Investigador Agrícola. ALVO: "{query_input}"
    
    Descubra a estrutura física do Grupo Econômico:
    1. Área total (Hectares). Se achar números diferentes, pegue o maior/mais recente.
    2. Culturas (Soja, Milho, Algodão, Cana, HF).
    3. Infraestrutura (Silos, Sementeiras, Algodoeiras).
    
    Retorne JSON:
    {{
        "nome_grupo": "Nome",
        "hectares_total": numero,
        "culturas": ["lista"],
        "verticalizacao": {{ "agroindustria": bool, "sementeira": bool, "silos": bool }}
    }}
    Comece com {{ e termine com }}.
    """
    
    try:
        resp_recon = client.models.generate_content(
            model='gemini-2.5-flash', contents=recon_prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool], temperature=0.1)
        )
        data_ops = clean_and_parse_json(resp_recon.text) or {}
    except Exception as e:
        data_ops = {"nome_grupo": query_input, "hectares_total": 0}

    grupo_nome = data_ops.get('nome_grupo', query_input)

    # --- AGENTE 2: SNIPER FINANCEIRO (Deep Dive) ---
    fin_prompt = f"""
    ATUE COMO: Analista de Mercado de Capitais. ALVO: "{grupo_nome}"
    
    Vasculhe a web procurando ESPECIFICAMENTE por:
    1. Emissões de CRA (Certificados de Recebíveis do Agronegócio).
    2. Fiagro (Fundos de Investimento) que investiram neles (Ex: Suno, XP, Valora).
    3. Notícias de M&A ou Auditoria.
    4. Capital Social (Procure em sites como Econodata, Casa dos Dados).
    
    Retorne JSON:
    {{
        "capital_social_estimado": numero (somente numeros),
        "funcionarios_estimados": numero,
        "movimentos_financeiros": ["Lista de fatos: Ex: Emissão de CRA de R$ 50M", "Fiagro Suno SNFZ11", "Auditoria XYZ"],
        "resumo_financeiro": "Texto curto sobre a robustez financeira."
    }}
    Comece com {{ e termine com }}.
    """
    
    try:
        resp_fin = client.models.generate_content(
            model='gemini-2.5-flash', contents=fin_prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool], temperature=0.1)
        )
        data_fin = clean_and_parse_json(resp_fin.text) or {}
    except:
        data_fin = {}

    # --- FUSÃO DE DADOS ---
    final_data = {**data_ops, **data_fin}
    
    if 'resumo_operacao' not in final_data:
        final_data['resumo_operacao'] = f"Grupo com {final_data.get('hectares_total', '?')} ha. {final_data.get('resumo_financeiro', '')}"

    # --- CÁLCULO E ANÁLISE ---
    score_result = calculate_sas_score(final_data)
    
    analysis_prompt = f"""
    CONTEXTO COMPLETO: {json.dumps(final_data)}
    SCORE: {score_result['score']} ({score_result['tier']})
    
    {SYSTEM_PROMPT_SARA}
    """
    
    try:
        resp_analysis = client.models.generate_content(
            model='gemini-2.5-flash', contents=analysis_prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool])
        )
        full_text = resp_analysis.text
    except:
        full_text = "Erro na análise."

    sections = full_text.split('|||')
    if len(sections) < 2: sections = [full_text, "", "", ""]
        
    return final_data, score_result, sections
