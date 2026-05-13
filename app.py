import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json, os
import numpy as np

TZ = ZoneInfo("America/Lima")
def now_lima(): return datetime.now(TZ).replace(tzinfo=None)

try:
    _U = st.secrets["CMW_USER"]
    _P = st.secrets["CMW_PASS"]
except Exception:
    st.error("⚠ Configura CMW_USER y CMW_PASS en .streamlit/secrets.toml"); st.stop()

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_AGENTES = {
    "8668106":{"nombre":"Central Virtual","activo":True, "es_central":True},
    "8668109":{"nombre":"Edwin Loyola",     "activo":True, "es_central":False},
    "8668110":{"nombre":"Jose Luis Cahuana","activo":True,"es_central":False},
    "8668112":{"nombre":"Daniel Huayta",   "activo":True, "es_central":False},
    "8668111":{"nombre":"Deivy Chavez",    "activo":True, "es_central":False},
    "8668114":{"nombre":"Joe Villanueva",  "activo":True, "es_central":False},
    "8672537":{"nombre":"Victor Figueroa", "activo":True, "es_central":False},
}

DEFAULT_TURNOS = [
    {"dias":[0,1,2,3,4],"h_ini": 6,"h_fin":14,"agente":"Edwin Loyola",    "activo":True},
    {"dias":[0,1,2,3,4],"h_ini":14,"h_fin":22,"agente":"Jose Luis Cahuana","activo":True},
    {"dias":[0,1,2,3,4],"h_ini":22,"h_fin":30,"agente":"Deivy Chavez",     "activo":True},
    {"dias":[5,6],      "h_ini": 6,"h_fin":14,"agente":"Daniel Huayta",    "activo":True},
    {"dias":[5,6],      "h_ini":14,"h_fin":22,"agente":"Victor Figueroa",  "activo":True},
    {"dias":[5,6],      "h_ini":22,"h_fin":30,"agente":"Joe Villanueva",   "activo":True},
]

DEFAULT_NUMS_EXCLUIDOS = ["51902871550"]

CONFIG_FILE = "config.json"

