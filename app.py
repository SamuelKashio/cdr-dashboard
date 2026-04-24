import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ─── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard CDRs — CallMyWay",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Estilos ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stMetric { background: #1e2130; border-radius: 10px; padding: 16px; border: 1px solid rgba(255,255,255,0.07); }
    div[data-testid="metric-container"] { background: #1e2130; border-radius: 10px; padding: 16px 20px; border: 1px solid rgba(255,255,255,0.08); }
    .pill { display:inline-block; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:500; }
    .pill-ok   { background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); }
    .pill-no   { background:rgba(245,158,11,0.15);  color:#fbbf24; border:1px solid rgba(245,158,11,0.3); }
    .pill-busy { background:rgba(239,68,68,0.15);   color:#f87171; border:1px solid rgba(239,68,68,0.3); }
    .pill-other{ background:rgba(100,116,139,0.15); color:#94a3b8; border:1px solid rgba(100,116,139,0.3); }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar — Credenciales y filtros ────────────────────────────────────────
with st.sidebar:
    st.title("📞 Dashboard CDRs")
    st.caption("CallMyWay API")
    st.divider()

    st.subheader("🔐 Credenciales")
    username = st.text_input("Usuario (7 dígitos)", placeholder="8569841", max_chars=7)
    password = st.text_input("Contraseña (11 dígitos)", placeholder="01234567891", type="password")

    st.divider()
    st.subheader("📅 Rango de fechas")

    hoy = datetime.now()
    ayer = hoy - timedelta(days=1)

    fecha_inicio = st.date_input("Fecha inicio", value=ayer.date())
    hora_inicio  = st.time_input("Hora inicio",  value=datetime.strptime("00:00", "%H:%M").time())
    fecha_fin    = st.date_input("Fecha fin",    value=hoy.date())
    hora_fin     = st.time_input("Hora fin",     value=datetime.strptime("23:59", "%H:%M").time())

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        btn_consultar = st.button("⟳ Consultar", type="primary", use_container_width=True)
    with col2:
        btn_24h = st.button("Últimas 24h", use_container_width=True)

    st.divider()
    live_mode = st.toggle("🔴 Modo en vivo", value=False)
    if live_mode:
        st.caption("Actualizando cada 10 segundos")

    st.divider()
    st.caption("v1.0 · Solo uso interno")

# ─── Función para consultar la API ───────────────────────────────────────────
def fetch_cdrs(username, password, date_start=None, date_end=None, recent=False, live=False):
    base = "https://callmyway.com/getCdrs.php"
    params = {"username": username, "password": password, "format": "json"}

    if live:
        params["live"] = 1
        params["fullAccount"] = 1
    elif recent:
        params["recent"] = 1
    else:
        params["dateStart"] = date_start
        params["dateEnd"]   = date_end
        params["ini"]       = 0
        params["cant"]      = 5000

    try:
        resp = requests.get(base, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return pd.DataFrame(data), None
        elif isinstance(data, dict) and "error" in data:
            return None, data["error"]
        else:
            for key in ("cdrs", "data", "records"):
                if key in data:
                    return pd.DataFrame(data[key]), None
            return pd.DataFrame(data if isinstance(data, list) else [data]), None
    except requests.exceptions.ConnectionError:
        return None, "No se pudo conectar con la API de CallMyWay. Verifica tu conexión a internet."
    except requests.exceptions.Timeout:
        return None, "La consulta tardó demasiado. Intenta con un rango de fechas más pequeño."
    except Exception as e:
        return None, str(e)

# ─── Función para normalizar columnas ────────────────────────────────────────
def normalizar(df):
    alias = {
        "calldate": "fecha",  "start": "fecha",
        "src":      "origen", "callerid": "origen", "from": "origen",
        "dst":      "destino","destination": "destino", "to": "destino",
        "duration": "duracion", "billsec": "duracion", "seconds": "duracion",
        "disposition": "estado", "status": "estado", "callstatus": "estado",
        "channel":  "canal",  "troncal": "canal", "trunk": "canal",
    }
    df = df.rename(columns={k: v for k, v in alias.items() if k in df.columns})
    if "duracion" in df.columns:
        df["duracion"] = pd.to_numeric(df["duracion"], errors="coerce").fillna(0).astype(int)
    if "estado" in df.columns:
        df["estado"] = df["estado"].str.upper().fillna("DESCONOCIDO")
    return df

# ─── Función para badge de estado ────────────────────────────────────────────
def badge_estado(estado):
    mapa = {
        "ANSWERED":  ('<span class="pill pill-ok">ANSWERED</span>', "✅"),
        "NO ANSWER": ('<span class="pill pill-no">NO ANSWER</span>', "⚠️"),
        "BUSY":      ('<span class="pill pill-busy">BUSY</span>',    "🔴"),
    }
    return mapa.get(estado, (f'<span class="pill pill-other">{estado}</span>', "⚪"))

# ─── Lógica principal ─────────────────────────────────────────────────────────
df = None
error_msg = None
modo = None

if not username or not password:
    st.info("👈 Ingresa tus credenciales en el panel izquierdo para comenzar.")
    st.stop()

# Modo en vivo — auto-refresh
if live_mode:
    modo = "live"
    placeholder = st.empty()
    with placeholder.container():
        st.subheader("🔴 Llamadas en vivo")
        with st.spinner("Consultando llamadas activas..."):
            df, error_msg = fetch_cdrs(username, password, live=True)
    time.sleep(10)
    st.rerun()

elif btn_24h:
    modo = "24h"
    with st.spinner("Consultando últimas 24 horas..."):
        df, error_msg = fetch_cdrs(username, password, recent=True)

elif btn_consultar:
    modo = "historico"
    ds = datetime.combine(fecha_inicio, hora_inicio).strftime("%Y-%m-%d %H:%M:%S")
    de = datetime.combine(fecha_fin,    hora_fin).strftime("%Y-%m-%d %H:%M:%S")
    with st.spinner(f"Consultando del {ds} al {de}..."):
        df, error_msg = fetch_cdrs(username, password, date_start=ds, date_end=de)

else:
    st.info("👈 Configura el rango de fechas y haz clic en **Consultar** para cargar los CDRs.")
    st.stop()

# ─── Mostrar error ────────────────────────────────────────────────────────────
if error_msg:
    st.error(f"⚠️ {error_msg}")
    st.stop()

if df is None or df.empty:
    st.warning("No se encontraron registros para el rango seleccionado.")
    st.stop()

# ─── Normalizar ───────────────────────────────────────────────────────────────
df = normalizar(df)

# ─── MÉTRICAS ─────────────────────────────────────────────────────────────────
total     = len(df)
answered  = len(df[df["estado"] == "ANSWERED"]) if "estado" in df.columns else 0
noanswer  = len(df[df["estado"] == "NO ANSWER"]) if "estado" in df.columns else 0
busy      = len(df[df["estado"] == "BUSY"])      if "estado" in df.columns else 0
pct_ans   = round(answered / total * 100) if total else 0

dur_ans   = df[df["estado"] == "ANSWERED"]["duracion"] if "estado" in df.columns and "duracion" in df.columns else pd.Series([], dtype=int)
avg_dur   = int(dur_ans.mean()) if len(dur_ans) else 0
total_min = int(dur_ans.sum() / 60) if len(dur_ans) else 0

titulo = "Llamadas en vivo" if modo == "live" else f"Historial — {total:,} registros"
st.subheader(f"{'🔴 ' if modo == 'live' else '📊 '}{titulo}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total llamadas",    f"{total:,}")
c2.metric("Respondidas",       f"{answered:,}",   f"{pct_ans}%")
c3.metric("No respondidas",    f"{noanswer:,}",   f"{round(noanswer/total*100) if total else 0}%")
c4.metric("Duración promedio", f"{avg_dur}s")
c5.metric("Minutos totales",   f"{total_min:,}")

st.divider()

# ─── GRÁFICOS ─────────────────────────────────────────────────────────────────
col_g1, col_g2 = st.columns([1, 2])

with col_g1:
    if "estado" in df.columns:
        counts = df["estado"].value_counts().reset_index()
        counts.columns = ["Estado", "Cantidad"]
        color_map = {"ANSWERED": "#10b981", "NO ANSWER": "#f59e0b", "BUSY": "#ef4444", "FAILED": "#6b7280"}
        fig_donut = px.pie(
            counts, names="Estado", values="Cantidad",
            hole=0.6, color="Estado", color_discrete_map=color_map,
            title="Distribución por estado"
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", title_font_color="#e2e8f0",
            legend=dict(font=dict(size=11)),
            margin=dict(t=40, b=10, l=10, r=10)
        )
        fig_donut.update_traces(textfont_color="#e2e8f0")
        st.plotly_chart(fig_donut, use_container_width=True)

with col_g2:
    if "fecha" in df.columns:
        df["_hora"] = pd.to_datetime(df["fecha"], errors="coerce").dt.hour
        horas = df["_hora"].value_counts().sort_index().reset_index()
        horas.columns = ["Hora", "Llamadas"]
        horas = horas.sort_values("Hora")
        fig_bar = px.bar(
            horas, x="Hora", y="Llamadas",
            title="Llamadas por hora del día",
            color_discrete_sequence=["#3b82f6"]
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", title_font_color="#e2e8f0",
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickmode="linear", dtick=1),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ─── TABLA ────────────────────────────────────────────────────────────────────
col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
with col_t1:
    busqueda = st.text_input("🔍 Buscar por número o extensión", placeholder="Ej: 506, 8001...")
with col_t2:
    estados_disponibles = df["estado"].unique().tolist() if "estado" in df.columns else []
    filtro_estado = st.multiselect("Filtrar por estado", options=estados_disponibles, default=estados_disponibles)
with col_t3:
    st.write("")
    st.write("")
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Exportar CSV", data=csv, file_name=f"cdrs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)

# Aplicar filtros
df_vista = df.copy()
if busqueda:
    mask = pd.Series([False] * len(df_vista))
    for col in ["origen", "destino", "canal"]:
        if col in df_vista.columns:
            mask |= df_vista[col].astype(str).str.contains(busqueda, case=False, na=False)
    df_vista = df_vista[mask]
if filtro_estado and "estado" in df_vista.columns:
    df_vista = df_vista[df_vista["estado"].isin(filtro_estado)]

st.caption(f"Mostrando {len(df_vista):,} de {total:,} registros")

# Columnas a mostrar
cols_mostrar = [c for c in ["fecha", "origen", "destino", "duracion", "estado", "canal"] if c in df_vista.columns]
df_show = df_vista[cols_mostrar].copy()

# Formato duración
if "duracion" in df_show.columns:
    df_show["duracion"] = df_show["duracion"].apply(lambda s: f"{int(s)//60}m {int(s)%60}s" if s > 0 else "—")

st.dataframe(
    df_show,
    use_container_width=True,
    height=450,
    column_config={
        "fecha":    st.column_config.TextColumn("Fecha / Hora", width="medium"),
        "origen":   st.column_config.TextColumn("Origen"),
        "destino":  st.column_config.TextColumn("Destino"),
        "duracion": st.column_config.TextColumn("Duración"),
        "estado":   st.column_config.TextColumn("Estado"),
        "canal":    st.column_config.TextColumn("Canal / Troncal", width="large"),
    },
    hide_index=True
)
