"""
Dashboard de Central Telefónica (PBX) - Versión Professional
Monitoreo en tiempo real de llamadas, agentes y métricas de servicio
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os
from typing import Dict, List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

TIMEZONE = ZoneInfo("America/Lima")
CONFIG_FILE = "config.json"


def get_lima_time() -> datetime:
    """Obtiene hora actual en zona Lima."""
    return datetime.now(TIMEZONE).replace(tzinfo=None)


def load_credentials() -> Tuple[str, str]:
    """Carga credenciales desde secrets."""
    try:
        return st.secrets["CMW_USER"], st.secrets["CMW_PASS"]
    except KeyError:
        st.error("⚠ Configura CMW_USER y CMW_PASS en .streamlit/secrets.toml")
        st.stop()


CMWUSER, CMWPASS = load_credentials()


# ═══════════════════════════════════════════════════════════════════════════════
# DATOS POR DEFECTO
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_AGENTS = {
    "8668106": {"nombre": "Central Virtual", "activo": True, "es_central": True},
    "8668109": {"nombre": "Alonso Loyola", "activo": True, "es_central": False},
    "8668110": {"nombre": "Jose Luis Cahuana", "activo": True, "es_central": False},
    "8668112": {"nombre": "Daniel Huayta", "activo": True, "es_central": False},
    "8668111": {"nombre": "Deivy Chavez", "activo": True, "es_central": False},
    "8668114": {"nombre": "Joe Villanueva", "activo": True, "es_central": False},
    "8672537": {"nombre": "Victor Figueroa", "activo": True, "es_central": False},
}

DEFAULT_SHIFTS = [
    {"dias": [0, 1, 2, 3, 4], "h_ini": 6, "h_fin": 14, "agente": "Alonso Loyola", "activo": True},
    {"dias": [0, 1, 2, 3, 4], "h_ini": 14, "h_fin": 22, "agente": "Jose Luis Cahuana", "activo": True},
    {"dias": [0, 1, 2, 3, 4], "h_ini": 22, "h_fin": 30, "agente": "Deivy Chavez", "activo": True},
    {"dias": [5, 6], "h_ini": 6, "h_fin": 14, "agente": "Daniel Huayta", "activo": True},
    {"dias": [5, 6], "h_ini": 14, "h_fin": 22, "agente": "Luz Goicochea", "activo": True},
    {"dias": [5, 6], "h_ini": 22, "h_fin": 30, "agente": "Joe Villanueva", "activo": True},
]

DEFAULT_EXCLUDED_NUMBERS = ["51902871550"]


# ═══════════════════════════════════════════════════════════════════════════════
# GESTIÓN DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def load_config() -> Tuple[Dict, List[Dict], List[str], int, bool]:
    """Carga configuración desde archivo JSON."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return (
                saved.get("agents", json.loads(json.dumps(DEFAULT_AGENTS))),
                saved.get("shifts", json.loads(json.dumps(DEFAULT_SHIFTS))),
                saved.get("excluded_numbers", list(DEFAULT_EXCLUDED_NUMBERS)),
                saved.get("callback_window", 5),
                saved.get("demo_mode", False)
            )
        except (json.JSONDecodeError, IOError) as e:
            st.warning(f"Error al leer config: {e}")
    
    return (
        json.loads(json.dumps(DEFAULT_AGENTS)),
        json.loads(json.dumps(DEFAULT_SHIFTS)),
        list(DEFAULT_EXCLUDED_NUMBERS),
        5,
        False
    )


