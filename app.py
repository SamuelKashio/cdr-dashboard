import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================
API_BASE_URL = "https://callmyway.com/getCdrs.php"
API_BASE_URL_LIVE = "https://www.callmyway.com/getCdrs.php"

# Credenciales hardcodeadas
USERNAME = "8668334"
PASSWORD = "28719014429"

# Mapeo de agentes (Endpoint -> Nombre)
AGENTES = {
    "8668106": "Central_Virtual",
    "8668109": "Edwin Loyola",
    "8668110": "Jose Luis Cahuana",
    "8668112": "Daniel Huayta",
    "8668111": "Deivy Chavez",
    "8668114": "Joe Villanueva",
    "8672537": "Victor Figueroa"
}

# Nombres esperados de columnas en el JSON de la API
COL_DURATION = "duration"          # Duración en segundos
COL_AGENT = "src"                  # Extensión/agente origen
COL_STATUS = "disposition"         # Estado de la llamada (Answered, Busy, No Answer, etc.)
COL_CALLER_ID = "caller_id"
COL_DST = "dst"
COL_START_TIME = "start_time"
COL_ANSWER_TIME = "answer_time"
COL_END_TIME = "end_time"

# =============================================================================
# FUNCIONES DE CONSUMO DE API
# =============================================================================
def fetch_cdrs_history(date_start, date_end, offset=0, limit=5000):
    """
    Obtiene CDRs históricos por rango de fechas con paginación.
    Retorna un DataFrame de pandas o None si hay error.
    """
    params = {
        "username": USERNAME,
        "password": PASSWORD,
        "dateStart": date_start,
        "dateEnd": date_end,
        "ini": offset,
        "cant": limit,
        "format": "json"
    }
    try:
        response = requests.get(API_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict) and "data" in data:
            return pd.DataFrame(data["data"])
        else:
            st.error("Formato de respuesta inesperado en histórico.")
            return None
    except Exception as e:
        st.error(f"Error al consultar histórico: {e}")
        return None

def fetch_cdrs_live():
    """
    Obtiene CDRs de llamadas en vivo.
    Retorna un DataFrame de pandas o None si hay error o no hay datos.
    """
    params = {
        "username": USERNAME,
        "password": PASSWORD,
        "live": 1,
        "fullAccount": 1,
        "format": "json"
    }
    try:
        response = requests.get(API_BASE_URL_LIVE, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict) and "data" in data:
            return pd.DataFrame(data["data"])
        else:
            # Puede que devuelva un objeto vacío o mensaje
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al consultar llamadas en vivo: {e}")
        return None

# =============================================================================
# FUNCIONES DE PROCESAMIENTO Y MÉTRICAS
# =============================================================================
def safe_float_convert(series):
    """Convierte una serie a numérico, forzando errores a NaN."""
    return pd.to_numeric(series, errors='coerce')

def calculate_metrics(df):
    """
    Calcula KPIs a partir del DataFrame de CDRs.
    Retorna un diccionario con las métricas.
    """
    if df.empty:
        return {
            "total_calls": 0,
            "total_duration_min": 0.0,
            "avg_duration_sec": 0.0,
            "asr": 0.0
        }
    
    total_calls = len(df)
    
    # Duración total (segundos) -> minutos
    if COL_DURATION in df.columns:
        durations = safe_float_convert(df[COL_DURATION])
        total_duration_sec = durations.sum()
        total_duration_min = total_duration_sec / 60.0
        avg_duration_sec = durations.mean()
    else:
        total_duration_min = 0.0
        avg_duration_sec = 0.0
    
    # ASR: Llamadas contestadas / total
    if COL_STATUS in df.columns:
        answered = df[df[COL_STATUS].astype(str).str.lower() == "answered"].shape[0]
        asr = (answered / total_calls * 100) if total_calls > 0 else 0.0
    else:
        asr = 0.0
    
    return {
        "total_calls": total_calls,
        "total_duration_min": round(total_duration_min, 2),
        "avg_duration_sec": round(avg_duration_sec, 2),
        "asr": round(asr, 2)
    }

def enrich_agent_names(df):
    """Añade columna con nombre legible del agente basado en el mapeo."""
    if COL_AGENT in df.columns:
        df["agent_name"] = df[COL_AGENT].astype(str).map(AGENTES)
        # Los que no tengan mapeo conservan el número original
        df["agent_name"] = df["agent_name"].fillna(df[COL_AGENT].astype(str))
    return df

