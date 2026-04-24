"""
Dashboard de Monitoreo PBX — CallMyWay
Ejecutar con:
    pip install streamlit pandas requests plotly
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+

# ──────────────────────────────────────────────
# CREDENCIALES
# ──────────────────────────────────────────────
USERNAME = "8668334"
PASSWORD = "28719014429"
BASE_URL  = "https://callmyway.com/getCdrs.php"
TZ        = ZoneInfo("America/Lima")

# ──────────────────────────────────────────────
# MAPA DE AGENTES  endpoint -> nombre legible
# ──────────────────────────────────────────────
AGENTS = {
    "8668106": "Central Virtual",
    "8668109": "Edwin Loyola",
    "8668110": "Jose L. Cahuana",
    "8668112": "Daniel Huayta",
    "8668111": "Deivy Chavez",
    "8668114": "Joe Villanueva",
    "8672537": "Victor Figueroa",
}

STATUS_COLORS = {
    "ANSWERED":  "#1D9E75",
    "NO ANSWER": "#EF9F27",
    "BUSY":      "#E24B4A",
    "FAILED":    "#888780",
}

# ──────────────────────────────────────────────
# COLUMNAS ESPERADAS DE LA API
# ──────────────────────────────────────────────
COL_DURATION = "duration"
COL_BILLSEC  = "billsec"
COL_AGENT    = "src"
COL_DST      = "dst"
COL_STATUS   = "disposition"
COL_CALLDATE = "calldate"
COL_CLID     = "clid"


# ══════════════════════════════════════════════
# HELPERS API
# ══════════════════════════════════════════════

def _parse_response(data) -> pd.DataFrame:
    """Normaliza cualquier estructura JSON de la API a un DataFrame."""
    if isinstance(data, list):
        return pd.DataFrame(data) if data else pd.DataFrame()
    if isinstance(data, dict):
        for key in ("data", "cdrs", "records", "calls", "result"):
            if isinstance(data.get(key), list):
                return pd.DataFrame(data[key]) if data[key] else pd.DataFrame()
        if data:
            return pd.DataFrame([data])
    return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_live_calls() -> pd.DataFrame:
    url = (f"{BASE_URL}?username={USERNAME}&password={PASSWORD}"
           f"&live=1&fullAccount=1&format=json")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return _parse_response(r.json())
    except Exception as e:
        st.warning(f"No se pudo obtener llamadas en vivo: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_historic(date_start: str, date_end: str, limit: int = 5000) -> pd.DataFrame:
    all_rows, offset, page_size = [], 0, min(500, limit)
    prog = st.progress(0, text="Descargando registros...")
    while len(all_rows) < limit:
        batch = min(page_size, limit - len(all_rows))
        url = (f"{BASE_URL}?username={USERNAME}&password={PASSWORD}"
               f"&dateStart={date_start}&dateEnd={date_end}"
               f"&ini={offset}&cant={batch}&format=json")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            chunk = _parse_response(r.json())
        except Exception as e:
            st.error(f"Error en la API: {e}")
            break
        if chunk.empty:
            break
        all_rows.append(chunk)
        offset += len(chunk)
        total_so_far = sum(len(x) for x in all_rows)
        prog.progress(min(total_so_far / limit, 1.0), text=f"Descargando... {total_so_far:,} registros")
        if len(chunk) < batch:
            break
    prog.empty()
    return pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()


# ══════════════════════════════════════════════
# HELPERS ANALISIS
# ══════════════════════════════════════════════

def best_dur_col(df: pd.DataFrame):
    for c in (COL_BILLSEC, COL_DURATION):
        if c in df.columns:
            return c
    return None


def to_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def label_agent(val) -> str:
    return AGENTS.get(str(val).strip(), str(val))


def compute_kpis(df: pd.DataFrame):
    total = len(df)
    dur_col = best_dur_col(df)
    dur_min = dur_avg = 0.0
    if dur_col:
        secs = to_numeric(df, dur_col)
        dur_min = secs.sum() / 60
        dur_avg = secs.mean() if total else 0.0
    asr = 0.0
    if COL_STATUS in df.columns and total:
        ans = df[COL_STATUS].str.upper().eq("ANSWERED").sum()
        asr = ans / total * 100
    return total, dur_min, dur_avg, asr


# ══════════════════════════════════════════════
# PAGINA
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard PBX - CallMyWay",
    page_icon="phone",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stMetricValue"]  { font-size: 2.2rem !important; font-weight: 500; }
[data-testid="stMetricLabel"]  { font-size: .85rem; color: #888; }
.block-container               { padding-top: 1.2rem; padding-bottom: 2rem; }
div[data-testid="column"]      { padding: 0 6px; }
.stTabs [data-baseweb="tab"]   { font-size: .95rem; padding: .5rem 1.2rem; }
hr                             { margin: 1rem 0; opacity: .25; }
</style>
""", unsafe_allow_html=True)