# ── Config Management ──────────────────────────────────────────────────────────
def load_config():
    """Carga la configuración guardada o usa defaults"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,"r",encoding="utf-8") as f:
                saved = json.load(f)
                return (
                    saved.get("agentes", json.loads(json.dumps(DEFAULT_AGENTES))),
                    saved.get("turnos", json.loads(json.dumps(DEFAULT_TURNOS))),
                    saved.get("nums_excluidos", list(DEFAULT_NUMS_EXCLUIDOS)),
                    saved.get("ventana_cb", 5),
                    saved.get("modo_demo", False)
                )
        except: pass
    return (json.loads(json.dumps(DEFAULT_AGENTES)), 
            json.loads(json.dumps(DEFAULT_TURNOS)),
            list(DEFAULT_NUMS_EXCLUIDOS), 5, False)

def save_config():
    """Guarda la configuración actual"""
    try:
        with open(CONFIG_FILE,"w",encoding="utf-8") as f:
            json.dump({
                "agentes": st.session_state.cfg_agentes,
                "turnos": st.session_state.cfg_turnos,
                "nums_excluidos": st.session_state.cfg_nums_excluidos,
                "ventana_cb": st.session_state.cfg_ventana_cb,
                "modo_demo": st.session_state.cfg_modo_demo
            }, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")
        return False

# ── Themes ─────────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":"#06080F","sidebar":"#090B14","card":"#0C0F1C","card2":"#0b1120",
        "border":"rgba(255,255,255,.05)","border2":"rgba(255,255,255,.04)",
        "text":"#C8D8E8","muted":"#2A4060","muted2":"#1A3050","muted3":"#0F2030",
        "primary":"#5A9AEA","primary_dim":"#0F1A2E","primary_border":"rgba(60,120,220,.35)",
        "green":"#22C55E","green_dim":"#166534","green_border":"rgba(34,197,94,.15)",
        "red":"#EF4444","red_dim":"#7F1D1D","red_border":"rgba(239,68,68,.15)",
        "yellow":"#EAB308","yellow_dim":"#92400E",
        "plot_bg":"#06080F","grid":"rgba(255,255,255,.03)",
        "bar_green":"#166534","bar_red":"#7F1D1D","bar_blue":"#1D4ED8","bar_dark":"#4A0404",
        "input_bg":"#0F1525","scrollbar":"#1A2A40",
    },
    "light": {
        "bg":"#F0F4F8","sidebar":"#FFFFFF","card":"#FFFFFF","card2":"#F8FAFC",
        "border":"rgba(0,0,0,.12)","border2":"rgba(0,0,0,.08)",
        "text":"#0F172A","muted":"#334155","muted2":"#475569","muted3":"#64748B",
        "primary":"#4F46E5","primary_dim":"#EEF2FF","primary_border":"rgba(79,70,229,.3)",
        "green":"#16A34A","green_dim":"#14532D","green_border":"rgba(22,163,74,.25)",
        "red":"#DC2626","red_dim":"#7F1D1D","red_border":"rgba(220,38,38,.22)",
        "yellow":"#B45309","yellow_dim":"#78350F",
        "plot_bg":"#FFFFFF","grid":"rgba(0,0,0,.09)",
        "bar_green":"#16A34A","bar_red":"#DC2626","bar_blue":"#2563EB","bar_dark":"#7C3AED",
        "input_bg":"#F8FAFC","scrollbar":"#CBD5E1",
    }
}

def get_css(colors):
    """Genera CSS personalizado según el tema"""
    is_light = colors["bg"] != "#06080F"
    sidebar_text = colors["muted"] if not is_light else colors["text"]
    sidebar_label = colors["muted2"] if not is_light else colors["muted2"]
    
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{{font-family:'Outfit',sans-serif!important}}
.stApp{{background:{colors['bg']}!important}}.stApp>header{{background:transparent!important}}
section[data-testid="stSidebar"]{{background:{colors['sidebar']}!important;border-right:1px solid {colors['border']}!important}}
section[data-testid="stSidebar"] *{{color:{sidebar_text}!important}}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] strong{{color:{colors['text']}!important}}
section[data-testid="stSidebar"] label{{color:{sidebar_label}!important;font-size:11px!important;letter-spacing:.5px;text-transform:uppercase}}
section[data-testid="stSidebar"] input{{background:{colors['input_bg']}!important;border:1px solid {colors['primary_border']}!important;color:{colors['text']}!important;font-family:'JetBrains Mono',monospace!important;font-size:13px!important}}
section[data-testid="stSidebar"] .stButton button{{width:100%;background:{colors['primary_dim']}!important;border:1px solid {colors['primary_border']}!important;color:{colors['primary']}!important;font-weight:600!important}}
[data-testid="metric-container"]{{background:{colors['card']}!important;border:1px solid {colors['border']}!important;border-radius:12px!important;padding:16px 18px!important}}
[data-testid="stMetricLabel"]{{color:{colors['muted']}!important;font-size:10px!important;letter-spacing:1.8px!important;text-transform:uppercase!important;font-family:'JetBrains Mono',monospace!important}}
[data-testid="stMetricValue"]{{color:{colors['text']}!important;font-size:26px!important;font-weight:300!important}}
</style>"""

# ── Utility Functions ──────────────────────────────────────────────────────────
def fmt_dur(segundos):
    """Formatea duración en segundos a formato legible"""
    if not segundos or segundos == 0: return "0s"
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}h {m}m"
    elif m > 0: return f"{m}m {s}s"
    else: return f"{s}s"

def get_plotly_layout(title="", colors=None, height=400):
    """Devuelve configuración estándar para gráficos Plotly"""
    if colors is None:
        colors = THEMES["dark"]
    
    return dict(
        title=dict(text=title, font=dict(size=13, color=colors["muted"]), x=0),
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font=dict(family="Outfit, sans-serif", color=colors["text"], size=11),
        hovermode="closest",
        margin=dict(l=40, r=20, t=30, b=40),
        height=height,
        xaxis=dict(gridcolor=colors["grid"], showgrid=True, zeroline=False),
        yaxis=dict(gridcolor=colors["grid"], showgrid=True, zeroline=False),
        legend=dict(font_size=10, bgcolor="rgba(0,0,0,0)")
    )

