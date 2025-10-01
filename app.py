# app.py (VERSÃO CORRIGIDA - sem erro de coluna)
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(page_title="Análise PNAES - Todas as Regiões", layout="wide")

# FUNÇÃO DE CONEXÃO
@st.cache_resource
def init_connection():
    try:
        connection_string = "postgresql://data_iesb:iesb@bigdata.dataiesb.com:5432/iesb"
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            st.success("✅ Conexão estabelecida com sucesso!")
        return engine
    except Exception as e:
        st.error(f"❌ Erro na conexão: {str(e)}")
        return None

# FUNÇÕES PARA CARREGAR DADOS - VERSÃO CORRIGIDA
@st.cache_data
def load_ambulatory_data(_engine):
    query = """
    SELECT 
        municipio_codigo_com_dv as codigo_municipio,
        municipio_nome as nome_municipio,
        regiao_nome,
        uf_sigla,
        ano_producao_ambulatorial,
        qtd_total,
        vl_total,
        qtd_total_subgrupos
    FROM sus_procedimento_ambulatorial 
    WHERE ano_producao_ambulatorial >= '2020'
    """
    return pd.read_sql(query, _engine)

@st.cache_data
def load_population_data(_engine):
    query = """
    SELECT 
        "ANO",
        "CO_MUNICIPIO",
        "IDADE", 
        "SEXO",
        "TOTAL" as populacao
    FROM "Censo_20222_Populacao_Idade_Sexo" 
    LIMIT 100000
    """
    return pd.read_sql(query, _engine)

@st.cache_data
def load_economic_data(_engine):
    query = """
    SELECT 
        codigo_municipio_dv,
        ano_pib,
        vl_pib,
        vl_pib_per_capta,
        vl_servicos
    FROM pib_municipios 
    WHERE ano_pib >= '2020'
    LIMIT 50000
    """
    return pd.read_sql(query, _engine)

@st.cache_data
def load_municipio_data(_engine):
    # CONSULTA CORRIGIDA - apenas colunas que existem
    query = """
    SELECT 
        codigo_municipio_dv as codigo_municipio,
        nome_municipio,
        municipio_capital,
        latitude,
        longitude
        -- Removidas uf_sigla e regiao_nome que não existem na tabela
    FROM municipio 
    LIMIT 5000
    """
    return pd.read_sql(query, _engine)

# FUNÇÃO PARA EXPLORAR ESTRUTURA DAS TABELAS
@st.cache_data
def explore_database_structure(_engine):
    """Função para explorar quais colunas existem nas tabelas"""
    tables = ['municipio', 'sus_procedimento_ambulatorial', 'pib_municipios', 'Censo_20222_Populacao_Idade_Sexo']
    
    structure_info = {}
    
    for table in tables:
        try:
            # Pega algumas linhas para ver a estrutura
            sample_query = f"SELECT * FROM {table} LIMIT 1"
            sample_df = pd.read_sql(sample_query, _engine)
            structure_info[table] = {
                'columns': list(sample_df.columns),
                'sample_data': sample_df.iloc[0] if not sample_df.empty else None
            }
        except Exception as e:
            structure_info[table] = {'error': str(e)}
    
    return structure_info

