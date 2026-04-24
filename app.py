import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ─── Agentes ──────────────────────────────────────────────────────────────────
AGENTES = {
    "8668106": "Central Virtual",
    "8668109": "Edwin Loyola",
    "8668110": "Jose Luis Cahuana",
    "8668112": "Daniel Huayta",
    "8668111": "Deivy Chavez",
    "8668114": "Joe Villanueva",
    "8672537": "Victor Figueroa",
}

st.set_page_config(
    page_title="CallCenter — Panel de Control",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
.stApp { background: #080C14; }
.stApp > header { background: transparent !important; }
[data-testid="stSidebar"] { background: #0D1220 !important; border-right: 1px solid rgba(0,200,255,0.1); }
[data-testid="stSidebar"] * { color: #A0B4C8 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #E0EEF8 !important; }
[data-testid="stSidebar"] .stButton button { background: linear-gradient(135deg,#0077FF,#00C8FF) !important; border: none !important; color: white !important; font-weight: 600 !important; border-radius: 8px !important; }
[data-testid="metric-container"] { background: linear-gradient(135deg,#0D1A2D,#101E35) !important; border: 1px solid rgba(0,150,255,0.15) !important; border-radius: 12px !important; padding: 18px 20px !important; position: relative; overflow: hidden; }
[data-testid="metric-container"]::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background: linear-gradient(90deg,transparent,#0077FF,#00C8FF,transparent); }
[data-testid="metric-container"] [data-testid="stMetricLabel"] { color: #6A8AAA !important; font-size: 11px !important; letter-spacing: 1px; text-transform: uppercase; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #E0F4FF !important; font-size: 26px !important; font-weight: 600 !important; }
h1,h2,h3 { color: #E0EEF8 !important; font-family:'Space Grotesk',sans-serif !important; }
p, li, span { color: #A0B4C8 !important; }
.stTabs [data-baseweb="tab-list"] { background: #0D1220 !important; border-radius: 10px; padding: 4px; gap: 4px; border: 1px solid rgba(0,200,255,0.1); }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #6A8AAA !important; border-radius: 7px !important; font-weight: 500; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg,#0D2A4A,#0D3A5A) !important; color: #00C8FF !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px !important; }
.stDownloadButton button { background: transparent !important; border: 1px solid rgba(0,200,255,0.3) !important; color: #00C8FF !important; border-radius:8px !important; }
.agent-card { background: linear-gradient(135deg,#0D1A2D 0%,#0A1525 100%); border: 1px solid rgba(0,150,255,0.15); border-radius: 14px; padding: 18px; margin-bottom: 12px; position: relative; overflow: hidden; }
.agent-card::after { content:''; position:absolute; top:0; left:0; width:3px; height:100%; background: linear-gradient(180deg,#0077FF,#00C8FF); border-radius:14px 0 0 14px; }
.agent-name { color: #E0F0FF !important; font-size:15px; font-weight:600; margin-bottom:4px; }
.agent-id { color: #4A6A8A !important; font-size:11px; font-family:'JetBrains Mono',monospace; letter-spacing:1px; }
@keyframes fadeInUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
.fade-in { animation: fadeInUp 0.5s ease forwards; }
.dash-header { background: linear-gradient(90deg,#0D1A2D,#080C14); border: 1px solid rgba(0,200,255,0.1); border-radius:14px; padding:20px 28px; margin-bottom:20px; display:flex; align-items:center; justify-content:space-between; position:relative; overflow:hidden; }
.dash-header::before { content:''; position:absolute; top:0; left:0; right:0; height:1px; background: linear-gradient(90deg,transparent,#0077FF,#00C8FF,transparent); }
.dash-title { color:#E0F4FF !important; font-size:22px; font-weight:700; letter-spacing:-0.5px; }
.dash-subtitle { color:#4A7A9A !important; font-size:13px; font-family:'JetBrains Mono',monospace; }
.live-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(255,50,50,0.15); border:1px solid rgba(255,80,80,0.4); color:#FF6B6B !important; padding:5px 12px; border-radius:20px; font-size:12px; font-weight:600; }
.live-dot { width:7px;height:7px;border-radius:50%;background:#FF4444;animation:blink 1s infinite;display:inline-block; }
.online-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(0,200,120,0.12); border:1px solid rgba(0,220,140,0.3); color:#00DC8C !important; padding:5px 12px; border-radius:20px; font-size:12px; font-weight:600; }
.online-dot { width:7px;height:7px;border-radius:50%;background:#00DC8C;animation:blink 2s infinite;display:inline-block; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
.section-title { color:#00C8FF !important; font-size:11px; font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid rgba(0,200,255,0.1); }
.stat-green { color:#00E896 !important; } .stat-yellow { color:#FFB347 !important; } .stat-red { color:#FF6B6B !important; } .stat-blue { color:#00C8FF !important; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────
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
        r = requests.get(base, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return pd.DataFrame(data), None
        if isinstance(data, dict) and "error" in data:
            return None, data["error"]
        for k in ("cdrs","data","records"):
            if k in data:
                return pd.DataFrame(data[k]), None
        return pd.DataFrame([data] if data else []), None
    except requests.exceptions.ConnectionError:
        return None, "Sin conexion con CallMyWay."
    except requests.exceptions.Timeout:
        return None, "Timeout. Intenta con un rango menor."
    except Exception as e:
        return None, str(e)

def normalizar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    alias = {
        "calldate":"fecha","start":"fecha",
        "src":"origen","callerid":"origen","from":"origen",
        "dst":"destino","destination":"destino","to":"destino",
        "duration":"duracion","billsec":"duracion","seconds":"duracion",
        "disposition":"estado","status":"estado","callstatus":"estado",
        "channel":"canal","troncal":"canal","trunk":"canal",
    }
    df = df.rename(columns={k:v for k,v in alias.items() if k in df.columns})
    if "duracion" in df.columns:
        df["duracion"] = pd.to_numeric(df["duracion"], errors="coerce").fillna(0).astype(int)
    if "estado" in df.columns:
        df["estado"] = df["estado"].str.upper().fillna("DESCONOCIDO")
    if "origen" in df.columns:
        df["origen"] = df["origen"].astype(str).str.strip()
    return df

def identificar_agente(df):
    if "origen" not in df.columns:
        return df
    df = df.copy()
    df["agente_nombre"] = df["origen"].map(AGENTES).fillna("Externo")
    return df

def stats_agente(df, aid, nombre):
    sub = df[df["origen"].astype(str) == str(aid)]
    total    = len(sub)
    answered = int((sub["estado"] == "ANSWERED").sum()) if "estado" in sub.columns else 0
    noanswer = int((sub["estado"] == "NO ANSWER").sum()) if "estado" in sub.columns else 0
    busy     = int((sub["estado"] == "BUSY").sum())      if "estado" in sub.columns else 0
    durs     = sub[sub["estado"]=="ANSWERED"]["duracion"] if "estado" in sub.columns and "duracion" in sub.columns else pd.Series([], dtype=int)
    avg_dur  = int(durs.mean()) if len(durs) else 0
    pct      = round(answered/total*100) if total else 0
    return {"id":aid,"nombre":nombre,"total":total,"answered":answered,
            "noanswer":noanswer,"busy":busy,"avg_dur":avg_dur,"pct":pct}

def color_bar(pct):
    if pct >= 70: return "#00E896"
    if pct >= 40: return "#FFB347"
    return "#FF6B6B"

def fmt_dur(s):
    s = int(s)
    if s == 0: return "—"
    return f"{s//60}m {s%60}s"

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📡 CallCenter Panel")
    st.markdown("---")
    st.markdown("**🔐 Credenciales**")
    username = st.text_input("Usuario", placeholder="7 digitos")
    password = st.text_input("Contrasena", type="password")
    st.markdown("---")
    st.markdown("**📅 Periodo**")
    hoy  = datetime.now()
    ayer = hoy - timedelta(days=1)
    fi   = st.date_input("Desde", value=ayer.date())
    hi   = st.time_input("Hora inicio", value=datetime.strptime("00:00","%H:%M").time())
    ff   = st.date_input("Hasta",  value=hoy.date())
    hf   = st.time_input("Hora fin",   value=datetime.strptime("23:59","%H:%M").time())
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        btn_consultar = st.button("Consultar", type="primary", use_container_width=True)
    with c2:
        btn_24h = st.button("Hoy", use_container_width=True)
    st.markdown("---")
    live_mode = st.toggle("🔴 Modo en vivo", value=False)
    if live_mode:
        intervalo = st.slider("Actualizar cada (seg)", 5, 60, 10)
    else:
        intervalo = 10
    st.markdown("---")
    st.markdown("**👥 Agentes**")
    for aid, nombre in AGENTES.items():
        st.markdown(f"<div style='font-size:12px;padding:3px 0'>▸ <span style='color:#A0C8E8 !important'>{nombre}</span></div>", unsafe_allow_html=True)

# ─── Sesion ───────────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df     = None
    st.session_state.label  = ""
    st.session_state.error  = None
    st.session_state.loaded = False

if not username or not password:
    st.markdown('<div class="dash-header fade-in"><div><div class="dash-title">📡 Panel de Control de Llamadas</div><div class="dash-subtitle">CallMyWay CDR Analytics</div></div></div>', unsafe_allow_html=True)
    st.info("👈 Ingresa tus credenciales en el panel izquierdo para comenzar.")
    st.stop()

if live_mode:
    with st.spinner(""):
        df_raw, err = fetch_cdrs(username, password, live=True)
    if err:
        st.error(f"Error: {err}")
        st.stop()
    st.session_state.df     = normalizar(df_raw)
    st.session_state.label  = f"En vivo {datetime.now().strftime('%H:%M:%S')}"
    st.session_state.loaded = True

elif btn_consultar:
    ds = datetime.combine(fi, hi).strftime("%Y-%m-%d %H:%M:%S")
    de = datetime.combine(ff, hf).strftime("%Y-%m-%d %H:%M:%S")
    with st.spinner("Consultando API..."):
        df_raw, err = fetch_cdrs(username, password, date_start=ds, date_end=de)
    if err:
        st.session_state.error = err
    else:
        st.session_state.df     = normalizar(df_raw)
        st.session_state.label  = f"{fi.strftime('%d/%m')} a {ff.strftime('%d/%m/%Y')}"
        st.session_state.error  = None
        st.session_state.loaded = True

elif btn_24h:
    with st.spinner("Consultando ultimas 24h..."):
        df_raw, err = fetch_cdrs(username, password, recent=True)
    if err:
        st.session_state.error = err
    else:
        st.session_state.df     = normalizar(df_raw)
        st.session_state.label  = "Ultimas 24 horas"
        st.session_state.error  = None
        st.session_state.loaded = True

if st.session_state.error:
    st.error(f"Error: {st.session_state.error}")
    st.stop()

if not st.session_state.loaded or st.session_state.df is None:
    st.markdown('<div class="dash-header fade-in"><div><div class="dash-title">📡 Panel de Control de Llamadas</div><div class="dash-subtitle">CallMyWay CDR Analytics</div></div></div>', unsafe_allow_html=True)
    st.info("Configura el periodo y pulsa Consultar.")
    st.stop()

# ─── Datos ────────────────────────────────────────────────────────────────────
df  = identificar_agente(st.session_state.df)
lbl = st.session_state.label

total    = len(df)
answered = int((df["estado"] == "ANSWERED").sum()) if "estado" in df.columns else 0
noanswer = int((df["estado"] == "NO ANSWER").sum()) if "estado" in df.columns else 0
busy     = int((df["estado"] == "BUSY").sum())      if "estado" in df.columns else 0
durs     = df[df["estado"]=="ANSWERED"]["duracion"] if "estado" in df.columns and "duracion" in df.columns else pd.Series([], dtype=int)
avg_dur  = int(durs.mean()) if len(durs) else 0
total_min= int(durs.sum()/60) if len(durs) else 0
pct_ans  = round(answered/total*100) if total else 0

# ─── Header ───────────────────────────────────────────────────────────────────
badge = '<span class="live-badge"><span class="live-dot"></span> EN VIVO</span>' if live_mode else f'<span class="online-badge"><span class="online-dot"></span> {lbl}</span>'
st.markdown(f"""
<div class="dash-header fade-in">
    <div>
        <div class="dash-title">📡 Panel de Control de Llamadas</div>
        <div class="dash-subtitle" style="margin-top:4px">CallMyWay · {total:,} registros</div>
    </div>
    <div>{badge}</div>
</div>
""", unsafe_allow_html=True)

# ─── Metricas ─────────────────────────────────────────────────────────────────
m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("Total llamadas",    f"{total:,}")
m2.metric("Respondidas",       f"{answered:,}",  f"{pct_ans}%")
m3.metric("No respondidas",    f"{noanswer:,}")
m4.metric("Ocupado / Fallo",   f"{busy:,}")
m5.metric("Duracion promedio", fmt_dur(avg_dur))
m6.metric("Minutos totales",   f"{total_min:,}")

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["👥  Agentes", "📊  Analisis", "📋  Registros", "📈  Tendencias"])

PLOT_STYLE = dict(
    plot_bgcolor="#0D1220", paper_bgcolor="#0D1220",
    font=dict(color="#A0B4C8", family="Space Grotesk"),
    margin=dict(t=10,b=40,l=10,r=10)
)
COLOR_MAP = {"ANSWERED":"#00E896","NO ANSWER":"#FFB347","BUSY":"#FF6B6B","FAILED":"#4A6A8A"}

# ── TAB 1 Agentes ─────────────────────────────────────────────────────────────
with tab1:
    stats_list = sorted(
        [stats_agente(df, aid, nombre) for aid, nombre in AGENTES.items()],
        key=lambda x: x["total"], reverse=True
    )
    st.markdown('<div class="section-title">Rendimiento por agente</div>', unsafe_allow_html=True)
    cols_cards = st.columns(3)
    ranks = ["🥇","🥈","🥉"]
    for i, s in enumerate(stats_list):
        col = cols_cards[i % 3]
        bc  = color_bar(s["pct"])
        rnk = ranks[i] if i < 3 else f"#{i+1}"
        with col:
            st.markdown(f"""
            <div class="agent-card fade-in" style="animation-delay:{i*0.08}s">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
                    <div>
                        <div class="agent-name">{rnk} {s['nombre']}</div>
                        <div class="agent-id">ID: {s['id']}</div>
                    </div>
                    <div style="font-size:26px;opacity:0.5">📞</div>
                </div>
                <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap">
                    <span style="font-size:12px;color:#00C8FF">📥 {s['total']}</span>
                    <span style="font-size:12px;color:#00E896">✅ {s['answered']}</span>
                    <span style="font-size:12px;color:#FFB347">❌ {s['noanswer']}</span>
                </div>
                <div style="margin-bottom:6px">
                    <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
                        <span style="color:#4A6A8A">Tasa de respuesta</span>
                        <span style="color:{bc};font-weight:600">{s['pct']}%</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.05);border-radius:4px;height:5px;overflow:hidden">
                        <div style="width:{s['pct']}%;height:100%;background:{bc};border-radius:4px"></div>
                    </div>
                </div>
                <div style="font-size:11px;color:#4A6A8A;margin-top:8px">Duracion media: <span style="color:#A0C0E0">{fmt_dur(s['avg_dur'])}</span></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Comparativa de llamadas por agente</div>', unsafe_allow_html=True)
    df_stats = pd.DataFrame(stats_list)
    if not df_stats.empty and df_stats["total"].sum() > 0:
        fig_ag = go.Figure()
        for estado_col, color_val, nombre_col in [("answered","#00E896","Respondidas"),("noanswer","#FFB347","No respondidas"),("busy","#FF6B6B","Ocupado")]:
            fig_ag.add_trace(go.Bar(name=nombre_col, x=df_stats["nombre"], y=df_stats[estado_col], marker_color=color_val, marker_line_width=0))
        fig_ag.update_layout(barmode="stack", height=300, legend=dict(orientation="h",y=-0.2,font_size=11), **PLOT_STYLE)
        st.plotly_chart(fig_ag, use_container_width=True)

# ── TAB 2 Analisis ────────────────────────────────────────────────────────────
with tab2:
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="section-title">Distribucion por estado</div>', unsafe_allow_html=True)
        if "estado" in df.columns:
            ec = df["estado"].value_counts().reset_index()
            ec.columns = ["Estado","Cantidad"]
            fig_pie = px.pie(ec, names="Estado", values="Cantidad", color="Estado", color_discrete_map=COLOR_MAP, hole=0.55)
            fig_pie.update_layout(height=300, legend=dict(orientation="h",y=-0.12,font_size=11), **PLOT_STYLE)
            fig_pie.update_traces(textfont_color="white", textfont_size=11)
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_r:
        st.markdown('<div class="section-title">Llamadas por hora del dia</div>', unsafe_allow_html=True)
        if "fecha" in df.columns:
            df["_hora"] = pd.to_datetime(df["fecha"], errors="coerce").dt.hour
            horas = df.groupby("_hora").size().reset_index(name="llamadas").sort_values("_hora")
            max_h = horas["llamadas"].max()
            fig_h = px.bar(horas, x="_hora", y="llamadas")
            fig_h.update_traces(marker_color=["#00C8FF" if v==max_h else "#0055CC" for v in horas["llamadas"]], marker_line_width=0)
            fig_h.update_layout(height=300, xaxis=dict(title="Hora",gridcolor="rgba(255,255,255,0.03)",dtick=1,tickfont_size=10), yaxis=dict(title="",gridcolor="rgba(0,150,255,0.07)"), **PLOT_STYLE)
            st.plotly_chart(fig_h, use_container_width=True)

    st.markdown('<div class="section-title">Duracion promedio por agente (segundos)</div>', unsafe_allow_html=True)
    df_dur = pd.DataFrame(stats_list)
    df_dur = df_dur[df_dur["avg_dur"] > 0].sort_values("avg_dur")
    if not df_dur.empty:
        fig_dur = px.bar(df_dur, x="avg_dur", y="nombre", orientation="h",
            color="avg_dur", color_continuous_scale=["#0033AA","#0077FF","#00C8FF","#00E896"])
        fig_dur.update_layout(height=280, xaxis=dict(title="Segundos",gridcolor="rgba(0,150,255,0.07)"), yaxis_title="", coloraxis_showscale=False, **PLOT_STYLE)
        fig_dur.update_traces(marker_line_width=0)
        st.plotly_chart(fig_dur, use_container_width=True)

# ── TAB 3 Registros ───────────────────────────────────────────────────────────
with tab3:
    fc1,fc2,fc3,fc4 = st.columns([2,1,1,1])
    with fc1:
        busqueda = st.text_input("🔍 Buscar numero o extension", placeholder="Ej: 8668109")
    with fc2:
        estados_disp = df["estado"].unique().tolist() if "estado" in df.columns else []
        filtro_est   = st.multiselect("Estado", options=estados_disp, default=estados_disp)
    with fc3:
        filtro_ag = st.selectbox("Agente", ["Todos"] + list(AGENTES.values()))
    with fc4:
        st.markdown("<br>", unsafe_allow_html=True)
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV", data=csv_data, file_name=f"cdrs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)

    df_v = df.copy()
    if busqueda:
        mask = pd.Series([False]*len(df_v))
        for c in ["origen","destino","canal"]:
            if c in df_v.columns:
                mask |= df_v[c].astype(str).str.contains(busqueda, case=False, na=False)
        df_v = df_v[mask]
    if filtro_est and "estado" in df_v.columns:
        df_v = df_v[df_v["estado"].isin(filtro_est)]
    if filtro_ag != "Todos" and "agente_nombre" in df_v.columns:
        df_v = df_v[df_v["agente_nombre"] == filtro_ag]

    st.caption(f"Mostrando {len(df_v):,} de {total:,} registros")
    cols_show = [c for c in ["fecha","agente_nombre","origen","destino","duracion","estado","canal"] if c in df_v.columns]
    df_show = df_v[cols_show].copy()
    if "duracion" in df_show.columns:
        df_show["duracion"] = df_show["duracion"].apply(fmt_dur)
    rename_map = {"fecha":"Fecha","agente_nombre":"Agente","origen":"Origen","destino":"Destino","duracion":"Duracion","estado":"Estado","canal":"Canal"}
    df_show = df_show.rename(columns={k:v for k,v in rename_map.items() if k in df_show.columns})
    st.dataframe(df_show, use_container_width=True, height=480, hide_index=True)

# ── TAB 4 Tendencias ──────────────────────────────────────────────────────────
with tab4:
    if "fecha" in df.columns:
        df["_dt"]      = pd.to_datetime(df["fecha"], errors="coerce")
        df["_fecha_d"] = df["_dt"].dt.date

        st.markdown('<div class="section-title">Evolucion diaria de llamadas</div>', unsafe_allow_html=True)
        daily = df.groupby(["_fecha_d","estado"]).size().reset_index(name="n")
        if not daily.empty:
            fig_line = px.line(daily, x="_fecha_d", y="n", color="estado",
                color_discrete_map=COLOR_MAP, markers=True)
            fig_line.update_layout(height=300, xaxis_title="Fecha", yaxis_title="Llamadas",
                legend=dict(orientation="h",y=-0.2,font_size=11),
                xaxis=dict(gridcolor="rgba(255,255,255,0.03)"),
                yaxis=dict(gridcolor="rgba(0,150,255,0.07)"), **PLOT_STYLE)
            fig_line.update_traces(line_width=2, marker_size=5)
            st.plotly_chart(fig_line, use_container_width=True)

        st.markdown('<div class="section-title">Mapa de calor — Hora vs Dia de semana</div>', unsafe_allow_html=True)
        df["_dow"]  = df["_dt"].dt.day_name()
        df["_hour"] = df["_dt"].dt.hour
        dias_order  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        heat        = df.groupby(["_dow","_hour"]).size().reset_index(name="n")
        if not heat.empty:
            hp = heat.pivot_table(index="_dow", columns="_hour", values="n", fill_value=0)
            hp = hp.reindex([d for d in dias_order if d in hp.index])
            fig_heat = px.imshow(hp, color_continuous_scale=["#080C14","#0033AA","#0077FF","#00C8FF","#00E896"],
                aspect="auto", labels=dict(x="Hora",y="Dia",color="Llamadas"))
            fig_heat.update_layout(height=260, **PLOT_STYLE)
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No hay datos de fecha para graficar tendencias.")

# ─── Auto-refresh live ────────────────────────────────────────────────────────
if live_mode:
    time.sleep(intervalo)
    st.rerun()
