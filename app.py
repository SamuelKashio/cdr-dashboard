import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ─── Configuración ────────────────────────────────────────────────────────────
AGENTES = {
    "8668106": "Central Virtual",
    "8668109": "Edwin Loyola",
    "8668110": "Jose Luis Cahuana",
    "8668112": "Daniel Huayta",
    "8668111": "Deivy Chavez",
    "8668114": "Joe Villanueva",
    "8672537": "Victor Figueroa",
}

END_REASONS = {
    "OK": "Completada",
    "CANCELLED": "Cancelada",
    "NO_ANSWER": "Sin respuesta",
    "TEMPORARILY_UNAVAILABLE": "No disponible",
    "NOT_FOUND": "No encontrado",
    "DECLINE": "Rechazada",
    "SERVICE_UNAVAILABLE": "Servicio no disponible",
}

st.set_page_config(
    page_title="CallCenter · Panel de Control",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #07090F; }
.stApp > header { background: transparent !important; }

section[data-testid="stSidebar"] {
    background: #0C0F1A !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] * { color: #8899AA !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] strong { color: #CCD8E8 !important; }
section[data-testid="stSidebar"] label { color: #6677AA !important; font-size: 11px !important; letter-spacing: 0.5px; }
section[data-testid="stSidebar"] input {
    background: #12182A !important;
    border: 1px solid rgba(100,130,200,0.2) !important;
    color: #CCD8E8 !important;
    font-family: 'DM Mono', monospace !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #1A3A6A, #0A2A5A) !important;
    border: 1px solid rgba(80,140,220,0.4) !important;
    color: #7AB8FF !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: linear-gradient(135deg, #204080, #102060) !important;
    border-color: rgba(100,180,255,0.6) !important;
    color: #AAD4FF !important;
}

[data-testid="metric-container"] {
    background: #0C0F1A !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    padding: 16px 18px !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: #445566 !important;
    font-size: 10px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    font-family: 'DM Mono', monospace !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #CCD8E8 !important;
    font-size: 24px !important;
    font-weight: 300 !important;
    letter-spacing: -0.5px !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 11px !important; }

h1, h2, h3 { color: #CCD8E8 !important; font-family: 'DM Sans', sans-serif !important; }
p, li, span { color: #8899AA !important; }

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    padding: 0 !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #445566 !important;
    border-radius: 0 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #7AB8FF !important;
    border-bottom: 2px solid #3A80D0 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px !important; }

.stDownloadButton button {
    background: transparent !important;
    border: 1px solid rgba(100,130,200,0.25) !important;
    color: #6688BB !important;
    font-size: 12px !important;
}
.stDownloadButton button:hover {
    border-color: rgba(100,160,255,0.5) !important;
    color: #88AADD !important;
}

.stDataFrame { border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 10px !important; }

.stMultiSelect span[data-baseweb="tag"] {
    background: #12182A !important;
    color: #6688BB !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers de API ────────────────────────────────────────────────────────────
def fetch_cdrs(username, password, date_start=None, date_end=None, recent=False, live=False):
    base   = "https://callmyway.com/getCdrs.php"
    params = {"username": username, "password": password, "format": "json"}
    if live:
        params.update({"live": 1, "fullAccount": 1})
    elif recent:
        params["recent"] = 1
    else:
        params.update({"dateStart": date_start, "dateEnd": date_end, "ini": 0, "cant": 5000})
    try:
        r = requests.get(base, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "error" in data:
            return None, data["error"]
        cdrs = data.get("cdrs", data) if isinstance(data, dict) else data
        return pd.DataFrame(cdrs) if cdrs else pd.DataFrame(), None
    except requests.exceptions.Timeout:
        return None, "Timeout. Intenta con un rango de fechas menor."
    except Exception as e:
        return None, str(e)


# ─── Lógica de deduplicación y análisis ───────────────────────────────────────
def procesar_cdrs(df_raw):
    """
    La API devuelve múltiples registros por llamada (intentos de ring al agente).
    Necesitamos:
      1. Llamadas únicas (por original_callid)
      2. Determinar si fue atendida
      3. Identificar qué agente atendió
      4. Calcular tiempo de espera real
    """
    if df_raw is None or df_raw.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = df_raw.copy()

    # Normalizar campos numéricos
    for col in ["duration", "ring_time"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Timestamps
    for col in ["detect_time", "connect_time", "disconnect_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col].replace("", None), errors="coerce")

    # ── Identificar agente por dnis_user (campo confiable) ─────────────────────
    # name_endpoint_dnis puede decir "Central_Virtual" incluso cuando el agente que
    # contestó es otro. dnis_user contiene el ID real del endpoint (8668109, 8668110, etc.)
    df["agente_dnis"] = df["dnis_user"].astype(str).map(AGENTES)       # quién recibe
    df["agente_ani"]  = df["ani_user"].astype(str).map(AGENTES)        # quién llama
    # Para salientes: el agente es el que origina (ani_user)
    df["agente_nombre"] = df["agente_dnis"].fillna(df["agente_ani"]).fillna("Externo")

    # ── VISTA DETALLE: todos los registros (para tabla de intentos)
    df_all = df.copy()

    # ── VISTA LLAMADAS ÚNICAS: agrupar por original_callid ─────────────────────
    if "original_callid" not in df.columns:
        return df_all, df_all

    df["ref_callid"] = df["ref_callid"].astype(str).str.strip()
    df_padres = df[df["ref_callid"] == "0"].copy()

    # Registros con duration > 0 Y dnis_user es un agente conocido = llamada atendida por ese agente
    agentes_ids = set(AGENTES.keys())
    df["es_agente_dnis"] = df["dnis_user"].astype(str).isin(agentes_ids)

    atendidas_mask = (df["duration"] > 0) & df["es_agente_dnis"]
    df_atendidas = df[atendidas_mask].copy()
    df_atendidas["agente_real"] = df_atendidas["dnis_user"].astype(str).map(AGENTES)

    atendidas = df_atendidas.groupby("original_callid").agg(
        agente_atendio=("agente_real", "first"),
        duracion_real=("duration", "max"),
        connect_time_real=("connect_time", "first"),
    ).reset_index()

    # Tiempo de espera = suma de ring_time de intentos fallidos antes de que conteste
    espera = df.groupby("original_callid").agg(
        total_ring=("ring_time", "sum"),
        n_intentos=("callid", "count"),
    ).reset_index()

    # Join
    llamadas = df_padres.merge(atendidas, on="original_callid", how="left")
    llamadas = llamadas.merge(espera, on="original_callid", how="left")

    llamadas["atendida"] = llamadas["duracion_real"].notna() & (llamadas["duracion_real"] > 0)
    llamadas["duracion_real"] = llamadas["duracion_real"].fillna(0).astype(int)
    llamadas["agente_atendio"] = llamadas["agente_atendio"].fillna("No atendida")
    llamadas["end_reason_es"] = llamadas["end_reason"].map(END_REASONS).fillna(llamadas["end_reason"])
    llamadas["hora"] = llamadas["detect_time"].dt.hour
    llamadas["fecha"] = llamadas["detect_time"].dt.date
    llamadas["dia_semana"] = llamadas["detect_time"].dt.day_name()

    return llamadas, df_all


def fmt_dur(s):
    s = int(s) if s else 0
    if s <= 0: return "—"
    if s < 60: return f"{s}s"
    return f"{s//60}m {s%60}s"


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 CallCenter")
    st.markdown("---")

    username = st.text_input("Usuario", placeholder="8668334")
    password = st.text_input("Contraseña", type="password")

    st.markdown("---")
    hoy  = datetime.now()
    ayer = hoy - timedelta(days=1)
    fi = st.date_input("Desde", value=ayer.date())
    hi = st.time_input("Hora inicio", value=datetime.strptime("00:00", "%H:%M").time())
    ff = st.date_input("Hasta",  value=hoy.date())
    hf = st.time_input("Hora fin", value=datetime.strptime("23:59", "%H:%M").time())

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1: btn_ok  = st.button("Consultar", type="primary", use_container_width=True)
    with c2: btn_hoy = st.button("Hoy",       use_container_width=True)

    st.markdown("---")
    live_mode = st.toggle("🔴 En vivo", value=False)
    if live_mode:
        intervalo = st.slider("Refrescar (seg)", 5, 60, 15)
    else:
        intervalo = 15

    st.markdown("---")
    st.markdown("**Agentes**")
    for aid, nombre in AGENTES.items():
        st.markdown(
            f"<div style='font-size:11px;padding:2px 0;font-family:DM Mono,monospace'>"
            f"<span style='color:#334466'>{aid}</span> "
            f"<span style='color:#8899AA'>{nombre}</span></div>",
            unsafe_allow_html=True
        )


# ─── Estado de sesión ─────────────────────────────────────────────────────────
if "llamadas" not in st.session_state:
    st.session_state.llamadas  = None
    st.session_state.df_all    = None
    st.session_state.label     = ""
    st.session_state.error     = None
    st.session_state.loaded    = False

if not username or not password:
    st.markdown("""
    <div style='padding:80px 0;text-align:center'>
        <div style='font-size:48px;margin-bottom:16px'>📡</div>
        <div style='color:#334466;font-size:18px;font-weight:300'>Panel de Control de Llamadas</div>
        <div style='color:#223344;font-size:13px;margin-top:8px;font-family:DM Mono,monospace'>
            Ingresa tus credenciales para comenzar
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── Cargar datos ─────────────────────────────────────────────────────────────
def cargar(df_raw, label):
    if df_raw is None: return
    llamadas, df_all = procesar_cdrs(df_raw)
    st.session_state.llamadas = llamadas
    st.session_state.df_all   = df_all
    st.session_state.label    = label
    st.session_state.error    = None
    st.session_state.loaded   = True

if live_mode:
    with st.spinner(""):
        df_raw, err = fetch_cdrs(username, password, live=True)
    if err: st.error(f"⚠ {err}"); st.stop()
    cargar(df_raw, f"EN VIVO · {datetime.now().strftime('%H:%M:%S')}")

elif btn_ok:
    ds = datetime.combine(fi, hi).strftime("%Y-%m-%d %H:%M:%S")
    de = datetime.combine(ff, hf).strftime("%Y-%m-%d %H:%M:%S")
    with st.spinner("Consultando API..."):
        df_raw, err = fetch_cdrs(username, password, date_start=ds, date_end=de)
    if err: st.session_state.error = err
    else: cargar(df_raw, f"{fi.strftime('%d/%m')} – {ff.strftime('%d/%m/%Y')}")

elif btn_hoy:
    with st.spinner("Consultando..."):
        df_raw, err = fetch_cdrs(username, password, recent=True)
    if err: st.session_state.error = err
    else: cargar(df_raw, "Últimas 24 horas")

if st.session_state.error:
    st.error(f"⚠ {st.session_state.error}")
    st.stop()

if not st.session_state.loaded:
    st.info("Configura el período y pulsa **Consultar** para cargar los CDRs.")
    st.stop()

# ─── Datos ────────────────────────────────────────────────────────────────────
llamadas = st.session_state.llamadas
df_all   = st.session_state.df_all
lbl      = st.session_state.label

if llamadas is None or llamadas.empty:
    st.warning("No se encontraron registros para el período seleccionado.")
    st.stop()

# ─── KPIs globales ────────────────────────────────────────────────────────────
total         = len(llamadas)
atendidas     = int(llamadas["atendida"].sum()) if "atendida" in llamadas.columns else 0
no_atendidas  = total - atendidas
pct_atencion  = round(atendidas / total * 100) if total else 0

dur_ok        = llamadas[llamadas["atendida"] == True]["duracion_real"] if "duracion_real" in llamadas.columns else pd.Series([], dtype=int)
avg_dur       = int(dur_ok.mean()) if len(dur_ok) else 0
total_min     = int(dur_ok.sum() / 60) if len(dur_ok) else 0

espera_ok     = llamadas[llamadas["atendida"] == True]["total_ring"] if "total_ring" in llamadas.columns else pd.Series([], dtype=int)
avg_espera    = int(espera_ok.mean()) if len(espera_ok) else 0

incoming_u    = len(llamadas[llamadas["type"] == "incoming"])  if "type" in llamadas.columns else 0
outgoing_u    = len(llamadas[llamadas["type"] == "outgoing"])  if "type" in llamadas.columns else 0

# ─── HEADER ───────────────────────────────────────────────────────────────────
live_badge = "🔴 EN VIVO" if live_mode else lbl
st.markdown(f"""
<div style='display:flex;align-items:center;justify-content:space-between;
            padding:14px 0 20px;border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:20px'>
    <div>
        <div style='font-size:20px;font-weight:300;color:#CCD8E8;letter-spacing:-0.3px'>
            Panel de Control · Llamadas
        </div>
        <div style='font-size:11px;color:#334466;font-family:DM Mono,monospace;margin-top:3px'>
            {total:,} registros únicos · {live_badge}
        </div>
    </div>
    <div style='font-size:11px;color:#223344;font-family:DM Mono,monospace'>
        CallMyWay API · {username}
    </div>
</div>
""", unsafe_allow_html=True)

# ─── MÉTRICAS ─────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
c1.metric("Total llamadas",    f"{total:,}")
c2.metric("Atendidas",         f"{atendidas:,}",  f"{pct_atencion}%")
c3.metric("No atendidas",      f"{no_atendidas:,}")
c4.metric("% Atención",        f"{pct_atencion}%")
c5.metric("Duración prom.",    fmt_dur(avg_dur))
c6.metric("Espera prom.",      fmt_dur(avg_espera))
c7.metric("Minutos totales",   f"{total_min:,}")

st.markdown("<br>", unsafe_allow_html=True)

# ─── ESTILO PLOTLY ────────────────────────────────────────────────────────────
PLOT = dict(
    paper_bgcolor="#07090F", plot_bgcolor="#07090F",
    font=dict(color="#445566", family="DM Sans"),
    margin=dict(t=10, b=30, l=10, r=10),
)
COLORS = {
    "atendida_si": "#3A7A5A",
    "atendida_no": "#7A3A3A",
    "OK": "#3A7A5A", "CANCELLED": "#4A5A7A",
    "NO_ANSWER": "#7A6A3A", "TEMPORARILY_UNAVAILABLE": "#5A3A7A",
    "NOT_FOUND": "#7A4A3A", "DECLINE": "#7A3A5A",
}

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "RESUMEN", "AGENTES", "ANÁLISIS", "REGISTROS", "DIAGNÓSTICO"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1: RESUMEN
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns([1.2, 2])

    with col_l:
        # Donut atendidas vs no atendidas
        fig_donut = go.Figure(data=[go.Pie(
            labels=["Atendidas", "No atendidas"],
            values=[atendidas, no_atendidas],
            hole=0.68,
            marker=dict(colors=["#2A6A4A", "#6A2A2A"], line=dict(width=0)),
            textfont=dict(color="#CCD8E8", size=11),
        )])
        fig_donut.add_annotation(
            text=f"<b>{pct_atencion}%</b>", x=0.5, y=0.52,
            font=dict(size=28, color="#CCD8E8"), showarrow=False
        )
        fig_donut.add_annotation(
            text="atención", x=0.5, y=0.38,
            font=dict(size=11, color="#445566"), showarrow=False
        )
        fig_donut.update_layout(
            height=220, showlegend=True,
            legend=dict(font=dict(size=11, color="#445566"), orientation="h", y=-0.05),
            **PLOT
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # Entrantes vs salientes
        if "type" in llamadas.columns:
            tc = llamadas["type"].value_counts()
            fig_tipo = go.Figure(data=[go.Bar(
                x=tc.index.map({"incoming": "Entrantes", "outgoing": "Salientes"}),
                y=tc.values,
                marker_color=["#2A4A6A", "#2A6A4A"],
                marker_line_width=0,
            )])
            fig_tipo.update_layout(height=160, **PLOT,
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)"),
            )
            st.plotly_chart(fig_tipo, use_container_width=True)

    with col_r:
        # Llamadas por hora
        if "hora" in llamadas.columns:
            horas = llamadas.groupby(["hora", "atendida"]).size().reset_index(name="n")
            horas["estado"] = horas["atendida"].map({True: "Atendida", False: "No atendida"})
            fig_h = px.bar(horas, x="hora", y="n", color="estado",
                color_discrete_map={"Atendida": "#2A5A3A", "No atendida": "#5A2A2A"},
                barmode="stack",
            )
            fig_h.update_layout(height=200, **PLOT,
                xaxis=dict(title="Hora", dtick=1, gridcolor="rgba(255,255,255,0.03)", tickfont_size=10),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                legend=dict(font_size=11, orientation="h", y=-0.2),
            )
            fig_h.update_traces(marker_line_width=0)
            st.plotly_chart(fig_h, use_container_width=True)

        # Razones de fin
        if "end_reason" in llamadas.columns:
            er = llamadas["end_reason"].value_counts().reset_index()
            er.columns = ["reason", "n"]
            er["label"] = er["reason"].map(END_REASONS).fillna(er["reason"])
            er = er.sort_values("n")
            fig_er = px.bar(er, x="n", y="label", orientation="h",
                color="reason",
                color_discrete_map=COLORS,
            )
            fig_er.update_layout(height=200, **PLOT,
                showlegend=False,
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
            )
            fig_er.update_traces(marker_line_width=0)
            st.plotly_chart(fig_er, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2: AGENTES
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    if "agente_atendio" not in llamadas.columns:
        st.info("No hay datos de agentes en este período.")
    else:
        # Stats por agente — usa df_all (registros raw) para cruzar por dnis_user (ID real)
        ag_stats = []
        for aid, nombre in AGENTES.items():
            if nombre == "Central Virtual":
                continue

            # Llamadas atendidas: agente_atendio viene de dnis_user mapeado
            atendidas_ag = llamadas[
                (llamadas["agente_atendio"] == nombre) & (llamadas["atendida"] == True)
            ]
            n_atendidas = len(atendidas_ag)
            dur_ag  = atendidas_ag["duracion_real"].dropna().tolist()
            avg_d   = int(sum(dur_ag) / len(dur_ag)) if dur_ag else 0
            total_d = int(sum(dur_ag) / 60)
            espera_ag = atendidas_ag["total_ring"].dropna().tolist() if "total_ring" in atendidas_ag.columns else []
            avg_esp = int(sum(espera_ag) / len(espera_ag)) if espera_ag else 0

            # Salientes y rebotes usando df_all (todos los registros, no deduplicados)
            sal, no_at = 0, 0
            if df_all is not None and not df_all.empty:
                if "type" in df_all.columns and "ani_user" in df_all.columns:
                    sal = int(((df_all["type"] == "outgoing") &
                               (df_all["ani_user"].astype(str) == str(aid)) &
                               (df_all["duration"] > 0)).sum())
                if "dnis_user" in df_all.columns:
                    routed = df_all[df_all["dnis_user"].astype(str) == str(aid)]
                    no_at  = int((routed["duration"] == 0).sum())

            ag_stats.append({
                "id": aid, "nombre": nombre,
                "atendidas": n_atendidas,
                "no_at_ring": no_at,
                "avg_dur": avg_d,
                "total_min": total_d,
                "salientes": sal,
                "avg_espera": avg_esp,
            })

        ag_stats.sort(key=lambda x: x["atendidas"], reverse=True)
        df_ag = pd.DataFrame(ag_stats)

        # Tarjetas
        cols = st.columns(3)
        for i, ag in enumerate(ag_stats):
            with cols[i % 3]:
                rank = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
                st.markdown(f"""
                <div style='background:#0C0F1A;border:1px solid rgba(255,255,255,0.06);
                            border-radius:10px;padding:16px;margin-bottom:12px'>
                    <div style='font-size:13px;color:#8899AA;margin-bottom:8px'>
                        {rank} <span style='color:#CCD8E8;font-weight:500'>{ag['nombre']}</span>
                    </div>
                    <div style='font-size:24px;font-weight:300;color:#CCD8E8;letter-spacing:-1px;margin-bottom:10px'>
                        {ag['atendidas']}
                        <span style='font-size:12px;color:#445566;font-weight:400'> llamadas</span>
                    </div>
                    <div style='display:flex;gap:16px;font-size:11px;font-family:DM Mono,monospace;color:#334466'>
                        <span>⏱ {fmt_dur(ag['avg_dur'])}</span>
                        <span>⏳ {fmt_dur(ag['avg_espera'])} espera</span>
                        <span>📞 {ag['salientes']} sal.</span>
                        <span>🔁 {ag['no_at_ring']} rebotes</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Gráfico comparativo
        if not df_ag.empty and df_ag["atendidas"].sum() > 0:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_ag = px.bar(
                    df_ag.sort_values("atendidas"), x="atendidas", y="nombre",
                    orientation="h", title="Llamadas atendidas",
                    color="atendidas",
                    color_continuous_scale=["#1A3A2A", "#2A6A4A", "#3AAA6A"],
                )
                fig_ag.update_layout(height=260, coloraxis_showscale=False, **PLOT,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title=""),
                    yaxis=dict(title=""),
                    title_font=dict(color="#445566", size=12),
                )
                fig_ag.update_traces(marker_line_width=0)
                st.plotly_chart(fig_ag, use_container_width=True)

            with col_g2:
                fig_dur = px.bar(
                    df_ag[df_ag["avg_dur"] > 0].sort_values("avg_dur"),
                    x="avg_dur", y="nombre", orientation="h",
                    title="Duración promedio (segundos)",
                    color="avg_dur",
                    color_continuous_scale=["#1A2A4A", "#2A4A7A", "#3A7AAA"],
                )
                fig_dur.update_layout(height=260, coloraxis_showscale=False, **PLOT,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", title=""),
                    yaxis=dict(title=""),
                    title_font=dict(color="#445566", size=12),
                )
                fig_dur.update_traces(marker_line_width=0)
                st.plotly_chart(fig_dur, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3: ANÁLISIS
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    col_a, col_b = st.columns(2)

    with col_a:
        # Mapa de calor hora × día
        if "hora" in llamadas.columns and "dia_semana" in llamadas.columns:
            dias_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            heat = llamadas.groupby(["dia_semana","hora"]).size().reset_index(name="n")
            hp = heat.pivot_table(index="dia_semana", columns="hora", values="n", fill_value=0)
            hp = hp.reindex([d for d in dias_order if d in hp.index])
            dias_es = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mié",
                       "Thursday":"Jue","Friday":"Vie","Saturday":"Sáb","Sunday":"Dom"}
            hp.index = [dias_es.get(d, d) for d in hp.index]
            fig_heat = px.imshow(hp,
                color_continuous_scale=["#07090F","#0A1A2A","#1A3A5A","#2A6A8A","#3AAAAA"],
                aspect="auto", title="Mapa de calor — Hora × Día",
                labels=dict(x="Hora", y="Día"),
            )
            fig_heat.update_layout(height=240, **PLOT,
                title_font=dict(color="#445566", size=12),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    with col_b:
        # Evolución diaria
        if "fecha" in llamadas.columns:
            daily = llamadas.groupby(["fecha","atendida"]).size().reset_index(name="n")
            daily["estado"] = daily["atendida"].map({True:"Atendida",False:"No atendida"})
            fig_line = px.line(daily, x="fecha", y="n", color="estado",
                title="Evolución diaria",
                color_discrete_map={"Atendida":"#2A6A4A","No atendida":"#6A2A2A"},
                markers=True,
            )
            fig_line.update_layout(height=240, **PLOT,
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                legend=dict(font_size=11, orientation="h", y=-0.2),
                title_font=dict(color="#445566", size=12),
            )
            fig_line.update_traces(line_width=1.5, marker_size=4)
            st.plotly_chart(fig_line, use_container_width=True)

    # Distribución de duraciones
    if "duracion_real" in llamadas.columns:
        dur_data = llamadas[llamadas["duracion_real"] > 0]["duracion_real"]
        if not dur_data.empty:
            fig_hist = px.histogram(dur_data, nbins=30,
                title="Distribución de duración de llamadas (segundos)",
                color_discrete_sequence=["#2A5A7A"],
            )
            fig_hist.update_layout(height=200, **PLOT,
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)", title="Segundos"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title="Frecuencia"),
                showlegend=False,
                title_font=dict(color="#445566", size=12),
            )
            fig_hist.update_traces(marker_line_width=0)
            st.plotly_chart(fig_hist, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4: REGISTROS
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    r1, r2, r3, r4 = st.columns([2, 1, 1, 1])
    with r1:
        busqueda = st.text_input("Buscar número ANI/DNIS", placeholder="51900807026…")
    with r2:
        tipos_disp = sorted(llamadas["type"].dropna().unique().tolist()) if "type" in llamadas.columns else []
        filtro_tipo = st.multiselect("Tipo", tipos_disp, default=tipos_disp)
    with r3:
        agentes_disp = ["Todos"] + [n for n in AGENTES.values() if n != "Central Virtual"]
        filtro_ag = st.selectbox("Agente", agentes_disp)
    with r4:
        st.markdown("<br>", unsafe_allow_html=True)
        csv = llamadas.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ CSV", data=csv,
            file_name=f"cdrs_unicos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)

    # Filtros
    df_v = llamadas.copy()
    if busqueda:
        mask = pd.Series([False]*len(df_v))
        for c in ["ani","dnis"]:
            if c in df_v.columns:
                mask |= df_v[c].astype(str).str.contains(busqueda, case=False, na=False)
        df_v = df_v[mask]
    if filtro_tipo and "type" in df_v.columns:
        df_v = df_v[df_v["type"].isin(filtro_tipo)]
    if filtro_ag != "Todos" and "agente_atendio" in df_v.columns:
        df_v = df_v[df_v["agente_atendio"] == filtro_ag]

    st.caption(f"Mostrando {len(df_v):,} de {total:,} llamadas únicas")

    # Columnas a mostrar
    cols_show = [c for c in ["detect_time","ani","dnis","type","agente_atendio",
                               "duracion_real","total_ring","n_intentos","end_reason_es",
                               "route_name"] if c in df_v.columns]
    df_show = df_v[cols_show].copy()
    if "duracion_real" in df_show.columns:
        df_show["duracion_real"] = df_show["duracion_real"].apply(fmt_dur)
    if "total_ring" in df_show.columns:
        df_show["total_ring"] = df_show["total_ring"].apply(fmt_dur)

    rename = {
        "detect_time":"Fecha/Hora", "ani":"Origen", "dnis":"Destino",
        "type":"Tipo", "agente_atendio":"Agente", "duracion_real":"Duración",
        "total_ring":"Espera", "n_intentos":"Intentos",
        "end_reason_es":"Resultado", "route_name":"Ruta",
    }
    df_show = df_show.rename(columns={k:v for k,v in rename.items() if k in df_show.columns})
    st.dataframe(df_show, use_container_width=True, height=460, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5: DIAGNÓSTICO (raw data para debugging)
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("#### Todos los registros CDR (incluyendo intentos de ring)")
    st.caption("Útil para ver el detalle de cada intento de enrutamiento")

    if df_all is not None and not df_all.empty:
        cols_raw = [c for c in ["detect_time","callid","original_callid","ref_callid",
                                  "ani","dnis","ani_user","dnis_user",
                                  "name_endpoint_ani","name_endpoint_dnis",
                                  "type","duration","ring_time","end_reason",
                                  "route_name","connect_time"] if c in df_all.columns]
        df_raw_show = df_all[cols_raw].copy()

        busq2 = st.text_input("Buscar en registros raw")
        if busq2:
            mask2 = pd.Series([False]*len(df_raw_show))
            for c in ["ani","dnis","callid","original_callid"]:
                if c in df_raw_show.columns:
                    mask2 |= df_raw_show[c].astype(str).str.contains(busq2, case=False, na=False)
            df_raw_show = df_raw_show[mask2]

        st.caption(f"{len(df_raw_show):,} registros (total sin deduplicar)")
        csv_raw = df_raw_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ CSV raw completo", data=csv_raw,
            file_name=f"cdrs_raw_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv")
        st.dataframe(df_raw_show, use_container_width=True, height=420, hide_index=True)

        st.markdown("---")
        st.markdown("**Estadísticas del raw**")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Registros totales", f"{len(df_all):,}")
        s2.metric("Con duration > 0", f"{int((df_all['duration'] > 0).sum()):,}" if "duration" in df_all.columns else "—")
        s3.metric("end_reason OK", f"{int((df_all['end_reason'] == 'OK').sum()):,}" if "end_reason" in df_all.columns else "—")
        unique_orig = df_all["original_callid"].nunique() if "original_callid" in df_all.columns else 0
        s4.metric("original_callid únicos", f"{unique_orig:,}")

# ─── Auto-refresh live ────────────────────────────────────────────────────────
if live_mode:
    time.sleep(intervalo)
    st.rerun()
