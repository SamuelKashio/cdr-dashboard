"""
Dashboard de Monitoreo PBX - CallMyWay
Ejecutar con: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# CREDENCIALES (hardcodeadas)
# ──────────────────────────────────────────────
USERNAME = "8668334"
PASSWORD = "28719014429"
BASE_URL  = "https://callmyway.com/getCdrs.php"

# ──────────────────────────────────────────────
# NOMBRES DE COLUMNAS ESPERADAS
# Ajusta aquí si la API devuelve nombres distintos
# ──────────────────────────────────────────────
COL_DURATION    = "duration"       # Duración de la llamada (segundos)
COL_AGENT       = "src"            # Agente / extensión origen
COL_STATUS      = "disposition"    # Estado: ANSWERED, NO ANSWER, BUSY, FAILED…
COL_CALLDATE    = "calldate"       # Fecha/hora de la llamada
COL_DST         = "dst"            # Destino


# ══════════════════════════════════════════════
# HELPERS DE API
# ══════════════════════════════════════════════

def fetch_live_calls() -> pd.DataFrame:
    """Trae las llamadas activas en este momento."""
    url = (
        f"{BASE_URL}?username={USERNAME}&password={PASSWORD}"
        f"&live=1&fullAccount=1&format=json"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            # Algunos endpoints envuelven los registros en una clave
            for key in ("data", "cdrs", "records", "calls"):
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
            return pd.DataFrame([data]) if data else pd.DataFrame()
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error de conexión: {e}")
        return pd.DataFrame()
    except ValueError as e:
        st.error(f"❌ Error al parsear JSON: {e}")
        return pd.DataFrame()


def fetch_historic_calls(date_start: str, date_end: str, limit: int = 5000) -> pd.DataFrame:
    """
    Trae CDRs históricos con paginación automática hasta `limit` registros.
    date_start / date_end formato: 'yyyy-mm-dd HH:MM:SS'
    """
    all_records = []
    page_size   = 500
    offset      = 0

    progress = st.progress(0, text="Descargando registros…")

    while len(all_records) < limit:
        batch = min(page_size, limit - len(all_records))
        url = (
            f"{BASE_URL}?username={USERNAME}&password={PASSWORD}"
            f"&dateStart={date_start}&dateEnd={date_end}"
            f"&ini={offset}&cant={batch}&format=json"
        )
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error de conexión: {e}")
            break
        except ValueError as e:
            st.error(f"❌ Error al parsear JSON: {e}")
            break

        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ("data", "cdrs", "records", "calls"):
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break

        if not records:
            break  # No hay más datos

        all_records.extend(records)
        offset += len(records)

        pct = min(len(all_records) / limit, 1.0)
        progress.progress(pct, text=f"Descargando… {len(all_records):,} registros")

        if len(records) < batch:
            break  # Última página (devolvió menos de lo pedido)

    progress.empty()
    return pd.DataFrame(all_records) if all_records else pd.DataFrame()


# ══════════════════════════════════════════════
# HELPERS DE ANÁLISIS
# ══════════════════════════════════════════════

def col_exists(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


def ensure_numeric(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col_exists(df, col):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def compute_kpis(df: pd.DataFrame):
    total = len(df)

    # Duración
    dur_total_min = 0.0
    dur_avg_sec   = 0.0
    if col_exists(df, COL_DURATION):
        df = ensure_numeric(df, COL_DURATION)
        dur_total_min = df[COL_DURATION].sum() / 60
        dur_avg_sec   = df[COL_DURATION].mean()

    # ASR
    asr = 0.0
    if col_exists(df, COL_STATUS) and total > 0:
        answered = df[COL_STATUS].str.upper().eq("ANSWERED").sum()
        asr = answered / total * 100

    return total, dur_total_min, dur_avg_sec, asr


# ══════════════════════════════════════════════
# CONFIGURACIÓN DE LA PÁGINA
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard PBX - CallMyWay",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS mínimo para mejorar la apariencia
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 2rem; }
    .block-container { padding-top: 1.5rem; }
    h1 { color: #1f6feb; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ENCABEZADO
# ══════════════════════════════════════════════
st.title("📞 Dashboard de Monitoreo PBX")
st.caption(f"Central: **{USERNAME}** · CallMyWay  |  Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.divider()


# ══════════════════════════════════════════════
# PESTAÑAS PRINCIPALES
# ══════════════════════════════════════════════
tab_live, tab_hist = st.tabs(["🔴  Llamadas en Vivo", "📊  Histórico y Métricas"])


# ─────────────────────────────────────────────
# PESTAÑA 1: LLAMADAS EN VIVO
# ─────────────────────────────────────────────
with tab_live:
    st.subheader("🔴 Llamadas en Vivo")

    col_btn, col_ts = st.columns([1, 5])
    with col_btn:
        if st.button("🔄 Recargar", use_container_width=True):
            st.rerun()
    with col_ts:
        st.caption(f"Último refresco: {datetime.now().strftime('%H:%M:%S')}")

    with st.spinner("Consultando llamadas activas…"):
        df_live = fetch_live_calls()

    if df_live.empty:
        st.metric("📞 Llamadas Activas", 0)
        st.info("✅ No hay llamadas en curso en este momento.")
    else:
        total_live = len(df_live)
        st.metric("📞 Llamadas Activas", total_live)
        st.success(f"Se encontraron **{total_live}** llamada(s) activa(s).")
        st.dataframe(df_live, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# PESTAÑA 2: HISTÓRICO Y MÉTRICAS
# ─────────────────────────────────────────────
with tab_hist:
    st.subheader("📊 Histórico y Métricas")

    # ── Filtros ──────────────────────────────
    with st.container(border=True):
        st.markdown("**🔎 Filtros de búsqueda**")
        f1, f2, f3 = st.columns([2, 2, 1])

        with f1:
            date_start = st.date_input(
                "Fecha de Inicio",
                value=datetime.now().date() - timedelta(days=7),
                format="DD/MM/YYYY",
            )
            time_start = st.time_input("Hora de Inicio", value=datetime.strptime("00:00:00", "%H:%M:%S").time())

        with f2:
            date_end = st.date_input(
                "Fecha de Fin",
                value=datetime.now().date(),
                format="DD/MM/YYYY",
            )
            time_end = st.time_input("Hora de Fin", value=datetime.strptime("23:59:59", "%H:%M:%S").time())

        with f3:
            limit = st.number_input("Límite de registros", min_value=1, max_value=50000, value=5000, step=500)

        search_btn = st.button("🔍 Buscar en la API", type="primary", use_container_width=True)

    # Construir strings de fecha/hora
    ds = f"{date_start} {time_start.strftime('%H:%M:%S')}"
    de = f"{date_end} {time_end.strftime('%H:%M:%S')}"

    # ── Búsqueda ─────────────────────────────
    if search_btn:
        if date_start > date_end:
            st.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin.")
        else:
            with st.spinner("Consultando API…"):
                df_hist = fetch_historic_calls(ds, de, int(limit))
            st.session_state["df_hist"] = df_hist
            st.session_state["hist_ds"]  = ds
            st.session_state["hist_de"]  = de

    # ── Resultados ───────────────────────────
    if "df_hist" in st.session_state:
        df_hist: pd.DataFrame = st.session_state["df_hist"]

        if df_hist.empty:
            st.warning("⚠️ La API no devolvió registros para el rango seleccionado.")
        else:
            st.success(
                f"✅ {len(df_hist):,} registros descargados  "
                f"({st.session_state['hist_ds']} → {st.session_state['hist_de']})"
            )

            # ── Advertencias de columnas faltantes ──
            missing = [c for c in [COL_DURATION, COL_AGENT, COL_STATUS]
                       if not col_exists(df_hist, c)]
            if missing:
                st.warning(
                    f"⚠️ Las siguientes columnas no fueron encontradas en los datos: "
                    f"`{'`, `'.join(missing)}`. "
                    f"Algunas métricas y gráficos no estarán disponibles. "
                    f"Columnas disponibles: `{'`, `'.join(df_hist.columns.tolist())}`"
                )

            # Asegurar duración numérica
            df_hist = ensure_numeric(df_hist, COL_DURATION)

            # ── KPIs ────────────────────────────────
            total, dur_min, dur_avg, asr = compute_kpis(df_hist)

            st.markdown("### 📌 KPIs Globales")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📞 Total Llamadas",          f"{total:,}")
            k2.metric("⏱️ Duración Total (min)",    f"{dur_min:,.1f}")
            k3.metric("⏱️ Duración Promedio (seg)", f"{dur_avg:,.1f}")
            k4.metric("✅ ASR (Tasa de Respuesta)",  f"{asr:.1f} %")

            st.divider()

            # ── Gráficos ────────────────────────────
            g_left, g_right = st.columns(2)

            # Dona: distribución de estados
            with g_left:
                st.markdown("#### 🍩 Distribución de Estados")
                if col_exists(df_hist, COL_STATUS):
                    status_counts = (
                        df_hist[COL_STATUS]
                        .fillna("UNKNOWN")
                        .str.upper()
                        .value_counts()
                        .reset_index()
                    )
                    status_counts.columns = ["Estado", "Cantidad"]
                    fig_pie = px.pie(
                        status_counts,
                        names="Estado",
                        values="Cantidad",
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Bold,
                    )
                    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                    fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info(f"Columna `{COL_STATUS}` no disponible.")

            # Barras: Top 10 agentes
            with g_right:
                st.markdown("#### 🏆 Top 10 Agentes por Volumen")
                if col_exists(df_hist, COL_AGENT):
                    top_agents = (
                        df_hist[COL_AGENT]
                        .fillna("Sin agente")
                        .value_counts()
                        .head(10)
                        .reset_index()
                    )
                    top_agents.columns = ["Agente", "Llamadas"]
                    top_agents = top_agents.sort_values("Llamadas", ascending=True)
                    fig_bar = px.bar(
                        top_agents,
                        x="Llamadas",
                        y="Agente",
                        orientation="h",
                        color="Llamadas",
                        color_continuous_scale="Blues",
                        text="Llamadas",
                    )
                    fig_bar.update_traces(textposition="outside")
                    fig_bar.update_layout(
                        margin=dict(t=10, b=10, l=10, r=10),
                        coloraxis_showscale=False,
                        yaxis_title=None,
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info(f"Columna `{COL_AGENT}` no disponible.")

            st.divider()

            # ── Tabla por Agente ────────────────────
            st.markdown("### 👤 Resumen por Agente")
            if col_exists(df_hist, COL_AGENT):
                agg_dict: dict = {"_count": (COL_AGENT, "count")}
                if col_exists(df_hist, COL_DURATION):
                    agg_dict["Duración Total (seg)"] = (COL_DURATION, "sum")
                    agg_dict["Duración Promedio (seg)"] = (COL_DURATION, "mean")

                df_agent = (
                    df_hist.groupby(COL_AGENT)
                    .agg(**agg_dict)
                    .reset_index()
                    .rename(columns={COL_AGENT: "Agente", "_count": "Total Llamadas"})
                    .sort_values("Total Llamadas", ascending=False)
                )

                # Redondear columnas numéricas
                for col in ["Duración Total (seg)", "Duración Promedio (seg)"]:
                    if col in df_agent.columns:
                        df_agent[col] = df_agent[col].round(1)

                st.dataframe(
                    df_agent,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Total Llamadas":        st.column_config.NumberColumn(format="%d"),
                        "Duración Total (seg)":  st.column_config.NumberColumn(format="%.1f"),
                        "Duración Promedio (seg)": st.column_config.NumberColumn(format="%.1f"),
                    },
                )
            else:
                st.info(f"Columna `{COL_AGENT}` no disponible. Mostrando datos crudos:")
                st.dataframe(df_hist, use_container_width=True, hide_index=True)

            st.divider()

            # ── Tabla cruda completa ─────────────────
            with st.expander("📋 Ver todos los registros (tabla cruda)", expanded=False):
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                csv = df_hist.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Descargar CSV",
                    data=csv,
                    file_name=f"cdrs_{ds[:10]}_{de[:10]}.csv",
                    mime="text/csv",
                )
    else:
        st.info("👆 Selecciona un rango de fechas y presiona **Buscar en la API** para cargar los datos.")
