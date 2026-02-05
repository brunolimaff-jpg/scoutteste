"""
services/market_estimator.py — Motor SAS 4.0
Equivalente ao marketEstimator.ts.
Calculadora determinística (sem IA) do Senior Agro Score.
Inclui lookup tables robustas, heurísticas de preenchimento e justificativas.
"""
import math
from typing import Optional

from scout_types import (
    SASResult, SASBreakdown, Tier, Verticalizacao,
)


# =============================================================================
# LOOKUP TABLES
# =============================================================================

def _lookup_capital(valor: float) -> tuple[int, str]:
    """Capital social → pontos (max 200)."""
    if valor >= 200_000_000: return 200, "Capital ≥ R$200M → Corporação de Grande Porte"
    if valor >= 100_000_000: return 180, "Capital ≥ R$100M → Grande Empresa"
    if valor >= 50_000_000:  return 150, "Capital ≥ R$50M → Empresa Consolidada"
    if valor >= 20_000_000:  return 120, "Capital ≥ R$20M → Empresa de Médio-Grande Porte"
    if valor >= 10_000_000:  return 100, "Capital ≥ R$10M → Média Empresa"
    if valor >= 5_000_000:   return 70,  "Capital ≥ R$5M → PME Robusta"
    if valor >= 1_000_000:   return 50,  "Capital ≥ R$1M → PME"
    if valor >= 500_000:     return 30,  "Capital ≥ R$500k → Pequena Empresa"
    return 10, "Capital < R$500k → Microempresa"


def _lookup_hectares(valor: int) -> tuple[int, str]:
    """Hectares → pontos (max 200)."""
    if valor >= 100_000: return 200, f"{valor:,} ha → Mega-operação"
    if valor >= 50_000:  return 180, f"{valor:,} ha → Operação Gigante"
    if valor >= 20_000:  return 150, f"{valor:,} ha → Grande Produtor"
    if valor >= 10_000:  return 130, f"{valor:,} ha → Produtor Consolidado"
    if valor >= 5_000:   return 100, f"{valor:,} ha → Médio-Grande"
    if valor >= 3_000:   return 80,  f"{valor:,} ha → Médio Produtor"
    if valor >= 1_000:   return 50,  f"{valor:,} ha → Pequeno-Médio"
    if valor >= 500:     return 30,  f"{valor:,} ha → Pequeno Produtor"
    if valor > 0:        return 10,  f"{valor:,} ha → Micro Produtor"
    return 0, "Sem dados de área"


def _lookup_cultura(culturas: list[str]) -> tuple[int, str]:
    """Culturas → pontos de complexidade (max 150)."""
    if not culturas:
        return 50, "Culturas não identificadas → score padrão"
    
    txt = " ".join(culturas).lower()
    
    # Scoring por complexidade operacional
    scores = {
        "cana": 150, "usina": 150,
        "semente": 140, "sementes": 140,
        "algod": 130, "algodoeira": 130,
        "café": 120, "cafe": 120,
        "alho": 120, "batata": 110, "hf": 110, "hortifruti": 110,
        "pecuária": 100, "pecuaria": 100, "gado": 100, "boi": 100,
        "laranja": 100, "citrus": 100,
        "soja": 80, "milho": 80,
        "trigo": 70,
        "feijão": 60, "feijao": 60,
        "arroz": 60,
    }
    
    best_score = 50
    best_label = "Culturas genéricas"
    
    for keyword, score in scores.items():
        if keyword in txt and score > best_score:
            best_score = score
            best_label = f"Cultura detectada: {keyword}"
    
    # Bônus por diversificação (múltiplas culturas = mais complexidade)
    unique_crops = len(set(culturas))
    if unique_crops >= 4:
        best_score = min(best_score + 30, 150)
        best_label += f" + {unique_crops} culturas (diversificado)"
    elif unique_crops >= 2:
        best_score = min(best_score + 15, 150)
        best_label += f" + {unique_crops} culturas"
    
    return best_score, best_label


