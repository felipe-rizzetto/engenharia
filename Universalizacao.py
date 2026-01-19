import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel Universalização", page_icon="📊", layout="wide")

# --- CONFIGURAÇÃO DOS CAMINHOS ---
CAMINHO_OBRA_LEAN = "Executado Obra Lean.xlsx"
CAMINHO_UNIVERSALIZACAO = "Universalização 2026.xlsx"

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

    # --- 2. CARREGA EXECUTADO ---
    if os.path.exists(CAMINHO_OBRA_LEAN):
        try:
            df_exec = pd.read_excel(CAMINHO_OBRA_LEAN, sheet_name='Tarefas') 
        except:
            df_exec = pd.read_excel(CAMINHO_OBRA_LEAN)
            
        if 'Data' in df_exec.columns:
            df_exec['Data'] = pd.to_datetime(df_exec['Data'], errors='coerce')
        
        cols_num = ['Extensão (m)', 'Ligações (und)']
        for col in cols_num:
            if col in df_exec.columns:
                df_exec[col] = pd.to_numeric(df_exec[col], errors='coerce').fillna(0)
        
        if 'Bacia' in df_exec.columns:
            df_exec['Bacia'] = df_exec['Bacia'].fillna('N/A').astype(str)
    else:
        df_exec = pd.DataFrame()

    return df_plan_ano, df_exec, df_plan_bacia

# Carrega Dados
df_plan_ano, df_exec, df_plan_bacia = load_data()

if df_plan_ano.empty:
    st.warning("Dados de planejamento não encontrados.")
    st.stop()

# ==========================================
# === FILTROS ===
# ==========================================
st.sidebar.header("🎛️ Filtros do Painel")

# 1. Filtro de Data
# 1. Filtro de Data
# Define as datas padrão solicitadas: 01/01/2025 e Hoje
default_start = pd.to_datetime("2025-01-01").date()
default_end = pd.Timestamp.now().date()

st.sidebar.markdown("**Período**")
c1, c2 = st.sidebar.columns(2)

# O parâmetro 'value' define qual data já vem selecionada quando abre o painel
d_ini = c1.date_input("Início", value=default_start)
d_fim = c2.date_input("Fim", value=default_end)

# 2. Filtro de Bacia
lista_bacias = sorted(df_exec['Bacia'].unique()) if not df_exec.empty and 'Bacia' in df_exec.columns else []
if not lista_bacias: lista_bacias = ["Sem Bacia Definida"]
sel_bacia = st.sidebar.multiselect("Filtrar Bacia", lista_bacias, default=lista_bacias)

# Aplica Filtros
if not df_exec.empty:
    mask_date = (df_exec['Data'].dt.date >= d_ini) & (df_exec['Data'].dt.date <= d_fim)
    mask_bacia = df_exec['Bacia'].isin(sel_bacia) if sel_bacia else [True] * len(df_exec)
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

# --- GRÁFICO 2: BARRAS (Extensão de Rede) ---
st.subheader("📊 Extensão de Rede por Bacia")

if not df_plan_bacia.empty:
    bacia_plan_totals = {}
    cols_bacia = [c for c in df_plan_bacia.columns if c != 'Mês']
    
    for col in cols_bacia:
        incluir = False
        if not sel_bacia: incluir = True
        else:
             for b in sel_bacia:
                 if b.lower() in col.lower(): incluir = True; break
        if incluir: bacia_plan_totals[col] = df_plan_bacia[col].sum()

    bacia_exec_totals = {key: 0.0 for key in bacia_plan_totals.keys()}
    if not df_exec_filtered.empty and 'Sub Bacia' in df_exec_filtered.columns:
        df_exec_group = df_exec_filtered.groupby(['Sub Bacia'])['Extensão (m)'].sum().reset_index()
        for _, row in df_exec_group.iterrows():
            sub = str(row['Sub Bacia']).strip()
            val = row['Extensão (m)']
            for plan_col in bacia_plan_totals.keys():
                if sub.lower() in plan_col.lower(): bacia_exec_totals[plan_col] += val; break

    if bacia_plan_totals:
        df_bacia_comp = pd.DataFrame({
            'Bacia': list(bacia_plan_totals.keys()),
            'Previsto': list(bacia_plan_totals.values()),
            'Executado': [bacia_exec_totals.get(k, 0) for k in bacia_plan_totals.keys()]
        }).sort_values('Previsto', ascending=True)

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(y=df_bacia_comp['Bacia'], x=df_bacia_comp['Previsto'], name='Previsto', orientation='h', marker_color='blue', text=df_bacia_comp['Previsto'].apply(lambda x: f"{x:,.0f}"), textposition='auto'))
        fig_bar.add_trace(go.Bar(y=df_bacia_comp['Bacia'], x=df_bacia_comp['Executado'], name='Executado', orientation='h', marker_color='green', text=df_bacia_comp['Executado'].apply(lambda x: f"{x:,.0f}"), textposition='auto'))
        fig_bar.update_layout(barmode='group', height=500, legend=dict(orientation="h", y=1.1, x=0))
        st.plotly_chart(fig_bar, use_container_width=True)

# --- TABELA SIMPLIFICADA (SOLICITADA) ---
st.markdown("---")
st.subheader("📋 Resumo Executado por Bacia (Obra Lean)")

if not df_exec_filtered.empty:
    # Seleciona apenas as colunas necessárias para o agrupamento
    # Soma Extensão e Ligações por Bacia
    cols_sum = []
    if 'Extensão (m)' in df_exec_filtered.columns: cols_sum.append('Extensão (m)')
    if 'Ligações (und)' in df_exec_filtered.columns: cols_sum.append('Ligações (und)')
    
    if 'Bacia' in df_exec_filtered.columns and cols_sum:
        df_tabela = df_exec_filtered.groupby('Bacia')[cols_sum].sum().reset_index()
        
        # Formatação e Exibição
        st.dataframe(
            df_tabela.style.format({
                'Extensão (m)': '{:,.2f}', 
                'Ligações (und)': '{:,.0f}'
            }),
            use_container_width=True,
            height=500
        )
    else:
        st.error("Colunas 'Bacia', 'Extensão (m)' ou 'Ligações (und)' não encontradas no arquivo executado.")
else:
    st.info("Nenhum dado executado encontrado para os filtros selecionados.")