# ── Encabezado ────────────────────────────────
now_lima = datetime.now(TZ)
h1, h2 = st.columns([5, 2])
with h1:
    st.markdown("## Dashboard PBX — CallMyWay")
    st.caption(f"Central **{USERNAME}** · Lima, Peru · {now_lima.strftime('%A %d %b %Y, %H:%M:%S')}")
with h2:
    if st.button("Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ══════════════════════════════════════════════
# PESTANAS PRINCIPALES
# ══════════════════════════════════════════════
tab_live, tab_hist = st.tabs(["Llamadas en Vivo", "Historico y Metricas"])


# ─────────────────────────────────────────────
# PESTANA 1: LLAMADAS EN VIVO
# ─────────────────────────────────────────────
with tab_live:
    with st.spinner("Consultando llamadas activas..."):
        df_live = fetch_live_calls()

    total_live = len(df_live)
    kc1, kc2, kc3 = st.columns(3)
    kc1.metric("Llamadas activas ahora", total_live)

    if not df_live.empty:
        dur_col = best_dur_col(df_live)
        if dur_col:
            kc2.metric("Duracion promedio", f"{to_numeric(df_live, dur_col).mean():.0f}s")
        if COL_AGENT in df_live.columns:
            kc3.metric("Agentes en linea", df_live[COL_AGENT].nunique())

    st.divider()

    if df_live.empty:
        st.info("Sin llamadas activas ahora mismo. Pulsa **Recargar datos** para refrescar.")
    else:
        if COL_AGENT in df_live.columns:
            df_live["Agente"] = df_live[COL_AGENT].apply(label_agent)
        st.success(f"**{total_live}** llamada(s) en curso")
        priority = ["Agente", COL_AGENT, COL_DST, COL_CALLDATE, COL_DURATION, COL_BILLSEC, COL_STATUS, COL_CLID]
        cols_show = [c for c in priority if c in df_live.columns]
        cols_rest = [c for c in df_live.columns if c not in cols_show]
        st.dataframe(df_live[cols_show + cols_rest], use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# PESTANA 2: HISTORICO Y METRICAS
# ─────────────────────────────────────────────
with tab_hist:

    # Filtros
    with st.container(border=True):
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
        with fc1:
            d_start = st.date_input("Fecha inicio", value=now_lima.date() - timedelta(days=7), format="DD/MM/YYYY")
            t_start = st.time_input("Hora inicio",  value=datetime.strptime("00:00:00", "%H:%M:%S").time())
        with fc2:
            d_end   = st.date_input("Fecha fin",    value=now_lima.date(), format="DD/MM/YYYY")
            t_end   = st.time_input("Hora fin",     value=datetime.strptime("23:59:59", "%H:%M:%S").time())
        with fc3:
            limit = st.number_input("Limite registros", 100, 50_000, 5_000, 500)
            agent_filter = st.selectbox("Filtrar agente", ["Todos"] + list(AGENTS.values()))
        with fc4:
            st.markdown("<br>", unsafe_allow_html=True)
            run = st.button("Buscar", type="primary", use_container_width=True)

    if run:
        if d_start > d_end:
            st.error("La fecha de inicio no puede ser posterior a la fecha fin.")
        else:
            ds_str = f"{d_start} {t_start.strftime('%H:%M:%S')}"
            de_str = f"{d_end} {t_end.strftime('%H:%M:%S')}"
            with st.spinner("Consultando API..."):
                df_h = fetch_historic(ds_str, de_str, int(limit))
            st.session_state["df_hist"] = df_h
            st.session_state["hist_range"] = (ds_str, de_str)

    if "df_hist" not in st.session_state:
        st.info("Selecciona un rango de fechas y pulsa **Buscar** para cargar el historico.")
        st.stop()

    df_h: pd.DataFrame = st.session_state["df_hist"].copy()
    ds_str, de_str = st.session_state["hist_range"]

    if df_h.empty:
        st.warning("La API no devolvio registros para ese rango. Prueba con otro periodo.")
        st.stop()

    # Enriquecer nombres de agente
    if COL_AGENT in df_h.columns:
        df_h["Agente"] = df_h[COL_AGENT].apply(label_agent)

    # Filtro local por agente
    if agent_filter != "Todos" and "Agente" in df_h.columns:
        df_h = df_h[df_h["Agente"] == agent_filter]

    # Advertencias columnas faltantes
    missing = [c for c in [COL_DURATION, COL_AGENT, COL_STATUS] if c not in df_h.columns]
    if missing:
        st.warning(f"Columnas no encontradas: `{'`, `'.join(missing)}`. "
                   f"Disponibles: `{'`, `'.join(df_h.columns.tolist())}`")

    dur_col = best_dur_col(df_h)
    if dur_col:
        df_h[dur_col] = to_numeric(df_h, dur_col)

    st.success(f"**{len(df_h):,}** registros · {ds_str}  ->  {de_str}")

    # ── KPIs ─────────────────────────────────
    st.markdown("### KPIs Globales")
    total, dur_min, dur_avg, asr = compute_kpis(df_h)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total llamadas",          f"{total:,}")
    k2.metric("Duracion total (min)",    f"{dur_min:,.1f}")
    k3.metric("Duracion promedio (seg)", f"{dur_avg:,.1f}")
    k4.metric("ASR - Tasa de respuesta", f"{asr:.1f}%")

    st.divider()

    # ── Graficos ─────────────────────────────
    st.markdown("### Visualizaciones")
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("#### Distribucion de estados")
        if COL_STATUS in df_h.columns:
            sc = (df_h[COL_STATUS].fillna("DESCONOCIDO").str.upper()
                  .value_counts().reset_index())
            sc.columns = ["Estado", "Llamadas"]
            fig_pie = px.pie(
                sc, names="Estado", values="Llamadas", hole=.45,
                color="Estado", color_discrete_map=STATUS_COLORS,
            )
            fig_pie.update_traces(
                textposition="inside", textinfo="percent+label",
                marker=dict(line=dict(width=2, color="white"))
            )
            fig_pie.update_layout(
                showlegend=True, margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(font=dict(size=12))
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info(f"Columna `{COL_STATUS}` no disponible.")

    with g2:
        st.markdown("#### Top 10 agentes - volumen")
        agent_col = "Agente" if "Agente" in df_h.columns else (COL_AGENT if COL_AGENT in df_h.columns else None)
        if agent_col:
            ta = (df_h[agent_col].fillna("Sin agente")
                  .value_counts().head(10).reset_index())
            ta.columns = ["Agente", "Llamadas"]
            ta = ta.sort_values("Llamadas")
            fig_bar = px.bar(
                ta, x="Llamadas", y="Agente", orientation="h",
                color="Llamadas", color_continuous_scale="Blues", text="Llamadas",
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                coloraxis_showscale=False, yaxis_title=None
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Columna de agente no disponible.")

    # ── Serie temporal ────────────────────────
    if COL_CALLDATE in df_h.columns:
        st.markdown("#### Llamadas por hora")
        try:
            dfc = df_h.copy()
            dfc[COL_CALLDATE] = pd.to_datetime(dfc[COL_CALLDATE], errors="coerce")
            hourly = (dfc.dropna(subset=[COL_CALLDATE])
                      .set_index(COL_CALLDATE)
                      .resample("1h").size().reset_index())
            hourly.columns = ["Hora", "Llamadas"]
            fig_ts = px.bar(
                hourly, x="Hora", y="Llamadas",
                color_discrete_sequence=["#378ADD"],
            )
            fig_ts.update_layout(margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None)
            st.plotly_chart(fig_ts, use_container_width=True)
        except Exception:
            pass

    st.divider()

    # ── Tabla por agente ──────────────────────
    st.markdown("### Resumen por agente")
    agent_col = "Agente" if "Agente" in df_h.columns else (COL_AGENT if COL_AGENT in df_h.columns else None)

    if agent_col:
        agg = {"Total llamadas": (agent_col, "count")}
        if dur_col:
            agg["Dur. total (min)"] = (dur_col, lambda x: round(x.sum() / 60, 1))
            agg["Dur. prom. (seg)"] = (dur_col, lambda x: round(x.mean(), 1))
        if COL_STATUS in df_h.columns:
            agg["Contestadas"] = (COL_STATUS, lambda x: int(x.str.upper().eq("ANSWERED").sum()))

        df_ag = (df_h.groupby(agent_col)
                 .agg(**agg)
                 .reset_index()
                 .rename(columns={agent_col: "Agente"})
                 .sort_values("Total llamadas", ascending=False))

        if "Contestadas" in df_ag.columns:
            df_ag["ASR %"] = (df_ag["Contestadas"] / df_ag["Total llamadas"] * 100).round(1)

        st.dataframe(
            df_ag, use_container_width=True, hide_index=True,
            column_config={
                "Total llamadas":   st.column_config.NumberColumn(format="%d"),
                "Dur. total (min)": st.column_config.NumberColumn(format="%.1f"),
                "Dur. prom. (seg)": st.column_config.NumberColumn(format="%.1f"),
                "Contestadas":      st.column_config.NumberColumn(format="%d"),
                "ASR %":            st.column_config.ProgressColumn(
                                        format="%.1f%%", min_value=0, max_value=100),
            },
        )
    else:
        st.dataframe(df_h, use_container_width=True, hide_index=True)

    st.divider()

    # ── Tabla cruda completa ──────────────────
    with st.expander("Ver todos los registros", expanded=False):
        priority = ["Agente", COL_AGENT, COL_CALLDATE, COL_DST, dur_col, COL_STATUS]
        cols_show = [c for c in priority if c and c in df_h.columns]
        cols_rest = [c for c in df_h.columns if c not in cols_show]
        st.dataframe(df_h[cols_show + cols_rest], use_container_width=True, hide_index=True)
        csv = df_h.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar CSV completo",
            data=csv,
            file_name=f"pbx_cdrs_{ds_str[:10]}_{de_str[:10]}.csv",
            mime="text/csv",
            use_container_width=True,
        )