def get_top_agents(df, top_n=10):
    """Retorna DataFrame con top N agentes por volumen de llamadas."""
    if df.empty or COL_AGENT not in df.columns:
        return pd.DataFrame()
    
    agent_counts = df[COL_AGENT].value_counts().reset_index()
    agent_counts.columns = [COL_AGENT, "total_calls"]
    agent_counts = agent_counts.head(top_n)
    # Añadir nombre legible
    agent_counts["agent_name"] = agent_counts[COL_AGENT].astype(str).map(AGENTES)
    agent_counts["agent_name"] = agent_counts["agent_name"].fillna(agent_counts[COL_AGENT].astype(str))
    return agent_counts

def get_agent_summary(df):
    """
    Retorna DataFrame agrupado por agente con:
    Total llamadas, Duración Total (min), Duración Promedio (seg)
    """
    if df.empty or COL_AGENT not in df.columns:
        return pd.DataFrame()
    
    # Asegurar duración numérica
    if COL_DURATION in df.columns:
        df["_duration_num"] = safe_float_convert(df[COL_DURATION])
    else:
        df["_duration_num"] = 0
    
    summary = df.groupby(COL_AGENT).agg(
        total_calls=(COL_AGENT, 'count'),
        total_duration_sec=('_duration_num', 'sum')
    ).reset_index()
    
    summary["total_duration_min"] = summary["total_duration_sec"] / 60.0
    summary["avg_duration_sec"] = summary.apply(
        lambda row: row["total_duration_sec"] / row["total_calls"] if row["total_calls"] > 0 else 0,
        axis=1
    )
    # Redondeos
    summary["total_duration_min"] = summary["total_duration_min"].round(2)
    summary["avg_duration_sec"] = summary["avg_duration_sec"].round(2)
    
    # Agregar nombre legible
    summary["agent_name"] = summary[COL_AGENT].astype(str).map(AGENTES)
    summary["agent_name"] = summary["agent_name"].fillna(summary[COL_AGENT].astype(str))
    
    # Ordenar por total de llamadas descendente
    summary = summary.sort_values("total_calls", ascending=False)
    
    # Seleccionar columnas finales
    return summary[[COL_AGENT, "agent_name", "total_calls", "total_duration_min", "avg_duration_sec"]]

# =============================================================================
# INTERFAZ STREAMLIT
# =============================================================================
st.set_page_config(page_title="Dashboard PBX - Monitoreo Telefónico", layout="wide")
st.title("📞 Dashboard de Monitoreo de Central Telefónica (PBX)")

# Crear dos pestañas principales
tab_live, tab_history = st.tabs(["🎥 Llamadas en Vivo", "📊 Histórico y Métricas"])

# =============================================================================
# PESTAÑA 1: LLAMADAS EN VIVO
# =============================================================================
with tab_live:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Llamadas Activas en este momento")
    with col2:
        if st.button("🔄 Recargar", use_container_width=True):
            st.rerun()
    
    # Consultar live data
    df_live = fetch_cdrs_live()
    
    if df_live is None:
        st.warning("No se pudo obtener información de llamadas en vivo.")
    elif df_live.empty:
        st.info("✅ No hay llamadas activas en este momento.")
    else:
        # KPI: total de llamadas activas
        total_active = len(df_live)
        st.metric("📞 Llamadas Activas", total_active)
        
        # Mostrar tabla enriquecida con nombres de agentes
        df_live_display = enrich_agent_names(df_live)
        # Seleccionar columnas relevantes si existen
        cols_to_show = []
        if COL_AGENT in df_live_display.columns:
            cols_to_show.append("agent_name")
        for col in [COL_CALLER_ID, COL_DST, COL_STATUS, COL_DURATION, COL_START_TIME]:
            if col in df_live_display.columns:
                cols_to_show.append(col)
        if not cols_to_show:
            cols_to_show = df_live_display.columns.tolist()
        
        st.dataframe(df_live_display[cols_to_show], use_container_width=True)

