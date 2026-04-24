import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Central Telefónica", layout="wide")

USERNAME = "8668334"
PASSWORD = "28719014429"
BASE_URL = "https://callmyway.com/getCdrs.php"

# --- FUNCIONES DE CONSUMO DE API ---
@st.cache_data(ttl=10)
def get_live_cdrs():
    url = f"https://www.callmyway.com/getCdrs.php?username={USERNAME}&password={PASSWORD}&live=1&fullAccount=1&format=json"
    try:
        response = requests.get(url)
        if response.status_code == 200 and response.text.strip():
            return response.json()
        return []
    except Exception as e:
        return []

def get_historical_cdrs(start_date, end_date, offset=0, limit=1000):
    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")
    url = f"{BASE_URL}?username={USERNAME}&password={PASSWORD}&dateStart={start_str}&dateEnd={end_str}&ini={offset}&cant={limit}&format=json"
    try:
        response = requests.get(url)
        if response.status_code == 200 and response.text.strip():
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error conectando a la API: {e}")
        return []

# --- INTERFAZ DEL DASHBOARD ---
st.title("📞 Dashboard Avanzado de Central Telefónica")

tab1, tab2 = st.tabs(["🔴 Llamadas en Vivo (Live)", "📊 Analíticas y Métricas (Histórico)"])

with tab1:
    st.header("Monitoreo en Tiempo Real")
    if st.button("🔄 Actualizar Ahora (Live)"):
        st.rerun()
        
    live_data = get_live_cdrs()
    if live_data:
        df_live = pd.DataFrame(live_data)
        st.metric(label="Llamadas Activas", value=len(df_live))
        st.dataframe(df_live, use_container_width=True)
    else:
        st.info("No hay llamadas activas en este momento.")

with tab2:
    st.header("Análisis de Rendimiento y Agentes")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_d = st.date_input("Fecha Inicio", datetime.now() - timedelta(days=7))
    with col2:
        end_d = st.date_input("Fecha Fin", datetime.now())
    with col3:
        limit = st.number_input("Límite (Paginación)", min_value=1, value=5000)
        
    start_datetime = datetime.combine(start_d, datetime.min.time())
    end_datetime = datetime.combine(end_d, datetime.max.time())
    
    if st.button("🔍 Cargar Métricas"):
        with st.spinner("Procesando datos analíticos..."):
            hist_data = get_historical_cdrs(start_datetime, end_datetime, limit=limit)
            
            if hist_data:
                df = pd.DataFrame(hist_data)
                
                # =====================================================================
                # ATENCIÓN: Mapeo de columnas. 
                # Ajusta estos nombres según los que te devuelva tu API en el JSON real.
                # =====================================================================
                COL_DURATION = 'duration'       # O 'billsec', 'tiempo'
                COL_AGENT = 'src'               # O 'origen', 'callerid', 'accountcode'
                COL_STATUS = 'disposition'      # O 'estado', 'status' (ej. ANSWERED, FAILED)
                COL_DATE = 'calldate'           # O 'fecha', 'start'
                
                # Verificar si las columnas estándar existen para evitar errores
                missing_cols = [col for col in [COL_DURATION, COL_AGENT, COL_STATUS] if col not in df.columns]
                
                if missing_cols:
                    st.warning(f"⚠️ Las siguientes columnas estándar no se encontraron en el JSON de tu API: {missing_cols}. Se muestran los datos en crudo. Por favor, edita los nombres de las variables en el código.")
                    st.dataframe(df, use_container_width=True)
                else:
                    # Limpieza de datos básica
                    df[COL_DURATION] = pd.to_numeric(df[COL_DURATION], errors='coerce').fillna(0)
                    
                    st.markdown("---")
                    st.subheader("📈 Métricas Generales (KPIs)")
                    
                    # 1. KPIs Generales
                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                    total_llamadas = len(df)
                    duracion_total_min = df[COL_DURATION].sum() / 60
                    duracion_prom_sec = df[COL_DURATION].mean()
                    llamadas_contestadas = len(df[df[COL_STATUS].astype(str).str.contains('ANSWER', case=False, na=False)])
                    asr_porcentaje = (llamadas_contestadas / total_llamadas) * 100 if total_llamadas > 0 else 0

                    kpi1.metric("Total Llamadas", total_llamadas)
                    kpi2.metric("Duración Total (Minutos)", f"{duracion_total_min:.1f}")
                    kpi3.metric("Duración Promedio (Segundos)", f"{duracion_prom_sec:.1f}")
                    kpi4.metric("Tasa de Respuesta (ASR)", f"{asr_porcentaje:.1f}%")

                    st.markdown("---")
                    
                    # 2. Gráficos Generales
                    col_graf1, col_graf2 = st.columns(2)
                    
                    with col_graf1:
                        # Gráfico de estado de llamadas
                        status_counts = df[COL_STATUS].value_counts().reset_index()
                        status_counts.columns = ['Estado', 'Cantidad']
                        fig_status = px.pie(status_counts, values='Cantidad', names='Estado', title='Distribución del Estado de Llamadas', hole=0.4)
                        st.plotly_chart(fig_status, use_container_width=True)
                        
                    with col_graf2:
                        # Top 10 Agentes con más llamadas
                        agent_counts = df[COL_AGENT].value_counts().head(10).reset_index()
                        agent_counts.columns = ['Agente / Extensión', 'Llamadas']
                        fig_agents = px.bar(agent_counts, x='Agente / Extensión', y='Llamadas', title='Top 10 Agentes por Volumen de Llamadas', color='Llamadas')
                        st.plotly_chart(fig_agents, use_container_width=True)

                    st.markdown("---")
                    st.subheader("👥 Métricas Detalladas por Agente")
                    
                    # 3. Tabla Agrupada por Agente
                    agent_metrics = df.groupby(COL_AGENT).agg(
                        Total_Llamadas=(COL_DURATION, 'count'),
                        Duracion_Total_Seg=(COL_DURATION, 'sum'),
                        Duracion_Promedio=(COL_DURATION, 'mean')
                    ).reset_index()
                    
                    # Redondear duración promedio
                    agent_metrics['Duracion_Promedio'] = agent_metrics['Duracion_Promedio'].round(1)
                    
                    # Ordenar por el que hizo más llamadas
                    agent_metrics = agent_metrics.sort_values(by='Total_Llamadas', ascending=False)
                    
                    st.dataframe(agent_metrics, use_container_width=True)
                    
            else:
                st.warning("No se encontraron registros o hubo un error en la consulta.")