def _lookup_verticalizacao(vert: Optional[Verticalizacao]) -> tuple[int, str]:
    """Verticalização → pontos (max 100)."""
    if vert is None:
        return 0, "Sem dados de verticalização"
    
    pts = 0
    labels = []
    
    if vert.agroindustria:
        pts += 40
        labels.append("Agroindústria")
    if vert.usina:
        pts += 40
        labels.append("Usina")
    if vert.sementeira:
        pts += 30
        labels.append("Sementeira")
    if vert.silos:
        pts += 25
        labels.append("Silos")
    if vert.algodoeira:
        pts += 25
        labels.append("Algodoeira")
    if vert.frigorifico:
        pts += 35
        labels.append("Frigorífico")
    if vert.fabrica_racao:
        pts += 20
        labels.append("Fábrica de Ração")
    
    pts = min(pts, 100)
    label = ", ".join(labels) if labels else "Não verticalizado"
    return pts, label


def _lookup_funcionarios(valor: int) -> tuple[int, str]:
    """Funcionários → pontos (max 200)."""
    if valor >= 1000: return 200, f"{valor} funcs → Operação massiva"
    if valor >= 500:  return 150, f"{valor} funcs → Grande empregador"
    if valor >= 200:  return 120, f"{valor} funcs → Médio-Grande"
    if valor >= 100:  return 90,  f"{valor} funcs → Médio"
    if valor >= 50:   return 60,  f"{valor} funcs → Pequeno-Médio"
    if valor >= 20:   return 30,  f"{valor} funcs → Pequeno"
    if valor > 0:     return 15,  f"{valor} funcs → Micro"
    return 0, "Sem dados de funcionários"


def _lookup_governanca(dados: dict) -> tuple[int, str]:
    """Governança e momento → pontos (max 150)."""
    pts = 0
    labels = []
    
    # Fiagro/CRA = sinais fortes de governança
    movimentos = str(dados.get('movimentos_financeiros', '')).lower()
    fiagros = str(dados.get('fiagros', '')).lower()
    cras = str(dados.get('cras', '')).lower()
    all_fin = f"{movimentos} {fiagros} {cras}"
    
    if 'fiagro' in all_fin:
        pts += 40
        labels.append("Fiagro detectado")
    if 'cra' in all_fin:
        pts += 35
        labels.append("CRA emitido")
    if 'auditoria' in all_fin or dados.get('governanca', False):
        pts += 30
        labels.append("Governança corporativa")
    if any(x in all_fin for x in ['xp', 'suno', 'valora', 'itaú', 'btg']):
        pts += 25
        labels.append("Parceiro financeiro relevante")
    
    # Tecnologias
    techs = str(dados.get('tecnologias', '')).lower()
    if any(x in techs for x in ['erp', 'senior', 'sap', 'totvs']):
        pts += 20
        labels.append("ERP/sistema de gestão")
    if any(x in techs for x in ['agricultura de precisão', 'drone', 'telemetria', 'iot']):
        pts += 15
        labels.append("Ag-tech")
    
    # Natureza jurídica (S.A. = mais governança)
    nat_jur = str(dados.get('natureza_juridica', '')).lower()
    if 's.a.' in nat_jur or 'sociedade anônima' in nat_jur:
        pts += 25
        labels.append("S.A. (Governança implícita)")
    
    # QSA grande = estrutura complexa
    qsa_count = dados.get('qsa_count', 0)
    if qsa_count >= 5:
        pts += 15
        labels.append(f"QSA com {qsa_count} sócios")
    
    pts = min(pts, 150)
    label = "; ".join(labels) if labels else "Sem sinais de governança"
    return pts, label


# =============================================================================
# HEURÍSTICAS DE PREENCHIMENTO
# =============================================================================

