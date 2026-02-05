import streamlit as st
import pandas as pd
import random
from brain import investigate_company, SARA_PHRASES

# Configuração da Página
st.set_page_config(page_title="Senior Scout 360", page_icon="🕵️", layout="wide")

# CSS para ficar com cara de "Sistema"
st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #FF4B4B; color: white; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=50) # Placeholder Logo
    st.title("Senior Scout 360")
    st.markdown("---")
    
    target_company = st.text_input("Nome da Empresa ou CNPJ", placeholder="Ex: Bom Futuro Agrícola")
    
    # A CHAVE VAI AQUI (Secrets do Streamlit Cloud)
    # No seu computador local, você pode descomentar a linha abaixo para testar:
    # api_key = "SUA_API_KEY_AQUI" 
    api_key = st.secrets["GEMINI_API_KEY"] 
    
    btn_investigate = st.button("🚀 Iniciar Investigação")
    
    st.markdown("---")
    st.info("ℹ️ **Modo Online v1.0**\nBaseado na Engine SAS 4.0")

# Área Principal
if not target_company:
    st.header("👋 Bem-vindo ao Senior Scout")
    st.markdown("Digite o nome de um prospect agroindustrial ao lado para gerar um dossiê instantâneo.")
    
    # Exemplo visual do que faz
    with st.expander("Ver metodologia SAS 4.0"):
        st.write("O Senior Agro Score avalia 4 pilares: Músculo, Complexidade, Gente e Momento.")

else:
    if btn_investigate:
        # Efeito de loading com frases da Sara
        placeholder = st.empty()
        with st.spinner('Acionando Agente Sara...'):
            placeholder.info(random.choice(SARA_PHRASES))
            
            try:
                # Onde a mágica acontece
                data, score, analysis = investigate_company(target_company, api_key)
                
                placeholder.empty() # Limpa a mensagem
                
                # --- EXIBIÇÃO DOS RESULTADOS ---
                
                # 1. Cabeçalho e Score
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.metric("Senior Agro Score", f"{score['score']}/1000", score['tier'])
                with col2:
                    st.subheader(f"Dossiê: {target_company}")
                    st.caption(data.get('resumo_operacao'))
                
                # 2. Dados Estimados (Cards)
                st.markdown("### 📊 Dados de Inteligência Estimados")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Hectares", f"{data['hectares']:,} ha")
                c2.metric("Funcionários", data['funcionarios'])
                c3.metric("Capital Aprox.", f"R$ {data['capital_social']/1000000:.1f}M")
                c4.metric("Cultura", data['cultura_principal'])
                
                st.markdown("---")
                
                # 3. Análise da Sara
                st.markdown("### 🧠 Análise Estratégica (Agente Sara)")
                st.markdown(analysis)
                
                # 4. Gráfico Radar (Breakdown do Score)
                st.markdown("---")
                with st.expander("🔍 Detalhes do Score (Debug)"):
                    df_score = pd.DataFrame.from_dict(score['breakdown'], orient='index', columns=['Pontos'])
                    st.bar_chart(df_score)

            except Exception as e:
                st.error(f"Erro na investigação: {str(e)}")