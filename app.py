import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import time

# ── Zona horaria Lima ──────────────────────────────────────────────────────────
TZ = ZoneInfo("America/Lima")
def now_lima(): return datetime.now(TZ).replace(tzinfo=None)

# ── Credenciales desde secrets ─────────────────────────────────────────────────
try:
    _U = st.secrets["CMW_USER"]
    _P = st.secrets["CMW_PASS"]
except Exception:
    st.error("⚠ Configura CMW_USER y CMW_PASS en .streamlit/secrets.toml")
    st.stop()

# ── Constantes ─────────────────────────────────────────────────────────────────
CENTRAL_ID = "8668106"
AGENTES = {
    "8668106": "Central Virtual",
    "8668109": "Alonso Loyola",
    "8668110": "Jose Luis Cahuana",
    "8668112": "Daniel Huayta",
    "8668111": "Deivy Chavez",
    "8668114": "Joe Villanueva",
    "8672537": "Victor Figueroa",
}
AGENTES_SIN_CENTRAL = {k: v for k, v in AGENTES.items() if k != CENTRAL_ID}
AGENTES_SIN_ID = {"Luz Goicochea"}

TURNOS = [
    {"dias":[0,1,2,3,4],"h_ini": 6,"h_fin":14,"agente":"Alonso Loyola"},
    {"dias":[0,1,2,3,4],"h_ini":14,"h_fin":22,"agente":"Jose Luis Cahuana"},
    {"dias":[0,1,2,3,4],"h_ini":22,"h_fin":30,"agente":"Deivy Chavez"},
    {"dias":[5,6],      "h_ini": 6,"h_fin":14,"agente":"Daniel Huayta"},
    {"dias":[5,6],      "h_ini":14,"h_fin":22,"agente":"Luz Goicochea"},
    {"dias":[5,6],      "h_ini":22,"h_fin":30,"agente":"Joe Villanueva"},
]

ESCENARIOS = {
    "atendida":              {"es":"✅ Atendida",            "color":"#22C55E"},
    "colgó_en_ivr":          {"es":"📵 Colgó en IVR",        "color":"#6B7280"},
    "colgó_timbrando":       {"es":"📵 Colgó timbrando",     "color":"#F59E0B"},
    "no_enrutada":           {"es":"🚫 No enrutada",          "color":"#8B5CF6"},
    "agente_no_disponible":  {"es":"🔴 No disponible",        "color":"#EF4444"},
    "no_respondió":          {"es":"🔔 No respondió",         "color":"#EF4444"},
    "múltiples_no_respuesta":{"es":"🔄 Múltiples intentos",   "color":"#F97316"},
    "rechazada":             {"es":"❌ Rechazada",             "color":"#EC4899"},
    "perdida":               {"es":"❌ Perdida",               "color":"#EF4444"},
}
END_REASONS = {
    "OK":"Completada","CANCELLED":"Cancelada","NO_ANSWER":"Sin respuesta",
    "TEMPORARILY_UNAVAILABLE":"No disponible","NOT_FOUND":"No encontrado",
    "DECLINE":"Rechazada","SERVICE_UNAVAILABLE":"Servicio no disponible",
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Supervisor · Soporte",page_icon="🎯",
                   layout="wide",initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'Outfit',sans-serif!important}
