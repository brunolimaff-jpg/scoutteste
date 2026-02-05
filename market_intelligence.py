"""
utils/market_intelligence.py — Base de Conhecimento Estática
Equivalente ao marketIntelligence.ts.
Alimenta os prompts da IA com contexto de domínio sem custo de API.
"""

# =============================================================================
# DORES POR CNAE / SETOR
# =============================================================================

DORES_POR_CNAE = {
    "0111": {  # Cultivo de cereais
        "setor": "Grãos (Soja, Milho, Trigo)",
        "dores": [
            "Gestão de múltiplas safras simultâneas (safra/safrinha)",
            "Controle de insumos: fertilizantes, sementes, defensivos com custos voláteis",
            "Rastreabilidade exigida por tradings (Cargill, Bunge, ADM)",
            "Gestão de armazenagem e frete — logística de escoamento é gargalo",
            "Compliance com Renovabio e créditos de carbono",
            "Conciliação de contratos de hedge/barter",
        ],
        "modulos_senior": ["ERP Gestão Agrícola", "WMS (Armazéns)", "Financeiro", "BI Agrícola"],
    },
    "0113": {  # Cultivo de cana
        "setor": "Cana-de-Açúcar / Sucroenergético",
        "dores": [
            "Controle de CTT (Corte, Transporte, Transbordo) — mais de 40% do custo",
            "Gestão de moagem, produção de açúcar/etanol/energia",
            "RenovaBio: controle de CBIOs obrigatório",
            "Manutenção pesada: colhedoras, treminhões, caldeiras",
            "Gestão de gente: safra emprega 3x mais que entressafra",
            "Integração com CONSECANA para precificação",
        ],
        "modulos_senior": ["ERP Industrial", "Manutenção de Ativos", "RH/DP", "Gestão Agrícola"],
    },
    "0115": {  # Cultivo de tabaco, algodão
        "setor": "Algodão / Fibras",
        "dores": [
            "Beneficiamento: controle de algodoeira (pluma, caroço, fibrilha)",
            "Rastreabilidade ABR (Algodão Brasileiro Responsável)",
            "Gestão de classificação HVI por fardo",
            "Logística reversa de embalagens de defensivos",
            "Controle de irrigação (pivôs centrais) — custo energético alto",
        ],
        "modulos_senior": ["ERP Gestão Agrícola", "WMS", "Qualidade", "Manutenção"],
    },
    "0119": {  # Outros cultivos temporários
        "setor": "HF / Culturas Especiais",
        "dores": [
            "Perecibilidade: janela de colheita/venda muito curta",
            "Rastreabilidade de alimentos exigida por redes de varejo",
            "MIP (Manejo Integrado de Pragas) intensivo",
            "Gestão de câmaras frias e packing houses",
            "Mão de obra sazonal massiva e compliance trabalhista",
        ],
        "modulos_senior": ["ERP Gestão Agrícola", "RH/DP", "WMS", "Qualidade"],
    },
    "0151": {  # Criação de bovinos
        "setor": "Pecuária de Corte / Leite",
        "dores": [
            "Rastreabilidade individual (GTA, SISBOV, exportação)",
            "Gestão nutricional: confinamento, suplementação, dieta",
            "Controle reprodutivo: IATF, estação de monta, genética",
            "Gestão de pastagens e reforma de pasto",
            "Frigoríficos: controle de abate, rendimento de carcaça, SIF",
        ],
        "modulos_senior": ["ERP Pecuária", "Gestão de Rebanho", "Manutenção", "Financeiro"],
    },
    "generico_agro": {
        "setor": "Agronegócio Geral",
        "dores": [
            "Dificuldade de integrar operações de campo com o administrativo",
            "Planilhas substituindo ERP → risco operacional e fiscal",
            "Gestão de frota própria e manutenção de máquinas",
            "Compliance fiscal rural: Funrural, ICMS diferido, REINF",
            "Falta de visibilidade de custos reais por talhão/safra",
            "Gestão de contratos de parceria agrícola e arrendamento",
        ],
        "modulos_senior": ["ERP Gestão Agrícola", "Financeiro", "RH/DP", "BI"],
    },
}


# =============================================================================
# CONTEXTO REGIONAL
# =============================================================================