def save_config() -> bool:
    """Guarda configuración en archivo JSON."""
    try:
        config_data = {
            "agents": st.session_state.cfg_agents,
            "shifts": st.session_state.cfg_shifts,
            "excluded_numbers": st.session_state.cfg_excluded_numbers,
            "callback_window": st.session_state.cfg_callback_window,
            "demo_mode": st.session_state.cfg_demo_mode
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        st.error(f"No se pudo guardar: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════

def format_duration(seconds: int) -> str:
    """Convierte segundos a formato HH:MM:SS."""
    if not seconds or seconds <= 0:
        return "00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes:02d}:{secs:02d}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Formatea valor como porcentaje."""
    return f"{value:.{decimals}f}%" if isinstance(value, (int, float)) else "—"


def get_color_scale(value: float, max_val: float = 100) -> str:
    """Retorna color según valor (rojo-amarillo-verde)."""
    ratio = value / max_val if max_val > 0 else 0
    if ratio < 0.5:
        return "#EF4444"  # Rojo
    elif ratio < 0.8:
        return "#F59E0B"  # Amarillo
    else:
        return "#22C55E"  # Verde


# ═══════════════════════════════════════════════════════════════════════════════
# TEMAS Y ESTILOS
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "dark": {
        "bg": "#06080F",
        "sidebar": "#090B14",
        "card": "#0C0F1C",
        "text": "#C8D8E8",
        "muted": "#2A4060",
        "primary": "#5A9AEA",
        "green": "#22C55E",
        "red": "#EF4444",
        "yellow": "#EAB308",
        "plot_bg": "#06080F",
        "grid": "rgba(255,255,255,.03)",
        "border": "rgba(255,255,255,.05)",
    },
    "light": {
        "bg": "#F0F4F8",
        "sidebar": "#FFFFFF",
        "card": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#334155",
        "primary": "#4F46E5",
        "green": "#16A34A",
        "red": "#DC2626",
        "yellow": "#B45309",
        "plot_bg": "#FFFFFF",
        "grid": "rgba(0,0,0,.09)",
        "border": "rgba(0,0,0,.12)",
    },
}


def get_plotly_template(colors: Dict) -> Dict:
    """Retorna configuración para gráficos Plotly."""
    return {
        "plot_bgcolor": colors["plot_bg"],
        "paper_bgcolor": colors["plot_bg"],
        "font": {"family": "Arial, sans-serif", "size": 11, "color": colors["text"]},
        "margin": {"l": 50, "r": 20, "t": 40, "b": 40},
        "xaxis": {"gridcolor": colors["grid"], "zeroline": False},
        "yaxis": {"gridcolor": colors["grid"], "zeroline": False},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def init_session():
    """Inicializa variables de sesión."""
    if "cfg_agents" not in st.session_state:
        agents, shifts, excluded, callback, demo = load_config()
        st.session_state.cfg_agents = agents
        st.session_state.cfg_shifts = shifts
        st.session_state.cfg_excluded_numbers = excluded
        st.session_state.cfg_callback_window = callback
        st.session_state.cfg_demo_mode = demo
        st.session_state.refresh_count = 0


init_session()

# Configuración página
st.set_page_config(
    page_title="PBX Dashboard | Central Telefónica",
    page_icon="☎️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - CONTROLES GLOBALES
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ☎️ Dashboard Central")
    st.markdown("---")
    
    # Selector de tema
    theme = st.radio("🎨 Tema", ["dark", "light"], horizontal=True)
    colors = THEMES[theme]
    
    # Selector de rango de fechas
    st.markdown("### 📅 Período")
    date_range = st.radio(
        "Mostrar datos de:",
        ["Hoy", "Últimos 7 días", "Este mes"],
        horizontal=True
    )
    
    # Modo demo
    st.markdown("### ⚙️ Configuración")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄", help="Refrescar datos"):
            st.session_state.refresh_count += 1
            st.rerun()
    with col2:
        if st.button("⚙️", help="Configuración"):
            st.session_state.show_settings = True
    
    st.markdown("---")
    st.caption(f"Última actualización: {get_lima_time().strftime('%H:%M:%S')}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - TABS PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

# Header
st.title("☎️ Dashboard Central Telefónica")
hoy = get_lima_time()
st.markdown(f"📅 {hoy.strftime('%A, %d de %B de %Y').replace('Monday', 'Lunes').replace('Tuesday', 'Martes').replace('Wednesday', 'Miércoles').replace('Thursday', 'Jueves').replace('Friday', 'Viernes').replace('Saturday', 'Sábado').replace('Sunday', 'Domingo')} | Modo: {'📱 Demo' if st.session_state.cfg_demo_mode else '🔗 Conectado'}")

# Crear datos de ejemplo para demostración
def generate_sample_data():
    """Genera datos de ejemplo para demostración."""
    import random
    
    dates = pd.date_range(end=get_lima_time(), periods=200, freq='15min')
    agents = list(st.session_state.cfg_agents.values())
    
    data = {
        'detect_time': dates,
        'numero_cliente': [f"+51{random.randint(900000000, 999999999)}" for _ in range(len(dates))],
        'agente': [random.choice([a['nombre'] for a in agents]) for _ in range(len(dates))],
        'atendida': [random.choice([True, True, True, False]) for _ in range(len(dates))],
        'duracion': [random.randint(0, 3600) for _ in range(len(dates))],
        'type': [random.choice(['incoming', 'outgoing']) for _ in range(len(dates))],
    }
    return pd.DataFrame(data)


# Cargar datos (usa generate_sample_data para demostración)
if st.session_state.cfg_demo_mode:
    df_calls = generate_sample_data()
else:
    # Aquí iría la lógica para obtener datos reales desde la API
    df_calls = pd.DataFrame()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Resumen",
    "👥 Agentes",
    "⏰ Turnos",
    "📋 Registros",
    "⚙️ Configuración"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════

with tab1:
    if df_calls.empty:
        st.info("📡 Modo demo desactivado. Activa en Configuración para ver datos de ejemplo.")
    else:
        # Métricas principales
        st.markdown("### 📊 Métricas Principales")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_calls = len(df_calls)
        answered = int((df_calls['atendida'] == True).sum()) if 'atendida' in df_calls else 0
        lost = total_calls - answered
        rate = (answered / total_calls * 100) if total_calls > 0 else 0
        avg_duration = int(df_calls[df_calls['duracion'] > 0]['duracion'].mean()) if len(df_calls) > 0 else 0
        
        with col1:
            st.metric("📞 Total", f"{total_calls:,}")
        with col2:
            st.metric("✅ Atendidas", f"{answered:,}", f"+{rate:.1f}%")
        with col3:
            st.metric("❌ Perdidas", f"{lost:,}", f"-{100-rate:.1f}%")
        with col4:
            st.metric("⏱️ Dur. promedio", format_duration(avg_duration))
        with col5:
            st.metric("📈 Tasa", f"{rate:.1f}%")
        
        st.markdown("---")
        
        # Gráficos principales
        plot_template = get_plotly_template(colors)
        
        # Gráfico 1: Llamadas por hora
        if 'detect_time' in df_calls.columns:
            df_calls['hora'] = pd.to_datetime(df_calls['detect_time']).dt.hour
            calls_by_hour = df_calls.groupby('hora').size()
            
            fig_timeline = go.Figure(
                data=[
                    go.Scatter(
                        x=calls_by_hour.index,
                        y=calls_by_hour.values,
                        mode='lines+markers',
                        name='Llamadas',
                        line=dict(color=colors['primary'], width=3),
                        marker=dict(size=8, color=colors['primary']),
                        fill='tozeroy',
                        fillcolor=f"rgba(90, 154, 234, 0.2)",
                    )
                ],
                layout=go.Layout(
                    title="Llamadas por hora",
                    height=350,
                    hovermode='x unified',
                    **plot_template
                )
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Gráficos secundarios
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Llamadas por agente
            if 'agente' in df_calls.columns:
                calls_by_agent = df_calls['agente'].value_counts().head(10)
                fig_agents = px.bar(
                    x=calls_by_agent.values,
                    y=calls_by_agent.index,
                    orientation='h',
                    title="Top 10 Agentes (por volumen)",
                    labels={'x': 'Llamadas', 'y': 'Agente'},
                    color=calls_by_agent.values,
                    color_continuous_scale=[colors['red'], colors['yellow'], colors['green']]
                )
                fig_agents.update_layout(height=300, **plot_template, showlegend=False)
                fig_agents.update_traces(marker_line_width=0)
                st.plotly_chart(fig_agents, use_container_width=True)
        
        with col_b:
            # Tasa de atención
            if 'atendida' in df_calls.columns:
                by_agent = df_calls.groupby('agente').agg({
                    'atendida': ['sum', 'count']
                }).reset_index()
                by_agent.columns = ['agente', 'atendidas', 'total']
                by_agent['tasa'] = (by_agent['atendidas'] / by_agent['total'] * 100).round(1)
                by_agent = by_agent.sort_values('tasa', ascending=False).head(10)
                
                fig_rate = px.bar(
                    by_agent,
                    y='agente',
                    x='tasa',
                    orientation='h',
                    title="Tasa de atención por agente",
                    labels={'tasa': 'Tasa %', 'agente': ''},
                    color='tasa',
                    color_continuous_scale=[colors['red'], colors['green']],
                    text='tasa'
                )
                fig_rate.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
                fig_rate.update_layout(height=300, **plot_template, showlegend=False)
                st.plotly_chart(fig_rate, use_container_width=True)
        
        # Tipo de llamadas
        col_c, col_d = st.columns(2)
        
        with col_c:
            if 'type' in df_calls.columns:
                call_types = df_calls['type'].value_counts()
                fig_types = go.Figure(data=[go.Pie(
                    labels=['📲 Entrante' if t == 'incoming' else '📤 Saliente' for t in call_types.index],
                    values=call_types.values,
                    marker=dict(colors=[colors['primary'], colors['green']])
                )])
                fig_types.update_layout(height=300, **plot_template)
                st.plotly_chart(fig_types, use_container_width=True)
        
        with col_d:
            if 'atendida' in df_calls.columns:
                status = df_calls['atendida'].value_counts()
                fig_status = go.Figure(data=[go.Pie(
                    labels=['✅ Atendida' if s else '❌ Perdida' for s in [True, False]],
                    values=[status.get(True, 0), status.get(False, 0)],
                    marker=dict(colors=[colors['green'], colors['red']])
                )])
                fig_status.update_layout(height=300, **plot_template)
                st.plotly_chart(fig_status, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: AGENTES
# ═══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("### 👥 Agentes Registrados")
    
    agent_rows = []
    for agent_id, info in st.session_state.cfg_agents.items():
        agent_rows.append({
            "🆔 ID": agent_id,
            "👤 Nombre": info['nombre'],
            "✅ Activo": "Sí" if info['activo'] else "No",
            "🏢 Central": "Sí" if info['es_central'] else "No"
        })
    
    st.dataframe(pd.DataFrame(agent_rows), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### 📊 Desempeño de Agentes")
    
    if not df_calls.empty and 'agente' in df_calls.columns:
        perf_data = df_calls.groupby('agente').agg({
            'atendida': ['sum', 'count'],
            'duracion': 'mean'
        }).reset_index()
        perf_data.columns = ['agente', 'atendidas', 'total', 'dur_promedio']
        perf_data['tasa'] = (perf_data['atendidas'] / perf_data['total'] * 100).round(1)
        perf_data = perf_data.sort_values('total', ascending=False)
        
        col1, col2 = st.columns(2)
        with col1:
            display_cols = perf_data[['agente', 'total', 'atendidas', 'tasa']].copy()
            display_cols.columns = ['Agente', 'Total', 'Atendidas', 'Tasa %']
            st.dataframe(display_cols, use_container_width=True, hide_index=True)
        
        with col2:
            fig_perf = px.bar(
                perf_data.head(8),
                x='agente',
                y='tasa',
                title="Tasa de atención",
                labels={'tasa': 'Porcentaje (%)', 'agente': 'Agente'},
                color='tasa',
                color_continuous_scale=[colors['red'], colors['green']]
            )
            fig_perf.update_layout(height=300, **plot_template, showlegend=False)
            st.plotly_chart(fig_perf, use_container_width=True)
    else:
        st.info("Activa modo demo para ver datos de desempeño")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: TURNOS
# ═══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("### ⏰ Turnos Configurados")
    
    shift_rows = []
    days_map = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}
    
    for turno in st.session_state.cfg_shifts:
        dias_str = ", ".join([days_map[d] for d in turno['dias']])
        h_fin_display = f"{turno['h_fin']}:00" if turno['h_fin'] < 24 else "06:00 (+1)"
        
        shift_rows.append({
            "📅 Días": dias_str,
            "⏤ Inicio": f"{turno['h_ini']:02d}:00",
            "⏤ Fin": h_fin_display,
            "👤 Agente": turno['agente'],
            "✅ Activo": "Sí" if turno['activo'] else "No"
        })
    
    st.dataframe(pd.DataFrame(shift_rows), use_container_width=True, hide_index=True)
    
    if st.button("✏️ Editar Turnos"):
        st.session_state.show_shift_editor = True
        st.info("Edición de turnos: próximamente")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: REGISTROS
# ═══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("### 📋 Registros Detallados")
    
    if df_calls.empty:
        st.info("No hay registros disponibles. Activa modo demo.")
    else:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search = st.text_input("🔍 Buscar número")
        with col2:
            agent_filter = st.selectbox("Agente", ["Todos"] + sorted(df_calls['agente'].unique().tolist()))
        with col3:
            status_filter = st.selectbox("Estado", ["Todos", "Atendidas", "Perdidas"])
        
        # Aplicar filtros
        df_filtered = df_calls.copy()
        
        if search:
            df_filtered = df_filtered[df_filtered['numero_cliente'].astype(str).str.contains(search)]
        if agent_filter != "Todos":
            df_filtered = df_filtered[df_filtered['agente'] == agent_filter]
        if status_filter == "Atendidas":
            df_filtered = df_filtered[df_filtered['atendida'] == True]
        elif status_filter == "Perdidas":
            df_filtered = df_filtered[df_filtered['atendida'] == False]
        
        # Mostrar datos
        st.dataframe(
            df_filtered[[c for c in ['detect_time', 'numero_cliente', 'agente', 'atendida', 'duracion', 'type'] if c in df_filtered.columns]],
            use_container_width=True,
            height=400
        )
        
        # Descargar
        csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "⬇ Descargar CSV",
            data=csv,
            file_name=f"registros_{hoy.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("### ⚙️ Configuración del Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📱 Modo Demo")
        demo_mode = st.toggle(
            "Activar datos de ejemplo",
            value=st.session_state.cfg_demo_mode
        )
        st.session_state.cfg_demo_mode = demo_mode
        
        if demo_mode:
            st.success("✅ Modo demo activo. Ves datos de ejemplo.")
        else:
            st.info("🔗 Conectado a central real. (Verifica credenciales)")
    
    with col2:
        st.markdown("#### 📞 Parámetros")
        callback_window = st.slider(
            "Ventana de callback (minutos)",
            min_value=1,
            max_value=30,
            value=st.session_state.cfg_callback_window
        )
        st.session_state.cfg_callback_window = callback_window
    
    st.markdown("---")
    
    st.markdown("#### 🗂️ Agentes y Turnos")
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("✏️ Editar Agentes", use_container_width=True):
            st.info("Editor de agentes: próximamente")
    
    with col_b:
        if st.button("✏️ Editar Turnos", use_container_width=True):
            st.info("Editor de turnos: próximamente")
    
    st.markdown("---")
    
    st.markdown("#### 💾 Persistencia")
    col_save, col_reset = st.columns(2)
    
    with col_save:
        if st.button("💾 Guardar Configuración", use_container_width=True):
            if save_config():
                st.success("✅ Configuración guardada")
            else:
                st.error("❌ Error al guardar")
    
    with col_reset:
        if st.button("🔄 Restaurar Defaults", use_container_width=True):
            st.session_state.cfg_agents = json.loads(json.dumps(DEFAULT_AGENTS))
            st.session_state.cfg_shifts = json.loads(json.dumps(DEFAULT_SHIFTS))
            st.session_state.cfg_excluded_numbers = list(DEFAULT_EXCLUDED_NUMBERS)
            st.session_state.cfg_callback_window = 5
            st.session_state.cfg_demo_mode = False
            if save_config():
                st.success("✅ Configuración restaurada a valores por defecto")
            st.rerun()
    
    st.markdown("---")
    st.markdown("#### 📝 Información")
    st.caption("Dashboard v2.0 | Central Telefónica PBX")
    st.caption(f"Hora actual: {get_lima_time().strftime('%Y-%m-%d %H:%M:%S')} (Lima)")