.stApp{background:#06080F}.stApp>header{background:transparent!important}
section[data-testid="stSidebar"]{background:#090B14!important;border-right:1px solid rgba(255,255,255,0.05)!important}
section[data-testid="stSidebar"] *{color:#7A8AA0!important}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] strong{color:#C8D8E8!important}
section[data-testid="stSidebar"] label{color:#3A5070!important;font-size:11px!important;letter-spacing:.5px;text-transform:uppercase}
section[data-testid="stSidebar"] input{background:#0F1525!important;border:1px solid rgba(80,120,200,.2)!important;color:#C8D8E8!important;font-family:'JetBrains Mono',monospace!important;font-size:13px!important}
section[data-testid="stSidebar"] .stButton button{width:100%;background:#0F1A2E!important;border:1px solid rgba(60,120,220,.35)!important;color:#6A9ADA!important;font-weight:500!important}
[data-testid="metric-container"]{background:#0C0F1C!important;border:1px solid rgba(255,255,255,0.05)!important;border-radius:12px!important;padding:16px 18px!important}
[data-testid="stMetricLabel"]{color:#2A4060!important;font-size:10px!important;letter-spacing:1.8px!important;text-transform:uppercase!important;font-family:'JetBrains Mono',monospace!important}
[data-testid="stMetricValue"]{color:#C8D8E8!important;font-size:26px!important;font-weight:300!important}
h1,h2,h3{color:#C8D8E8!important;font-family:'Outfit',sans-serif!important}
p,li{color:#7A8AA0!important}
.stTabs [data-baseweb="tab-list"]{background:transparent!important;gap:2px!important;border-bottom:1px solid rgba(255,255,255,0.05)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#2A4060!important;font-size:11px!important;font-weight:600!important;letter-spacing:1px!important;text-transform:uppercase!important;padding:10px 18px!important;border-bottom:2px solid transparent!important;border-radius:0!important}
.stTabs [aria-selected="true"]{color:#5A9AEA!important;border-bottom:2px solid #3A7ACA!important}
.stTabs [data-baseweb="tab-border"]{display:none!important}
.stTabs [data-baseweb="tab-panel"]{padding-top:22px!important}
.stDataFrame{border:1px solid rgba(255,255,255,0.05)!important;border-radius:10px!important}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:#1A2A40;border-radius:4px}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_dur(s):
    try:
        s = int(s or 0)
        if s <= 0: return "—"
        if s < 60: return f"{s}s"
        m, sec = divmod(s, 60)
        return f"{m}m {sec:02d}s" if sec else f"{m}m"
    except: return "—"

def safe_mean(df, col):
    """Retorna la media entera de df[col] para filas atendidas, o 0 si no hay datos."""
    try:
        if df is None or df.empty: return 0
        if col not in df.columns or "atendida" not in df.columns: return 0
        s = df[df["atendida"] == True][col].dropna()
        if len(s) == 0: return 0
        m = float(s.mean())
        return 0 if m != m else int(m)  # NaN check
    except: return 0

def norm_num(n):
    n = str(n or "").strip().replace("+","").replace(" ","").replace("-","")
    return n[-9:] if len(n) >= 9 else n

def agente_de_turno(dt):
    if pd.isna(dt): return "Sin turno"
    dow, h = dt.weekday(), dt.hour
    h_ext = h if h >= 6 else h + 24
    for t in TURNOS:
        if dow in t["dias"] and t["h_ini"] <= h_ext < t["h_fin"]: return t["agente"]
    dow_prev = (dow - 1) % 7
    for t in TURNOS:
        if dow_prev in t["dias"] and t["h_ini"] <= h_ext < t["h_fin"]: return t["agente"]
    return "Sin turno"

def esc_es(k): return ESCENARIOS.get(k,{}).get("es",k)
def esc_color(k): return ESCENARIOS.get(k,{}).get("color","#6B7280")

# ── API ────────────────────────────────────────────────────────────────────────
PAGE_SIZE = 1000; CHUNK_DAYS = 10

def _fetch_chunk(ds, de):
    base = {"username":_U,"password":_P,"format":"json","dateStart":ds,"dateEnd":de}
    all_cdrs, ini = [], 0
    while True:
        r = requests.get("https://callmyway.com/getCdrs.php",
                         params={**base,"ini":ini,"cant":PAGE_SIZE},timeout=30)
        r.raise_for_status()
        data = r.json()
        page = data.get("cdrs",data) if isinstance(data,dict) else data
        if not page: break
        all_cdrs.extend(page)
        if len(page) < PAGE_SIZE: break
        ini += PAGE_SIZE
    return all_cdrs

def fetch_cdrs(date_start=None,date_end=None,live=False,progress_cb=None):
    if live:
        try:
            r = requests.get("https://callmyway.com/getCdrs.php",
                params={"username":_U,"password":_P,"live":1,"fullAccount":1,"format":"json"},timeout=20)
            r.raise_for_status()
            data = r.json()
            cdrs = data.get("cdrs",data) if isinstance(data,dict) else data
            return pd.DataFrame(cdrs or []), None
        except Exception as e: return None, str(e)

    try:
        dt_ini = datetime.strptime(date_start,"%Y-%m-%d %H:%M:%S")
        dt_fin = datetime.strptime(date_end,  "%Y-%m-%d %H:%M:%S")
    except Exception as e: return None, f"Fechas inválidas: {e}"

    chunks, cursor = [], dt_ini
    while cursor < dt_fin:
        chunk_end = min(cursor+timedelta(days=CHUNK_DAYS),dt_fin)
        chunks.append((cursor,chunk_end)); cursor = chunk_end

    all_cdrs = []
    for i,(c_ini,c_fin) in enumerate(chunks):
        if progress_cb: progress_cb(i/len(chunks),
            f"Chunk {i+1}/{len(chunks)} · {c_ini.strftime('%d/%m')}→{c_fin.strftime('%d/%m')} · {len(all_cdrs):,} registros")
        try: all_cdrs.extend(_fetch_chunk(c_ini.strftime("%Y-%m-%d %H:%M:%S"),c_fin.strftime("%Y-%m-%d %H:%M:%S")))
        except: pass
    if progress_cb: progress_cb(1.0,f"Completado · {len(all_cdrs):,} registros")
    return (pd.DataFrame(all_cdrs) if all_cdrs else pd.DataFrame()), None

# ── Clasificación entrantes ────────────────────────────────────────────────────
def clasificar_entrantes(df_inc):
    if df_inc is None or df_inc.empty: return pd.DataFrame()
    agentes_reales = set(AGENTES_SIN_CENTRAL.keys())
    df_inc = df_inc.copy()
    for col in ["dnis_user","ani_user","original_callid","ref_callid","ani","dnis"]:
        if col in df_inc.columns:
            df_inc[col] = df_inc[col].astype(str).str.strip().replace(
                {"None":"","nan":"","null":"","<NA>":""})

    df_trn = df_inc[df_inc["dnis_user"] == CENTRAL_ID]
    df_ag  = df_inc[df_inc["dnis_user"].isin(agentes_reales)]

    trn_by_ref = {}
    for _,row in df_trn.iterrows():
        ref = str(row.get("ref_callid","")).strip()
        if ref: trn_by_ref[ref] = row

    ag_orig_set = set(df_ag["original_callid"].unique()) if not df_ag.empty else set()
    resultados = []

    def _append(orig_cid,detect_time,ani_cliente,atendida,agente_id,
                duracion,ring_total,n_intentos,end_reason,escenario):
        resultados.append({
            "original_callid":orig_cid,"detect_time":detect_time,
            "numero_cliente":ani_cliente,"atendida":atendida,
            "agente":AGENTES.get(str(agente_id),"Sin atender") if agente_id else "Sin atender",
            "agente_id":agente_id,"duracion":duracion,"espera_total":ring_total,
            "n_intentos":n_intentos,"end_reason":end_reason,
            "end_reason_es":END_REASONS.get(end_reason,end_reason),
            "escenario":escenario,"escenario_es":esc_es(escenario),
            "hora":detect_time.hour if pd.notna(detect_time) else None,
            "fecha":detect_time.date() if pd.notna(detect_time) else None,
        })

    for orig_cid,ag_grp in (df_ag.groupby("original_callid") if not df_ag.empty else []):
        trunk = trn_by_ref.get(orig_cid)
        if trunk is not None:
            ani_cliente = str(trunk.get("ani","—") or "—")
            detect_time = min(trunk.get("detect_time"),ag_grp["detect_time"].min())
        else:
            ani_val = ag_grp["ani"].replace("",pd.NA).dropna()
            ani_cliente = str(ani_val.iloc[0]) if not ani_val.empty else "—"
            detect_time = ag_grp["detect_time"].min()

        ring_total = int(ag_grp["ring_time"].apply(lambda x: max(0,int(x or 0))).sum())
        n_intentos = len(ag_grp)
        contestado = ag_grp[ag_grp["duration"] > 0]
        if not contestado.empty:
            best = contestado.loc[contestado["duration"].idxmax()]
            _append(orig_cid,detect_time,ani_cliente,True,str(best["dnis_user"]),
                    int(best["duration"]),ring_total,n_intentos,
                    str(best.get("end_reason","OK") or "OK"),"atendida")
        else:
            ers = ag_grp["end_reason"].replace("",pd.NA).dropna()
            top_er = ers.mode().iloc[0] if not ers.empty else "UNKNOWN"
            if top_er == "CANCELLED": esc = "colgó_timbrando"
            elif top_er in ("TEMPORARILY_UNAVAILABLE","NOT_FOUND","SERVICE_UNAVAILABLE"): esc = "agente_no_disponible"
            elif top_er == "NO_ANSWER": esc = "múltiples_no_respuesta" if n_intentos>1 else "no_respondió"
            elif top_er == "DECLINE": esc = "rechazada"
            else: esc = "perdida"
            _append(orig_cid,detect_time,ani_cliente,False,None,0,ring_total,n_intentos,top_er,esc)

    for _,trn_row in (df_trn.iterrows() if not df_trn.empty else []):
        ref_cid = str(trn_row.get("ref_callid","")).strip()
        if ref_cid in ag_orig_set: continue
        orig_cid = str(trn_row.get("original_callid","")).strip()
        detect_time = trn_row.get("detect_time")
        ani_cliente = str(trn_row.get("ani","—") or "—")
        er = str(trn_row.get("end_reason","UNKNOWN") or "UNKNOWN")
        esc = "colgó_en_ivr" if er=="CANCELLED" else \
              "agente_no_disponible" if er in ("TEMPORARILY_UNAVAILABLE","NOT_FOUND","SERVICE_UNAVAILABLE") else \
              "no_enrutada"
        _append(orig_cid,detect_time,ani_cliente,False,None,0,0,0,er,esc)

    if not resultados: return pd.DataFrame()
    df = pd.DataFrame(resultados)
    df["agente_turno"] = df["detect_time"].apply(agente_de_turno)
    def calc_resp(r):
        if r["agente_turno"] in AGENTES_SIN_ID: return r["agente_turno"]
        return r["agente"] if r["atendida"] else r["agente_turno"]
    df["responsable"] = df.apply(calc_resp,axis=1)
    df.loc[df["agente_turno"].isin(AGENTES_SIN_ID),["atendida","agente"]] = [False,"Sin atender"]
    return df

# ── Procesamiento ──────────────────────────────────────────────────────────────
def procesar(df_raw):
    if df_raw is None or df_raw.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    df = df_raw.copy()
    for col in ["duration","ring_time"]:
        df[col] = pd.to_numeric(df.get(col,0),errors="coerce").fillna(0).astype(int)
    for col in ["detect_time","connect_time","disconnect_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col].replace("",None),errors="coerce")
    for col in ["ani_user","dnis_user","ref_callid","original_callid"]:
        if col in df.columns: df[col] = df[col].astype(str).str.strip()

    mask_sal = (
        (df["type"]=="outgoing") &
        (df["ani_user"].isin(AGENTES_SIN_CENTRAL.keys())) &
        (~df["dnis"].astype(str).str.startswith("833"))
    )
    df_sal = df[mask_sal].copy()
    df_sal["agente"]        = df_sal["ani_user"].map(AGENTES)
    df_sal["numero_cliente"]= df_sal["dnis"].astype(str)
    df_sal["atendida"]      = df_sal["duration"] > 0
    df_sal["hora"]          = df_sal["detect_time"].dt.hour
    df_sal["fecha"]         = df_sal["detect_time"].dt.date
    df_sal["end_reason_es"] = df_sal["end_reason"].map(END_REASONS).fillna(df_sal["end_reason"])

    df_inc = df[df["type"]=="incoming"].copy()
    df_ent = clasificar_entrantes(df_inc)
    return df_ent, df_sal, df

# ── Cumplimiento callbacks ─────────────────────────────────────────────────────
VENTANA_CB = pd.Timedelta(minutes=5)
ESC_RESPONSABLE = {"no_respondió","múltiples_no_respuesta","agente_no_disponible","rechazada","colgó_timbrando","perdida"}

def calcular_cumplimiento(df_ent, df_sal):
    if df_ent is None or df_ent.empty: return pd.DataFrame()
    if "escenario" not in df_ent.columns: return pd.DataFrame()
    perdidas = df_ent[(df_ent["atendida"]==False) & (df_ent["escenario"].isin(ESC_RESPONSABLE))].copy().sort_values("detect_time")
    if perdidas.empty: return pd.DataFrame()

    df_sal2 = df_sal.copy() if not df_sal.empty else pd.DataFrame()
    df_ent2 = df_ent.copy()
    if not df_sal2.empty and "numero_cliente" in df_sal2.columns:
        df_sal2["_num"] = df_sal2["numero_cliente"].apply(norm_num)
    if "numero_cliente" in df_ent2.columns:
        df_ent2["_num"] = df_ent2["numero_cliente"].apply(norm_num)

    resultados = []
    for _,row in perdidas.iterrows():
        t0 = row["detect_time"]
        if pd.isna(t0): continue
        num = norm_num(row["numero_cliente"])
        t_lim = t0 + VENTANA_CB
        cb_sal = pd.DataFrame()
        if not df_sal2.empty and "detect_time" in df_sal2.columns:
            cb_sal = df_sal2[(df_sal2["_num"]==num)&(df_sal2["detect_time"]>t0)&
                             (df_sal2["detect_time"]<=t_lim)&(df_sal2["atendida"]==True)]
        cb_ent = pd.DataFrame()
        if "detect_time" in df_ent2.columns:
            cb_ent = df_ent2[(df_ent2["_num"]==num)&(df_ent2["detect_time"]>t0)&
                             (df_ent2["detect_time"]<=t_lim)&(df_ent2["atendida"]==True)]
        if not cb_sal.empty:
            tipo="📞 Agente llamó"; t_cb=cb_sal["detect_time"].min()
            ag_cb=cb_sal.iloc[0].get("agente","—"); seg=int((t_cb-t0).total_seconds())
        elif not cb_ent.empty:
            tipo="↩️ Cliente volvió"; t_cb=cb_ent["detect_time"].min()
            ag_cb=cb_ent.iloc[0].get("agente","—"); seg=int((t_cb-t0).total_seconds())
        else:
            tipo="❌ Sin resolución"; t_cb=None; ag_cb="—"; seg=None
        resultados.append({
            "Fecha/Hora":t0,"Número":row["numero_cliente"],
            "Responsable":row.get("responsable","—"),"Escenario":esc_es(row.get("escenario","")),
            "Resolución":tipo,"Tiempo respuesta":fmt_dur(seg) if seg is not None else "> 5 min",
            "Agente resolvió":ag_cb,"Cumplimiento":tipo!="❌ Sin resolución","_seg":seg,
        })
    return pd.DataFrame(resultados)

# ── Sidebar ────────────────────────────────────────────────────────────────────
hoy_lima = now_lima()

# Inicializar session state para fechas
if "fi" not in st.session_state: st.session_state.fi = (hoy_lima - timedelta(days=1)).date()
if "ff" not in st.session_state: st.session_state.ff = hoy_lima.date()

with st.sidebar:
    st.markdown("## 🎯 Supervisor · Soporte")
    st.markdown(f"""<div style='background:#0C0F1C;border:1px solid rgba(80,120,200,.15);border-radius:8px;
        padding:10px 12px;margin-bottom:16px'>
        <div style='color:#1A3050;font-size:10px;font-family:JetBrains Mono,monospace;letter-spacing:.5px'>CUENTA</div>
        <div style='color:#4A7ABA;font-size:13px;font-family:JetBrains Mono,monospace;margin-top:2px'>{_U}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")
    fi = st.date_input("Desde",      value=st.session_state.fi, key="fi")
    hi = st.time_input("Hora inicio", value=datetime.strptime("00:00","%H:%M").time())
    ff = st.date_input("Hasta",       value=st.session_state.ff, key="ff")
    hf = st.time_input("Hora fin",    value=datetime.strptime("23:59","%H:%M").time())
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1: btn_ok  = st.button("⟳ Consultar",type="primary",use_container_width=True)
    with c2: btn_hoy = st.button("Hoy",use_container_width=True)
    st.markdown("---")
    live_mode = st.toggle("🔴 Modo en vivo",value=False)
    intervalo = st.slider("Refrescar cada (seg)",5,60,15) if live_mode else 15

# ── Sesión ─────────────────────────────────────────────────────────────────────
for k in ["df_ent","df_sal","df_raw","df_live_raw","label","error","loaded"]:
    if k not in st.session_state:
        st.session_state[k] = None if k!="loaded" else False

def cargar(df_raw, label):
    df_e,df_s,df_r = procesar(df_raw)
    st.session_state.update(df_ent=df_e,df_sal=df_s,df_raw=df_r,
                             df_live_raw=None,label=label,error=None,loaded=True)

def cargar_live(df_raw, label):
    st.session_state.update(df_live_raw=df_raw,label=label,error=None,loaded=True)

# ── Carga ──────────────────────────────────────────────────────────────────────
if live_mode:
    df_raw_live,err = fetch_cdrs(live=True)
    if err: st.error(f"⚠ {err}"); st.stop()
    cargar_live(df_raw_live,f"EN VIVO · {hoy_lima.strftime('%H:%M:%S')}")

elif btn_hoy:
    # Forzar fechas a hoy en session state
    st.session_state.fi = hoy_lima.date()
    st.session_state.ff = hoy_lima.date()
    ds = hoy_lima.replace(hour=0,minute=0,second=0,microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    de = hoy_lima.strftime("%Y-%m-%d %H:%M:%S")
    with st.spinner("Consultando hoy..."):
        df_raw_h,err = fetch_cdrs(date_start=ds,date_end=de)
    if err: st.session_state.error = err
    else:   cargar(df_raw_h,f"Hoy {hoy_lima.strftime('%d/%m/%Y')} · desde las 00:00")
    st.rerun()

elif btn_ok:
    ds = datetime.combine(fi,hi).strftime("%Y-%m-%d %H:%M:%S")
    de = datetime.combine(ff,hf).strftime("%Y-%m-%d %H:%M:%S")
    pb = st.progress(0,text="Iniciando consulta…")
    df_raw_h,err = fetch_cdrs(date_start=ds,date_end=de,
                               progress_cb=lambda p,m: pb.progress(p,text=m))
    pb.empty()
    if err: st.session_state.error = err
    else:   cargar(df_raw_h,f"{fi.strftime('%d/%m')} – {ff.strftime('%d/%m/%Y')}")

if st.session_state.error: st.error(f"⚠ {st.session_state.error}"); st.stop()
if not st.session_state.loaded: st.info("Configura el período y pulsa **Consultar**."); st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MODO EN VIVO
# ══════════════════════════════════════════════════════════════════════════════
if live_mode:
    df_live = st.session_state.get("df_live_raw",pd.DataFrame())
    lbl     = st.session_state.label
    llamadas_activas = []

    if df_live is not None and not df_live.empty:
        df_lv = df_live.copy()
        for col in ["dnis_user","ani_user","original_callid","ref_callid","ani","dnis","connect_time","disconnect_time"]:
            if col in df_lv.columns:
                df_lv[col] = df_lv[col].astype(str).str.strip().replace({"None":"","nan":"","null":"","<NA>":""})

        agentes_reales = set(AGENTES_SIN_CENTRAL.keys())
        df_lv_trn = df_lv[df_lv["dnis_user"] == CENTRAL_ID]
        df_lv_ag  = df_lv[df_lv["dnis_user"].isin(agentes_reales)]

        ag_by_orig = {}
        for _,row in df_lv_ag.iterrows():
            orig = row.get("original_callid","")
            if not orig: continue
            if orig not in ag_by_orig or int(row.get("duration",0) or 0) > int(ag_by_orig[orig].get("duration",0) or 0):
                ag_by_orig[orig] = row

        procesados = set()
        for _,trn in df_lv_trn.iterrows():
            disc_trn = str(trn.get("disconnect_time","") or "")
            if disc_trn not in ("","None","null","nan"): continue
            ref_cid  = str(trn.get("ref_callid","") or "")
            trn_orig = str(trn.get("original_callid","") or "")
            if trn_orig in procesados: continue
            procesados.add(trn_orig)

            ag_row = ag_by_orig.get(ref_cid)
            if ag_row is not None:
                disc_ag = str(ag_row.get("disconnect_time","") or "")
                if disc_ag not in ("","None","null","nan"): continue  # agente ya colgó

            ani_cliente  = str(trn.get("ani","-") or "-")
            dnis_marcado = str(trn.get("dnis","-") or "-")

            if ag_row is not None:
                ag_id    = str(ag_row.get("dnis_user",""))
                ag_dur   = int(ag_row.get("duration",0) or 0)
                ag_ct    = str(ag_row.get("connect_time","") or "")
                ag_ring  = max(0,int(ag_row.get("ring_time",0) or 0))
                connected= ag_ct not in ("","None","null","nan")
                if connected and ag_dur > 0:
                    estado="en_llamada"; duracion=ag_dur; connect_time=ag_ct
                else:
                    estado="timbrando"; duracion=0; connect_time=""
                agente_conocido=True
            else:
                ag_id=""; ag_ring=0
                estado="conectando"; duracion=int(trn.get("duration",0) or 0)
                connect_time=str(trn.get("connect_time","") or "")
                agente_conocido=False

            llamadas_activas.append({
                "ag_id":ag_id,"agente":AGENTES.get(ag_id,"Por identificar") if ag_id else "Por identificar",
                "numero_cliente":ani_cliente,"dnis_marcado":dnis_marcado,
                "duracion":duracion,"ring_time":ag_ring,"estado":estado,
                "connect_time":connect_time,"agente_conocido":agente_conocido,
            })

    ag_ocupados  = {c["ag_id"] for c in llamadas_activas if c["ag_id"]}
    n_activas    = len(llamadas_activas)
    n_conectadas = sum(1 for c in llamadas_activas if c["estado"]=="en_llamada")
    n_timbrando  = sum(1 for c in llamadas_activas if c["estado"]=="timbrando")
    n_libres     = len(AGENTES_SIN_CENTRAL)-len(ag_ocupados & set(AGENTES_SIN_CENTRAL))

    st.markdown(f"""<div style='display:flex;align-items:center;justify-content:space-between;padding:14px 18px;
        background:#0C0F1C;border:1px solid rgba(239,68,68,.2);border-radius:12px;margin-bottom:20px'>
      <div style='display:flex;align-items:center;gap:14px'>
        <div style='width:10px;height:10px;border-radius:50%;background:#EF4444;animation:blink 1s infinite'></div>
        <span style='color:#C8D8E8;font-size:17px;font-weight:300'>Monitoreo en Vivo</span>
        <span style='color:#1A3050;font-size:12px;font-family:JetBrains Mono,monospace'>{lbl}</span>
      </div>
      <div style='display:flex;gap:20px;font-family:JetBrains Mono,monospace;font-size:12px'>
        <span style='color:#22C55E'>{n_conectadas} en llamada</span>
        <span style='color:#EAB308'>{n_timbrando} timbrando</span>
        <span style='color:#1A3050'>refresca cada {intervalo}s</span>
      </div></div>""", unsafe_allow_html=True)

    kc1,kc2,kc3,kc4 = st.columns(4)
    kc1.metric("Llamadas activas",n_activas)
    kc2.metric("En conversación", n_conectadas)
    kc3.metric("Timbrando",       n_timbrando)
    kc4.metric("Agentes libres",  n_libres)
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("#### 👥 Estado de agentes")
    cols_ag = st.columns(3)
    for i,(ag_id,ag_nombre) in enumerate(AGENTES_SIN_CENTRAL.items()):
        llamada = next((c for c in llamadas_activas if c["ag_id"]==ag_id),None)
        if llamada is None:
            dot,borde="#22C55E","rgba(34,197,94,.2)"
            estado_h="<span style='color:#166534;font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>🟢 LIBRE</span>"
            det_h="<div style='color:#0F2030;font-size:12px;margin-top:10px;font-family:JetBrains Mono,monospace'>Sin actividad</div>"
        elif llamada["estado"]=="timbrando":
            dot,borde="#EAB308","rgba(234,179,8,.3)"
            estado_h="<span style='color:#92400E;font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace;animation:blink 1s infinite'>🟡 TIMBRANDO</span>"
            det_h=f"""<div style='margin-top:10px;background:rgba(234,179,8,.07);border-radius:8px;padding:10px'>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace'>
                <span style='color:#0F2030'>Cliente</span><span style='color:#C8D8E8'>{llamada['numero_cliente']}</span></div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>DID</span><span style='color:#7A9ABA'>{llamada['dnis_marcado']}</span></div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Timbrando</span><span style='color:#EAB308'>{llamada['ring_time']}s</span></div></div>"""
        else:
            dot,borde="#EF4444","rgba(239,68,68,.3)"
            estado_h="<span style='color:#7F1D1D;font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>🔴 EN LLAMADA</span>"
            m,s=divmod(llamada["duracion"],60); dur_f=f"{m}:{str(s).zfill(2)}"
            badge="" if llamada["agente_conocido"] else " <span style='font-size:9px;color:#92400E;background:rgba(234,179,8,.1);padding:2px 6px;border-radius:4px'>identificando…</span>"
            det_h=f"""<div style='margin-top:10px;background:rgba(239,68,68,.07);border-radius:8px;padding:10px'>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace'>
                <span style='color:#0F2030'>Cliente</span><span style='color:#C8D8E8'>{llamada['numero_cliente']}</span></div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>DID</span><span style='color:#7A9ABA'>{llamada['dnis_marcado']}</span></div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Duración</span><span style='color:#EF4444;font-weight:600'>{dur_f}</span></div>
              <div style='display:flex;justify-content:space-between;align-items:center;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Agente</span><span style='color:#7A9ABA'>{llamada['agente']}{badge}</span></div>
              {"<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'><span style='color:#0F2030'>Conectó</span><span style='color:#7A9ABA'>"+llamada['connect_time'][:16]+"</span></div>" if llamada["connect_time"] else ""}
            </div>"""
        with cols_ag[i%3]:
            st.markdown(f"""<div style='background:#0C0F1C;border:1px solid {borde};border-top:3px solid {dot};
                border-radius:10px;padding:16px;margin-bottom:14px'>
              <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                <div><div style='color:#C8D8E8;font-size:14px;font-weight:500'>{ag_nombre}</div>
                <div style='color:#1A3050;font-size:10px;font-family:JetBrains Mono,monospace;margin-top:2px'>ID {ag_id}</div></div>
                <div>{estado_h}</div></div>{det_h}</div>""", unsafe_allow_html=True)

    sin_asignar = [c for c in llamadas_activas if not c["agente_conocido"]]
    if sin_asignar:
        st.markdown("---"); st.markdown("#### 📞 Llamadas en cola / por asignar")
        for c in sin_asignar:
            m,s=divmod(c["duracion"],60); df_=f"{m}:{str(s).zfill(2)}" if c["duracion"]>0 else "—"
            st.markdown(f"""<div style='background:#0C0F1C;border:1px solid rgba(234,179,8,.25);border-left:3px solid #EAB308;
                border-radius:10px;padding:14px 18px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center'>
              <div style='font-family:JetBrains Mono,monospace'>
                <div style='color:#C8D8E8;font-size:14px'>📞 {c['numero_cliente']}</div>
                <div style='color:#1A3050;font-size:11px;margin-top:4px'>DID: {c['dnis_marcado']} · Conectó: {c['connect_time'][:16] if c['connect_time'] else '—'}</div>
              </div>
              <div style='text-align:right;font-family:JetBrains Mono,monospace'>
                <div style='color:#EAB308;font-size:18px;font-weight:300'>{df_}</div>
                <div style='color:#92400E;font-size:10px'>agente identificando…</div></div></div>""", unsafe_allow_html=True)
    elif n_activas==0:
        st.markdown("""<div style='text-align:center;padding:40px;background:#0C0F1C;
            border:1px solid rgba(255,255,255,0.04);border-radius:12px;margin-top:8px'>
          <div style='font-size:36px;margin-bottom:10px'>📵</div>
          <div style='color:#1A3050;font-size:14px'>No hay llamadas activas en este momento</div>
          <div style='color:#0F2030;font-size:11px;margin-top:6px;font-family:JetBrains Mono,monospace'>Todos los agentes libres</div>
        </div>""", unsafe_allow_html=True)

    time.sleep(intervalo); st.rerun(); st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MODO HISTÓRICO
# ══════════════════════════════════════════════════════════════════════════════
df_ent = st.session_state.df_ent if st.session_state.df_ent is not None else pd.DataFrame()
df_sal = st.session_state.df_sal if st.session_state.df_sal is not None else pd.DataFrame()
df_raw = st.session_state.df_raw
lbl    = st.session_state.label

if df_ent.empty and df_sal.empty: st.warning("Sin registros para el período."); st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
n_ent     = len(df_ent)
n_ent_at  = int(df_ent["atendida"].sum())      if not df_ent.empty else 0
n_ent_per = n_ent - n_ent_at
pct_at    = round(n_ent_at/n_ent*100)           if n_ent else 0
n_sal     = len(df_sal)
n_sal_ok  = int((df_sal["atendida"]==True).sum()) if not df_sal.empty else 0
avg_dur   = safe_mean(df_ent,"duracion")
avg_esp   = safe_mean(df_ent,"espera_total")

P = dict(paper_bgcolor="#06080F",plot_bgcolor="#06080F",
         font=dict(color="#2A4060",family="Outfit"),margin=dict(t=10,b=30,l=5,r=5))

st.markdown(f"""<div style='display:flex;align-items:flex-end;justify-content:space-between;
    padding:0 0 18px;border-bottom:1px solid rgba(255,255,255,.04);margin-bottom:22px'>
  <div><div style='font-size:22px;font-weight:300;color:#C8D8E8'>Panel de Supervisor · Soporte</div>
    <div style='font-size:11px;color:#1A3050;font-family:JetBrains Mono,monospace;margin-top:4px'>
      {lbl} · {n_ent} entrantes · {n_sal} salientes</div></div>
  <div style='font-size:11px;color:#0F2030;font-family:JetBrains Mono,monospace'>{_U} · CallMyWay</div>
</div>""", unsafe_allow_html=True)

c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
c1.metric("Entrantes",       f"{n_ent:,}")
c2.metric("Atendidas",       f"{n_ent_at:,}",  f"{pct_at}%")
c3.metric("Perdidas",        f"{n_ent_per:,}", f"-{100-pct_at}%")
c4.metric("% Atención",      f"{pct_at}%")
c5.metric("Salientes",       f"{n_sal:,}")
c6.metric("Sal. conectadas", f"{n_sal_ok:,}")
c7.metric("Dur. prom.",      fmt_dur(avg_dur))
c8.metric("Espera prom.",    fmt_dur(avg_esp))
st.markdown("<br>",unsafe_allow_html=True)

tabs = st.tabs(["VISIÓN GENERAL","ENTRANTES","SALIENTES","AGENTES","TURNOS","SEGUIMIENTO","CLIENTES","REGISTROS"])
tab_ov,tab_ent,tab_sal,tab_ag,tab_tur,tab_seg,tab_cl,tab_raw_t = tabs

# ── TAB 0: VISIÓN GENERAL ──────────────────────────────────────────────────────
with tab_ov:
    r1,r2,r3 = st.columns([1.1,1.4,1.5])
    with r1:
        fig_d = go.Figure(go.Pie(labels=["Atendidas","Perdidas"],values=[n_ent_at,n_ent_per],
            hole=0.7,marker=dict(colors=["#166534","#7F1D1D"],line=dict(width=0)),textinfo="none"))
        fig_d.add_annotation(text=f"<b>{pct_at}%</b>",x=0.5,y=0.56,font=dict(size=30,color="#C8D8E8"),showarrow=False)
        fig_d.add_annotation(text="atención",x=0.5,y=0.40,font=dict(size=12,color="#2A4060"),showarrow=False)
        fig_d.update_layout(height=200,showlegend=False,**P)
        st.plotly_chart(fig_d,use_container_width=True)
        st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:-10px'>
          <div style='background:#0C0F1C;border:1px solid rgba(34,197,94,.15);border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#166534;font-size:10px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>ATENDIDAS</div>
            <div style='color:#22C55E;font-size:22px;font-weight:300'>{n_ent_at}</div></div>
          <div style='background:#0C0F1C;border:1px solid rgba(239,68,68,.15);border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#7F1D1D;font-size:10px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>PERDIDAS</div>
            <div style='color:#EF4444;font-size:22px;font-weight:300'>{n_ent_per}</div></div>
        </div>""",unsafe_allow_html=True)
    with r2:
        if not df_ent.empty and "hora" in df_ent.columns:
            hd=df_ent.groupby(["hora","atendida"]).size().reset_index(name="n")
            hd["estado"]=hd["atendida"].map({True:"Atendida",False:"Perdida"})
            fig_h=px.bar(hd,x="hora",y="n",color="estado",
                color_discrete_map={"Atendida":"#166534","Perdida":"#7F1D1D"},barmode="stack")
            fig_h.update_layout(height=240,**P,
                xaxis=dict(title="Hora",dtick=1,gridcolor="rgba(255,255,255,.03)",tickfont_size=10),
                yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),bargap=0.15)
            fig_h.update_traces(marker_line_width=0)
            st.plotly_chart(fig_h,use_container_width=True)
    with r3:
        if not df_ent.empty and "escenario" in df_ent.columns:
            ec=df_ent["escenario"].value_counts().reset_index()
            ec.columns=["esc","n"]; ec["label"]=ec["esc"].apply(esc_es); ec["color"]=ec["esc"].apply(esc_color)
            ec=ec.sort_values("n",ascending=True)
            fig_ec=go.Figure(go.Bar(x=ec["n"],y=ec["label"],orientation="h",
                marker_color=ec["color"],marker_line_width=0,
                text=ec["n"],textposition="outside",textfont=dict(size=11,color="#2A4060")))
            fig_ec.update_layout(height=240,**P,
                title=dict(text="Escenarios de llamada",font=dict(size=12,color="#2A4060"),x=0),
                xaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""))
            st.plotly_chart(fig_ec,use_container_width=True)
    if not df_ent.empty and "fecha" in df_ent.columns:
        st.markdown("---")
        daily=df_ent.groupby(["fecha","atendida"]).size().reset_index(name="n")
        daily["estado"]=daily["atendida"].map({True:"Atendida",False:"Perdida"})
        if len(daily["fecha"].unique())>1:
            fig_ev=px.area(daily,x="fecha",y="n",color="estado",
                color_discrete_map={"Atendida":"#166534","Perdida":"#7F1D1D"})
            fig_ev.update_traces(opacity=0.7,line_width=1.5)
            fig_ev.update_layout(height=200,**P,
                xaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.25,font_color="#2A4060"),
                title=dict(text="Evolución diaria",font=dict(size=12,color="#2A4060"),x=0))
            st.plotly_chart(fig_ev,use_container_width=True)

# ── TAB 1: ENTRANTES ───────────────────────────────────────────────────────────
with tab_ent:
    if df_ent.empty: st.info("Sin llamadas entrantes.")
    else:
        fc1,fc2,fc3,fc4=st.columns([2,1,1,1])
        with fc1: busq=st.text_input("🔍 Buscar número",placeholder="519…",key="busq_ent")
        with fc2: f_est=st.selectbox("Estado",["Todos","Atendidas","Perdidas"],key="fest_ent")
        with fc3:
            esc_opts=["Todos"]+sorted(df_ent["escenario_es"].dropna().unique().tolist()) if "escenario_es" in df_ent.columns else ["Todos"]
            f_esc=st.selectbox("Escenario",esc_opts,key="fesc_ent")
        with fc4:
            ag_opts=["Todos"]+sorted(df_ent["agente"].dropna().unique().tolist())
            f_ag=st.selectbox("Agente",ag_opts,key="fag_ent")
        dv=df_ent.copy()
        if busq: dv=dv[dv["numero_cliente"].str.contains(busq,na=False)]
        if f_est=="Atendidas": dv=dv[dv["atendida"]==True]
        elif f_est=="Perdidas": dv=dv[dv["atendida"]==False]
        if f_esc!="Todos" and "escenario_es" in dv.columns: dv=dv[dv["escenario_es"]==f_esc]
        if f_ag!="Todos": dv=dv[dv["agente"]==f_ag]
        cols_t=[c for c in ["detect_time","numero_cliente","escenario_es","agente","responsable",
                             "agente_turno","duracion","espera_total","n_intentos"] if c in dv.columns]
        ds=dv[cols_t].copy()
        for col,fn in [("duracion",fmt_dur),("espera_total",fmt_dur)]:
            if col in ds.columns: ds[col]=ds[col].apply(fn)
        ds=ds.rename(columns={"detect_time":"Fecha/Hora","numero_cliente":"Número","escenario_es":"Escenario",
            "agente":"Contestó","responsable":"Responsable","agente_turno":"Turno",
            "duracion":"Duración","espera_total":"Espera","n_intentos":"Intentos"})
        st.caption(f"{len(dv):,} llamadas mostradas")
        st.dataframe(ds,use_container_width=True,height=460,hide_index=True)
        ec1,ec2=st.columns(2)
        with ec1: st.download_button("⬇ Exportar entrantes",data=df_ent.to_csv(index=False).encode("utf-8-sig"),file_name=f"entrantes_{hoy_lima.strftime('%Y%m%d')}.csv",mime="text/csv")
        with ec2: st.download_button("⬇ Exportar perdidas",data=df_ent[df_ent["atendida"]==False].to_csv(index=False).encode("utf-8-sig"),file_name=f"perdidas_{hoy_lima.strftime('%Y%m%d')}.csv",mime="text/csv")

# ── TAB 2: SALIENTES ───────────────────────────────────────────────────────────
with tab_sal:
    if df_sal.empty: st.info("Sin llamadas salientes.")
    else:
        s1,s2,s3,s4=st.columns(4)
        dur_s=df_sal[df_sal["atendida"]==True]["duration"].dropna()
        s1.metric("Total salientes", f"{n_sal:,}")
        s2.metric("Conectadas",      f"{n_sal_ok:,}",f"{round(n_sal_ok/n_sal*100) if n_sal else 0}%")
        s3.metric("No conectadas",   f"{n_sal-n_sal_ok:,}")
        s4.metric("Duración prom.",  fmt_dur(int(dur_s.mean()) if len(dur_s) else 0))
        st.markdown("<br>",unsafe_allow_html=True)
        sc1,sc2=st.columns(2)
        with sc1:
            ag_s=df_sal.groupby(["agente","atendida"]).size().reset_index(name="n")
            ag_s["estado"]=ag_s["atendida"].map({True:"Conectada",False:"No conectada"})
            fig_s=px.bar(ag_s,x="agente",y="n",color="estado",
                color_discrete_map={"Conectada":"#1D4ED8","No conectada":"#374151"},barmode="stack")
            fig_s.update_layout(height=260,**P,xaxis_title="",yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),
                title=dict(text="Salientes por agente",font=dict(size=12,color="#2A4060"),x=0))
            fig_s.update_traces(marker_line_width=0); st.plotly_chart(fig_s,use_container_width=True)
        with sc2:
            er_s=df_sal["end_reason"].value_counts().reset_index()
            er_s.columns=["r","n"]; er_s["label"]=er_s["r"].map(END_REASONS).fillna(er_s["r"])
            fig_ers=go.Figure(go.Bar(x=er_s["n"],y=er_s["label"],orientation="h",
                marker_color="#1D4ED8",marker_line_width=0,text=er_s["n"],textposition="outside",textfont=dict(size=11,color="#2A4060")))
            fig_ers.update_layout(height=260,**P,title=dict(text="Resultado salientes",font=dict(size=12,color="#2A4060"),x=0),
                xaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""))
            st.plotly_chart(fig_ers,use_container_width=True)
        busq_s=st.text_input("🔍 Buscar número",key="busq_sal")
        dvs=df_sal[df_sal["numero_cliente"].str.contains(busq_s,na=False)].copy() if busq_s else df_sal.copy()
        cols_s=[c for c in ["detect_time","agente","numero_cliente","atendida","duration","end_reason_es"] if c in dvs.columns]
        dss=dvs[cols_s].copy()
        if "duration" in dss.columns: dss["duration"]=dss["duration"].apply(fmt_dur)
        if "atendida" in dss.columns: dss["atendida"]=dss["atendida"].map({True:"✅ Conectada",False:"❌ No conectada"})
        dss=dss.rename(columns={"detect_time":"Fecha/Hora","agente":"Agente","numero_cliente":"Número","atendida":"Estado","duration":"Duración","end_reason_es":"Resultado"})
        st.dataframe(dss,use_container_width=True,height=360,hide_index=True)

# ── TAB 3: AGENTES ─────────────────────────────────────────────────────────────
with tab_ag:
    ag_data=[]
    for aid,nombre in AGENTES_SIN_CENTRAL.items():
        ea=df_ent[df_ent["agente"]==nombre] if not df_ent.empty else pd.DataFrame()
        durs=ea["duracion"].dropna().tolist() if "duracion" in ea.columns else []
        per_t=len(df_ent[(df_ent["responsable"]==nombre)&(df_ent["atendida"]==False)]) if not df_ent.empty and "responsable" in df_ent.columns else 0
        sal_a=df_sal[df_sal["agente"]==nombre] if not df_sal.empty else pd.DataFrame()
        ag_data.append({"id":aid,"nombre":nombre,"ent_at":len(ea),
            "avg_dur":int(sum(durs)/len(durs)) if durs else 0,
            "total_min":int(sum(durs)/60),"salientes":len(sal_a),"per_turno":per_t})
    ag_data.sort(key=lambda x:x["ent_at"],reverse=True)
    cols3=st.columns(3)
    for i,ag in enumerate(ag_data):
        with cols3[i%3]:
            rank=["🥇","🥈","🥉"][i] if i<3 else f"#{i+1}"
            tot=ag["ent_at"]+ag["per_turno"]; pct=round(ag["ent_at"]/tot*100) if tot else 0
            bc="#22C55E" if pct>=70 else "#F59E0B" if pct>=40 else "#EF4444"
            st.markdown(f"""<div style='background:#0C0F1C;border:1px solid rgba(255,255,255,.05);border-left:3px solid {bc};border-radius:10px;padding:16px;margin-bottom:12px'>
              <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>
                <div><div style='font-size:14px;color:#C8D8E8;font-weight:500'>{rank} {ag['nombre']}</div>
                  <div style='font-size:10px;color:#1A3050;font-family:JetBrains Mono,monospace'>ID {ag['id']}</div></div>
                <div style='text-align:right'><div style='font-size:26px;font-weight:300;color:{bc}'>{ag['ent_at']}</div>
                  <div style='font-size:10px;color:#1A3050'>atendidas</div></div></div>
              <div style='background:rgba(255,255,255,.04);border-radius:4px;height:4px;margin-bottom:10px'>
                <div style='width:{pct}%;height:100%;background:{bc};border-radius:4px'></div></div>
              <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:11px;font-family:JetBrains Mono,monospace'>
                {"".join([f"<div style='background:rgba(255,255,255,.03);border-radius:6px;padding:6px;text-align:center'><div style='color:#1A3050;font-size:9px'>{l}</div><div style='color:#7A9ABA;margin-top:2px'>{v}</div></div>" for l,v in [("DUR.PROM",fmt_dur(ag['avg_dur'])),("SALIENTES",ag['salientes']),("PERD.TURNO",ag['per_turno'])]])}
              </div>
              <div style='margin-top:8px;display:flex;justify-content:space-between;font-size:10px;font-family:JetBrains Mono,monospace'>
                <span style='color:#EF4444'>{ag['per_turno']} perd. en turno</span>
                <span style='color:#1A3050'>{ag['total_min']} min · {pct}% at.</span></div>
            </div>""",unsafe_allow_html=True)
    if ag_data:
        st.markdown("---"); df_ap=pd.DataFrame(ag_data)
        gc1,gc2=st.columns(2)
        with gc1:
            fig_c=go.Figure()
            fig_c.add_trace(go.Bar(name="Atendidas",x=df_ap["nombre"],y=df_ap["ent_at"],marker_color="#166534",marker_line_width=0))
            fig_c.add_trace(go.Bar(name="Salientes",x=df_ap["nombre"],y=df_ap["salientes"],marker_color="#4A0404",marker_line_width=0))
            fig_c.update_layout(height=280,barmode="group",**P,xaxis_title="",yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),
                title=dict(text="Comparativa por agente",font=dict(size=12,color="#2A4060"),x=0))
            st.plotly_chart(fig_c,use_container_width=True)
        with gc2:
            fig_d2=px.bar(df_ap[df_ap["avg_dur"]>0].sort_values("avg_dur"),x="avg_dur",y="nombre",orientation="h",
                color="avg_dur",color_continuous_scale=["#0F172A","#1D4ED8","#3B82F6","#93C5FD"])
            fig_d2.update_layout(height=280,coloraxis_showscale=False,**P,
                xaxis=dict(gridcolor="rgba(255,255,255,.03)",title="segundos"),yaxis_title="",
                title=dict(text="Duración promedio",font=dict(size=12,color="#2A4060"),x=0))
            fig_d2.update_traces(marker_line_width=0); st.plotly_chart(fig_d2,use_container_width=True)

# ── TAB 4: TURNOS ──────────────────────────────────────────────────────────────
with tab_tur:
    if df_ent.empty: st.info("Sin datos para analizar turnos.")
    else:
        st.markdown("#### 📅 Horario de turnos")
        st.dataframe(pd.DataFrame([
            {"Días":"Lun–Vie","Turno":"Mañana","Horario":"06:00–14:00","Agente":"Alonso Loyola",    "ID":"8668109","Estado":"✅"},
            {"Días":"Lun–Vie","Turno":"Tarde", "Horario":"14:00–22:00","Agente":"Jose Luis Cahuana","ID":"8668110","Estado":"✅"},
            {"Días":"Lun–Vie","Turno":"Noche", "Horario":"22:00–06:00","Agente":"Deivy Chavez",     "ID":"8668111","Estado":"✅"},
            {"Días":"Sáb–Dom","Turno":"Mañana","Horario":"06:00–14:00","Agente":"Daniel Huayta",    "ID":"8668112","Estado":"✅"},
            {"Días":"Sáb–Dom","Turno":"Tarde", "Horario":"14:00–22:00","Agente":"Luz Goicochea",    "ID":"pendiente","Estado":"⏳ Sin ID"},
            {"Días":"Sáb–Dom","Turno":"Noche", "Horario":"22:00–06:00","Agente":"Joe Villanueva",   "ID":"8668114","Estado":"✅"},
        ]),use_container_width=True,hide_index=True,height=250)
        st.markdown("---")
        if "responsable" in df_ent.columns:
            st.markdown("#### 📊 Rendimiento por responsable de turno")
            ts=[]
            for resp in sorted(df_ent["responsable"].dropna().unique()):
                sub=df_ent[df_ent["responsable"]==resp]; tot=len(sub); at=int((sub["atendida"]==True).sum())
                drs=sub[sub["atendida"]==True]["duracion"].dropna() if "duracion" in sub.columns else pd.Series()
                ts.append({"Responsable":resp,"Total":tot,"Atendidas":at,"Perdidas":tot-at,
                    "% Atención":round(at/tot*100) if tot else 0,"Dur. prom.":fmt_dur(int(drs.mean()) if len(drs) else 0)})
            df_ts=pd.DataFrame(ts).sort_values("% Atención",ascending=False)
            st.dataframe(df_ts,use_container_width=True,hide_index=True,height=280)
            tc1,tc2=st.columns(2)
            with tc1:
                fig_tr=go.Figure()
                fig_tr.add_trace(go.Bar(name="Atendidas",x=df_ts["Responsable"],y=df_ts["Atendidas"],marker_color="#166534",marker_line_width=0))
                fig_tr.add_trace(go.Bar(name="Perdidas", x=df_ts["Responsable"],y=df_ts["Perdidas"], marker_color="#7F1D1D",marker_line_width=0))
                fig_tr.update_layout(height=300,barmode="stack",**P,
                    xaxis=dict(tickangle=-20,tickfont_size=11),yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                    legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),
                    title=dict(text="Llamadas por responsable",font=dict(size=12,color="#2A4060"),x=0))
                st.plotly_chart(fig_tr,use_container_width=True)
            with tc2:
                fig_pct=px.bar(df_ts.sort_values("% Atención"),x="% Atención",y="Responsable",orientation="h",
                    color="% Atención",color_continuous_scale=["#7F1D1D","#92400E","#166534"],range_color=[0,100],text="% Atención")
                fig_pct.update_traces(marker_line_width=0,texttemplate="%{text}%",textposition="outside",textfont=dict(size=11,color="#2A4060"))
                fig_pct.update_layout(height=300,coloraxis_showscale=False,**P,
                    xaxis=dict(gridcolor="rgba(255,255,255,.03)",title="",range=[0,115]),yaxis_title="",
                    title=dict(text="% Atención por responsable",font=dict(size=12,color="#2A4060"),x=0))
                st.plotly_chart(fig_pct,use_container_width=True)

# ── TAB 5: SEGUIMIENTO ─────────────────────────────────────────────────────────
with tab_seg:
    st.markdown("#### 📋 Seguimiento de llamadas perdidas — ventana de 5 minutos")
    st.markdown("""<div style='background:#0C0F1C;border:1px solid rgba(80,120,200,.15);border-radius:8px;
        padding:12px 16px;margin-bottom:20px;font-size:13px;color:#4A7ABA'>
        <b>Cumplimiento</b> si en ≤5 min: el agente llamó de vuelta (<i>saliente conectada</i>)
        <b>o</b> el cliente volvió a llamar y fue atendido. Solo aplica a escenarios con responsabilidad del agente.
    </div>""",unsafe_allow_html=True)
    df_cb=calcular_cumplimiento(df_ent,df_sal)
    if df_cb.empty:
        st.info("No hay llamadas perdidas con responsabilidad de agente en este período.")
    else:
        total_per=len(df_cb); cumpl=int(df_cb["Cumplimiento"].sum())
        no_cumpl=total_per-cumpl; pct_cumpl=round(cumpl/total_per*100) if total_per else 0
        avg_t=df_cb[df_cb["_seg"].notna()]["_seg"].mean()
        sc1,sc2,sc3,sc4=st.columns(4)
        sc1.metric("Perdidas c/responsable",f"{total_per:,}")
        sc2.metric("✅ Con resolución",      f"{cumpl:,}",  f"{pct_cumpl}%")
        sc3.metric("❌ Sin resolución",      f"{no_cumpl:,}",f"-{100-pct_cumpl}%")
        sc4.metric("T. prom. respuesta",    fmt_dur(int(avg_t)) if not pd.isna(avg_t) else "—")
        st.markdown("<br>",unsafe_allow_html=True)
        if "Responsable" in df_cb.columns:
            cb_ag=df_cb.groupby(["Responsable","Cumplimiento"]).size().reset_index(name="n")
            cb_ag["estado"]=cb_ag["Cumplimiento"].map({True:"✅ Resuelto",False:"❌ Sin resolver"})
            fig_cb=px.bar(cb_ag,x="Responsable",y="n",color="estado",barmode="stack",
                color_discrete_map={"✅ Resuelto":"#166534","❌ Sin resolver":"#7F1D1D"})
            fig_cb.update_layout(height=260,**P,xaxis_title="",yaxis=dict(gridcolor="rgba(255,255,255,.03)",title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2,font_color="#2A4060"),
                title=dict(text="Cumplimiento por responsable",font=dict(size=12,color="#2A4060"),x=0))
            fig_cb.update_traces(marker_line_width=0); st.plotly_chart(fig_cb,use_container_width=True)
        sf1,sf2,sf3=st.columns([2,1,1])
        with sf1: busq_cb=st.text_input("🔍 Buscar número",key="busq_cb")
        with sf2: f_resp=st.selectbox("Responsable",["Todos"]+sorted(df_cb["Responsable"].dropna().unique().tolist()),key="fresp_cb")
        with sf3: f_cumpl=st.selectbox("Estado",["Todos","✅ Resuelto","❌ Sin resolver"],key="fcumpl_cb")
        dcb=df_cb.copy()
        if busq_cb: dcb=dcb[dcb["Número"].str.contains(busq_cb,na=False)]
        if f_resp!="Todos": dcb=dcb[dcb["Responsable"]==f_resp]
        if f_cumpl=="✅ Resuelto": dcb=dcb[dcb["Cumplimiento"]==True]
        elif f_cumpl=="❌ Sin resolver": dcb=dcb[dcb["Cumplimiento"]==False]
        dcb_show=dcb.drop(columns=["Cumplimiento","_seg"],errors="ignore")
        st.caption(f"{len(dcb):,} registros · {int(dcb['Cumplimiento'].sum()) if 'Cumplimiento' in dcb.columns else 0} resueltos")
        st.dataframe(dcb_show,use_container_width=True,height=440,hide_index=True)
        st.download_button("⬇ Exportar seguimiento CSV",
            data=dcb.drop(columns=["_seg"],errors="ignore").to_csv(index=False).encode("utf-8-sig"),
            file_name=f"seguimiento_{hoy_lima.strftime('%Y%m%d')}.csv",mime="text/csv")

# ── TAB 6: CLIENTES ────────────────────────────────────────────────────────────
with tab_cl:
    if df_ent.empty: st.info("Sin datos de clientes.")
    else:
        cl=df_ent.groupby("numero_cliente").agg(
            total=("numero_cliente","count"),atendidas=("atendida","sum"),
            ultima=("detect_time","max"),
            ag_frec=("agente",lambda x: x[x!="Sin atender"].mode().iloc[0] if not x[x!="Sin atender"].empty else "—"),
        ).reset_index()
        cl["perdidas"]=cl["total"]-cl["atendidas"]
        cl["pct_at"]=(cl["atendidas"]/cl["total"]*100).round(0).astype(int)
        cl=cl.sort_values("total",ascending=False)
        st.markdown(f"**{len(cl):,} números únicos** en este período")
        cp=cl[cl["perdidas"]>=2].sort_values("perdidas",ascending=False).head(10)
        if not cp.empty:
            st.markdown("#### ⚠️ Clientes con 2+ llamadas perdidas")
            for _,row in cp.iterrows():
                urg="🔴" if row["perdidas"]>=5 else "🟡" if row["perdidas"]>=3 else "🟠"
                st.markdown(f"""<div style='background:#0C0F1C;border:1px solid rgba(239,68,68,.2);border-radius:8px;
                    padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between'>
                  <div><span style='color:#C8D8E8;font-family:JetBrains Mono,monospace;font-size:14px'>{urg} {row['numero_cliente']}</span>
                  <span style='color:#1A3050;font-size:11px;margin-left:12px'>Último: {str(row['ultima'])[:16] if pd.notna(row['ultima']) else '—'}</span></div>
                  <div style='text-align:right;font-size:12px;font-family:JetBrains Mono,monospace'>
                    <span style='color:#EF4444'>{int(row['perdidas'])} perdidas</span>
                    <span style='color:#1A3050;margin-left:10px'>de {int(row['total'])}</span></div>
                </div>""",unsafe_allow_html=True)
        fig_cl=px.bar(cl.head(15).sort_values("total"),x="total",y="numero_cliente",orientation="h",
            color="pct_at",color_continuous_scale=["#7F1D1D","#F59E0B","#166534"],range_color=[0,100])
        fig_cl.update_layout(height=360,**P,xaxis=dict(gridcolor="rgba(255,255,255,.03)",title="Llamadas"),
            yaxis_title="",coloraxis_colorbar=dict(title="% At.",tickfont_size=10,len=0.7))
        fig_cl.update_traces(marker_line_width=0); st.plotly_chart(fig_cl,use_container_width=True)
        cl_s=cl[["numero_cliente","total","atendidas","perdidas","pct_at","ag_frec","ultima"]].copy()
        cl_s["ultima"]=cl_s["ultima"].astype(str).str[:16]
        cl_s=cl_s.rename(columns={"numero_cliente":"Número","total":"Total","atendidas":"Atendidas",
            "perdidas":"Perdidas","pct_at":"% At.","ag_frec":"Agente frecuente","ultima":"Última llamada"})
        st.dataframe(cl_s,use_container_width=True,height=320,hide_index=True)

# ── TAB 7: REGISTROS RAW ───────────────────────────────────────────────────────
with tab_raw_t:
    st.markdown("#### Registros completos sin procesar")
    if df_raw is not None and not df_raw.empty:
        busq_r=st.text_input("Buscar",key="busq_raw")
        dr=df_raw.copy()
        if busq_r:
            mask=pd.Series([False]*len(dr))
            for c in ["ani","dnis","callid","original_callid","ani_user","dnis_user"]:
                if c in dr.columns: mask|=dr[c].astype(str).str.contains(busq_r,case=False,na=False)
            dr=dr[mask]
        cols_r=[c for c in ["detect_time","type","ani","dnis","ani_user","dnis_user","duration","ring_time","end_reason","connect_time","route_name","original_callid"] if c in dr.columns]
        rs1,rs2,rs3,rs4=st.columns(4)
        rs1.metric("Registros totales",f"{len(df_raw):,}")
        rs2.metric("Con duration>0",  f"{int((df_raw['duration']>0).sum()):,}" if "duration" in df_raw.columns else "—")
        rs3.metric("Entrantes",       f"{int((df_raw['type']=='incoming').sum()):,}" if "type" in df_raw.columns else "—")
        rs4.metric("Salientes",       f"{int((df_raw['type']=='outgoing').sum()):,}" if "type" in df_raw.columns else "—")
        st.dataframe(dr[cols_r].rename(columns={"detect_time":"Fecha","type":"Tipo","ani":"ANI","dnis":"DNIS",
            "ani_user":"ANI User","dnis_user":"DNIS User","duration":"Dur(s)","ring_time":"Ring(s)",
            "end_reason":"Motivo","connect_time":"Conectó","route_name":"Ruta","original_callid":"CID"}),
            use_container_width=True,height=460,hide_index=True)
        st.download_button("⬇ Exportar raw CSV",data=dr[cols_r].to_csv(index=False).encode("utf-8-sig"),
            file_name=f"raw_{hoy_lima.strftime('%Y%m%d_%H%M')}.csv",mime="text/csv")
