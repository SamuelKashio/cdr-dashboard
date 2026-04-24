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
    "8668109": "Alonso Loyola",
    "8668110": "Jose Luis Cahuana",
    "8668112": "Daniel Huayta",
    "8668111": "Deivy Chavez",
    "8668114": "Joe Villanueva",
    "8672537": "Victor Figueroa",
}
AGENTES_SIN_CENTRAL = {k: v for k, v in AGENTES.items() if v != "Central Virtual"}

# ─── Turnos ────────────────────────────────────────────────────────────────────
# dias: 0=Lun … 4=Vie, 5=Sáb, 6=Dom
# Los turnos que cruzan medianoche (22-6) se manejan con lógica especial
TURNOS = [
    # Lunes a viernes
    {"dias": [0,1,2,3,4], "h_ini":  6, "h_fin": 14, "agente": "Alonso Loyola"},
    {"dias": [0,1,2,3,4], "h_ini": 14, "h_fin": 22, "agente": "Jose Luis Cahuana"},
    {"dias": [0,1,2,3,4], "h_ini": 22, "h_fin": 30, "agente": "Deivy Chavez"},   # 22h→30h = hasta 6am siguiente
    # Sábados y domingos
    {"dias": [5,6],        "h_ini":  6, "h_fin": 14, "agente": "Daniel Huayta"},
    {"dias": [5,6],        "h_ini": 14, "h_fin": 22, "agente": "Luz Goicochea"},  # sin ID aún — se asigna como perdida
    {"dias": [5,6],        "h_ini": 22, "h_fin": 30, "agente": "Joe Villanueva"},
]
# Agentes sin ID en la central — sus llamadas siempre serán "perdidas" hasta tener el ID
AGENTES_SIN_ID = {"Luz Goicochea"}

def agente_de_turno(dt):
    """Devuelve el nombre del agente de turno para un datetime dado."""
    if pd.isna(dt):
        return "Sin turno"
    dow = dt.weekday()  # 0=Lun
    # Hora extendida: si es 0-5am, pertenece al turno nocturno del día anterior
    h = dt.hour
    h_ext = h if h >= 6 else h + 24   # 0am→24, 1am→25 … 5am→29
    # Primero buscar en el mismo día de semana con hora extendida
    for t in TURNOS:
        if dow in t["dias"] and t["h_ini"] <= h_ext < t["h_fin"]:
            return t["agente"]
    # Para horas 0-5am, el turno nocturno pertenece al día anterior
    dow_prev = (dow - 1) % 7
    for t in TURNOS:
        if dow_prev in t["dias"] and t["h_ini"] <= h_ext < t["h_fin"]:
            return t["agente"]
    return "Sin turno"