# ── API Functions ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache por 5 minutos
def cargar_datos_api(fecha_ini, fecha_fin):
    """Carga datos reales de CallMyWay API"""
    try:
        # Ajusta esta URL según tu endpoint de CallMyWay
        url = "https://api.callmyway.com/cdr"
        
        params = {
            "from": fecha_ini.isoformat(),
            "to": fecha_fin.isoformat(),
            "limit": 1000
        }
        
        response = requests.get(
            url,
            params=params,
            auth=(_U, _P),
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if "cdrs" in data and data["cdrs"]:
                df = pd.DataFrame(data["cdrs"])
                st.success(f"✅ {len(df)} registros cargados de la API")
                return df, True
            else:
                st.info("ℹ️ No hay registros en este período")
                return pd.DataFrame(), True
        else:
            st.warning(f"⚠️ API respondió con código {response.status_code}")
            return pd.DataFrame(), False
            
    except requests.exceptions.Timeout:
        st.error("❌ Timeout: La API tardó demasiado en responder")
        return pd.DataFrame(), False
    except requests.exceptions.ConnectionError:
        st.error("❌ Error de conexión: Verifica tu conexión a internet")
        return pd.DataFrame(), False
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return pd.DataFrame(), False

# ── Session State Initialization ──────────────────────────────────────────────
if "cfg_agentes" not in st.session_state:
    agentes, turnos, excluidos, ventana, modo_demo = load_config()
    st.session_state.cfg_agentes = agentes
    st.session_state.cfg_turnos = turnos
    st.session_state.cfg_nums_excluidos = excluidos
    st.session_state.cfg_ventana_cb = ventana
    st.session_state.cfg_modo_demo = modo_demo

if "tema" not in st.session_state:
    st.session_state.tema = "dark"

if "df_actual" not in st.session_state:
    st.session_state.df_actual = pd.DataFrame()

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Central Telefónica",
    page_icon="☎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

colors = THEMES[st.session_state.tema]
P = get_plotly_layout("", colors)

st.markdown(get_css(colors), unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_theme = st.columns([0.8, 0.2])
with col_title:
    st.markdown("## ☎️ Dashboard Central Telefónica")
    st.markdown(f"<span style='color:{colors['muted']};font-size:12px'>Monitoreo en tiempo real de llamadas entrantes</span>", unsafe_allow_html=True)

with col_theme:
    nuevo_tema = st.selectbox("🎨 Tema", ["dark", "light"], key="tema_select")
    if nuevo_tema != st.session_state.tema:
        st.session_state.tema = nuevo_tema
        st.rerun()

# ── Sidebar Configuration ──────────────────────────────────────────────────────
hoy_lima = now_lima()

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    f_fecha_ini = st.date_input("Desde", hoy_lima.date(), key="f_ini")
    f_hora_ini = st.time_input("Hora inicio", datetime.min.time(), key="h_ini")
    
    f_fecha_fin = st.date_input("Hasta", hoy_lima.date(), key="f_fin")
    f_hora_fin = st.time_input("Hora fin", datetime.max.time(), key="h_fin")
    
    dt_ini = datetime.combine(f_fecha_ini, f_hora_ini)
    dt_fin = datetime.combine(f_fecha_fin, f_hora_fin)
    
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        btn_consultar = st.button("⟳ Consultar", type="primary", use_container_width=True)
    with col_sb2:
        btn_hoy = st.button("Hoy", use_container_width=True)
    
    st.markdown("---")
    
    live_mode = st.toggle("🔴 Modo en vivo", value=False)
    if live_mode:
        intervalo = st.slider("Refrescar cada (seg)", 5, 60, 15)
    
    st.markdown("---")
    st.markdown("### 📋 Gestión")
    
    if st.checkbox("Editar agentes"):
        st.markdown("#### Agentes")
        for agent_id, agent_info in st.session_state.cfg_agentes.items():
            st.session_state.cfg_agentes[agent_id]["nombre"] = st.text_input(
                f"ID {agent_id}", 
                agent_info["nombre"], 
                key=f"ag_{agent_id}"
            )
        if st.button("Guardar agentes"):
            save_config()
            st.success("✅ Agentes guardados")
    
    st.markdown("---")
    st.markdown("### ℹ️ Información")
    st.caption(f"Última actualización: {hoy_lima.strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("Versión: 2.1 (Mejorada con API)")

# ── Main Content ───────────────────────────────────────────────────────────────
if btn_hoy:
    dt_ini = datetime.combine(hoy_lima.date(), datetime.min.time())
    dt_fin = datetime.combine(hoy_lima.date(), datetime.max.time())

st.markdown("---")

# ── Cargar datos ───────────────────────────────────────────────────────────────
if btn_consultar or btn_hoy:
    with st.spinner("⏳ Cargando datos de CallMyWay..."):
        df_ent, api_ok = cargar_datos_api(dt_ini, dt_fin)
        
        if api_ok and not df_ent.empty:
            st.session_state.df_actual = df_ent
            usar_demo = False
        elif api_ok and df_ent.empty:
            usar_demo = True
            st.info("📊 Sin datos en este período. Mostrando demostración.")
        else:
            usar_demo = True
            st.warning("⚠️ Error conectando a API. Mostrando demostración.")
else:
    usar_demo = True
    df_ent = st.session_state.df_actual if not st.session_state.df_actual.empty else None

# ── Mostrar datos ──────────────────────────────────────────────────────────────
if usar_demo:
    st.info("📊 Modo demostración")
    
    # Crear datos de ejemplo
    sample_data = {
        "numero_cliente": ["51912345678", "51987654321", "51912345678", "51912345678", "51912345678"],
        "agente": ["Edwin Loyola", "Jose Luis Cahuana", "Edwin Loyola", "Deivy Chavez", "Sin atender"],
        "atendida": [True, True, True, True, False],
        "detect_time": [
            "2026-05-13 10:30:00",
            "2026-05-13 10:35:00",
            "2026-05-13 10:40:00",
            "2026-05-13 10:45:00",
            "2026-05-13 10:50:00"
        ],
        "duracion": [120, 180, 90, 150, 0]
    }
    df_ent = pd.DataFrame(sample_data)

# KPIs
if df_ent is not None and not df_ent.empty:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📞 Total llamadas", len(df_ent))
    with col2:
        atendidas = int(df_ent["atendida"].sum())
        pct = round(atendidas/len(df_ent)*100) if len(df_ent) > 0 else 0
        st.metric("✅ Atendidas", atendidas, f"{pct}%")
    with col3:
        perdidas = len(df_ent) - atendidas
        st.metric("❌ Perdidas", perdidas)
    with col4:
        duracion_prom = int(df_ent[df_ent["atendida"]]["duracion"].mean()) if len(df_ent[df_ent["atendida"]]) > 0 else 0
        st.metric("⏱️ Duración promedio", fmt_dur(duracion_prom))
    
    st.markdown("---")
    
    # Gráficos
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "👥 Agentes", "📈 Análisis"])
    
    with tab1:
        col_gr1, col_gr2 = st.columns(2)
        
        with col_gr1:
            # Gráfico de estado
            estado_data = pd.DataFrame({
                "estado": ["Atendidas", "Perdidas"],
                "cantidad": [atendidas, perdidas]
            })
            fig_estado = px.pie(
                estado_data,
                values="cantidad",
                names="estado",
                color_discrete_map={"Atendidas": colors["bar_green"], "Perdidas": colors["bar_red"]}
            )
            fig_estado.update_layout(**get_plotly_layout("Estado de llamadas", colors, 350))
            st.plotly_chart(fig_estado, use_container_width=True)
        
        with col_gr2:
            # Gráfico de agentes
            if "agente" in df_ent.columns:
                agentes_data = df_ent[df_ent["atendida"]].groupby("agente").size().reset_index(name="llamadas")
                if not agentes_data.empty:
                    fig_agentes = px.bar(
                        agentes_data,
                        x="agente",
                        y="llamadas",
                        color="llamadas",
                        color_continuous_scale=[colors["bar_blue"], colors["primary"]],
                        text_auto=True
                    )
                    fig_agentes.update_layout(**get_plotly_layout("Llamadas por agente", colors, 350))
                    fig_agentes.update_traces(marker_line_width=0)
                    st.plotly_chart(fig_agentes, use_container_width=True)
    
    with tab2:
        st.markdown("#### Desempeño por agente")
        if "agente" in df_ent.columns:
            agentes_stats = []
            for agente in df_ent["agente"].unique():
                sub = df_ent[df_ent["agente"] == agente]
                atendidas_ag = int(sub["atendida"].sum())
                total_ag = len(sub)
                agentes_stats.append({
                    "Agente": agente,
                    "Total": total_ag,
                    "Atendidas": atendidas_ag,
                    "Perdidas": total_ag - atendidas_ag,
                    "% Atención": round(atendidas_ag / total_ag * 100) if total_ag else 0
                })
            
            df_agentes_stats = pd.DataFrame(agentes_stats)
            
            fig_comp = px.bar(
                df_agentes_stats,
                x="Agente",
                y=["Atendidas", "Perdidas"],
                barmode="stack",
                color_discrete_map={"Atendidas": colors["bar_green"], "Perdidas": colors["bar_red"]}
            )
            fig_comp.update_layout(**get_plotly_layout("Comparativa de agentes", colors, 400))
            fig_comp.update_traces(marker_line_width=0)
            st.plotly_chart(fig_comp, use_container_width=True)
            
            st.dataframe(df_agentes_stats, use_container_width=True, hide_index=True)
    
    with tab3:
        st.markdown("#### Análisis adicional")
        st.info("💡 Gráficos avanzados disponibles en `graficos_avanzados.py`")

else:
    st.error("❌ No hay datos para mostrar")

st.markdown("---")
st.caption(f"🔧 Central Telefónica Dashboard v2.1 | Conectado a API CallMyWay")
