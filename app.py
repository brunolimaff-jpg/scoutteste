"""
app.py — Senior Scout 360 v3.0
Interface Streamlit com pipeline robusto de 6 passos.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
import random
import json

from services.dossier_orchestrator import gerar_dossie_completo
from services.market_estimator import calcular_sas
from services.cnpj_service import consultar_cnpj, formatar_cnpj, validar_cnpj, limpar_cnpj
from services import cache
from services.request_queue import request_queue
from utils.market_intelligence import (
    ARGUMENTOS_CONCORRENCIA, get_contexto_cnae, get_contexto_regional,
)
from scout_types import DossieCompleto, Tier, QualityLevel


# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="Senior Scout 360 v3.0",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SARA_PHRASES = [
    "☕ Enchendo a garrafa de café e calibrando os satélites...",
    "🛰️ Ativando reconhecimento orbital...",
    "🚜 Ligando os motores da inteligência...",
    "👢 Calçando a botina para entrar no mato digital...",
    "🤠 Ajeitando o chapéu: hora de caçar oportunidades...",
    "📡 Conectando com 5 agentes de inteligência...",
    "📊 Cruzando dados de satélite com balanços financeiros...",
    "🚁 Sobrevoando a operação em busca de sinais...",
    "💰 Rastreando movimentações no mercado de capitais...",
    "🔍 Investigando CRAs, Fiagros e governança...",
    "🧠 Gemini Pro está pensando profundamente...",
]

# =============================================================================
# CSS
# =============================================================================

st.markdown("""
<style>
    /* Métricas */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 18px;
        border-radius: 12px;
        color: white;
    }
    div[data-testid="stMetric"] label {
        color: rgba(255,255,255,0.8) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: rgba(255,255,255,0.9) !important;
    }
    
    /* Botão principal */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #FF4B4B, #FF6B35);
        color: white;
        font-weight: bold;
        padding: 0.6rem 1.2rem;
        border-radius: 10px;
        border: none;
        font-size: 1rem;
    }
    
    /* Cards de seção */
    .scout-section-card {
        background-color: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 16px 20px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
    
    /* Quality badge */
    .quality-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .quality-excelente { background: #d4edda; color: #155724; }
    .quality-bom { background: #cce5ff; color: #004085; }
    .quality-aceitavel { background: #fff3cd; color: #856404; }
    .quality-insuficiente { background: #f8d7da; color: #721c24; }
    
    /* Tier badges */
    .tier-diamante { 
        background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
        color: #3730a3;
        font-weight: bold;
        padding: 6px 16px;
        border-radius: 20px;
        display: inline-block;
    }
    .tier-ouro { background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; }
    .tier-prata { background: linear-gradient(135deg, #e5e7eb, #d1d5db); color: #374151; }
    .tier-bronze { background: linear-gradient(135deg, #fed7aa, #fdba74); color: #9a3412; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

if 'dossie' not in st.session_state:
    st.session_state.dossie = None
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'historico' not in st.session_state:
    st.session_state.historico = []


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("🕵️ Senior Scout 360")
    st.caption("Intelligence Unit | v3.0 (Multi-Agent Pipeline)")
    st.markdown("---")
    
    # === API KEY ===
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ API Key configurada")
    except (FileNotFoundError, KeyError):
        st.warning("⚠️ Modo Local")
        api_key = st.text_input("Gemini API Key:", type="password")
        if not api_key:
            st.error("Insira a API Key para operar.")
            st.stop()
    
    st.markdown("---")
    
    # === INPUTS ===
    st.subheader("🎯 Alvo")
    target_company = st.text_input(
        "Nome da Empresa ou Grupo",
        placeholder="Ex: Grupo SLC Agrícola, Bom Futuro...",
    )
    
    target_cnpj = st.text_input(
        "CNPJ (opcional)",
        placeholder="XX.XXX.XXX/XXXX-XX",
    )
    
    # Validação visual do CNPJ
    if target_cnpj:
        cnpj_limpo = limpar_cnpj(target_cnpj)
        if validar_cnpj(cnpj_limpo):
            st.caption(f"✅ CNPJ válido: {formatar_cnpj(cnpj_limpo)}")
        elif len(cnpj_limpo) > 0:
            st.caption("❌ CNPJ inválido")
    
    st.markdown("---")
    
    # === CONFIGURAÇÕES ===
    with st.expander("⚙️ Configurações Avançadas"):
        modelo_analise = st.selectbox(
            "Modelo para Análise",
            ["gemini-2.5-pro (Recomendado)", "gemini-2.5-flash (Mais rápido)"],
            index=0,
        )
        
        executar_audit_ia = st.checkbox("Executar Auditoria por IA", value=True)
        
        st.caption(f"Cache: {cache.stats['hit_rate']} hit rate | "
                   f"Queue: {request_queue.stats['total_requests']} requisições")
    
    st.markdown("---")
    
    # === BOTÃO ===
    btn_investigate = st.button(
        "🚀 Iniciar Investigação Completa",
        type="primary",
        disabled=not target_company,
        use_container_width=True,
    )
    
    st.markdown("---")
    
    # === INFO ===
    st.info("""**Pipeline v3.0 (6 Passos)**
1. 📋 Consulta CNPJ (BrasilAPI)
2. 🛰️ Recon Operacional (Flash)
3. 💰 Sniper Financeiro (Flash)
4. 📡 Intel de Mercado (Flash)
5. 🧠 Análise Estratégica (Pro)
6. ✅ Quality Gate (Pro)""")
    
    # === HISTÓRICO ===
    if st.session_state.historico:
        st.markdown("---")
        st.subheader("📚 Histórico")
        for h in reversed(st.session_state.historico[-5:]):
            st.caption(f"• {h['empresa']} — {h['tier']} ({h['score']}/1000)")


# =============================================================================
# ÁREA PRINCIPAL
# =============================================================================

if not target_company and st.session_state.dossie is None:
    # === TELA DE BOAS-VINDAS ===
    st.header("🕵️ Senior Scout 360")
    st.subheader("Sistema de Inteligência para Prospecção Agro")
    
    st.markdown("""
    O **Senior Scout 360 v3.0** utiliza **5 agentes de IA especializados** para investigar 
    empresas do agronegócio e gerar dossiês estratégicos completos.
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 🛰️ Reconhecimento")
        st.markdown("Mapeia estrutura física, hectares, culturas e verticalização do grupo econômico.")
    with col2:
        st.markdown("#### 💰 Inteligência Financeira")
        st.markdown("Rastreia CRAs, Fiagros, auditorias, parceiros financeiros e governança.")
    with col3:
        st.markdown("#### 🧠 Análise Profunda")
        st.markdown("Gemini Pro gera análise estratégica com plano de ataque personalizado.")
    
    st.markdown("---")
    st.markdown("**👈 Digite o nome de uma empresa na barra lateral para começar.**")

elif btn_investigate and target_company:
    # === EXECUÇÃO DO PIPELINE ===
    st.session_state.dossie = None
    st.session_state.logs = []
    
    # Containers para UI dinâmica
    header_container = st.container()
    progress_container = st.container()
    log_container = st.container()
    
    with header_container:
        st.header(f"🔍 Investigando: {target_company}")
    
    # Progress bar e status
    with progress_container:
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        phase_text = st.empty()
    
    def update_progress(pct: float, msg: str):
        progress_bar.progress(min(pct, 1.0))
        status_text.markdown(f"**{msg}**")
        phase_text.caption(random.choice(SARA_PHRASES))
    
    def add_log(msg: str):
        st.session_state.logs.append(msg)
    
    try:
        dossie = gerar_dossie_completo(
            empresa_alvo=target_company,
            api_key=api_key,
            cnpj=target_cnpj,
            log_callback=add_log,
            progress_callback=update_progress,
        )
        
        st.session_state.dossie = dossie
        st.session_state.historico.append({
            'empresa': dossie.dados_operacionais.nome_grupo or target_company,
            'score': dossie.sas_result.score,
            'tier': dossie.sas_result.tier.value,
            'timestamp': dossie.timestamp_geracao,
        })
        
        # Limpa progress
        progress_container.empty()
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erro no pipeline: {str(e)}")
        with st.expander("📋 Log de Execução"):
            for log in st.session_state.logs:
                st.text(log)


# =============================================================================
# EXIBIÇÃO DO DOSSIÊ
# =============================================================================

if st.session_state.dossie is not None:
    dossie: DossieCompleto = st.session_state.dossie
    
    # === CABEÇALHO ===
    nome_grupo = dossie.dados_operacionais.nome_grupo or dossie.empresa_alvo
    
    col_score, col_info, col_quality = st.columns([1, 2, 1])
    
    with col_score:
        tier_name = dossie.sas_result.tier.value
        st.metric(
            label="Senior Agro Score 4.0",
            value=f"{dossie.sas_result.score}/1000",
            delta=tier_name,
        )
    
    with col_info:
        st.subheader(f"📋 Dossiê: {nome_grupo}")
        
        # Badges
        badges = []
        vert = dossie.dados_operacionais.verticalizacao
        if vert.agroindustria: badges.append("🏭 Agroindústria")
        if vert.sementeira: badges.append("🌱 Sementeira")
        if vert.silos: badges.append("🏗️ Silos")
        if vert.algodoeira: badges.append("☁️ Algodoeira")
        if vert.usina: badges.append("⚡ Usina")
        if vert.frigorifico: badges.append("🥩 Frigorífico")
        if dossie.dados_financeiros.governanca_corporativa: badges.append("📊 Governança")
        
        if badges:
            st.markdown(" ".join([f"`{b}`" for b in badges]))
        
        # Meta info
        st.caption(
            f"⏱️ Gerado em {dossie.tempo_total_segundos:.1f}s | "
            f"📅 {dossie.timestamp_geracao} | "
            f"🤖 {dossie.modelo_usado}"
        )
    
    with col_quality:
        if dossie.quality_report:
            qr = dossie.quality_report
            level_colors = {
                QualityLevel.EXCELENTE: "🟢",
                QualityLevel.BOM: "🔵",
                QualityLevel.ACEITAVEL: "🟡",
                QualityLevel.INSUFICIENTE: "🔴",
            }
            st.metric(
                label="Quality Gate",
                value=f"{qr.score_qualidade:.0f}%",
                delta=f"{level_colors.get(qr.nivel, '')} {qr.nivel.value}",
            )
    
    st.markdown("---")
    
    # === MOVIMENTOS FINANCEIROS ===
    fin = dossie.dados_financeiros
    if fin.movimentos_financeiros or fin.fiagros_relacionados or fin.cras_emitidos:
        st.markdown("### 💰 Movimentos de Mercado & Governança")
        
        col_mov, col_fiagro = st.columns(2)
        
        with col_mov:
            for item in fin.movimentos_financeiros:
                st.markdown(f"- 🏦 **{item}**")
        
        with col_fiagro:
            if fin.fiagros_relacionados:
                st.markdown("**Fiagros:**")
                for f_item in fin.fiagros_relacionados:
                    st.markdown(f"- 📈 {f_item}")
            if fin.cras_emitidos:
                st.markdown("**CRAs:**")
                for c_item in fin.cras_emitidos:
                    st.markdown(f"- 📜 {c_item}")
            if fin.auditorias:
                st.markdown("**Auditorias:**")
                for a_item in fin.auditorias:
                    st.markdown(f"- ✅ {a_item}")
        
        st.markdown("---")
    
    # === RAIO-X DA OPERAÇÃO ===
    st.markdown("### 📊 Raio-X da Operação")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    hectares = dossie.dados_operacionais.hectares_total
    funcs = fin.funcionarios_estimados
    capital = fin.capital_social_estimado
    culturas = dossie.dados_operacionais.culturas
    fazendas = dossie.dados_operacionais.numero_fazendas
    
    c1.metric("Área Total", f"{hectares:,.0f} ha" if hectares > 0 else "N/D")
    c2.metric("Funcionários", f"{funcs:,}" if funcs > 0 else "N/D")
    c3.metric("Capital", f"R$ {capital/1e6:.1f}M" if capital > 0 else "N/D")
    c4.metric("Culturas", ", ".join(culturas[:3]) if culturas else "N/D")
    c5.metric("Fazendas", str(fazendas) if fazendas > 0 else "N/D")
    
    if dossie.sas_result.dados_inferidos:
        st.caption("⚠️ Alguns valores foram estimados por heurísticas de mercado.")
    
    st.markdown("---")
    
    # === SCORE BREAKDOWN (SPIDER CHART) ===
    st.markdown("### 📊 Breakdown do Score SAS 4.0")
    
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        breakdown = dossie.sas_result.breakdown
        categories = ["Músculo\n(Porte)", "Complexidade", "Gente\n(Gestão)", "Momento\n(Gov/Tech)"]
        values = [breakdown.musculo, breakdown.complexidade, breakdown.gente, breakdown.momento]
        max_values = [400, 250, 200, 150]
        percentages = [v/m*100 for v, m in zip(values, max_values)]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=percentages + [percentages[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name='Score',
            line_color='#667eea',
            fillcolor='rgba(102, 126, 234, 0.3)',
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%"),
            ),
            showlegend=False,
            height=350,
            margin=dict(l=60, r=60, t=30, b=30),
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_table:
        df_score = pd.DataFrame([
            {"Pilar": "Músculo (Porte)", "Pontos": breakdown.musculo, "Máx": 400,
             "Pct": f"{breakdown.musculo/400*100:.0f}%"},
            {"Pilar": "Complexidade", "Pontos": breakdown.complexidade, "Máx": 250,
             "Pct": f"{breakdown.complexidade/250*100:.0f}%"},
            {"Pilar": "Gente (Gestão)", "Pontos": breakdown.gente, "Máx": 200,
             "Pct": f"{breakdown.gente/200*100:.0f}%"},
            {"Pilar": "Momento (Gov)", "Pontos": breakdown.momento, "Máx": 150,
             "Pct": f"{breakdown.momento/150*100:.0f}%"},
        ])
        st.dataframe(df_score, hide_index=True, use_container_width=True)
        
        st.markdown(f"**Total: {dossie.sas_result.score}/1000** — {dossie.sas_result.tier.value}")
    
    # === JUSTIFICATIVAS DO SCORE ===
    if dossie.sas_result.justificativas:
        with st.expander("🔍 Justificativas do Cálculo"):
            for j in dossie.sas_result.justificativas:
                st.text(f"→ {j}")
    
    st.markdown("---")
    
    # === INTEL DE MERCADO ===
    intel = dossie.intel_mercado
    if intel.noticias_recentes or intel.sinais_compra or intel.dores_identificadas:
        st.markdown("### 📡 Inteligência de Mercado")
        
        tab_sinais, tab_noticias, tab_riscos = st.tabs(
            ["🎯 Sinais de Compra", "📰 Notícias", "⚠️ Riscos & Oportunidades"]
        )
        
        with tab_sinais:
            if intel.sinais_compra:
                for s in intel.sinais_compra:
                    st.markdown(f"- 🟢 {s}")
            if intel.dores_identificadas:
                st.markdown("**Dores Identificadas:**")
                for d in intel.dores_identificadas:
                    st.markdown(f"- 🔴 {d}")
        
        with tab_noticias:
            for n in intel.noticias_recentes:
                if isinstance(n, dict):
                    st.markdown(f"**{n.get('titulo', 'Notícia')}** ({n.get('data_aprox', '')})")
                    st.caption(n.get('resumo', ''))
                else:
                    st.markdown(f"- {n}")
        
        with tab_riscos:
            col_risk, col_opp = st.columns(2)
            with col_risk:
                st.markdown("**⚠️ Riscos:**")
                for r in intel.riscos:
                    st.markdown(f"- {r}")
            with col_opp:
                st.markdown("**💡 Oportunidades:**")
                for o in intel.oportunidades:
                    st.markdown(f"- {o}")
    
    st.markdown("---")
    
    # === ANÁLISE ESTRATÉGICA ===
    st.markdown("### 🧠 Inteligência Estratégica (Agente Sara)")
    
    for secao in dossie.secoes_analise:
        with st.expander(f"{secao.icone} {secao.titulo}", expanded=True):
            st.markdown(secao.conteudo)
    
    st.markdown("---")
    
    # === DADOS CNPJ ===
    if dossie.dados_cnpj:
        with st.expander("📋 Dados Cadastrais (CNPJ)"):
            cnpj_data = dossie.dados_cnpj
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Razão Social:** {cnpj_data.razao_social}")
                st.markdown(f"**Nome Fantasia:** {cnpj_data.nome_fantasia}")
                st.markdown(f"**CNPJ:** {formatar_cnpj(cnpj_data.cnpj)}")
                st.markdown(f"**Situação:** {cnpj_data.situacao_cadastral}")
                st.markdown(f"**Abertura:** {cnpj_data.data_abertura}")
            with col_b:
                st.markdown(f"**Natureza Jurídica:** {cnpj_data.natureza_juridica}")
                st.markdown(f"**Capital Social:** R$ {cnpj_data.capital_social:,.2f}")
                st.markdown(f"**Porte:** {cnpj_data.porte}")
                st.markdown(f"**CNAE:** {cnpj_data.cnae_principal} — {cnpj_data.cnae_descricao}")
                st.markdown(f"**Local:** {cnpj_data.municipio}/{cnpj_data.uf}")
            
            if cnpj_data.qsa:
                st.markdown("**Quadro Societário:**")
                df_qsa = pd.DataFrame(cnpj_data.qsa)
                st.dataframe(df_qsa, hide_index=True, use_container_width=True)
    
    # === QUALITY GATE ===
    if dossie.quality_report:
        with st.expander("✅ Relatório de Qualidade (Quality Gate)"):
            qr = dossie.quality_report
            
            for check in qr.checks:
                icon = "✅" if check.passou else "❌"
                st.markdown(f"{icon} **{check.criterio}** — {check.nota}")
            
            if qr.recomendacoes:
                st.markdown("**Recomendações:**")
                for rec in qr.recomendacoes:
                    st.markdown(f"- {rec}")
    
    # === EXPORTAÇÃO ===
    st.markdown("---")
    st.markdown("### 📤 Exportar Dossiê")
    
    col_export1, col_export2, col_export3 = st.columns(3)
    
    # Markdown completo
    md_content = f"# Dossiê: {nome_grupo}\n"
    md_content += f"**Score SAS 4.0:** {dossie.sas_result.score}/1000 — {dossie.sas_result.tier.value}\n\n"
    md_content += f"**Gerado em:** {dossie.timestamp_geracao}\n\n---\n\n"
    
    for secao in dossie.secoes_analise:
        md_content += f"## {secao.icone} {secao.titulo}\n\n{secao.conteudo}\n\n---\n\n"
    
    if fin.movimentos_financeiros:
        md_content += "## 💰 Movimentos Financeiros\n\n"
        for m in fin.movimentos_financeiros:
            md_content += f"- {m}\n"
    
    with col_export1:
        st.download_button(
            "📝 Baixar Markdown",
            data=md_content,
            file_name=f"dossie_{nome_grupo.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    
    with col_export2:
        json_export = {
            "empresa": nome_grupo,
            "score": dossie.sas_result.score,
            "tier": dossie.sas_result.tier.value,
            "breakdown": dossie.sas_result.breakdown.to_dict(),
            "dados_operacionais": {
                "hectares": dossie.dados_operacionais.hectares_total,
                "culturas": dossie.dados_operacionais.culturas,
                "regioes": dossie.dados_operacionais.regioes_atuacao,
            },
            "dados_financeiros": {
                "capital": fin.capital_social_estimado,
                "funcionarios": fin.funcionarios_estimados,
                "movimentos": fin.movimentos_financeiros,
                "fiagros": fin.fiagros_relacionados,
                "cras": fin.cras_emitidos,
            },
            "timestamp": dossie.timestamp_geracao,
        }
        st.download_button(
            "📊 Baixar JSON",
            data=json.dumps(json_export, indent=2, ensure_ascii=False),
            file_name=f"dossie_{nome_grupo.replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
        )
    
    with col_export3:
        if st.button("📋 Copiar Texto", use_container_width=True):
            st.code(md_content, language="markdown")
    
    # === LOG DE EXECUÇÃO ===
    with st.expander("🖥️ Log de Execução do Pipeline"):
        for log in st.session_state.logs:
            st.text(log)
        
        st.markdown("---")
        st.caption(f"Cache: {cache.stats} | Queue: {request_queue.stats}")
