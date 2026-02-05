"""
types.py — Contrato de Dados do Senior Scout 360
Equivalente ao types.ts da versão TypeScript.
Define a "forma" de todos os objetos de dados.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


# =============================================================================
# ENUMS
# =============================================================================

class Tier(str, Enum):
    DIAMANTE = "DIAMANTE 💎"
    OURO = "OURO 🥇"
    PRATA = "PRATA 🥈"
    BRONZE = "BRONZE 🥉"

class QualityLevel(str, Enum):
    EXCELENTE = "EXCELENTE"
    BOM = "BOM"
    ACEITAVEL = "ACEITÁVEL"
    INSUFICIENTE = "INSUFICIENTE"

class AgentRole(str, Enum):
    RECON_OPERACIONAL = "recon_operacional"
    SNIPER_FINANCEIRO = "sniper_financeiro"
    INTEL_MERCADO = "intel_mercado"
    ANALISTA_ESTRATEGICO = "analista_estrategico"
    AUDITOR_QUALIDADE = "auditor_qualidade"
    CNPJ_LOOKUP = "cnpj_lookup"

class ModelTier(str, Enum):
    PRO = "gemini-2.5-pro"          # Raciocínio profundo
    FLASH = "gemini-2.5-flash"      # Tarefas rápidas com search
    FLASH_LITE = "gemini-2.5-flash-lite"  # Ultra econômico


# =============================================================================
# DATA CLASSES — Dados da Empresa
# =============================================================================

@dataclass
class DadosCNPJ:
    cnpj: str = ""
    razao_social: str = ""
    nome_fantasia: str = ""
    situacao_cadastral: str = ""
    data_abertura: str = ""
    natureza_juridica: str = ""
    capital_social: float = 0.0
    porte: str = ""
    cnae_principal: str = ""
    cnae_descricao: str = ""
    cnaes_secundarios: list[str] = field(default_factory=list)
    municipio: str = ""
    uf: str = ""
    cep: str = ""
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    telefone: str = ""
    email: str = ""
    qsa: list[dict] = field(default_factory=list)
    # Metadados
    fonte: str = "brasilapi"
    timestamp: str = ""


@dataclass
class Verticalizacao:
    agroindustria: bool = False
    sementeira: bool = False
    silos: bool = False
    algodoeira: bool = False
    usina: bool = False
    frigorifico: bool = False
    fabrica_racao: bool = False


@dataclass
class DadosOperacionais:
    nome_grupo: str = ""
    hectares_total: int = 0
    culturas: list[str] = field(default_factory=list)
    verticalizacao: Verticalizacao = field(default_factory=Verticalizacao)
    regioes_atuacao: list[str] = field(default_factory=list)
    numero_fazendas: int = 0
    tecnologias_identificadas: list[str] = field(default_factory=list)
    confianca: float = 0.0  # 0-1, quão confiável é a informação


@dataclass
class DadosFinanceiros:
    capital_social_estimado: float = 0.0
    funcionarios_estimados: int = 0
    faturamento_estimado: float = 0.0
    movimentos_financeiros: list[str] = field(default_factory=list)
    fiagros_relacionados: list[str] = field(default_factory=list)
    cras_emitidos: list[str] = field(default_factory=list)
    parceiros_financeiros: list[str] = field(default_factory=list)
    auditorias: list[str] = field(default_factory=list)
    governanca_corporativa: bool = False
    resumo_financeiro: str = ""
    confianca: float = 0.0


@dataclass
class IntelMercado:
    noticias_recentes: list[dict] = field(default_factory=list)
    concorrentes: list[str] = field(default_factory=list)
    tendencias_setor: list[str] = field(default_factory=list)
    dores_identificadas: list[str] = field(default_factory=list)
    oportunidades: list[str] = field(default_factory=list)
    sinais_compra: list[str] = field(default_factory=list)
    riscos: list[str] = field(default_factory=list)
    confianca: float = 0.0


# =============================================================================
# DATA CLASSES — Score e Análise
# =============================================================================

@dataclass
class SASBreakdown:
    musculo: int = 0          # max 400
    complexidade: int = 0     # max 250
    gente: int = 0            # max 200
    momento: int = 0          # max 150

    @property
    def total(self) -> int:
        return self.musculo + self.complexidade + self.gente + self.momento

    def to_dict(self) -> dict:
        return {
            "Músculo (Porte)": self.musculo,
            "Complexidade": self.complexidade,
            "Gente (Gestão)": self.gente,
            "Momento (Tec/Gov)": self.momento,
        }


@dataclass
class SASResult:
    score: int = 0
    tier: Tier = Tier.BRONZE
    breakdown: SASBreakdown = field(default_factory=SASBreakdown)
    dados_inferidos: bool = False
    justificativas: list[str] = field(default_factory=list)


@dataclass 
class QualityCheck:
    criterio: str = ""
    passou: bool = False
    nota: str = ""
    peso: float = 1.0


@dataclass
class QualityReport:
    nivel: QualityLevel = QualityLevel.INSUFICIENTE
    score_qualidade: float = 0.0
    checks: list[QualityCheck] = field(default_factory=list)
    recomendacoes: list[str] = field(default_factory=list)
    timestamp: str = ""


# =============================================================================
# DATA CLASSES — Dossiê Completo
# =============================================================================

@dataclass
class SecaoAnalise:
    titulo: str = ""
    conteudo: str = ""
    icone: str = "📄"


@dataclass
class DossieCompleto:
    # Identificação
    empresa_alvo: str = ""
    cnpj: str = ""
    
    # Dados coletados
    dados_cnpj: Optional[DadosCNPJ] = None
    dados_operacionais: DadosOperacionais = field(default_factory=DadosOperacionais)
    dados_financeiros: DadosFinanceiros = field(default_factory=DadosFinanceiros)
    intel_mercado: IntelMercado = field(default_factory=IntelMercado)
    
    # Score
    sas_result: SASResult = field(default_factory=SASResult)
    
    # Análise Estratégica (texto gerado pela IA)
    secoes_analise: list[SecaoAnalise] = field(default_factory=list)
    analise_bruta: str = ""
    
    # Qualidade
    quality_report: Optional[QualityReport] = None
    
    # Metadados
    modelo_usado: str = ""
    timestamp_geracao: str = ""
    tempo_total_segundos: float = 0.0
    tokens_consumidos: int = 0
    pipeline_log: list[str] = field(default_factory=list)
    
    def merge_dados(self) -> dict:
        """Funde todos os dados em um dict plano para o score calculator."""
        merged = {}
        
        if self.dados_cnpj:
            merged['capital_social'] = self.dados_cnpj.capital_social
            merged['cnae_principal'] = self.dados_cnpj.cnae_principal
            merged['cnae_descricao'] = self.dados_cnpj.cnae_descricao
            merged['uf'] = self.dados_cnpj.uf
            merged['municipio'] = self.dados_cnpj.municipio
            merged['natureza_juridica'] = self.dados_cnpj.natureza_juridica
            merged['qsa_count'] = len(self.dados_cnpj.qsa)
        
        merged['nome_grupo'] = self.dados_operacionais.nome_grupo or self.empresa_alvo
        merged['hectares_total'] = self.dados_operacionais.hectares_total
        merged['culturas'] = self.dados_operacionais.culturas
        merged['verticalizacao'] = self.dados_operacionais.verticalizacao
        merged['regioes_atuacao'] = self.dados_operacionais.regioes_atuacao
        merged['numero_fazendas'] = self.dados_operacionais.numero_fazendas
        merged['tecnologias'] = self.dados_operacionais.tecnologias_identificadas
        
        merged['capital_social_estimado'] = self.dados_financeiros.capital_social_estimado
        merged['funcionarios_estimados'] = self.dados_financeiros.funcionarios_estimados
        merged['faturamento_estimado'] = self.dados_financeiros.faturamento_estimado
        merged['movimentos_financeiros'] = self.dados_financeiros.movimentos_financeiros
        merged['fiagros'] = self.dados_financeiros.fiagros_relacionados
        merged['cras'] = self.dados_financeiros.cras_emitidos
        merged['governanca'] = self.dados_financeiros.governanca_corporativa
        merged['parceiros_financeiros'] = self.dados_financeiros.parceiros_financeiros
        
        return merged
