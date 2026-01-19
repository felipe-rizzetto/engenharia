import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Universalização", page_icon="📊", layout="wide")

# --- CONFIGURAÇÃO DOS CAMINHOS ---
PASTA_LEAN = r""

# Lista dos arquivos a serem lidos
ARQUIVOS_LEAN = [
    "UNIVERSALIZAÇÃO MACEIÓ (BACIA ICARAI) - Apontamentos.xlsx",
    "UNIVERSALIZAÇÃO LARGO DA BATALHA _ BADU (BACIA ICARAI) - Apontamentos.xlsx",
    "UNIVERSALIZAÇÃO ENGENHOCA (BACIA BARRETO) - Apontamentos.xlsx",
    "UNIVERSALIZAÇÃO SANTA BÁRBARA (BACIA SAPÊ) - Apontamentos.xlsx"
]

CAMINHO_UNIVERSALIZACAO = r"Universalização 2026.xlsx"

@st.cache_data
def load_data():
    # --- 1. CARREGA PLANEJADO ---
    if os.path.exists(CAMINHO_UNIVERSALIZACAO):
        try:
            df_plan_ano = pd.read_excel(CAMINHO_UNIVERSALIZACAO, sheet_name='Serviços por Ano')
            df_plan_ano['Data'] = pd.to_datetime(df_plan_ano['Data'], errors='coerce')
        except:
            df_plan_ano = pd.DataFrame()
            
        try:
            df_plan_bacia = pd.read_excel(CAMINHO_UNIVERSALIZACAO, sheet_name='Planejamento Físico Bacias')
        except:
            df_plan_bacia = pd.DataFrame()
    else:
        df_plan_ano = pd.DataFrame()
        df_plan_bacia = pd.DataFrame()

    # --- 2. CARREGA EXECUTADO (AGRUPADO NAS 3 BACIAS) ---
    lista_dfs_exec = []
    
    for arquivo in ARQUIVOS_LEAN:
        caminho_completo = os.path.join(PASTA_LEAN, arquivo)
        
        if os.path.exists(caminho_completo):
            try:
                df_temp = pd.read_excel(caminho_completo, sheet_name='Tarefas')
                
                # --- DEFINIÇÃO DA MACRO BACIA PELA NOMENCLATURA DO ARQUIVO ---
                # Forçamos a classificação correta ignorando o que está escrito dentro da planilha se necessário
                nome_arq = arquivo.upper()
                bacia_detectada = "Outra"
                
                if 'ICARAI' in nome_arq:
                    bacia_detectada = "Bacia Icaraí"
                elif 'BARRETO' in nome_arq:
                    bacia_detectada = "Bacia Barreto"
                elif 'SAPÊ' in nome_arq or 'SAPE' in nome_arq:
                    bacia_detectada = "Bacia Sapê"
                
                # Aplica a bacia detectada em todas as linhas desse arquivo
                df_temp['Bacia_Macro'] = bacia_detectada
                
                lista_dfs_exec.append(df_temp)
            except Exception as e:
                st.warning(f"Erro ao ler arquivo {arquivo}: {e}")
                continue
    
    if lista_dfs_exec:
        df_exec = pd.concat(lista_dfs_exec, ignore_index=True)
        
        if 'Data' in df_exec.columns:
            df_exec['Data'] = pd.to_datetime(df_exec['Data'], errors='coerce')
        
        cols_num = ['Extensão (m)', 'Ligações (und)']
        for col in cols_num:
            if col in df_exec.columns:
                df_exec[col] = pd.to_numeric(df_exec[col], errors='coerce').fillna(0)
    else:
        df_exec = pd.DataFrame()

    return df_plan_ano, df_exec, df_plan_bacia

# Carrega Dados
df_plan_ano, df_exec, df_plan_bacia = load_data()

if df_plan_ano.empty and df_exec.empty:
    st.error("Nenhum dado encontrado.")
    st.stop()

# ==========================================
# === FILTROS ===
# ==========================================
st.sidebar.header("🎛️ Filtros do Painel")

# 1. Filtro de Data
default_start = pd.to_datetime("2025-01-01").date()
default_end = pd.Timestamp.now().date()
c1, c2 = st.sidebar.columns(2)
d_ini = c1.date_input("Início", value=default_start)
d_fim = c2.date_input("Fim", value=default_end)