def _heuristic_fill(dados: dict) -> tuple[dict, list[str]]:
    """
    Se a busca na web não trouxe números exatos, estima via heurísticas.
    Retorna (dados_preenchidos, lista_de_inferencias).
    """
    inferencias = []
    hectares = dados.get('hectares_total', 0)
    
    # Funcionários estimados
    if dados.get('funcionarios_estimados', 0) == 0 and hectares > 0:
        culturas_txt = " ".join(dados.get('culturas', [])).lower()
        
        # Fator: hectares por funcionário
        if any(x in culturas_txt for x in ['cana', 'batata', 'alho', 'semente', 'hf']):
            fator = 120  # Culturas intensivas
        elif any(x in culturas_txt for x in ['café', 'algod', 'laranja']):
            fator = 200
        else:
            fator = 350  # Grãos mecanizados
        
        est = math.ceil(hectares / fator)
        dados['funcionarios_estimados'] = est
        inferencias.append(f"Funcionários estimados: ~{est} (heurística {hectares}ha ÷ {fator})")
    
    # Capital operacional estimado
    if dados.get('capital_social_estimado', 0) == 0 and hectares > 0:
        # R$ por hectare depende da região e cultura
        regioes = str(dados.get('regioes_atuacao', '')).lower()
        if any(x in regioes for x in ['mt', 'mato grosso', 'matopiba', 'ba', 'to', 'pi', 'ma']):
            valor_ha = 3500  # Cerrado valorizado
        elif any(x in regioes for x in ['sp', 'são paulo', 'pr', 'paraná', 'rs']):
            valor_ha = 5000  # Sul/Sudeste
        else:
            valor_ha = 2500  # Conservador
        
        est = hectares * valor_ha
        dados['capital_social_estimado'] = est
        inferencias.append(f"Capital estimado: R${est/1e6:.1f}M (heurística {hectares}ha × R${valor_ha}/ha)")
    
    # Faturamento estimado (se não existir)
    if dados.get('faturamento_estimado', 0) == 0 and hectares > 0:
        # Estimativa conservadora: R$ 3k-8k por hectare de receita anual
        receita_ha = 5000
        est = hectares * receita_ha
        dados['faturamento_estimado'] = est
        inferencias.append(f"Faturamento estimado: R${est/1e6:.1f}M/ano (heurística)")
    
    return dados, inferencias


# =============================================================================
# CALCULADORA PRINCIPAL
# =============================================================================

def calcular_sas(dados: dict) -> SASResult:
    """
    Calcula o Senior Agro Score 4.0.
    
    Pilares:
    - Músculo (Porte): Capital + Hectares → max 400 pts
    - Complexidade: Culturas + Verticalização → max 250 pts  
    - Gente (Gestão): Funcionários → max 200 pts
    - Momento (Tec/Gov): Governança + Tecnologia → max 150 pts
    
    Total: max 1000 pts
    """
    # Preenche lacunas com heurísticas
    dados, inferencias = _heuristic_fill(dados)
    justificativas = list(inferencias)
    
    # === PILAR 1: MÚSCULO (max 400) ===
    cap_pts, cap_label = _lookup_capital(dados.get('capital_social_estimado', 0) or dados.get('capital_social', 0))
    hec_pts, hec_label = _lookup_hectares(dados.get('hectares_total', 0))
    musculo = min(cap_pts + hec_pts, 400)
    justificativas.append(f"Músculo: {cap_label} ({cap_pts}) + {hec_label} ({hec_pts}) = {musculo}")
    
    # === PILAR 2: COMPLEXIDADE (max 250) ===
    cult_pts, cult_label = _lookup_cultura(dados.get('culturas', []))
    vert_pts, vert_label = _lookup_verticalizacao(dados.get('verticalizacao'))
    complexidade = min(cult_pts + vert_pts, 250)
    justificativas.append(f"Complexidade: {cult_label} ({cult_pts}) + {vert_label} ({vert_pts}) = {complexidade}")
    
    # === PILAR 3: GENTE (max 200) ===
    func_pts, func_label = _lookup_funcionarios(dados.get('funcionarios_estimados', 0))
    gente = min(func_pts, 200)
    justificativas.append(f"Gente: {func_label} = {gente}")
    
    # === PILAR 4: MOMENTO (max 150) ===
    gov_pts, gov_label = _lookup_governanca(dados)
    momento = min(gov_pts, 150)
    justificativas.append(f"Momento: {gov_label} = {momento}")
    
    # === TOTAL ===
    total = musculo + complexidade + gente + momento
    
    if total >= 751:
        tier = Tier.DIAMANTE
    elif total >= 501:
        tier = Tier.OURO
    elif total >= 251:
        tier = Tier.PRATA
    else:
        tier = Tier.BRONZE
    
    return SASResult(
        score=total,
        tier=tier,
        breakdown=SASBreakdown(
            musculo=musculo,
            complexidade=complexidade,
            gente=gente,
            momento=momento,
        ),
        dados_inferidos=len(inferencias) > 0,
        justificativas=justificativas,
    )