CONTEXTO_REGIONAL = {
    "MT": {
        "nome": "Mato Grosso",
        "perfil": "Maior produtor de grãos do Brasil. Operações gigantes (10k-100k+ ha). Alta mecanização.",
        "desafios": "Logística de escoamento (BR-163), armazenagem, distância dos portos.",
        "concorrentes_erp": ["TOTVS Agro", "SAP Rural", "Datacoper", "Siagri"],
    },
    "GO": {
        "nome": "Goiás",
        "perfil": "Forte em grãos, cana e pecuária. Muitas usinas sucroenergéticas.",
        "desafios": "Diversificação de culturas, irrigação por pivô, gestão de usinas.",
        "concorrentes_erp": ["TOTVS", "Siagri", "Datacoper"],
    },
    "SP": {
        "nome": "São Paulo",
        "perfil": "Capital do sucroenergético. Também forte em HF, citricultura e café.",
        "desafios": "Custo de terra alto, pressão urbana, compliance ambiental rigoroso.",
        "concorrentes_erp": ["SAP", "TOTVS", "Oracle"],
    },
    "PR": {
        "nome": "Paraná",
        "perfil": "Diversificado: grãos, frango, suínos, cooperativas fortes.",
        "desafios": "Integração cooperativa-cooperado, gestão multisite, logística portuária (Paranaguá).",
        "concorrentes_erp": ["TOTVS", "Cooperativas com sistema próprio"],
    },
    "MS": {
        "nome": "Mato Grosso do Sul",
        "perfil": "Pecuária forte + grãos + celulose (Suzano, Eldorado). Crescimento rápido.",
        "desafios": "Fronteira agrícola em expansão, gestão pecuária + lavoura integrada.",
        "concorrentes_erp": ["TOTVS", "Siagri"],
    },
    "BA": {
        "nome": "Bahia",
        "perfil": "MATOPIBA: fronteira do agro. Grandes operações de algodão e soja no Oeste Baiano.",
        "desafios": "Irrigação (Cerrado baiano), logística, regularização fundiária.",
        "concorrentes_erp": ["Siagri", "TOTVS"],
    },
    "MG": {
        "nome": "Minas Gerais",
        "perfil": "Café (maior produtor), leite (maior bacia), grãos no Triângulo Mineiro.",
        "desafios": "Topografia acidentada, muitas pequenas-médias propriedades, gestão de qualidade de café.",
        "concorrentes_erp": ["TOTVS", "Siagri", "sistemas locais"],
    },
    "RS": {
        "nome": "Rio Grande do Sul",
        "perfil": "Arroz irrigado, soja, pecuária, vinicultura. Cooperativismo forte.",
        "desafios": "Eventos climáticos extremos, gestão de irrigação, compliance de cooperativas.",
        "concorrentes_erp": ["TOTVS", "Cooperativas com ERP próprio"],
    },
}


# =============================================================================
# ARGUMENTOS CONTRA CONCORRENTES ("Matador de Concorrência")
# =============================================================================

ARGUMENTOS_CONCORRENCIA = {
    "totvs": {
        "nome": "TOTVS Agro (Protheus/RM)",
        "fraquezas": [
            "Customização cara e lenta — depende de fábrica de software",
            "Módulo agrícola é 'adaptação' do ERP industrial, não nativo",
            "Interface defasada — produtores reclamam da usabilidade",
            "Custo total de propriedade (TCO) alto com licenças + consultoria",
        ],
        "senior_vantagem": [
            "Senior tem módulo agrícola nativo, não adaptado",
            "Cloud-first: atualizações automáticas, sem servidor local",
            "UX moderna — curva de aprendizado menor para o campo",
        ],
    },
    "sap": {
        "nome": "SAP (S/4HANA)",
        "fraquezas": [
            "Complexidade absurda para operações agro",
            "Custo de implementação: R$2M+ para operação média",
            "Poucos consultores SAP que entendem agro no Brasil",
            "Tempo de deploy: 12-24 meses é o normal",
        ],
        "senior_vantagem": [
            "Deploy em 3-6 meses com expertise agro comprovada",
            "Custo 60-70% menor que SAP com funcionalidade equivalente",
            "Suporte local em português com conhecimento setorial",
        ],
    },
    "siagri": {
        "nome": "Siagri (Agrowin)",
        "fraquezas": [
            "Focado demais em financeiro — módulos operacionais fracos",
            "Sem módulo robusto de RH/DP para operações com 200+ funcionários",
            "Escalabilidade limitada para grupos econômicos multi-CNPJ",
            "Sem módulo de manutenção de ativos nativo",
        ],
        "senior_vantagem": [
            "Suite completa: ERP + RH + Manutenção + BI em uma plataforma",
            "Gestão multi-empresa/multi-fazenda nativa",
            "Integração com folha de pagamento eSocial robusta",
        ],
    },
}


# =============================================================================
# HELPERS PARA ENRIQUECIMENTO DE PROMPTS
# =============================================================================

def get_contexto_cnae(cnae: str) -> dict:
    """Retorna contexto de dores por CNAE (primeiros 4 dígitos)."""
    cnae_4 = str(cnae)[:4] if cnae else ""
    return DORES_POR_CNAE.get(cnae_4, DORES_POR_CNAE["generico_agro"])


def get_contexto_regional(uf: str) -> dict:
    """Retorna contexto regional por UF."""
    return CONTEXTO_REGIONAL.get(str(uf).upper(), {
        "nome": uf or "Não identificado",
        "perfil": "Sem perfil regional detalhado.",
        "desafios": "A ser investigado.",
        "concorrentes_erp": [],
    })


def enriquecer_prompt_com_contexto(cnae: str = "", uf: str = "") -> str:
    """Gera bloco de contexto para injetar no prompt da IA."""
    ctx_cnae = get_contexto_cnae(cnae)
    ctx_uf = get_contexto_regional(uf)
    
    return f"""
=== INTELIGÊNCIA DE MERCADO (Base de Conhecimento Senior) ===
SETOR: {ctx_cnae['setor']}
DORES TÍPICAS DO SETOR:
{chr(10).join(f'  - {d}' for d in ctx_cnae['dores'])}

REGIÃO: {ctx_uf.get('nome', 'N/D')}
PERFIL REGIONAL: {ctx_uf.get('perfil', 'N/D')}
DESAFIOS REGIONAIS: {ctx_uf.get('desafios', 'N/D')}
CONCORRENTES ERP NA REGIÃO: {', '.join(ctx_uf.get('concorrentes_erp', []))}
MÓDULOS SENIOR RECOMENDADOS: {', '.join(ctx_cnae.get('modulos_senior', []))}
"""