END_REASONS = {
    "OK": "Completada",
    "CANCELLED": "Cancelada por cliente",
    "NO_ANSWER": "Sin respuesta",
    "TEMPORARILY_UNAVAILABLE": "Agente no disponible",
    "NOT_FOUND": "No encontrado",
    "DECLINE": "Rechazada",
    "SERVICE_UNAVAILABLE": "Servicio no disponible",
}
END_COLORS = {
    "OK": "#22C55E",
    "CANCELLED": "#F59E0B",
    "NO_ANSWER": "#EF4444",
    "TEMPORARILY_UNAVAILABLE": "#8B5CF6",
    "NOT_FOUND": "#6B7280",
    "DECLINE": "#EC4899",
    "SERVICE_UNAVAILABLE": "#6B7280",
}

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Supervisor · Soporte",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; }
.stApp { background: #06080F; }
.stApp > header { background: transparent !important; }

section[data-testid="stSidebar"] {
    background: #090B14 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
section[data-testid="stSidebar"] * { color: #7A8AA0 !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] strong { color: #C8D8E8 !important; }
section[data-testid="stSidebar"] label { color: #3A5070 !important; font-size: 11px !important; letter-spacing: 0.5px; text-transform: uppercase; }
section[data-testid="stSidebar"] input {
    background: #0F1525 !important; border: 1px solid rgba(80,120,200,0.2) !important;
    color: #C8D8E8 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important;
}
section[data-testid="stSidebar"] .stButton button {
    width: 100%; background: #0F1A2E !important;
    border: 1px solid rgba(60,120,220,0.35) !important;
    color: #6A9ADA !important; font-weight: 500 !important; letter-spacing: 0.3px;
    transition: all 0.15s;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: #152240 !important; border-color: rgba(80,160,255,0.6) !important; color: #8ABCFF !important;
}

[data-testid="metric-container"] {
    background: #0C0F1C !important; border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 12px !important; padding: 16px 18px !important; position: relative; overflow: hidden;
}
[data-testid="stMetricLabel"] { color: #2A4060 !important; font-size: 10px !important; letter-spacing: 1.8px !important; text-transform: uppercase !important; font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stMetricValue"] { color: #C8D8E8 !important; font-size: 26px !important; font-weight: 300 !important; letter-spacing: -0.5px !important; }
[data-testid="stMetricDelta"] { font-size: 11px !important; }

h1, h2, h3 { color: #C8D8E8 !important; font-family: 'Outfit', sans-serif !important; letter-spacing: -0.3px; }
p, li { color: #7A8AA0 !important; }

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important; gap: 2px !important; padding: 0 !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #2A4060 !important;
    font-size: 11px !important; font-weight: 600 !important; letter-spacing: 1px !important;
    text-transform: uppercase !important; padding: 10px 18px !important;
    border-bottom: 2px solid transparent !important; border-radius: 0 !important;
}
.stTabs [aria-selected="true"] { color: #5A9AEA !important; border-bottom: 2px solid #3A7ACA !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 22px !important; }

.stDataFrame { border: 1px solid rgba(255,255,255,0.05) !important; border-radius: 10px !important; }
.stDownloadButton button {
    background: transparent !important; border: 1px solid rgba(80,120,200,0.2) !important;
    color: #3A6AAA !important; font-size: 12px !important;
}
.stMultiSelect span[data-baseweb="tag"] { background: #0F1A2E !important; color: #5A8ACA !important; }
div[data-testid="stSelectbox"] select { background: #0C0F1C !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1A2A40; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ─── API con paginación ───────────────────────────────────────────────────────
PAGE_SIZE = 1000   # registros por página

def _fetch_page(params, ini):
    """Trae una página de resultados."""
    p = {**params, "ini": ini, "cant": PAGE_SIZE}
    r = requests.get("https://callmyway.com/getCdrs.php", params=p, timeout=30)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "error" in data:
        raise ValueError(data["error"])
    cdrs = data.get("cdrs", data) if isinstance(data, dict) else data
    return cdrs if cdrs else []

def fetch_cdrs(username, password, date_start=None, date_end=None, recent=False, live=False,
               progress_cb=None):
    """
    Descarga CDRs con paginación automática para evitar timeouts en rangos grandes.
    progress_cb(pct, msg): callback opcional para mostrar progreso.
    """
    base_params = {"username": username, "password": password, "format": "json"}

    if live:
        base_params.update({"live": 1, "fullAccount": 1})
        try:
            cdrs = _fetch_page(base_params, 0)
            return pd.DataFrame(cdrs), None
        except Exception as e:
            return None, str(e)

    if recent:
        base_params["recent"] = 1
        try:
            cdrs = _fetch_page(base_params, 0)
            return pd.DataFrame(cdrs), None
        except Exception as e:
            return None, str(e)

    # Histórico con paginación
    base_params.update({"dateStart": date_start, "dateEnd": date_end})
    all_cdrs = []
    ini = 0
    try:
        while True:
            page = _fetch_page(base_params, ini)
            if not page:
                break
            all_cdrs.extend(page)
            if progress_cb:
                progress_cb(min(ini / max(len(all_cdrs), 1), 0.95),
                            f"Descargando… {len(all_cdrs):,} registros")
            if len(page) < PAGE_SIZE:
                break   # última página
            ini += PAGE_SIZE
        return (pd.DataFrame(all_cdrs) if all_cdrs else pd.DataFrame()), None
    except Exception as e:
        if all_cdrs:   # devolver lo que tenemos aunque haya fallado en alguna página
            return pd.DataFrame(all_cdrs), None
        return None, str(e)


# ─── Motor de procesamiento ───────────────────────────────────────────────────
def procesar(df_raw):
    if df_raw is None or df_raw.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df_raw.copy()

    # Normalizar
    for col in ["duration", "ring_time"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0).astype(int)
    for col in ["detect_time", "connect_time", "disconnect_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col].replace("", None), errors="coerce")

    df["ani_user"]  = df["ani_user"].astype(str).str.strip()
    df["dnis_user"] = df["dnis_user"].astype(str).str.strip()
    df["ref_callid"] = df["ref_callid"].astype(str).str.strip()

    agentes_ids = set(AGENTES.keys())

    # ── 1. LLAMADAS SALIENTES DE AGENTES A CLIENTES REALES ──────────────────
    # outgoing + ani_user es agente + dnis empieza con 51 (número peruano externo) + tiene route_name o es largo
    mask_sal = (
        (df["type"] == "outgoing") &
        (df["ani_user"].isin(agentes_ids)) &
        (df["ani_user"] != "8668106") &           # excluir Central Virtual
        (~df["dnis"].astype(str).str.startswith("833"))  # excluir extensiones internas (8330929)
    )
    df_salientes = df[mask_sal].copy()
    df_salientes["agente"]    = df_salientes["ani_user"].map(AGENTES)
    df_salientes["numero_cliente"] = df_salientes["dnis"].astype(str)
    df_salientes["atendida"]  = df_salientes["duration"] > 0
    df_salientes["tipo_call"] = "Saliente"
    df_salientes["hora"]      = df_salientes["detect_time"].dt.hour
    df_salientes["fecha"]     = df_salientes["detect_time"].dt.date
    df_salientes["end_reason_es"] = df_salientes["end_reason"].map(END_REASONS).fillna(df_salientes["end_reason"])

    # ── 2. LLAMADAS ENTRANTES — lógica correcta ─────────────────────────────
    #
    # La central genera DOS tipos de registros por llamada:
    #   A) Registro tronco: dnis_user=8668106 (Central Virtual) — la llamada llega al sistema
    #   B) Registros agente: dnis_user=8668109/8668110/etc — intentos de ring al agente
    #
    # Regla: una llamada existe SI Y SOLO SI hay al menos un registro tipo B.
    # Atendida = existe registro tipo B con duration > 0.
    # Perdida  = solo existen registros tipo B con duration == 0.
    # El registro tipo A (tronco) se ignora completamente para métricas.

    df_inc = df[df["type"] == "incoming"].copy()

    if df_inc.empty:
        df_entrantes = pd.DataFrame()
    else:
        agentes_reales = {k for k in agentes_ids if k != "8668106"}

        # Solo registros donde el destinatario es un agente real (no Central Virtual)
        df_agentes = df_inc[df_inc["dnis_user"].isin(agentes_reales)].copy()

        if df_agentes.empty:
            df_entrantes = pd.DataFrame()
        else:
            # Número de cliente viene del registro del tronco (ani cuando ani_user=8668106)
            # o del propio registro del agente
            tronco_ani = (
                df_inc[df_inc["dnis_user"] == "8668106"]
                .groupby("original_callid")["ani"]
                .first()
                .reset_index()
                .rename(columns={"ani": "ani_cliente"})
            )
            # Fallback: tomar ani del primer registro del agente
            agente_ani = (
                df_agentes.groupby("original_callid")["ani"]
                .first()
                .reset_index()
                .rename(columns={"ani": "ani_cliente_fb"})
            )

            # Agrupar por original_callid usando solo registros de agentes reales
            df_grp = df_agentes.groupby("original_callid").agg(
                ring_total=("ring_time", "sum"),
                n_intentos=("callid", "count"),
                detect_time=("detect_time", "min"),
                # Agente que contestó = dnis_user del registro con mayor duration
                agente_id=("dnis_user", lambda x: x.loc[df_agentes.loc[x.index, "duration"].idxmax()]
                           if df_agentes.loc[x.index, "duration"].max() > 0 else None),
                duracion=("duration", "max"),
                # Motivo de no atención: la razón más frecuente distinta de OK
                end_reason=("end_reason", lambda x: (
                    x[x != "OK"].value_counts().index[0]
                    if (x != "OK").any() else "OK"
                )),
            ).reset_index()

            # Unir número de cliente
            df_grp = df_grp.merge(tronco_ani, on="original_callid", how="left")
            df_grp = df_grp.merge(agente_ani,  on="original_callid", how="left")
            df_grp["ani_cliente"] = df_grp["ani_cliente"].fillna(df_grp["ani_cliente_fb"])
            df_grp.drop(columns=["ani_cliente_fb"], inplace=True, errors="ignore")

            df_grp["atendida"]        = df_grp["duracion"].notna() & (df_grp["duracion"] > 0)
            df_grp["duracion"]        = df_grp["duracion"].fillna(0).astype(int)
            df_grp["agente"]          = df_grp["agente_id"].map(AGENTES).fillna("Sin atender")
            df_grp["tipo_call"]       = "Entrante"
            df_grp["hora"]            = df_grp["detect_time"].dt.hour
            df_grp["fecha"]           = df_grp["detect_time"].dt.date
            df_grp["end_reason_es"]   = df_grp["end_reason"].map(END_REASONS).fillna(df_grp["end_reason"])
            df_grp["numero_cliente"]  = df_grp["ani_cliente"].astype(str)
            # Agente de turno según horario (para llamadas perdidas)
            df_grp["agente_turno"] = df_grp["detect_time"].apply(agente_de_turno)
            # Responsable:
            #   - Si atendida Y el agente de turno TIENE ID → quien contestó
            #   - Si perdida  → agente de turno (incluyendo Luz Goicochea sin ID)
            #   - Si turno es AGENTES_SIN_ID → siempre perdida/responsable = ese agente
            def calc_responsable(r):
                if r["agente_turno"] in AGENTES_SIN_ID:
                    return r["agente_turno"]   # sin ID = no puede contestar = perdida
                return r["agente"] if r["atendida"] else r["agente_turno"]
            df_grp["responsable"] = df_grp.apply(calc_responsable, axis=1)
            # Forzar atendida=False para turnos sin ID
            df_grp.loc[df_grp["agente_turno"].isin(AGENTES_SIN_ID), "atendida"] = False
            df_grp.loc[df_grp["agente_turno"].isin(AGENTES_SIN_ID), "agente"]   = "Sin atender"
            df_entrantes = df_grp.rename(columns={"ring_total": "espera_total"})

    return df_entrantes, df_salientes, df


def fmt_dur(s):
    s = int(s or 0)
    if s <= 0: return "—"
    if s < 60: return f"{s}s"
    m, sec = divmod(s, 60)
    return f"{m}m {sec:02d}s" if sec else f"{m}m"


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 Supervisor · Soporte")
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
    with c1: btn_ok  = st.button("⟳ Consultar", type="primary", use_container_width=True)
    with c2: btn_hoy = st.button("Hoy",          use_container_width=True)
    st.markdown("---")
    live_mode = st.toggle("🔴 Modo en vivo", value=False)
    if live_mode:
        intervalo = st.slider("Refrescar cada (seg)", 5, 60, 15)
    else:
        intervalo = 15


# ─── Sesión ───────────────────────────────────────────────────────────────────
for k in ["df_ent","df_sal","df_raw","label","error","loaded"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "loaded" else False

if not username or not password:
    st.markdown("""
    <div style='padding:100px 0;text-align:center'>
        <div style='font-size:52px;margin-bottom:16px'>🎯</div>
        <div style='color:#1A3050;font-size:22px;font-weight:300;letter-spacing:-0.5px'>Panel de Supervisor</div>
        <div style='color:#0F2030;font-size:13px;margin-top:8px;font-family:JetBrains Mono,monospace'>
            Ingresa credenciales en el panel izquierdo
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

def cargar(df_raw, label):
    df_e, df_s, df_r = procesar(df_raw)
    st.session_state.df_ent  = df_e
    st.session_state.df_sal  = df_s
    st.session_state.df_raw  = df_r
    st.session_state.label   = label
    st.session_state.error   = None
    st.session_state.loaded  = True

if live_mode:
    df_raw, err = fetch_cdrs(username, password, live=True)
    if err: st.error(f"⚠ {err}"); st.stop()
    cargar(df_raw, f"EN VIVO · {datetime.now().strftime('%H:%M:%S')}")
elif btn_ok:
    ds = datetime.combine(fi, hi).strftime("%Y-%m-%d %H:%M:%S")
    de = datetime.combine(ff, hf).strftime("%Y-%m-%d %H:%M:%S")
    prog_bar = st.progress(0, text="Iniciando consulta…")
    def on_progress(pct, msg):
        prog_bar.progress(pct, text=msg)
    df_raw, err = fetch_cdrs(username, password, date_start=ds, date_end=de,
                             progress_cb=on_progress)
    prog_bar.empty()
    if err: st.session_state.error = err
    else:   cargar(df_raw, f"{fi.strftime('%d/%m')} – {ff.strftime('%d/%m/%Y')}")
elif btn_hoy:
    with st.spinner("Consultando..."):
        df_raw, err = fetch_cdrs(username, password, recent=True)
    if err: st.session_state.error = err
    else:   cargar(df_raw, "Últimas 24 horas")

if st.session_state.error:
    st.error(f"⚠ {st.session_state.error}"); st.stop()
if not st.session_state.loaded:
    st.info("Configura el período y pulsa **Consultar**.")
    st.stop()

df_ent = st.session_state.df_ent
df_sal = st.session_state.df_sal
df_raw = st.session_state.df_raw
lbl    = st.session_state.label

if (df_ent is None or df_ent.empty) and (df_sal is None or df_sal.empty):
    st.warning("Sin registros para el período seleccionado."); st.stop()

df_ent = df_ent if df_ent is not None else pd.DataFrame()
df_sal = df_sal if df_sal is not None else pd.DataFrame()

# ─── KPIs ─────────────────────────────────────────────────────────────────────
n_ent          = len(df_ent)
n_ent_at       = int(df_ent["atendida"].sum())   if not df_ent.empty else 0
n_ent_per      = n_ent - n_ent_at
pct_at         = round(n_ent_at / n_ent * 100)   if n_ent else 0
n_sal          = len(df_sal)
n_sal_ok       = int((df_sal["atendida"] == True).sum()) if not df_sal.empty else 0

dur_ent        = df_ent[df_ent["atendida"] == True]["duracion"].dropna()  if not df_ent.empty else pd.Series([], dtype=int)
avg_dur_ent    = int(dur_ent.mean())  if len(dur_ent) else 0
total_min      = int(dur_ent.sum() / 60) if len(dur_ent) else 0

esp            = df_ent[df_ent["atendida"] == True]["espera_total"].dropna() if not df_ent.empty and "espera_total" in df_ent.columns else pd.Series([], dtype=int)
avg_esp        = int(esp.mean()) if len(esp) else 0

# ─── HEADER ───────────────────────────────────────────────────────────────────
live_dot = '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#EF4444;animation:blink 1s infinite;margin-right:5px;vertical-align:middle"></span>' if live_mode else ""
st.markdown(f"""
<style>@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.2}}}}</style>
<div style='display:flex;align-items:flex-end;justify-content:space-between;
            padding:0 0 18px;border-bottom:1px solid rgba(255,255,255,0.04);margin-bottom:22px'>
  <div>
    <div style='font-size:22px;font-weight:300;color:#C8D8E8;letter-spacing:-0.5px'>
        {live_dot}Panel de Supervisor · Soporte
    </div>
    <div style='font-size:11px;color:#1A3050;font-family:JetBrains Mono,monospace;margin-top:4px'>
        {lbl} · {n_ent} entrantes · {n_sal} salientes
    </div>
  </div>
  <div style='text-align:right;font-size:11px;color:#0F2030;font-family:JetBrains Mono,monospace'>
    {username} · CallMyWay
  </div>
</div>
""", unsafe_allow_html=True)

# ─── MÉTRICAS PRINCIPALES ─────────────────────────────────────────────────────
c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
c1.metric("Entrantes",       f"{n_ent:,}")
c2.metric("Atendidas",       f"{n_ent_at:,}",   f"{pct_at}%")
c3.metric("Perdidas",        f"{n_ent_per:,}",  f"-{100-pct_at}%")
c4.metric("% Atención",      f"{pct_at}%")
c5.metric("Salientes",       f"{n_sal:,}")
c6.metric("Sal. conectadas", f"{n_sal_ok:,}")
c7.metric("Dur. prom. ent.", fmt_dur(avg_dur_ent))
c8.metric("Espera prom.",    fmt_dur(avg_esp))

st.markdown("<br>", unsafe_allow_html=True)

# ─── PLOTLY THEME ─────────────────────────────────────────────────────────────
P = dict(paper_bgcolor="#06080F", plot_bgcolor="#06080F",
         font=dict(color="#2A4060", family="Outfit"), margin=dict(t=10,b=30,l=5,r=5))

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab_ov, tab_ent, tab_sal, tab_ag, tab_turnos, tab_cl, tab_raw = st.tabs([
    "VISIÓN GENERAL", "ENTRANTES", "SALIENTES", "AGENTES", "TURNOS", "CLIENTES", "REGISTROS"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 0 — VISIÓN GENERAL
# ════════════════════════════════════════════════════════════════════════════════
with tab_ov:
    r1c1, r1c2, r1c3 = st.columns([1.1, 1.4, 1.5])

    # Donut atención
    with r1c1:
        fig_d = go.Figure(go.Pie(
            labels=["Atendidas","Perdidas"],
            values=[n_ent_at, n_ent_per],
            hole=0.7,
            marker=dict(colors=["#166534","#7F1D1D"], line=dict(width=0)),
            textinfo="none",
        ))
        fig_d.add_annotation(text=f"<b>{pct_at}%</b>", x=0.5, y=0.56,
            font=dict(size=30,color="#C8D8E8"), showarrow=False)
        fig_d.add_annotation(text="atención", x=0.5, y=0.40,
            font=dict(size=12,color="#2A4060"), showarrow=False)
        fig_d.update_layout(height=200, showlegend=False, **P)
        st.plotly_chart(fig_d, use_container_width=True)

        # Mini stats
        st.markdown(f"""
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:-10px'>
          <div style='background:#0C0F1C;border:1px solid rgba(34,197,94,0.15);border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#166534;font-size:10px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>ATENDIDAS</div>
            <div style='color:#22C55E;font-size:22px;font-weight:300'>{n_ent_at}</div>
          </div>
          <div style='background:#0C0F1C;border:1px solid rgba(239,68,68,0.15);border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#7F1D1D;font-size:10px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>PERDIDAS</div>
            <div style='color:#EF4444;font-size:22px;font-weight:300'>{n_ent_per}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Volumen por hora
    with r1c2:
        if not df_ent.empty and "hora" in df_ent.columns:
            h_data = df_ent.groupby(["hora","atendida"]).size().reset_index(name="n")
            h_data["estado"] = h_data["atendida"].map({True:"Atendida",False:"Perdida"})
            fig_h = px.bar(h_data, x="hora", y="n", color="estado",
                color_discrete_map={"Atendida":"#166534","Perdida":"#7F1D1D"},
                barmode="stack")
            fig_h.update_layout(height=240, **P,
                xaxis=dict(title="Hora del día", dtick=1, gridcolor="rgba(255,255,255,0.03)", tickfont_size=10),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                legend=dict(font_size=11, orientation="h", y=-0.2, font_color="#2A4060"),
                bargap=0.15)
            fig_h.update_traces(marker_line_width=0)
            st.plotly_chart(fig_h, use_container_width=True)

    # Razones de pérdida
    with r1c3:
        if not df_ent.empty:
            per = df_ent[df_ent["atendida"] == False]
            if not per.empty:
                er = per["end_reason"].value_counts().reset_index()
                er.columns = ["reason","n"]
                er["label"] = er["reason"].map(END_REASONS).fillna(er["reason"])
                er["color"] = er["reason"].map(END_COLORS).fillna("#6B7280")
                er = er.sort_values("n", ascending=True)
                fig_er = go.Figure(go.Bar(
                    x=er["n"], y=er["label"], orientation="h",
                    marker_color=er["color"], marker_line_width=0,
                    text=er["n"], textposition="outside",
                    textfont=dict(size=11, color="#2A4060"),
                ))
                fig_er.update_layout(height=240, **P,
                    title=dict(text="Motivos de llamadas perdidas", font=dict(size=12,color="#2A4060"), x=0),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                )
                st.plotly_chart(fig_er, use_container_width=True)

    # Evolución diaria
    if not df_ent.empty and "fecha" in df_ent.columns:
        st.markdown("---")
        daily = df_ent.groupby(["fecha","atendida"]).size().reset_index(name="n")
        daily["estado"] = daily["atendida"].map({True:"Atendida",False:"Perdida"})
        if len(daily["fecha"].unique()) > 1:
            fig_ev = px.area(daily, x="fecha", y="n", color="estado",
                color_discrete_map={"Atendida":"#166534","Perdida":"#7F1D1D"})
            fig_ev.update_traces(opacity=0.7, line_width=1.5)
            fig_ev.update_layout(height=200, **P,
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                legend=dict(font_size=11, orientation="h", y=-0.25, font_color="#2A4060"),
                title=dict(text="Evolución diaria", font=dict(size=12,color="#2A4060"), x=0),
            )
            st.plotly_chart(fig_ev, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — ENTRANTES
# ════════════════════════════════════════════════════════════════════════════════
with tab_ent:
    if df_ent.empty:
        st.info("Sin llamadas entrantes en este período.")
    else:
        # Filtros
        fc1, fc2, fc3 = st.columns([2,1,1])
        with fc1:
            busq = st.text_input("🔍 Buscar número de cliente", placeholder="519…", key="busq_ent")
        with fc2:
            f_estado = st.selectbox("Estado", ["Todos","Atendidas","Perdidas"], key="fest_ent")
        with fc3:
            ags_disp = ["Todos"] + sorted(df_ent["agente"].dropna().unique().tolist())
            f_ag = st.selectbox("Agente", ags_disp, key="fag_ent")

        df_v = df_ent.copy()
        if busq:
            df_v = df_v[df_v["numero_cliente"].str.contains(busq, na=False)]
        if f_estado == "Atendidas":
            df_v = df_v[df_v["atendida"] == True]
        elif f_estado == "Perdidas":
            df_v = df_v[df_v["atendida"] == False]
        if f_ag != "Todos":
            df_v = df_v[df_v["agente"] == f_ag]

        # Tabla visual de llamadas
        cols_tabla = [c for c in ["detect_time","numero_cliente","atendida","agente",
                                   "responsable","agente_turno",
                                   "duracion","espera_total","n_intentos","end_reason_es"] if c in df_v.columns]
        df_show = df_v[cols_tabla].copy()
        if "duracion"      in df_show.columns: df_show["duracion"]      = df_show["duracion"].apply(fmt_dur)
        if "espera_total"  in df_show.columns: df_show["espera_total"]  = df_show["espera_total"].apply(fmt_dur)
        if "atendida"      in df_show.columns: df_show["atendida"]      = df_show["atendida"].map({True:"✅ Atendida", False:"❌ Perdida"})

        df_show = df_show.rename(columns={
            "detect_time":"Fecha/Hora","numero_cliente":"Número","atendida":"Estado",
            "agente":"Contestó","responsable":"Responsable","agente_turno":"Turno asignado",
            "duracion":"Duración","espera_total":"Espera",
            "n_intentos":"Intentos","end_reason_es":"Resultado",
        })
        st.caption(f"{len(df_v):,} llamadas · Atendidas: {int((df_v['atendida']==True).sum())} · Perdidas: {int((df_v['atendida']==False).sum())}")
        st.dataframe(df_show, use_container_width=True, height=460, hide_index=True)

        ec1, ec2 = st.columns(2)
        with ec1:
            csv_e = df_ent.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇ Exportar entrantes CSV", data=csv_e,
                file_name=f"entrantes_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        with ec2:
            # Solo perdidas
            csv_per = df_ent[df_ent["atendida"]==False].to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇ Exportar perdidas CSV", data=csv_per,
                file_name=f"perdidas_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — SALIENTES
# ════════════════════════════════════════════════════════════════════════════════
with tab_sal:
    if df_sal.empty:
        st.info("Sin llamadas salientes a clientes en este período.")
    else:
        s1,s2,s3,s4 = st.columns(4)
        dur_sal = df_sal[df_sal["atendida"]==True]["duration"].dropna()
        s1.metric("Total salientes",    f"{len(df_sal):,}")
        s2.metric("Conectadas",         f"{n_sal_ok:,}", f"{round(n_sal_ok/len(df_sal)*100) if df_sal is not None and len(df_sal) else 0}%")
        s3.metric("No conectadas",      f"{len(df_sal)-n_sal_ok:,}")
        s4.metric("Duración prom.",     fmt_dur(int(dur_sal.mean()) if len(dur_sal) else 0))

        st.markdown("<br>", unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)

        with sc1:
            ag_sal = df_sal.groupby(["agente","atendida"]).size().reset_index(name="n")
            ag_sal["estado"] = ag_sal["atendida"].map({True:"Conectada",False:"No conectada"})
            fig_sal_ag = px.bar(ag_sal, x="agente", y="n", color="estado",
                color_discrete_map={"Conectada":"#1D4ED8","No conectada":"#374151"},
                barmode="stack", title="Salientes por agente")
            fig_sal_ag.update_layout(height=260, **P,
                xaxis_title="", yaxis=dict(gridcolor="rgba(255,255,255,0.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),
                title_font=dict(size=12,color="#2A4060"),
            )
            fig_sal_ag.update_traces(marker_line_width=0)
            st.plotly_chart(fig_sal_ag, use_container_width=True)

        with sc2:
            er_sal = df_sal["end_reason"].value_counts().reset_index()
            er_sal.columns = ["reason","n"]
            er_sal["label"] = er_sal["reason"].map(END_REASONS).fillna(er_sal["reason"])
            er_sal["color"] = er_sal["reason"].map(END_COLORS).fillna("#6B7280")
            fig_er_sal = go.Figure(go.Bar(
                x=er_sal["n"], y=er_sal["label"], orientation="h",
                marker_color=er_sal["color"], marker_line_width=0,
                text=er_sal["n"], textposition="outside",
                textfont=dict(size=11,color="#2A4060"),
            ))
            fig_er_sal.update_layout(height=260, **P,
                title=dict(text="Resultado de salientes", font=dict(size=12,color="#2A4060"),x=0),
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)",title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,0.03)",title=""),
            )
            st.plotly_chart(fig_er_sal, use_container_width=True)

        # Tabla salientes
        busq_sal = st.text_input("🔍 Buscar número", key="busq_sal")
        df_vs = df_sal.copy()
        if busq_sal:
            df_vs = df_vs[df_vs["numero_cliente"].str.contains(busq_sal, na=False)]

        cols_sal = [c for c in ["detect_time","agente","numero_cliente","atendida","duration","end_reason_es","route_name"] if c in df_vs.columns]
        ds_show = df_vs[cols_sal].copy()
        if "duration"  in ds_show.columns: ds_show["duration"] = ds_show["duration"].apply(fmt_dur)
        if "atendida"  in ds_show.columns: ds_show["atendida"] = ds_show["atendida"].map({True:"✅ Conectada",False:"❌ No conectada"})
        ds_show = ds_show.rename(columns={
            "detect_time":"Fecha/Hora","agente":"Agente","numero_cliente":"Número",
            "atendida":"Estado","duration":"Duración","end_reason_es":"Resultado","route_name":"Ruta",
        })
        st.dataframe(ds_show, use_container_width=True, height=360, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — AGENTES
# ════════════════════════════════════════════════════════════════════════════════
with tab_ag:
    ag_data = []
    for aid, nombre in AGENTES_SIN_CENTRAL.items():
        # Entrantes atendidas
        ent_at = df_ent[df_ent["agente"] == nombre] if not df_ent.empty else pd.DataFrame()
        n_at   = len(ent_at)
        durs   = ent_at["duracion"].dropna().tolist()
        avg_d  = int(sum(durs)/len(durs)) if durs else 0
        total_min_ag = int(sum(durs)/60)
        esps   = ent_at["espera_total"].dropna().tolist() if "espera_total" in ent_at.columns else []
        avg_e  = int(sum(esps)/len(esps)) if esps else 0

        # Salientes
        sal_ag = df_sal[df_sal["agente"] == nombre] if not df_sal.empty else pd.DataFrame()
        n_sal_ag = len(sal_ag)
        n_sal_ok_ag = int((sal_ag["atendida"]==True).sum()) if not sal_ag.empty else 0

        # Rebotes (timbreó pero no contestó) — desde df_raw
        rebotes = 0
        if df_raw is not None and not df_raw.empty and "dnis_user" in df_raw.columns:
            rebotes = int(((df_raw["dnis_user"].astype(str) == str(aid)) &
                           (df_raw["type"] == "incoming") &
                           (df_raw["duration"] == 0)).sum())

        ag_data.append({
            "id": aid, "nombre": nombre,
            "ent_atendidas": n_at, "avg_dur": avg_d, "total_min": total_min_ag,
            "avg_espera": avg_e, "salientes": n_sal_ag,
            "sal_ok": n_sal_ok_ag, "rebotes": rebotes,
                "per_turno": len(df_ent[(df_ent.get("responsable","") == nombre) & (df_ent.get("atendida",False)==False)]) if not df_ent.empty and "responsable" in df_ent.columns else 0,
        })

    ag_data.sort(key=lambda x: x["ent_atendidas"], reverse=True)

    # Tarjetas
    cols3 = st.columns(3)
    for i, ag in enumerate(ag_data):
        with cols3[i % 3]:
            rank = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
            total_act = ag["ent_atendidas"] + ag["rebotes"]
            pct_ag = round(ag["ent_atendidas"]/total_act*100) if total_act else 0
            bar_color = "#22C55E" if pct_ag >= 70 else "#F59E0B" if pct_ag >= 40 else "#EF4444"
            st.markdown(f"""
            <div style='background:#0C0F1C;border:1px solid rgba(255,255,255,0.05);
                        border-left:3px solid {bar_color};
                        border-radius:10px;padding:16px;margin-bottom:12px'>
              <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div>
                  <div style='font-size:14px;color:#C8D8E8;font-weight:500'>{rank} {ag['nombre']}</div>
                  <div style='font-size:10px;color:#1A3050;font-family:JetBrains Mono,monospace;margin-top:2px'>ID {ag['id']}</div>
                </div>
                <div style='text-align:right'>
                  <div style='font-size:26px;font-weight:300;color:{bar_color};letter-spacing:-1px'>{ag['ent_atendidas']}</div>
                  <div style='font-size:10px;color:#1A3050'>atendidas</div>
                </div>
              </div>
              <div style='background:rgba(255,255,255,0.04);border-radius:4px;height:4px;margin-bottom:10px'>
                <div style='width:{pct_ag}%;height:100%;background:{bar_color};border-radius:4px'></div>
              </div>
              <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:11px;font-family:JetBrains Mono,monospace'>
                <div style='background:rgba(255,255,255,0.03);border-radius:6px;padding:6px;text-align:center'>
                  <div style='color:#1A3050;font-size:9px;letter-spacing:0.5px'>DUR. PROM</div>
                  <div style='color:#7A9ABA;margin-top:2px'>{fmt_dur(ag['avg_dur'])}</div>
                </div>
                <div style='background:rgba(255,255,255,0.03);border-radius:6px;padding:6px;text-align:center'>
                  <div style='color:#1A3050;font-size:9px;letter-spacing:0.5px'>SALIENTES</div>
                  <div style='color:#7A9ABA;margin-top:2px'>{ag['salientes']}</div>
                </div>
                <div style='background:rgba(255,255,255,0.03);border-radius:6px;padding:6px;text-align:center'>
                  <div style='color:#1A3050;font-size:9px;letter-spacing:0.5px'>REBOTES</div>
                  <div style='color:#7A9ABA;margin-top:2px'>{ag['rebotes']}</div>
                </div>
              </div>
              <div style='margin-top:8px;display:flex;justify-content:space-between;font-size:10px;font-family:JetBrains Mono,monospace'>
                <span style='color:#EF4444'>{ag['per_turno']} perd. en turno</span>
                <span style='color:#1A3050'>{total_min_ag} min · {pct_ag}% at.</span>
              </div>
            </div>
            """.replace("total_min_ag", str(ag["total_min"])), unsafe_allow_html=True)

    # Gráficos comparativos
    st.markdown("---")
    df_ag_plot = pd.DataFrame(ag_data)
    if not df_ag_plot.empty:
        gc1, gc2 = st.columns(2)
        with gc1:
            fig_cmp = go.Figure()
            fig_cmp.add_trace(go.Bar(name="Atendidas", x=df_ag_plot["nombre"], y=df_ag_plot["ent_atendidas"],
                marker_color="#166534", marker_line_width=0))
            fig_cmp.add_trace(go.Bar(name="Salientes", x=df_ag_plot["nombre"], y=df_ag_plot["salientes"],
                marker_color="#1D4ED8", marker_line_width=0))
            fig_cmp.add_trace(go.Bar(name="Rebotes", x=df_ag_plot["nombre"], y=df_ag_plot["rebotes"],
                marker_color="#4A0404", marker_line_width=0))
            fig_cmp.update_layout(height=280, barmode="group", **P,
                xaxis_title="", yaxis=dict(gridcolor="rgba(255,255,255,0.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),
                title=dict(text="Comparativa por agente", font=dict(size=12,color="#2A4060"),x=0),
                bargap=0.2, bargroupgap=0.05,
            )
            st.plotly_chart(fig_cmp, use_container_width=True)

        with gc2:
            fig_dur_ag = px.bar(
                df_ag_plot[df_ag_plot["avg_dur"]>0].sort_values("avg_dur"),
                x="avg_dur", y="nombre", orientation="h",
                color="avg_dur", title="Duración promedio (seg)",
                color_continuous_scale=["#0F172A","#1D4ED8","#3B82F6","#93C5FD"],
            )
            fig_dur_ag.update_layout(height=280, coloraxis_showscale=False, **P,
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)",title="segundos"),
                yaxis_title="",
                title_font=dict(size=12,color="#2A4060"),
            )
            fig_dur_ag.update_traces(marker_line_width=0)
            st.plotly_chart(fig_dur_ag, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — TURNOS
# ════════════════════════════════════════════════════════════════════════════════
with tab_turnos:
    if df_ent.empty:
        st.info("Sin datos para analizar turnos.")
    else:
        # ── Tabla de horarios ─────────────────────────────────────────────────
        st.markdown("#### 📅 Horario de turnos")
        horario_data = [
            {"Días": "Lun – Vie", "Turno": "Mañana", "Horario": "06:00 – 14:00", "Agente": "Alonso Loyola",      "ID Central": "8668109", "Estado": "✅ Activo"},
            {"Días": "Lun – Vie", "Turno": "Tarde",  "Horario": "14:00 – 22:00", "Agente": "Jose Luis Cahuana", "ID Central": "8668110", "Estado": "✅ Activo"},
            {"Días": "Lun – Vie", "Turno": "Noche",  "Horario": "22:00 – 06:00", "Agente": "Deivy Chavez",      "ID Central": "8668111", "Estado": "✅ Activo"},
            {"Días": "Sáb – Dom", "Turno": "Mañana", "Horario": "06:00 – 14:00", "Agente": "Daniel Huayta",     "ID Central": "8668112", "Estado": "✅ Activo"},
            {"Días": "Sáb – Dom", "Turno": "Tarde",  "Horario": "14:00 – 22:00", "Agente": "Luz Goicochea",     "ID Central": "pendiente","Estado": "⏳ Sin ID"},
            {"Días": "Sáb – Dom", "Turno": "Noche",  "Horario": "22:00 – 06:00", "Agente": "Joe Villanueva",    "ID Central": "8668114", "Estado": "✅ Activo"},
        ]
        st.dataframe(pd.DataFrame(horario_data), use_container_width=True, hide_index=True, height=250)

        st.markdown("---")

        # ── Métricas por responsable de turno ─────────────────────────────────
        st.markdown("#### 📊 Rendimiento por responsable de turno")

        if "responsable" in df_ent.columns:
            t_stats = []
            todos_responsables = df_ent["responsable"].dropna().unique().tolist()
            for resp in sorted(todos_responsables):
                sub = df_ent[df_ent["responsable"] == resp]
                tot = len(sub)
                at  = int((sub["atendida"] == True).sum())
                per = tot - at
                pct = round(at/tot*100) if tot else 0
                durs = sub[sub["atendida"]==True]["duracion"].dropna()
                avg_d = int(durs.mean()) if len(durs) else 0
                t_stats.append({
                    "Agente / Responsable": resp,
                    "Total": tot, "Atendidas": at, "Perdidas": per,
                    "% Atención": pct, "Dur. prom.": fmt_dur(avg_d),
                })

            df_ts = pd.DataFrame(t_stats).sort_values("% Atención", ascending=False)
            st.dataframe(df_ts, use_container_width=True, hide_index=True, height=280)

            # Gráfico: atendidas vs perdidas por responsable
            tc1, tc2 = st.columns(2)
            with tc1:
                fig_tr = go.Figure()
                fig_tr.add_trace(go.Bar(name="Atendidas",
                    x=df_ts["Agente / Responsable"], y=df_ts["Atendidas"],
                    marker_color="#166534", marker_line_width=0))
                fig_tr.add_trace(go.Bar(name="Perdidas",
                    x=df_ts["Agente / Responsable"], y=df_ts["Perdidas"],
                    marker_color="#7F1D1D", marker_line_width=0))
                fig_tr.update_layout(height=300, barmode="stack", **P,
                    xaxis_title="", yaxis=dict(gridcolor="rgba(255,255,255,0.03)", title=""),
                    legend=dict(font_size=11, orientation="h", y=-0.2, font_color="#2A4060"),
                    title=dict(text="Llamadas por responsable de turno", font=dict(size=12,color="#2A4060"),x=0),
                    xaxis=dict(tickangle=-20, tickfont_size=11),
                )
                st.plotly_chart(fig_tr, use_container_width=True)

            with tc2:
                df_ts2 = df_ts.copy()
                fig_pct = px.bar(df_ts2.sort_values("% Atención"),
                    x="% Atención", y="Agente / Responsable", orientation="h",
                    color="% Atención",
                    color_continuous_scale=["#7F1D1D","#92400E","#166534"],
                    range_color=[0, 100],
                    text="% Atención",
                )
                fig_pct.update_traces(marker_line_width=0,
                    texttemplate="%{text}%", textposition="outside",
                    textfont=dict(size=11, color="#2A4060"),
                )
                fig_pct.update_layout(height=300, coloraxis_showscale=False, **P,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.03)", title="% Atención", range=[0,115]),
                    yaxis_title="",
                    title=dict(text="% Atención por responsable", font=dict(size=12,color="#2A4060"),x=0),
                )
                st.plotly_chart(fig_pct, use_container_width=True)

            # ── Mapa de calor: hora × día coloreado por turno ─────────────────
            st.markdown("---")
            st.markdown("#### 🕐 Distribución de llamadas por hora y día")

            if "fecha" in df_ent.columns and "hora" in df_ent.columns:
                df_heat = df_ent.copy()
                df_heat["dia_semana"] = df_ent["detect_time"].dt.day_name()
                dias_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                dias_es    = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mié",
                              "Thursday":"Jue","Friday":"Vie","Saturday":"Sáb","Sunday":"Dom"}

                # Separar atendidas y perdidas
                hc1, hc2 = st.columns(2)
                for col_h, titulo_h, mask_h in [
                    (hc1, "Llamadas atendidas", df_heat["atendida"]==True),
                    (hc2, "Llamadas perdidas",  df_heat["atendida"]==False),
                ]:
                    sub_h = df_heat[mask_h]
                    heat = sub_h.groupby(["dia_semana","hora"]).size().reset_index(name="n")
                    hp = heat.pivot_table(index="dia_semana", columns="hora", values="n", fill_value=0)
                    hp = hp.reindex([d for d in dias_order if d in hp.index])
                    hp.index = [dias_es.get(d, d) for d in hp.index]
                    # Llenar horas faltantes con 0
                    for h in range(24):
                        if h not in hp.columns: hp[h] = 0
                    hp = hp[sorted(hp.columns)]
                    color_scale = ["#06080F","#166534","#22C55E"] if "atendidas" in titulo_h else ["#06080F","#7F1D1D","#EF4444"]
                    fig_hm = px.imshow(hp, color_continuous_scale=color_scale,
                        aspect="auto", labels=dict(x="Hora",y="Día",color="Llamadas"))
                    fig_hm.update_layout(height=220, **P,
                        title=dict(text=titulo_h, font=dict(size=12,color="#2A4060"),x=0),
                        coloraxis_showscale=True,
                        xaxis=dict(dtick=2, title="Hora"),
                        yaxis_title="",
                    )
                    with col_h:
                        st.plotly_chart(fig_hm, use_container_width=True)

            # ── Detalle de perdidas por turno ─────────────────────────────────
            st.markdown("---")
            st.markdown("#### ❌ Llamadas perdidas por turno")
            df_per_turno = df_ent[df_ent["atendida"]==False].copy()
            if not df_per_turno.empty and "responsable" in df_per_turno.columns:
                cols_per = [c for c in ["detect_time","numero_cliente","responsable",
                                         "agente_turno","espera_total","n_intentos","end_reason_es"] if c in df_per_turno.columns]
                dp_show = df_per_turno[cols_per].copy()
                if "espera_total" in dp_show.columns:
                    dp_show["espera_total"] = dp_show["espera_total"].apply(fmt_dur)
                dp_show = dp_show.rename(columns={
                    "detect_time":"Fecha/Hora","numero_cliente":"Número",
                    "responsable":"Responsable","agente_turno":"Turno",
                    "espera_total":"Espera","n_intentos":"Intentos","end_reason_es":"Motivo",
                })
                dp_show = dp_show.sort_values("Fecha/Hora", ascending=False)
                st.caption(f"{len(dp_show):,} llamadas perdidas")
                st.dataframe(dp_show, use_container_width=True, height=380, hide_index=True)
                csv_per_t = df_per_turno.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇ Exportar perdidas por turno",
                    data=csv_per_t, file_name=f"perdidas_turno_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — CLIENTES (números que más llaman / oportunidades de seguimiento)
# ════════════════════════════════════════════════════════════════════════════════
with tab_cl:
    if df_ent.empty:
        st.info("Sin datos de clientes.")
    else:
        # Agrupar por número de cliente
        cl = df_ent.groupby("numero_cliente").agg(
            total_llamadas=("original_callid","count") if "original_callid" in df_ent.columns else ("numero_cliente","count"),
            atendidas=("atendida","sum"),
            ultima_llamada=("detect_time","max"),
            agente_frecuente=("agente", lambda x: x[x != "Sin atender"].mode().iloc[0] if not x[x != "Sin atender"].empty else "—"),
        ).reset_index()
        cl["perdidas"]   = cl["total_llamadas"] - cl["atendidas"]
        cl["pct_at"]     = (cl["atendidas"] / cl["total_llamadas"] * 100).round(0).astype(int)
        cl = cl.sort_values("total_llamadas", ascending=False)

        st.markdown(f"**{len(cl):,} números de clientes únicos** en este período")
        st.markdown("<br>", unsafe_allow_html=True)

        # Alertas: clientes con muchas llamadas perdidas (necesitan seguimiento)
        cl_perdidas = cl[cl["perdidas"] >= 2].sort_values("perdidas", ascending=False).head(10)
        if not cl_perdidas.empty:
            st.markdown("#### ⚠️ Clientes que necesitan seguimiento (2+ llamadas perdidas)")
            for _, row in cl_perdidas.iterrows():
                urgencia = "🔴" if row["perdidas"] >= 5 else "🟡" if row["perdidas"] >= 3 else "🟠"
                st.markdown(f"""
                <div style='background:#0C0F1C;border:1px solid rgba(239,68,68,0.2);border-radius:8px;
                            padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between'>
                  <div>
                    <span style='color:#C8D8E8;font-family:JetBrains Mono,monospace;font-size:14px'>{urgencia} {row['numero_cliente']}</span>
                    <span style='color:#1A3050;font-size:11px;margin-left:12px'>Último intento: {str(row['ultima_llamada'])[:16] if pd.notna(row['ultima_llamada']) else '—'}</span>
                  </div>
                  <div style='text-align:right;font-size:12px;font-family:JetBrains Mono,monospace'>
                    <span style='color:#EF4444'>{int(row['perdidas'])} perdidas</span>
                    <span style='color:#1A3050;margin-left:10px'>de {int(row['total_llamadas'])} intentos</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>")

        # Top clientes por volumen
        st.markdown("#### 📊 Top clientes por volumen")
        fig_cl = px.bar(cl.head(15).sort_values("total_llamadas"),
            x="total_llamadas", y="numero_cliente", orientation="h",
            color="pct_at",
            color_continuous_scale=["#7F1D1D","#F59E0B","#166534"],
            range_color=[0,100],
            labels={"total_llamadas":"Llamadas","numero_cliente":"Número","pct_at":"% Atención"},
        )
        fig_cl.update_layout(height=360, **P,
            xaxis=dict(gridcolor="rgba(255,255,255,0.03)",title="Llamadas totales"),
            yaxis_title="",
            coloraxis_colorbar=dict(title="% At.",tickfont_size=10,len=0.7),
        )
        fig_cl.update_traces(marker_line_width=0)
        st.plotly_chart(fig_cl, use_container_width=True)

        # Tabla completa
        cl_show = cl[["numero_cliente","total_llamadas","atendidas","perdidas","pct_at","agente_frecuente","ultima_llamada"]].copy()
        cl_show["ultima_llamada"] = cl_show["ultima_llamada"].astype(str).str[:16]
        cl_show = cl_show.rename(columns={
            "numero_cliente":"Número","total_llamadas":"Total","atendidas":"Atendidas",
            "perdidas":"Perdidas","pct_at":"% At.","agente_frecuente":"Agente frecuente","ultima_llamada":"Última llamada",
        })
        st.dataframe(cl_show, use_container_width=True, height=320, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — REGISTROS RAW
# ════════════════════════════════════════════════════════════════════════════════
with tab_raw:
    st.markdown("#### Registros completos sin procesar")
    st.caption("Todos los registros CDR incluyendo intentos de ring individuales")

    if df_raw is not None and not df_raw.empty:
        busq_r = st.text_input("Buscar en todos los campos", key="busq_raw")
        df_rshow = df_raw.copy()
        if busq_r:
            mask = pd.Series([False]*len(df_rshow))
            for c in ["ani","dnis","callid","original_callid","ani_user","dnis_user"]:
                if c in df_rshow.columns:
                    mask |= df_rshow[c].astype(str).str.contains(busq_r, case=False, na=False)
            df_rshow = df_rshow[mask]

        cols_r = [c for c in ["detect_time","type","ani","dnis","ani_user","dnis_user",
                               "duration","ring_time","end_reason","connect_time",
                               "route_name","original_callid","ref_callid"] if c in df_rshow.columns]

        r_show = df_rshow[cols_r].copy()
        r_show = r_show.rename(columns={
            "detect_time":"Fecha","type":"Tipo","ani":"ANI","dnis":"DNIS",
            "ani_user":"ANI User","dnis_user":"DNIS User","duration":"Dur(s)",
            "ring_time":"Ring(s)","end_reason":"Motivo","connect_time":"Conectó",
            "route_name":"Ruta","original_callid":"Original CID","ref_callid":"Ref CID",
        })

        rs1,rs2,rs3,rs4 = st.columns(4)
        rs1.metric("Registros totales", f"{len(df_raw):,}")
        rs2.metric("Con duration > 0",  f"{int((df_raw['duration']>0).sum()):,}" if "duration" in df_raw.columns else "—")
        rs3.metric("Entrantes",         f"{int((df_raw['type']=='incoming').sum()):,}" if "type" in df_raw.columns else "—")
        rs4.metric("Salientes",         f"{int((df_raw['type']=='outgoing').sum()):,}" if "type" in df_raw.columns else "—")

        st.dataframe(r_show, use_container_width=True, height=460, hide_index=True)
        csv_r = df_rshow[cols_r].to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ Exportar raw CSV", data=csv_r,
            file_name=f"raw_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

# ─── Live refresh ─────────────────────────────────────────────────────────────
if live_mode:
    time.sleep(intervalo)
    st.rerun()