# =============================================================================
# PESTAÑA 2: HISTÓRICO Y MÉTRICAS
# =============================================================================
with tab_history:
    st.subheader("Configuración de consulta")
    
    # Filtros interactivos
    col_date1, col_date2, col_limit = st.columns(3)
    with col_date1:
        # Fecha inicio: por defecto hoy 00:00:00
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = st.date_input("Fecha Inicio", value=today)
        start_time = st.time_input("Hora Inicio", value=datetime.strptime("00:00:00", "%H:%M:%S").time())
    with col_date2:
        # Fecha fin: por defecto hoy 23:59:59
        end_date = st.date_input("Fecha Fin", value=today)
        end_time = st.time_input("Hora Fin", value=datetime.strptime("23:59:59", "%H:%M:%S").time())
    with col_limit:
        limit_registros = st.number_input("Límite de registros", min_value=1, max_value=100000, value=5000, step=100)
    
    # Botón de búsqueda
    search_clicked = st.button("🔍 Buscar CDRs", type="primary", use_container_width=True)
    
    if search_clicked:
        # Construir strings fecha-hora en formato exacto: yyyy-mm-dd HH:ii:ss
        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
        start_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        with st.spinner("Consultando CDRs históricos..."):
            # Llamada a la API (offset=0, usamos el límite directamente)
            df_history = fetch_cdrs_history(start_str, end_str, offset=0, limit=limit_registros)
        
        if df_history is None:
            st.error("No se pudieron obtener los datos históricos.")
        elif df_history.empty:
            st.warning("No se encontraron registros en el rango seleccionado.")
        else:
            st.success(f"Se obtuvieron {len(df_history)} registros.")
            
            # Enriquecer con nombres de agentes
            df_history = enrich_agent_names(df_history)
            
            # Verificar si existen columnas necesarias
            required_cols = [COL_DURATION, COL_STATUS, COL_AGENT]
            missing_cols = [c for c in required_cols if c not in df_history.columns]
            
            if missing_cols:
                st.warning(f"El JSON devuelto no contiene las columnas esperadas: {missing_cols}. Se mostrará la tabla en crudo.")
                st.dataframe(df_history, use_container_width=True)
            else:
                # 1. KPIs Globales
                metrics = calculate_metrics(df_history)
                col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
                with col_kpi1:
                    st.metric("📞 Total llamadas", metrics["total_calls"])
                with col_kpi2:
                    st.metric("⏱️ Duración Total (min)", metrics["total_duration_min"])
                with col_kpi3:
                    st.metric("⚡ Duración Promedio (seg)", metrics["avg_duration_sec"])
                with col_kpi4:
                    st.metric("📈 Tasa de Respuesta (ASR)", f"{metrics['asr']}%")
                
                # 2. Gráfico de dona: distribución de estados
                if COL_STATUS in df_history.columns:
                    status_counts = df_history[COL_STATUS].value_counts().reset_index()
                    status_counts.columns = ["Estado", "Cantidad"]
                    fig_donut = px.pie(status_counts, values="Cantidad", names="Estado", 
                                       title="Distribución por Estado de Llamada",
                                       hole=0.4)
                    st.plotly_chart(fig_donut, use_container_width=True)
                else:
                    st.info("No se pudo mostrar gráfico de estados: columna 'disposition' no encontrada.")
                
                # 3. Gráfico de barras: Top 10 agentes por volumen
                top_agents = get_top_agents(df_history, top_n=10)
                if not top_agents.empty:
                    fig_bar = px.bar(top_agents, x="agent_name", y="total_calls",
                                     title="Top 10 Agentes con Mayor Volumen de Llamadas",
                                     labels={"agent_name": "Agente", "total_calls": "Total llamadas"},
                                     text="total_calls")
                    fig_bar.update_traces(textposition="outside")
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("No se pudo generar el gráfico de agentes (sin datos o columna src faltante).")
                
                # 4. Tabla de Agentes (agrupada)
                st.subheader("📋 Resumen por Agente")
                agent_summary = get_agent_summary(df_history)
                if not agent_summary.empty:
                    # Renombrar para mejor presentación
                    agent_summary_display = agent_summary.rename(columns={
                        COL_AGENT: "Extensión",
                        "agent_name": "Agente",
                        "total_calls": "Total llamadas",
                        "total_duration_min": "Duración Total (min)",
                        "avg_duration_sec": "Duración Promedio (seg)"
                    })
                    st.dataframe(agent_summary_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No se pudo generar la tabla de resumen por agente.")
                
                # Opcional: mostrar muestra de los datos crudos (desplegable)
                with st.expander("Ver datos crudos (muestra)"):
                    st.dataframe(df_history.head(100), use_container_width=True)

# =============================================================================
# NOTA FINAL: El dashboard está listo para ejecutarse con: streamlit run app.py
# =============================================================================
