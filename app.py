import streamlit as st
import pandas as pd
import random
from brain import investigate_company, SARA_PHRASES

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Senior Scout 360", 
    page_icon="🕵️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado para "Cara de Sistema"
st.markdown("""
<style>
    /* Cards de métricas mais bonitos */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    /* Botão Principal Destacado */
    div.stButton > button:first-child {
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
    /* Títulos dos Expanders mais fortes */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #31333F;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BARRA LATERAL (CONTROLES)
# ==========================================
with st.sidebar:
    st.title("🕵️ Senior Scout 360")
    st.caption("Intelligence Unit | v2.1 (Financial Sniper)")
    st.markdown("---")
    
    # Input Principal
    target_company = st.text_input("Alvo (Nome ou CNPJ)", placeholder="Ex: Grupo Jequitibá, Bom Futuro...")
    
    # Botão de Ação
    btn_investigate = st.button("🚀 Iniciar Investigação", type="primary")
    
    st.markdown("---")
    
    # Gestão de API Key (Blindagem contra erros)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Sistema Operacional")
    except (FileNotFoundError, KeyError):
        st.warning("⚠️ Modo Local / Sem Chave")
        api_key = st.text_input("Cole sua Gemini API Key:", type="password")
        if not api_key:
            st.error("Chave necessária para operar.")
            st.stop()

    st.markdown("---")
    st.info("**Metodologia SAS 4.0**\n\nInclui:\n- Rastreio de Grupo Econômico\n- Varredura de Fiagro/CRA\n- Análise de Governança")

# ==========================================
# 3. ÁREA PRINCIPAL (DASHBOARD)
# ==========================================

if not target_company:
    # Tela de Boas-vindas
    st.header("👋 Pronto para prospectar?")
    st.markdown("""
    O **Senior Scout** investiga além do óbvio.
    
    **O que ele faz agora:**
    1.  🛰️ **Rastreia** o Grupo Econômico real.
    2.  💰 **Caça** o dinheiro (Fiagro, CRA, Investimentos).
    3.  💎 **Classifica** o lead (Diamante, Ouro, Prata).
    4.  🧠 **Gera** o plano de ataque comercial.
    
    *Digite o nome de uma empresa ao lado para começar.*
    """)

else:
    if btn_investigate:
        # Placeholder para animação de carregamento
        loading_placeholder = st.empty()
        
        try:
            # 1. Efeito de "Pensando"
            with loading_placeholder.container():
                with st.spinner(random.choice(SARA_PHRASES)):
                    # === CHAMADA DO CÉREBRO ===
                    data, score, sections = investigate_company(target_company, api_key)
            
            # Limpa o loading
            loading_placeholder.empty()

            # 2. Cabeçalho do Dossiê
            col_header_1, col_header_2 = st.columns([1, 3])
            
            with col_header_1:
                # Exibe o Score Grande
                st.metric(
                    label="Senior Agro Score", 
                    value=f"{score['score']}/1000", 
                    delta=score['tier']
                )
            
            with col_header_2:
                # Título e Resumo
                st.subheader(f"Dossiê: {data.get('nome_grupo', target_company)}")
                st.markdown(f"**Resumo da Operação:** {data.get('resumo_operacao', 'N/D')}")
                
                # Badges de Verticalização
                vert = data.get('verticalizacao', {})
                badges = []
                if vert.get('agroindustria'): badges.append("🏭 Agroindústria")
                if vert.get('sementeira'): badges.append("🌱 Sementeira")
                if vert.get('silos'): badges.append("silos Armazenagem")
                if vert.get('algodoeira'): badges.append("☁️ Algodoeira")
                
                if badges:
                    st.markdown(" ".join([f"`{b}`" for b in badges]))

            st.markdown("---")
            
            # === NOVIDADE: SEÇÃO DE FINANÇAS (SNIPER) ===
            financas = data.get('movimentos_financeiros', [])
            if financas:
                st.markdown("#### 💰 Movimentos de Mercado & Governança")
                # Exibe como bullet points destacados
                for item in financas:
                    st.markdown(f"- 🏦 **{item}**")
                st.markdown("---")
            # ============================================

            # 3. Cards de Inteligência (Dados Hard)
            st.markdown("### 📊 Raio-X da Operação")
            
            c1, c2, c3, c4 = st.columns(4)
            
            hectares = data.get('hectares_total', 0)
            funcs = data.get('funcionarios_estimados', 0)
            capital = data.get('capital_social_estimado', 0)
            culturas = data.get('culturas', [])
            
            # Formatação inteligente
            hec_display = f"{hectares:,.0f} ha" if hectares > 0 else "N/D"
            func_display = f"{funcs}" if funcs > 0 else "N/D"
            cap_display = f"R$ {capital/1_000_000:.1f}M" if capital > 0 else "N/D"
            cult_display = ", ".join(culturas[:2]) if culturas else "Diversas"
            
            # Se for dado inferido, avisa
            if data.get('dados_inferidos'):
                st.caption("⚠️ Alguns dados foram estimados por heurística de mercado.")

            c1.metric("Área Estimada", hec_display)
            c2.metric("Funcionários (Est.)", func_display)
            c3.metric("Capital Aprox.", cap_display)
            c4.metric("Culturas", cult_display)

            st.markdown("---")

            # 4. Análise Estratégica da Sara (Segmentada)
            st.markdown("### 🧠 Inteligência Estratégica (Agente Sara)")
            
            # Garante que temos seções suficientes
            if not sections or len(sections) < 2:
                st.warning("A IA gerou a análise em bloco único. Leia abaixo:")
                st.markdown(sections[0] if sections else "Sem análise gerada.")
            else:
                if len(sections) >= 1:
                    with st.expander("🏢 1. Perfil e Mercado", expanded=True):
                        st.markdown(sections[0])
                
                if len(sections) >= 2:
                    with st.expander("🚜 2. Complexidade e Dores", expanded=True):
                        st.markdown(sections[1])
                        
                if len(sections) >= 3:
                    with st.expander("💡 3. Fit Senior (O Pitch)", expanded=True):
                        st.markdown(sections[2])

                if len(sections) >= 4:
                    with st.expander("⚔️ 4. Plano de Ataque", expanded=True):
                        st.markdown(sections[3])

            # 5. Breakdown do Score
            st.markdown("---")
            with st.expander("🔍 Ver Detalhes do Cálculo do Score"):
                st.markdown("Entenda como chegamos a este número:")
                
                breakdown = score.get('breakdown', {})
                df_score = pd.DataFrame([
                    {"Pilar": "Músculo (Porte)", "Pontos": breakdown.get('Músculo', 0), "Max": 400},
                    {"Pilar": "Complexidade", "Pontos": breakdown.get('Complexidade', 0), "Max": 250},
                    {"Pilar": "Gente (Gestão)", "Pontos": breakdown.get('Gente', 0), "Max": 200},
                    {"Pilar": "Momento (Tec/Gov)", "Pontos": breakdown.get('Momento', 0), "Max": 150},
                ])
                
                col_chart, col_table = st.columns(2)
                with col_chart:
                    st.bar_chart(df_score.set_index("Pilar")["Pontos"])
                with col_table:
                    st.table(df_score)

        except Exception as e:
            st.error("❌ Ocorreu um erro durante a investigação.")
            st.error(f"Detalhe técnico: {str(e)}")
            st.info("Tente novamente ou verifique se o nome da empresa está correto.")