# 2. Filtro de Bacia (Macro)
# Pega as bacias únicas que criamos (Icaraí, Barreto, Sapê)
lista_bacias = sorted(df_exec['Bacia_Macro'].unique()) if not df_exec.empty and 'Bacia_Macro' in df_exec.columns else []
sel_bacia = st.sidebar.multiselect("Filtrar Bacia", lista_bacias, default=lista_bacias)

# Aplica Filtros
if not df_exec.empty:
    mask_date = (df_exec['Data'].dt.date >= d_ini) & (df_exec['Data'].dt.date <= d_fim)
    mask_bacia = df_exec['Bacia_Macro'].isin(sel_bacia) if sel_bacia else [True] * len(df_exec)
    df_exec_filtered = df_exec[mask_date & mask_bacia].copy()
else:
    df_exec_filtered = pd.DataFrame()

if not df_plan_ano.empty:
    mask_date_plan = (df_plan_ano['Data'].dt.date >= d_ini) & (df_plan_ano['Data'].dt.date <= d_fim)
    df_plan_ano_filtered = df_plan_ano[mask_date_plan].copy()
else:
    df_plan_ano_filtered = pd.DataFrame()

# ==========================================
# === DASHBOARD ===
# ==========================================
st.title("Universalização | Visão Geral")
st.markdown(f"**Período:** {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')} | **Bacias:** {', '.join(sel_bacia) if sel_bacia else 'Todas'}")
st.markdown("---")

# --- KPIS ---
if not df_plan_ano_filtered.empty:
    col_rede = 'Rede' if 'Rede' in df_plan_ano_filtered.columns else df_plan_ano_filtered.columns[1]
    total_rede_plan = df_plan_ano_filtered[col_rede].sum()
    col_lne = 'Ligações' if 'Ligações' in df_plan_ano_filtered.columns else None
    total_lne_plan = df_plan_ano_filtered[col_lne].sum() if col_lne else 0
else:
    total_rede_plan = 0; total_lne_plan = 0

total_rede_exec = df_exec_filtered['Extensão (m)'].sum() if not df_exec_filtered.empty else 0
total_lne_exec = df_exec_filtered['Ligações (und)'].sum() if not df_exec_filtered.empty else 0
pct_rede = (total_rede_exec / total_rede_plan * 100) if total_rede_plan > 0 else 0

st.markdown("""<style>div[data-testid="metric-container"] {background-color: #f0f2f6; border: 1px solid #d6d6d6; padding: 10px; border-radius: 5px;}</style>""", unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.metric("Previsto Rede (Período)", f"{total_rede_plan:,.0f}".replace(",", "."))
with col2: st.metric("Previsto LNE (Período)", f"{total_lne_plan:,.0f}".replace(",", "."))
with col3: st.metric("Avanço Físico", f"{pct_rede:.2f}%")
with col4: st.metric("Executado Rede", f"{total_rede_exec:,.0f}".replace(",", "."))
with col5: st.metric("Executado LNE", f"{total_lne_exec:,.0f}".replace(",", "."))

st.markdown("---")

# --- GRÁFICO 1: CURVA S ---
st.subheader("📈 Evolução Acumulada (Período Selecionado)")
if not df_plan_ano_filtered.empty:
    df_chart_plan = df_plan_ano_filtered[['Data', 'Rede Acumulado']].sort_values('Data')
    if not df_exec_filtered.empty:
        df_exec_filtered['Mes_Ano'] = df_exec_filtered['Data'].dt.to_period('M').dt.to_timestamp()
        df_exec_monthly = df_exec_filtered.groupby('Mes_Ano')['Extensão (m)'].sum().reset_index().sort_values('Mes_Ano')
        df_exec_monthly['Executado Acumulado'] = df_exec_monthly['Extensão (m)'].cumsum()
    else:
        df_exec_monthly = pd.DataFrame()
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_chart_plan['Data'], y=df_chart_plan['Rede Acumulado'], mode='lines+markers', name='Previsto Acum.', line=dict(color='blue')))
    if not df_exec_monthly.empty:
        fig_line.add_trace(go.Scatter(x=df_exec_monthly['Mes_Ano'], y=df_exec_monthly['Executado Acumulado'], mode='lines+markers', name='Executado Acum.', line=dict(color='green'), fill='tozeroy'))
    fig_line.update_layout(height=400, xaxis_title="Mês", yaxis_title="Metros (m)", hovermode="x unified")
    st.plotly_chart(fig_line, use_container_width=True)