def main():
    st.title("🏥 Análise PNAES - Sistema de Saúde Brasileiro")
    
    # Inicializar conexão
    if 'engine' not in st.session_state:
        with st.spinner("Conectando ao banco de dados..."):
            st.session_state.engine = init_connection()
    
    if st.session_state.engine:
        # Botão para explorar estrutura do banco (debug)
        with st.expander("🔍 Explorar Estrutura do Banco (Debug)"):
            if st.button("Ver estrutura das tabelas"):
                structure = explore_database_structure(st.session_state.engine)
                for table, info in structure.items():
                    st.write(f"**Tabela: {table}**")
                    if 'columns' in info:
                        st.write(f"Colunas: {info['columns']}")
                    if 'error' in info:
                        st.error(f"Erro: {info['error']}")
                    st.write("---")
        
        # Carregar dados
        with st.spinner("Carregando dados do sistema de saúde..."):
            df_ambulatorial = load_ambulatory_data(st.session_state.engine)
        
        with st.spinner("Carregando dados populacionais..."):
            df_populacao = load_population_data(st.session_state.engine)
        
        with st.spinner("Carregando dados de municípios..."):
            df_municipio = load_municipio_data(st.session_state.engine)
        
        with st.spinner("Carregando dados econômicos..."):
            df_economico = load_economic_data(st.session_state.engine)
        
        # Mostrar diagnóstico inicial
        st.header("📊 Diagnóstico dos Dados Carregados")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Dados Ambulatoriais", f"{len(df_ambulatorial):,}")
            if not df_ambulatorial.empty:
                st.caption(f"Regiões: {df_ambulatorial['regiao_nome'].nunique()}")
        
        with col2:
            st.metric("Dados Populacionais", f"{len(df_populacao):,}")
        
        with col3:
            st.metric("Municípios", f"{len(df_municipio):,}")
        
        with col4:
            st.metric("Dados Econômicos", f"{len(df_economico):,}")
        
        # Análise por Região (usando dados ambulatoriais que têm região)
        if not df_ambulatorial.empty:
            st.header("🏥 Análise por Região")
            
            # Verificar distribuição regional
            distribuicao_regioes = df_ambulatorial['regiao_nome'].value_counts()
            
            st.subheader("📈 Distribuição dos Dados por Região")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_dist = px.bar(
                    x=distribuicao_regioes.index,
                    y=distribuicao_regioes.values,
                    title="Quantidade de Registros por Região",
                    labels={'x': 'Região', 'y': 'Número de Registros'},
                    color=distribuicao_regioes.index
                )
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                st.write("**Resumo por Região:**")
                for regiao, count in distribuicao_regioes.items():
                    st.write(f"- {regiao}: {count:,} registros")
            
            # Análise de investimento por região
            st.subheader("💰 Investimento em Saúde por Região")
            
            investimento_regiao = df_ambulatorial.groupby('regiao_nome').agg({
                'vl_total': 'sum',
                'qtd_total': 'sum',
                'codigo_municipio': 'nunique'
            }).reset_index()
            
            investimento_regiao = investimento_regiao.rename(columns={
                'codigo_municipio': 'municipios',
                'vl_total': 'investimento_total',
                'qtd_total': 'procedimentos_total'
            })
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_invest = px.bar(
                    investimento_regiao,
                    x='regiao_nome',
                    y='investimento_total',
                    title='Investimento Total por Região (R$)',
                    color='regiao_nome',
                    labels={'investimento_total': 'Investimento (R$)', 'regiao_nome': 'Região'}
                )
                st.plotly_chart(fig_invest, use_container_width=True)
            
            with col2:
                fig_proc = px.bar(
                    investimento_regiao,
                    x='regiao_nome',
                    y='procedimentos_total',
                    title='Procedimentos Totais por Região',
                    color='regiao_nome',
                    labels={'procedimentos_total': 'Procedimentos', 'regiao_nome': 'Região'}
                )
                st.plotly_chart(fig_proc, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("📋 Detalhes por Região")
            investimento_regiao['investimento_total'] = investimento_regiao['investimento_total'].round(2)
            investimento_regiao['investimento_por_municipio'] = (investimento_regiao['investimento_total'] / investimento_regiao['municipios']).round(2)
            investimento_regiao['procedimentos_por_municipio'] = (investimento_regiao['procedimentos_total'] / investimento_regiao['municipios']).round(2)
            
            st.dataframe(investimento_regiao, use_container_width=True)
            
            # Análise por Estado
            st.header("📊 Análise por Estado")
            
            if 'uf_sigla' in df_ambulatorial.columns:
                dados_uf = df_ambulatorial.groupby('uf_sigla').agg({
                    'vl_total': 'sum',
                    'qtd_total': 'sum',
                    'codigo_municipio': 'nunique'
                }).reset_index()
                
                dados_uf = dados_uf.rename(columns={
                    'codigo_municipio': 'municipios',
                    'vl_total': 'investimento_total',
                    'qtd_total': 'procedimentos_total'
                })
                
                # Top 10 estados por investimento
                top_estados = dados_uf.nlargest(10, 'investimento_total')
                
                fig_top_estados = px.bar(
                    top_estados,
                    x='uf_sigla',
                    y='investimento_total',
                    title='Top 10 Estados - Investimento em Saúde',
                    color='uf_sigla',
                    labels={'investimento_total': 'Investimento (R$)', 'uf_sigla': 'Estado'}
                )
                st.plotly_chart(fig_top_estados, use_container_width=True)
                
                # Dados completos por estado
                with st.expander("📋 Ver todos os estados"):
                    st.dataframe(dados_uf.sort_values('investimento_total', ascending=False), use_container_width=True)
        
        # Análise temporal
        if not df_ambulatorial.empty and 'ano_producao_ambulatorial' in df_ambulatorial.columns:
            st.header("📅 Análise Temporal")
            
            evolucao_anual = df_ambulatorial.groupby('ano_producao_ambulatorial').agg({
                'vl_total': 'sum',
                'qtd_total': 'sum'
            }).reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_evol_invest = px.line(
                    evolucao_anual,
                    x='ano_producao_ambulatorial',
                    y='vl_total',
                    title='Evolução do Investimento em Saúde',
                    labels={'vl_total': 'Investimento (R$)', 'ano_producao_ambulatorial': 'Ano'}
                )
                st.plotly_chart(fig_evol_invest, use_container_width=True)
            
            with col2:
                fig_evol_proc = px.line(
                    evolucao_anual,
                    x='ano_producao_ambulatorial',
                    y='qtd_total',
                    title='Evolução dos Procedimentos',
                    labels={'qtd_total': 'Procedimentos', 'ano_producao_ambulatorial': 'Ano'}
                )
                st.plotly_chart(fig_evol_proc, use_container_width=True)
        
        # Dados brutos para download
        st.header("💾 Exportar Dados")
        
        if not df_ambulatorial.empty:
            csv_data = df_ambulatorial.to_csv(index=False)
            st.download_button(
                label="📥 Download Dados Ambulatoriais Completos",
                data=csv_data,
                file_name="dados_saude_brasil.csv",
                mime="text/csv",
                help="Baixe todos os dados de procedimentos ambulatoriais"
            )
        
        # Informações sobre os dados
        with st.expander("ℹ️ Sobre os Dados"):
            st.markdown("""
            **Fontes dos dados:**
            - 🏥 **SUS**: Procedimentos ambulatoriais (2020+)
            - 👥 **IBGE**: Dados populacionais do Censo
            - 💰 **PIB Municipal**: Dados econômicos
            - 🗺️ **Municípios**: Informações geográficas
            
            **Limitações:**
            - Dados carregados com limite para performance
            - Algumas tabelas podem ter colunas diferentes do esperado
            - Período principal: 2020 em diante
            """)
    
    else:
        st.error("Não foi possível conectar ao banco de dados")

if __name__ == "__main__":
    main()