# --- GRÁFICO 2: BARRAS (AGRUPADO POR 3 BACIAS) ---
st.subheader("📊 Comparativo por Macro Bacia")

# 1. Preparar Dados de Planejamento (Agrupar colunas do Excel nas 3 Bacias)
# O Excel tem colunas como: "Maceió (Bacia Icaraí)", "Engenhoca (Bacia Barreto)"
bacias_alvo = ["Bacia Icaraí", "Bacia Barreto", "Bacia Sapê"]
plan_bacia_agrupado = {b: 0.0 for b in bacias_alvo}

if not df_plan_bacia.empty:
    cols_plan = [c for c in df_plan_bacia.columns if c != 'Mês']
    for col in cols_plan:
        valor_coluna = df_plan_bacia[col].sum()
        col_lower = col.lower()
        
        # Lógica de Agrupamento
        if "icaraí" in col_lower or "icarai" in col_lower:
            plan_bacia_agrupado["Bacia Icaraí"] += valor_coluna
        elif "barreto" in col_lower:
            plan_bacia_agrupado["Bacia Barreto"] += valor_coluna
        elif "sapê" in col_lower or "sape" in col_lower:
            plan_bacia_agrupado["Bacia Sapê"] += valor_coluna

# 2. Preparar Dados de Execução (Já temos a coluna Bacia_Macro correta)
exec_bacia_agrupado = {b: 0.0 for b in bacias_alvo}
if not df_exec_filtered.empty:
    # Agrupa pelo nome da Bacia Macro criada na leitura
    df_group = df_exec_filtered.groupby('Bacia_Macro')['Extensão (m)'].sum().reset_index()
    for _, row in df_group.iterrows():
        bacia = row['Bacia_Macro']
        if bacia in exec_bacia_agrupado:
            exec_bacia_agrupado[bacia] = row['Extensão (m)']

# 3. Filtrar apenas o que foi selecionado no Multiselect
keys_final = []
if sel_bacia:
    keys_final = [b for b in bacias_alvo if b in sel_bacia]
else:
    keys_final = bacias_alvo

# 4. Montar DataFrame Final para o Gráfico
df_bacia_comp = pd.DataFrame({
    'Bacia': keys_final,
    'Previsto': [plan_bacia_agrupado[k] for k in keys_final],
    'Executado': [exec_bacia_agrupado[k] for k in keys_final]
})

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(y=df_bacia_comp['Bacia'], x=df_bacia_comp['Previsto'], name='Previsto', orientation='h', marker_color='blue', text=df_bacia_comp['Previsto'].apply(lambda x: f"{x:,.0f}"), textposition='auto'))
fig_bar.add_trace(go.Bar(y=df_bacia_comp['Bacia'], x=df_bacia_comp['Executado'], name='Executado', orientation='h', marker_color='green', text=df_bacia_comp['Executado'].apply(lambda x: f"{x:,.0f}"), textposition='auto'))
fig_bar.update_layout(barmode='group', height=400, legend=dict(orientation="h", y=1.1, x=0))
st.plotly_chart(fig_bar, use_container_width=True)

# --- TABELA SIMPLIFICADA (APENAS 3 BACIAS) ---
st.markdown("---")
st.subheader("📋 Detalhamento Executado: Macro Bacias")

if not df_exec_filtered.empty:
    # Agrupa APENAS pela Bacia Macro
    df_tabela = df_exec_filtered.groupby('Bacia_Macro')[['Extensão (m)', 'Ligações (und)']].sum().reset_index()
    
    df_tabela.columns = ['Bacia', 'Extensão Executada (m)', 'Ligações Executadas (und)']
    df_tabela = df_tabela.sort_values('Bacia')
    
    st.dataframe(
        df_tabela.style.format({
            'Extensão Executada (m)': '{:,.2f}', 
            'Ligações Executadas (und)': '{:,.0f}'
        }),
        use_container_width=True,
        height=300, # Tabela menor pois tem poucas linhas agora
        hide_index=True 
    )
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")
