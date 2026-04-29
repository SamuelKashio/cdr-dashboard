import streamlit as st
import streamlit.components.v1 as components
import requests, pandas as pd, plotly.express as px, plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json, os

TZ = ZoneInfo("America/Lima")
def now_lima(): return datetime.now(TZ).replace(tzinfo=None)

try:
    _U = st.secrets["CMW_USER"]
    _P = st.secrets["CMW_PASS"]
except Exception:
    st.error("⚠ Configura CMW_USER y CMW_PASS en .streamlit/secrets.toml"); st.stop()

# ── Defaults ────────────────────────────────────────────────────────────────────
DEFAULT_AGENTES = {
    "8668106":{"nombre":"Central Virtual",  "activo":True,"es_central":True},
    "8668109":{"nombre":"Alonso Loyola",    "activo":True,"es_central":False},
    "8668110":{"nombre":"Jose Luis Cahuana","activo":True,"es_central":False},
    "8668112":{"nombre":"Daniel Huayta",    "activo":True,"es_central":False},
    "8668111":{"nombre":"Deivy Chavez",     "activo":True,"es_central":False},
    "8668114":{"nombre":"Joe Villanueva",   "activo":True,"es_central":False},
    "8672537":{"nombre":"Victor Figueroa",  "activo":True,"es_central":False},
    "SIN_ANEXO_MACEDO":{"nombre":"Victor Macedo","activo":True,"es_central":False,"sin_anexo":True},
}
DEFAULT_TURNOS = [
    {"dias":[0,1,2,3,4],"h_ini": 6,"h_fin":14,"agente":"Alonso Loyola",    "activo":True,"dids":[]},
    {"dias":[0,1,2,3,4],"h_ini":14,"h_fin":22,"agente":"Jose Luis Cahuana","activo":True,"dids":[]},
    {"dias":[0,1,2,3,4],"h_ini":22,"h_fin":30,"agente":"Deivy Chavez",     "activo":True,"dids":[]},
    {"dias":[5,6],      "h_ini": 6,"h_fin":14,"agente":"Daniel Huayta",    "activo":True,"dids":[]},
    {"dias":[5,6],      "h_ini":14,"h_fin":22,"agente":"Luz Goicochea",    "activo":True,"dids":[]},
    {"dias":[5,6],      "h_ini":22,"h_fin":30,"agente":"Joe Villanueva",   "activo":True,"dids":[]},
    {"dias":[0,1,2,3,4],"h_ini": 9,"h_fin":18,"agente":"Victor Macedo",   "activo":True,"dids":["7866715462"]},
]
DEFAULT_NUMS_EXCLUIDOS = ["51902871550"]
DEFAULT_DIDS = {
    "5116429375":{"pais":"Perú",          "bandera":"🇵🇪","activo":True},
    "7866715462":{"pais":"Estados Unidos","bandera":"🇺🇸","activo":True},
}

CONFIG_FILE = "config.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,"r",encoding="utf-8") as f: s=json.load(f)
            return (s.get("agentes",json.loads(json.dumps(DEFAULT_AGENTES))),
                    s.get("turnos", json.loads(json.dumps(DEFAULT_TURNOS))),
                    s.get("nums_excluidos",list(DEFAULT_NUMS_EXCLUIDOS)),
                    s.get("ventana_cb",5), s.get("modo_demo",False),
                    s.get("dids",json.loads(json.dumps(DEFAULT_DIDS))))
        except: pass
    return (json.loads(json.dumps(DEFAULT_AGENTES)),json.loads(json.dumps(DEFAULT_TURNOS)),
            list(DEFAULT_NUMS_EXCLUIDOS),5,False,json.loads(json.dumps(DEFAULT_DIDS)))

def save_config():
    try:
        with open(CONFIG_FILE,"w",encoding="utf-8") as f:
            json.dump({"agentes":st.session_state.cfg_agentes,"turnos":st.session_state.cfg_turnos,
                       "nums_excluidos":st.session_state.cfg_nums_excluidos,
                       "ventana_cb":st.session_state.cfg_ventana_cb,
                       "modo_demo":st.session_state.cfg_modo_demo,
                       "dids":st.session_state.cfg_dids},f,ensure_ascii=False,indent=2)
        return True
    except Exception as e: st.error(f"No se pudo guardar: {e}"); return False

# ── Temas ───────────────────────────────────────────────────────────────────────
T = {
    "dark":{
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
        "tab":"#2A4060","tab_sel":"#5A9AEA","tab_sel_border":"#3A7ACA",
    },
    "light":{
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
        "tab":"#64748B","tab_sel":"#4F46E5","tab_sel_border":"#4F46E5",
    },
}

def get_css(c):
    st_col = c["text"] if c["bg"]!="#06080F" else c["muted"]
    return (
        "<style>"
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700"
        "&family=JetBrains+Mono:wght@400;500&display=swap');"
        "html,body,[class*='css']{font-family:'Outfit',sans-serif!important}"
        f".stApp{{background:{c['bg']}!important}}.stApp>header{{background:transparent!important}}"
        f"section[data-testid='stSidebar']{{background:{c['sidebar']}!important;border-right:1px solid {c['border']}!important}}"
        f"section[data-testid='stSidebar'] *{{color:{st_col}!important}}"
        f"section[data-testid='stSidebar'] h1,section[data-testid='stSidebar'] strong{{color:{c['text']}!important}}"
        f"section[data-testid='stSidebar'] label{{color:{c['muted2']}!important;font-size:11px!important;letter-spacing:.5px;text-transform:uppercase}}"
        f"section[data-testid='stSidebar'] input{{background:{c['input_bg']}!important;border:1px solid {c['primary_border']}!important;color:{c['text']}!important;font-family:'JetBrains Mono',monospace!important;font-size:13px!important}}"
        f"section[data-testid='stSidebar'] .stButton button{{width:100%;background:{c['primary_dim']}!important;border:1px solid {c['primary_border']}!important;color:{c['primary']}!important;font-weight:600!important}}"
        f"[data-testid='metric-container']{{background:{c['card']}!important;border:1px solid {c['border']}!important;border-radius:12px!important;padding:16px 18px!important}}"
        f"[data-testid='stMetricLabel']{{color:{c['muted']}!important;font-size:10px!important;letter-spacing:1.8px!important;text-transform:uppercase!important;font-family:'JetBrains Mono',monospace!important}}"
        f"[data-testid='stMetricValue']{{color:{c['text']}!important;font-size:26px!important;font-weight:300!important}}"
        f"h1,h2,h3,h4,h5,h6{{color:{c['text']}!important;font-family:'Outfit',sans-serif!important}}"
        f".stMarkdown p,.stMarkdown li{{color:{c['muted']}!important}}"
        f".stCaption *{{color:{c['muted2']}!important}}"
        f".stTabs [data-baseweb='tab-list']{{background:transparent!important;gap:2px!important;border-bottom:1px solid {c['border']}!important}}"
        f".stTabs [data-baseweb='tab']{{background:transparent!important;color:{c['tab']}!important;font-size:11px!important;font-weight:600!important;letter-spacing:1px!important;text-transform:uppercase!important;padding:10px 18px!important;border-bottom:2px solid transparent!important;border-radius:0!important}}"
        f".stTabs [aria-selected='true']{{color:{c['tab_sel']}!important;border-bottom:2px solid {c['tab_sel_border']}!important}}"
        ".stTabs [data-baseweb='tab-border']{display:none!important}"
        ".stTabs [data-baseweb='tab-panel']{padding-top:22px!important}"
        f"[data-testid='stDataFrame']{{border:1px solid {c['border']}!important;border-radius:10px!important;overflow:hidden!important}}"
        f"[data-testid='stDataFrame'] *{{color:{c['text']}!important}}"
        f"[data-testid='stDataFrame'] th{{background:{c['card2']}!important;color:{c['muted']}!important;font-weight:600!important;border-bottom:1px solid {c['border']}!important}}"
        f"[data-testid='stDataFrame'] td{{background:{c['card']}!important;border-bottom:1px solid {c['border2']}!important}}"
        "::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:transparent}"
        f"::-webkit-scrollbar-thumb{{background:{c['scrollbar']};border-radius:4px}}"
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}"
        "</style>"
    )

ESCENARIOS = {
    "atendida":              {"es":"✅ Atendida",           "color":"#22C55E"},
    "colgó_en_ivr":          {"es":"📵 Colgó en IVR",       "color":"#6B7280"},
    "colgó_timbrando":       {"es":"📵 Colgó timbrando",    "color":"#F59E0B"},
    "no_enrutada":           {"es":"🚫 No enrutada",         "color":"#8B5CF6"},
    "agente_no_disponible":  {"es":"🔴 No disponible",       "color":"#EF4444"},
    "no_respondió":          {"es":"🔔 No respondió",        "color":"#EF4444"},
    "múltiples_no_respuesta":{"es":"🔄 Múltiples intentos",  "color":"#F97316"},
    "rechazada":             {"es":"❌ Rechazada",            "color":"#EC4899"},
    "perdida":               {"es":"❌ Perdida",              "color":"#EF4444"},
}
END_REASONS = {
    "OK":"Completada","CANCELLED":"Cancelada","NO_ANSWER":"Sin respuesta",
    "TEMPORARILY_UNAVAILABLE":"No disponible","NOT_FOUND":"No encontrado",
    "DECLINE":"Rechazada","SERVICE_UNAVAILABLE":"Servicio no disponible",
}
AGENTES_SIN_ID  = {"Luz Goicochea"}
ESC_RESPONSABLE = {"no_respondió","múltiples_no_respuesta","agente_no_disponible",
                   "rechazada","colgó_timbrando","perdida"}

st.set_page_config(page_title="Dashboard Central Telefónica",page_icon="📞",
                   layout="wide",initial_sidebar_state="expanded")

# ── Session state ───────────────────────────────────────────────────────────────
if "cfg_loaded" not in st.session_state:
    _ag,_tu,_ne,_vc,_md,_di = load_config()
    st.session_state.cfg_agentes=_ag; st.session_state.cfg_turnos=_tu
    st.session_state.cfg_nums_excluidos=_ne; st.session_state.cfg_ventana_cb=_vc
    st.session_state.cfg_modo_demo=_md; st.session_state.cfg_dids=_di
    st.session_state.cfg_loaded=True
if "show_config"  not in st.session_state: st.session_state.show_config=False
if "theme"        not in st.session_state: st.session_state.theme="dark"
if "auto_loaded"  not in st.session_state: st.session_state.auto_loaded=False
if "canal_sel"    not in st.session_state: st.session_state.canal_sel="🌐 Todos"
for k in ["df_ent","df_sal","df_raw","df_live_raw","label","error","loaded"]:
    if k not in st.session_state: st.session_state[k]=None if k!="loaded" else False
if "notif_ids_vistos"    not in st.session_state: st.session_state.notif_ids_vistos=set()
if "notif_sin_devolver"  not in st.session_state: st.session_state.notif_sin_devolver={}

# ── Config accessors ────────────────────────────────────────────────────────────
def get_agentes():          return {k:v["nombre"] for k,v in st.session_state.cfg_agentes.items()}
def get_central_id():       return next((k for k,v in st.session_state.cfg_agentes.items() if v.get("es_central")),"8668106")
def get_agentes_sin_central(): return {k:v["nombre"] for k,v in st.session_state.cfg_agentes.items() if not v.get("es_central") and v.get("activo",True)}
def get_agentes_con_anexo():   return {k:v["nombre"] for k,v in st.session_state.cfg_agentes.items() if not v.get("es_central") and v.get("activo",True) and not v.get("sin_anexo",False)}
def get_turnos():           return [t for t in st.session_state.cfg_turnos if t.get("activo",True)]
def get_nums_excluidos():   return [] if st.session_state.cfg_modo_demo else list(st.session_state.cfg_nums_excluidos)
def get_did_info(did):
    d = st.session_state.cfg_dids if "cfg_dids" in st.session_state else DEFAULT_DIDS
    return d.get(str(did),{"pais":"Desconocido","bandera":"🌐"})

# ── Helpers ─────────────────────────────────────────────────────────────────────
def fmt_dur(s):
    try:
        s=int(s or 0)
        if s<=0: return "—"
        if s<60: return f"{s}s"
        m,sec=divmod(s,60); return f"{m}m {sec:02d}s" if sec else f"{m}m"
    except: return "—"

def fmt_dt(dt):
    try:
        if dt is None or (isinstance(dt,float) and pd.isna(dt)): return "—"
        if isinstance(dt,str): dt=pd.to_datetime(dt,errors="coerce")
        if pd.isna(dt): return "—"
        return dt.strftime("%d/%m/%Y %H:%M:%S")+" GMT-5"
    except: return str(dt)[:19] if dt else "—"

def safe_mean(df,col):
    try:
        if df is None or df.empty or col not in df.columns or "atendida" not in df.columns: return 0
        s=df[df["atendida"]==True][col].dropna()
        if not len(s): return 0
        m=float(s.mean()); return 0 if m!=m else int(m)
    except: return 0

def norm_num(n):
    n=str(n or "").strip().replace("+","").replace(" ","").replace("-","")
    return n[-9:] if len(n)>=9 else n

def agente_de_turno(dt,did=None):
    try:
        if pd.isna(dt): return "Sin turno"
    except: return "Sin turno"
    try:
        did_str=None
        if did is not None:
            d=str(did).strip()
            did_str=d if d not in ("","nan","None","NaT") else None
        dow,h=dt.weekday(),dt.hour; h_ext=h if h>=6 else h+24
        turnos=get_turnos()
        did_tiene_turno=did_str and any(did_str in (t.get("dids") or []) for t in turnos)
        def turno_aplica(t):
            t_dids=t.get("dids") or []
            if t_dids: return did_str in t_dids if did_str else False
            return not did_tiene_turno
        for t in turnos:
            if turno_aplica(t) and dow in t["dias"] and t["h_ini"]<=h_ext<t["h_fin"]: return t["agente"]
        dp=(dow-1)%7
        for t in turnos:
            if turno_aplica(t) and dp in t["dias"] and t["h_ini"]<=h_ext<t["h_fin"]: return t["agente"]
        return "Sin turno"
    except: return "Sin turno"

def esc_es(k):    return ESCENARIOS.get(k,{}).get("es",k)
def esc_color(k): return ESCENARIOS.get(k,{}).get("color","#6B7280")

# ── API ──────────────────────────────────────────────────────────────────────────
PAGE_SIZE=1000; CHUNK_DAYS=10
def _fetch_chunk(ds,de):
    base={"username":_U,"password":_P,"format":"json","dateStart":ds,"dateEnd":de}
    all_cdrs,ini=[],0
    while True:
        r=requests.get("https://callmyway.com/getCdrs.php",params={**base,"ini":ini,"cant":PAGE_SIZE},timeout=30)
        r.raise_for_status(); data=r.json()
        page=data.get("cdrs",data) if isinstance(data,dict) else data
        if not page: break
        all_cdrs.extend(page)
        if len(page)<PAGE_SIZE: break
        ini+=PAGE_SIZE
    return all_cdrs

def fetch_cdrs(date_start=None,date_end=None,live=False,progress_cb=None):
    if live:
        try:
            r=requests.get("https://callmyway.com/getCdrs.php",
                params={"username":_U,"password":_P,"live":1,"fullAccount":1,"format":"json"},timeout=20)
            r.raise_for_status(); data=r.json()
            cdrs=data.get("cdrs",data) if isinstance(data,dict) else data
            return pd.DataFrame(cdrs or []),None
        except Exception as e: return None,str(e)
    try:
        dt_ini=datetime.strptime(date_start,"%Y-%m-%d %H:%M:%S")
        dt_fin=datetime.strptime(date_end,  "%Y-%m-%d %H:%M:%S")
    except Exception as e: return None,f"Fechas inválidas: {e}"
    chunks,cursor=[],dt_ini
    while cursor<dt_fin:
        ce=min(cursor+timedelta(days=CHUNK_DAYS),dt_fin); chunks.append((cursor,ce)); cursor=ce
    all_cdrs=[]
    for i,(c_ini,c_fin) in enumerate(chunks):
        if progress_cb: progress_cb(i/len(chunks),f"Chunk {i+1}/{len(chunks)} · {c_ini.strftime('%d/%m')}→{c_fin.strftime('%d/%m')} · {len(all_cdrs):,} reg")
        try: all_cdrs.extend(_fetch_chunk(c_ini.strftime("%Y-%m-%d %H:%M:%S"),c_fin.strftime("%Y-%m-%d %H:%M:%S")))
        except: pass
    if progress_cb: progress_cb(1.0,f"Completado · {len(all_cdrs):,} registros")
    return (pd.DataFrame(all_cdrs) if all_cdrs else pd.DataFrame()),None

# ── Clasificación ────────────────────────────────────────────────────────────────
def clasificar_entrantes(df_inc):
    if df_inc is None or df_inc.empty: return pd.DataFrame()
    CENTRAL_ID=get_central_id(); agentes_con_anexo=set(get_agentes_con_anexo().keys())
    nums_excluidos={norm_num(n) for n in get_nums_excluidos()}
    dids_cfg=st.session_state.cfg_dids if "cfg_dids" in st.session_state else DEFAULT_DIDS
    usa_dids={k for k,v in dids_cfg.items() if "Unidos" in v.get("pais","")}

    df_inc=df_inc.copy()
    for col in ["dnis_user","ani_user","original_callid","ref_callid","ani","dnis"]:
        if col in df_inc.columns:
            df_inc[col]=df_inc[col].astype(str).str.strip().replace({"None":"","nan":"","null":"","<NA>":""})
    if nums_excluidos and "ani" in df_inc.columns:
        df_inc=df_inc[~df_inc["ani"].apply(norm_num).isin(nums_excluidos)]
    if df_inc.empty: return pd.DataFrame()

    df_trn=df_inc[df_inc["dnis_user"]==CENTRAL_ID]
    df_ag =df_inc[df_inc["dnis_user"].isin(agentes_con_anexo)]
    trn_by_ref={}
    for _,row in df_trn.iterrows():
        ref=str(row.get("ref_callid","")).strip()
        if ref: trn_by_ref[ref]=row
    ag_orig_set=set(df_ag["original_callid"].unique()) if not df_ag.empty else set()
    resultados=[]

    def _append(orig_cid,detect_time,ani_cliente,atendida,agente_id,duracion,ring_total,
                n_intentos,end_reason,escenario,agente_timbrando=None,espera_usuario=0,dnis_marcado=""):
        dnis_str=str(dnis_marcado).strip() if dnis_marcado else ""
        di=get_did_info(dnis_str)
        resultados.append({"original_callid":orig_cid,"detect_time":detect_time,
            "numero_cliente":ani_cliente,"atendida":atendida,
            "agente":get_agentes().get(str(agente_id),"Sin atender") if agente_id else "Sin atender",
            "agente_id":agente_id,
            "agente_timbrando":get_agentes().get(str(agente_timbrando),"—") if agente_timbrando else "—",
            "espera_usuario":max(0,int(espera_usuario or 0)),"duracion":duracion,"espera_total":ring_total,
            "n_intentos":n_intentos,"end_reason":end_reason,"end_reason_es":END_REASONS.get(end_reason,end_reason),
            "escenario":escenario,"escenario_es":esc_es(escenario),
            "dnis_marcado":dnis_str,"pais":di["pais"],"bandera":di["bandera"],
            "hora":detect_time.hour if pd.notna(detect_time) else None,
            "fecha":detect_time.date() if pd.notna(detect_time) else None})

    for orig_cid,ag_grp in (df_ag.groupby("original_callid") if not df_ag.empty else []):
        trunk=trn_by_ref.get(orig_cid)
        if trunk is not None:
            ani_cliente=str(trunk.get("ani","—") or "—")
            dnis_marcado=str(trunk.get("dnis","") or "")
            detect_time=min(trunk.get("detect_time"),ag_grp["detect_time"].min())
        else:
            ani_val=ag_grp["ani"].replace("",pd.NA).dropna()
            ani_cliente=str(ani_val.iloc[0]) if not ani_val.empty else "—"
            dnis_marcado=""; detect_time=ag_grp["detect_time"].min()
        ring_total=int(ag_grp["ring_time"].apply(lambda x: max(0,int(x or 0))).sum())
        n_intentos=len(ag_grp); contestado=ag_grp[ag_grp["duration"]>0]
        if not contestado.empty:
            best=contestado.loc[contestado["duration"].idxmax()]
            _append(orig_cid,detect_time,ani_cliente,True,str(best["dnis_user"]),int(best["duration"]),
                    ring_total,n_intentos,str(best.get("end_reason","OK") or "OK"),"atendida",dnis_marcado=dnis_marcado)
        else:
            ers=ag_grp["end_reason"].replace("",pd.NA).dropna(); top_er=ers.mode().iloc[0] if not ers.empty else "UNKNOWN"
            if top_er=="CANCELLED":   esc="colgó_timbrando"
            elif top_er in ("TEMPORARILY_UNAVAILABLE","NOT_FOUND","SERVICE_UNAVAILABLE"): esc="agente_no_disponible"
            elif top_er=="NO_ANSWER": esc="múltiples_no_respuesta" if n_intentos>1 else "no_respondió"
            elif top_er=="DECLINE":   esc="rechazada"
            else: esc="perdida"
            ag_timbrando=None
            if esc=="colgó_timbrando":
                ringing=ag_grp.sort_values("detect_time",ascending=False)
                ag_timbrando=str(ringing.iloc[0]["dnis_user"]) if not ringing.empty else None
            _append(orig_cid,detect_time,ani_cliente,False,None,0,ring_total,n_intentos,top_er,esc,
                    agente_timbrando=ag_timbrando,espera_usuario=ring_total,dnis_marcado=dnis_marcado)

    for _,trn_row in (df_trn.iterrows() if not df_trn.empty else []):
        ref_cid=str(trn_row.get("ref_callid","")).strip()
        if ref_cid in ag_orig_set: continue
        orig_cid=str(trn_row.get("original_callid","")).strip()
        detect_time=trn_row.get("detect_time"); ani_cliente=str(trn_row.get("ani","—") or "—")
        dnis_marcado=str(trn_row.get("dnis","") or ""); er=str(trn_row.get("end_reason","UNKNOWN") or "UNKNOWN")
        if dnis_marcado in usa_dids:
            dur=int(trn_row.get("duration",0) or 0); atendida=dur>0
            esc=("atendida" if atendida else "colgó_en_ivr" if er=="CANCELLED" else
                 "agente_no_disponible" if er in ("TEMPORARILY_UNAVAILABLE","NOT_FOUND","SERVICE_UNAVAILABLE") else "no_enrutada")
            ag_id_usa=next((k for k,v in st.session_state.cfg_agentes.items() if v.get("sin_anexo") and v.get("activo",True)),None)
            _append(orig_cid,detect_time,ani_cliente,atendida,ag_id_usa,dur,0,1,er,esc,dnis_marcado=dnis_marcado)
        else:
            esc=("colgó_en_ivr" if er=="CANCELLED" else
                 "agente_no_disponible" if er in ("TEMPORARILY_UNAVAILABLE","NOT_FOUND","SERVICE_UNAVAILABLE") else "no_enrutada")
            _append(orig_cid,detect_time,ani_cliente,False,None,0,0,0,er,esc,dnis_marcado=dnis_marcado)

    if not resultados: return pd.DataFrame()
    df=pd.DataFrame(resultados)
    def _safe_turno(row):
        try:
            did=str(row.get("dnis_marcado","")).strip()
            did=None if did in ("","nan","None") else did
            return agente_de_turno(row["detect_time"],did)
        except: return "Sin turno"
    df["agente_turno"]=df.apply(_safe_turno,axis=1)
    def calc_resp(r):
        if r["agente_turno"] in AGENTES_SIN_ID: return r["agente_turno"]
        return r["agente"] if r["atendida"] else r["agente_turno"]
    df["responsable"]=df.apply(calc_resp,axis=1)
    df.loc[df["agente_turno"].isin(AGENTES_SIN_ID),["atendida","agente"]]=[False,"Sin atender"]
    return df

def procesar(df_raw):
    if df_raw is None or df_raw.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    CENTRAL_ID=get_central_id(); todos_agentes=set(get_agentes().keys())
    df=df_raw.copy()
    for col in ["duration","ring_time"]: df[col]=pd.to_numeric(df.get(col,0),errors="coerce").fillna(0).astype(int)
    for col in ["detect_time","connect_time","disconnect_time"]:
        if col in df.columns: df[col]=pd.to_datetime(df[col].replace("",None),errors="coerce")
    for col in ["ani_user","dnis_user","ref_callid","original_callid"]:
        if col in df.columns: df[col]=df[col].astype(str).str.strip()
    if "type" not in df.columns: df["type"]=""
    df["type"]=df["type"].astype(str).replace({"None":"","nan":"","null":"","<NA>":""})
    mask_null=df["type"]==""
    if mask_null.any():
        df.loc[mask_null&df["dnis_user"].isin(todos_agentes),"type"]="incoming"
        df.loc[mask_null&df["ani_user"].isin(get_agentes_con_anexo().keys())&~df["dnis_user"].isin(todos_agentes),"type"]="outgoing"
        df.loc[df["type"]=="","type"]="incoming"
    nums_excluidos={norm_num(n) for n in get_nums_excluidos()}
    mask_sal=((df["type"]=="outgoing")&(df["ani_user"].isin(get_agentes_con_anexo().keys()))&(~df["dnis"].astype(str).str.startswith("833")))
    df_sal=df[mask_sal].copy()
    if nums_excluidos and "dnis" in df_sal.columns:
        df_sal=df_sal[~df_sal["dnis"].apply(lambda x: norm_num(str(x))).isin(nums_excluidos)]
    df_sal["agente"]=df_sal["ani_user"].map(get_agentes()); df_sal["numero_cliente"]=df_sal["dnis"].astype(str)
    df_sal["atendida"]=df_sal["duration"]>0; df_sal["hora"]=df_sal["detect_time"].dt.hour
    df_sal["fecha"]=df_sal["detect_time"].dt.date; df_sal["end_reason_es"]=df_sal["end_reason"].map(END_REASONS).fillna(df_sal["end_reason"])
    df_ent=clasificar_entrantes(df[df["type"]=="incoming"].copy())
    return df_ent,df_sal,df

def calcular_cumplimiento(df_ent,df_sal):
    if df_ent is None or df_ent.empty or "escenario" not in df_ent.columns: return pd.DataFrame()
    ventana=pd.Timedelta(minutes=st.session_state.cfg_ventana_cb)
    perdidas=df_ent[(df_ent["atendida"]==False)&(df_ent["escenario"].isin(ESC_RESPONSABLE))].copy().sort_values("detect_time")
    if perdidas.empty: return pd.DataFrame()
    df_s2=df_sal.copy() if not df_sal.empty else pd.DataFrame()
    df_e2=df_ent.copy()
    if not df_s2.empty and "numero_cliente" in df_s2.columns: df_s2["_n"]=df_s2["numero_cliente"].apply(norm_num)
    if "numero_cliente" in df_e2.columns: df_e2["_n"]=df_e2["numero_cliente"].apply(norm_num)
    resultados=[]
    for _,row in perdidas.iterrows():
        t0=row["detect_time"]
        if pd.isna(t0): continue
        num=norm_num(row["numero_cliente"]); t_lim=t0+ventana
        cb_sal=pd.DataFrame()
        if not df_s2.empty and "detect_time" in df_s2.columns:
            cb_sal=df_s2[(df_s2["_n"]==num)&(df_s2["detect_time"]>t0)&(df_s2["detect_time"]<=t_lim)&(df_s2["atendida"]==True)]
        cb_ent=pd.DataFrame()
        if "detect_time" in df_e2.columns:
            cb_ent=df_e2[(df_e2["_n"]==num)&(df_e2["detect_time"]>t0)&(df_e2["detect_time"]<=t_lim)&(df_e2["atendida"]==True)]
        if not cb_sal.empty:
            tipo="📞 Agente llamó"; t_cb=cb_sal["detect_time"].min(); ag_cb=cb_sal.iloc[0].get("agente","—"); seg=int((t_cb-t0).total_seconds())
        elif not cb_ent.empty:
            tipo="↩️ Cliente volvió"; t_cb=cb_ent["detect_time"].min(); ag_cb=cb_ent.iloc[0].get("agente","—"); seg=int((t_cb-t0).total_seconds())
        else:
            tipo="❌ Sin resolución"; ag_cb="—"; seg=None
        resultados.append({"Fecha/Hora":t0,"Número":row["numero_cliente"],
            "Responsable":row.get("responsable","—"),"Escenario":esc_es(row.get("escenario","")),
            "Resolución":tipo,"Tiempo respuesta":fmt_dur(seg) if seg is not None else f"> {st.session_state.cfg_ventana_cb} min",
            "Agente resolvió":ag_cb,"Cumplimiento":tipo!="❌ Sin resolución","_seg":seg})
    return pd.DataFrame(resultados)

# ── Panel configuración ──────────────────────────────────────────────────────────
def render_config(c):
    st.markdown(f"<h2 style='color:{c['text']}'>⚙️ Configuración</h2>",unsafe_allow_html=True)
    st.markdown("---")
    cfg_tabs=st.tabs(["🔢 Agentes","📅 Turnos","🚫 Excluidos","📞 Canales","⚙️ General"])
    with cfg_tabs[0]:
        st.markdown("#### Gestión de agentes")
        for kid,val in list(st.session_state.cfg_agentes.items()):
            col1,col2,col3,col4=st.columns([1.2,2,.6,.5])
            with col1: st.text_input("ID",value=kid,disabled=True,key=f"ag_id_{kid}")
            with col2:
                nn=st.text_input("Nombre",value=val["nombre"],key=f"ag_nom_{kid}")
                st.session_state.cfg_agentes[kid]["nombre"]=nn
            with col3:
                act=st.checkbox("Activo",value=val.get("activo",True),key=f"ag_act_{kid}",disabled=val.get("es_central",False))
                st.session_state.cfg_agentes[kid]["activo"]=act
            with col4:
                if not val.get("es_central",False):
                    if st.button("🗑",key=f"ag_del_{kid}"): del st.session_state.cfg_agentes[kid]; st.rerun()
        st.markdown("---"); st.markdown("**Agregar agente**")
        na1,na2,na3,na4=st.columns([1.4,2,1,1])
        with na1: new_id=st.text_input("ID / Anexo",key="new_ag_id",placeholder="8668XXX")
        with na2: new_nom=st.text_input("Nombre",key="new_ag_nom",placeholder="Nombre Apellido")
        with na3: new_sa=st.checkbox("Sin anexo",key="new_ag_sa")
        with na4:
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("➕ Agregar",key="btn_add_ag"):
                if new_id and new_nom and new_id not in st.session_state.cfg_agentes:
                    st.session_state.cfg_agentes[new_id]={"nombre":new_nom,"activo":True,"es_central":False,"sin_anexo":new_sa}; st.rerun()
    with cfg_tabs[1]:
        st.markdown("#### Horario de turnos")
        DIAS_MAP={0:"Lun",1:"Mar",2:"Mié",3:"Jue",4:"Vie",5:"Sáb",6:"Dom"}
        for i,t in enumerate(st.session_state.cfg_turnos):
            h_fin_str=f"{t['h_fin']}h" if t['h_fin']<=24 else f"{t['h_fin']-24}h(+1)"
            dids_lbl=", ".join(t.get("dids") or []) or "Todos"
            with st.expander(f"Turno {i+1}: {t['agente']} · {t['h_ini']}h–{h_fin_str} · DIDs: {dids_lbl} {'✅' if t.get('activo',True) else '⏸'}"):
                tc1,tc2,tc3,tc4=st.columns([2,1,1,1])
                with tc1:
                    ag_nombres=[v["nombre"] for k,v in st.session_state.cfg_agentes.items() if not v.get("es_central")]
                    idx=ag_nombres.index(t["agente"]) if t["agente"] in ag_nombres else 0
                    t["agente"]=st.selectbox("Agente",ag_nombres,index=idx,key=f"t_ag_{i}")
                with tc2: t["h_ini"]=st.number_input("H. inicio",0,30,t["h_ini"],key=f"t_hi_{i}")
                with tc3: t["h_fin"]=st.number_input("H. fin",0,30,t["h_fin"],key=f"t_hf_{i}")
                with tc4: t["activo"]=st.checkbox("Activo",value=t.get("activo",True),key=f"t_act_{i}")
                t["dias"]=st.multiselect("Días",list(DIAS_MAP.keys()),format_func=lambda x:DIAS_MAP[x],default=t.get("dias",[]),key=f"t_dias_{i}")
                dids_str=st.text_input("DIDs exclusivos (coma, vacío=todos)",value=", ".join(t.get("dids") or []),key=f"t_dids_{i}")
                t["dids"]=[d.strip() for d in dids_str.split(",") if d.strip()]
                if st.button(f"🗑 Eliminar",key=f"t_del_{i}"): st.session_state.cfg_turnos.pop(i); st.rerun()
        if st.button("➕ Nuevo turno"):
            ag_list=[v["nombre"] for k,v in st.session_state.cfg_agentes.items() if not v.get("es_central")]
            st.session_state.cfg_turnos.append({"dias":[0,1,2,3,4],"h_ini":8,"h_fin":17,"agente":ag_list[0] if ag_list else "","activo":True,"dids":[]}); st.rerun()
    with cfg_tabs[2]:
        st.markdown("#### Números excluidos de métricas")
        st.session_state.cfg_modo_demo=st.toggle("🧪 Modo demo",value=st.session_state.cfg_modo_demo,key="toggle_demo_cfg")
        st.markdown("---")
        for i,num in enumerate(list(st.session_state.cfg_nums_excluidos)):
            nc1,nc2=st.columns([4,1])
            with nc1:
                nuevo=st.text_input(f"Número {i+1}",value=num,key=f"exc_num_{i}")
                st.session_state.cfg_nums_excluidos[i]=nuevo
            with nc2:
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("🗑",key=f"exc_del_{i}"): st.session_state.cfg_nums_excluidos.pop(i); st.rerun()
        nc1,nc2=st.columns([4,1])
        with nc1: nuevo_exc=st.text_input("Agregar número",placeholder="519XXXXXXXX",key="new_exc")
        with nc2:
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("➕",key="btn_add_exc"):
                if nuevo_exc and nuevo_exc not in st.session_state.cfg_nums_excluidos:
                    st.session_state.cfg_nums_excluidos.append(nuevo_exc); st.rerun()
    with cfg_tabs[3]:
        st.markdown("#### Canales / números DID")
        for did_k,did_v in list(st.session_state.cfg_dids.items()):
            dc1,dc2,dc3,dc4,dc5=st.columns([1.5,1.8,.6,.5,.5])
            with dc1: st.text_input("DID",value=did_k,disabled=True,key=f"did_id_{did_k}")
            with dc2:
                np_=st.text_input("País",value=did_v["pais"],key=f"did_pais_{did_k}")
                st.session_state.cfg_dids[did_k]["pais"]=np_
            with dc3:
                bf_=st.text_input("Bandera",value=did_v.get("bandera","🌐"),key=f"did_bf_{did_k}")
                st.session_state.cfg_dids[did_k]["bandera"]=bf_
            with dc4:
                act_=st.checkbox("Activo",value=did_v.get("activo",True),key=f"did_act_{did_k}")
                st.session_state.cfg_dids[did_k]["activo"]=act_
            with dc5:
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("🗑",key=f"did_del_{did_k}"): del st.session_state.cfg_dids[did_k]; st.rerun()
        st.markdown("---")
        nd1,nd2,nd3,nd4=st.columns([1.5,1.8,.6,.8])
        with nd1: new_dn=st.text_input("Número DID",placeholder="5116429375",key="new_did_num")
        with nd2: new_dp=st.text_input("País",placeholder="Perú",key="new_did_pais")
        with nd3: new_db=st.text_input("Bandera",placeholder="🇵🇪",key="new_did_bf")
        with nd4:
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("➕ Agregar",key="btn_add_did"):
                if new_dn and new_dn not in st.session_state.cfg_dids:
                    st.session_state.cfg_dids[new_dn]={"pais":new_dp,"bandera":new_db or "🌐","activo":True}; st.rerun()
    with cfg_tabs[4]:
        st.markdown("#### Parámetros generales")
        st.session_state.cfg_ventana_cb=st.slider("Ventana de cumplimiento (min)",1,15,st.session_state.cfg_ventana_cb)
        st.markdown("---")
        if st.button("⚠️ Restablecer a valores por defecto"):
            st.session_state.cfg_agentes=json.loads(json.dumps(DEFAULT_AGENTES))
            st.session_state.cfg_turnos=json.loads(json.dumps(DEFAULT_TURNOS))
            st.session_state.cfg_nums_excluidos=list(DEFAULT_NUMS_EXCLUIDOS)
            st.session_state.cfg_ventana_cb=5; st.session_state.cfg_modo_demo=False
            st.session_state.cfg_dids=json.loads(json.dumps(DEFAULT_DIDS))
            save_config(); st.success("Restablecido"); st.rerun()
    st.markdown("---")
    cs,cc=st.columns(2)
    with cs:
        if st.button("💾 Guardar",type="primary",use_container_width=True):
            if save_config(): st.success("✅ Guardado"); time.sleep(1); st.session_state.show_config=False; st.rerun()
    with cc:
        if st.button("✖ Cancelar",use_container_width=True):
            _ag,_tu,_ne,_vc,_md,_di=load_config()
            st.session_state.cfg_agentes=_ag; st.session_state.cfg_turnos=_tu
            st.session_state.cfg_nums_excluidos=_ne; st.session_state.cfg_ventana_cb=_vc
            st.session_state.cfg_modo_demo=_md; st.session_state.cfg_dids=_di
            st.session_state.show_config=False; st.rerun()

# ── SIDEBAR ──────────────────────────────────────────────────────────────────────
hoy_lima = now_lima()
with st.sidebar:
    st.markdown("## 📞 Dashboard Central Telefónica")
    _theme_on = st.toggle("☀️ Modo claro", value=st.session_state.theme=="light", key="theme_toggle")
    st.session_state.theme = "light" if _theme_on else "dark"
    c = T[st.session_state.theme]

    if st.session_state.cfg_modo_demo:
        st.markdown("<div style='background:rgba(234,179,8,.15);border:1px solid rgba(234,179,8,.4);"
                    "border-radius:6px;padding:6px 10px;text-align:center;font-size:11px;"
                    "color:#EAB308;margin-bottom:8px'>🧪 MODO DEMO</div>",unsafe_allow_html=True)
    cc_=c["card"]; cb_=c["border"]; cp_=c["primary"]; ct_=c["text"]; cm_=c["muted2"]
    st.markdown("<div style='background:"+cc_+";border:1px solid "+cb_+";border-radius:8px;"
                "padding:10px 12px;margin-bottom:8px'>"
                "<div style='color:"+cm_+";font-size:10px;font-family:JetBrains Mono,monospace'>CUENTA</div>"
                "<div style='color:"+cp_+";font-size:13px;font-family:JetBrains Mono,monospace;margin-top:2px'>"+_U+"</div></div>",
                unsafe_allow_html=True)
    if st.button("⚙️ Configuración",use_container_width=True):
        st.session_state.show_config=not st.session_state.show_config; st.rerun()
    st.markdown("---")
    fi=st.date_input("Desde",      value=(hoy_lima-timedelta(days=1)).date())
    hi=st.time_input("Hora inicio", value=datetime.strptime("00:00","%H:%M").time())
    ff=st.date_input("Hasta",       value=hoy_lima.date())
    hf=st.time_input("Hora fin",    value=datetime.strptime("23:59","%H:%M").time())
    st.markdown("---")
    # Canal selector
    _dids_sb=st.session_state.cfg_dids if "cfg_dids" in st.session_state else DEFAULT_DIDS
    _canal_opts=[x for x in ["🌐 Todos"]+[v["bandera"]+" "+v["pais"] for k,v in _dids_sb.items() if v.get("activo",True)]]
    _did_map={"🌐 Todos":None}
    for _k,_v in _dids_sb.items():
        if _v.get("activo",True): _did_map[_v["bandera"]+" "+_v["pais"]]=_k
    _idx=_canal_opts.index(st.session_state.canal_sel) if st.session_state.canal_sel in _canal_opts else 0
    _sel=st.selectbox("🌍 Canal",_canal_opts,index=_idx,key="canal_sb")
    if _sel!=st.session_state.canal_sel: st.session_state.canal_sel=_sel
    _did_filtro=_did_map.get(st.session_state.canal_sel)
    st.markdown("---")
    sb1,sb2=st.columns(2)
    with sb1: btn_ok =st.button("⟳ Consultar",type="primary",use_container_width=True)
    with sb2: btn_hoy=st.button("Hoy",         use_container_width=True)
    st.markdown("---")
    live_mode=st.toggle("🔴 Modo en vivo",value=False,key="live_toggle")
    intervalo=st.slider("Refrescar cada (seg)",5,60,15) if live_mode else 15

st.markdown(get_css(c),unsafe_allow_html=True)

if st.session_state.show_config: render_config(c); st.stop()

# ── Carga ────────────────────────────────────────────────────────────────────────
def cargar(df_raw,label):
    df_e,df_s,df_r=procesar(df_raw)
    st.session_state.update(df_ent=df_e,df_sal=df_s,df_raw=df_r,df_live_raw=None,label=label,error=None,loaded=True)
def cargar_live(df_raw,label):
    st.session_state.update(df_live_raw=df_raw,label=label,error=None,loaded=True)

if live_mode:
    df_raw_live,err=fetch_cdrs(live=True)
    if err: st.error(f"⚠ {err}"); st.stop()
    cargar_live(df_raw_live,f"EN VIVO · {hoy_lima.strftime('%H:%M:%S')}")
elif btn_hoy or (not st.session_state.loaded and not st.session_state.auto_loaded):
    ds=hoy_lima.replace(hour=0,minute=0,second=0,microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    de=hoy_lima.strftime("%Y-%m-%d %H:%M:%S")
    with st.spinner("Cargando datos de hoy..."):
        df_raw_h,err=fetch_cdrs(date_start=ds,date_end=de)
    if err: st.session_state.error=err
    else: cargar(df_raw_h,f"Hoy {hoy_lima.strftime('%d/%m/%Y')} · desde las 00:00"); st.session_state.auto_loaded=True
elif btn_ok:
    ds=datetime.combine(fi,hi).strftime("%Y-%m-%d %H:%M:%S"); de=datetime.combine(ff,hf).strftime("%Y-%m-%d %H:%M:%S")
    pb=st.progress(0,text="Iniciando…")
    df_raw_h,err=fetch_cdrs(date_start=ds,date_end=de,progress_cb=lambda p,m:pb.progress(p,text=m))
    pb.empty()
    if err: st.session_state.error=err
    else: cargar(df_raw_h,f"{fi.strftime('%d/%m')} – {ff.strftime('%d/%m/%Y')}")

if st.session_state.error: st.error(f"⚠ {st.session_state.error}"); st.stop()
if not st.session_state.loaded: st.info("Configura el período y pulsa **Consultar**."); st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MODO EN VIVO
# ══════════════════════════════════════════════════════════════════════════════
if live_mode:
    df_live=st.session_state.get("df_live_raw",pd.DataFrame()); lbl=st.session_state.label
    CENTRAL_ID=get_central_id()
    _ahora=now_lima()
    _hace6=(_ahora-timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M:%S")
    _hasta=_ahora.strftime("%Y-%m-%d %H:%M:%S")
    _debug_info=""
    try:
        _df_rec,_=fetch_cdrs(date_start=_hace6,date_end=_hasta)
        if _df_rec is not None and not _df_rec.empty:
            _df_rec_proc,_df_sal_rec,_=procesar(_df_rec)
            _debug_info=f"CDRs últimos 6 min: {len(_df_rec)} registros · {len(_df_rec_proc)} entrantes"
        else: _df_rec_proc,_df_sal_rec=pd.DataFrame(),pd.DataFrame(); _debug_info="Sin CDRs en últimos 6 min"
    except Exception as _ex: _df_rec_proc,_df_sal_rec=pd.DataFrame(),pd.DataFrame(); _debug_info=f"Error: {_ex}"

    _notif_js=[]
    if not _df_rec_proc.empty and "escenario" in _df_rec_proc.columns:
        for _,_row in _df_rec_proc[(_df_rec_proc["atendida"]==False)&(_df_rec_proc["escenario"].isin(ESC_RESPONSABLE))].iterrows():
            _cid=str(_row.get("original_callid","")); _num=str(_row.get("numero_cliente","—"))
            _esc=esc_es(_row.get("escenario","")); _resp=str(_row.get("responsable","—")); _t=_row.get("detect_time")
            if _cid not in st.session_state.notif_ids_vistos:
                st.session_state.notif_ids_vistos.add(_cid)
                st.session_state.notif_sin_devolver[_cid]={"num":_num,"esc":_esc,"resp":_resp,"t":_t}
                st.toast(f"📵 {_num} ({_esc}) · {_resp}",icon="🔔")
                _notif_js.append(f"Llamada perdida\\n{_num}\\n{_resp}")
        _cb=calcular_cumplimiento(_df_rec_proc,_df_sal_rec)
        if not _cb.empty and "Cumplimiento" in _cb.columns:
            for _,_r in _cb[_cb["Cumplimiento"]==True].iterrows():
                _n=norm_num(str(_r.get("Número","")))
                for _k,_v in list(st.session_state.notif_sin_devolver.items()):
                    if norm_num(_v["num"])==_n: del st.session_state.notif_sin_devolver[_k]; break
        _vseg=st.session_state.cfg_ventana_cb*60
        for _cid,_info in list(st.session_state.notif_sin_devolver.items()):
            _t=_info.get("t")
            if _t is not None and pd.notna(_t) and (_ahora-pd.Timestamp(_t)).total_seconds()>_vseg:
                _ak=f"a5_{_cid}"
                if _ak not in st.session_state.notif_ids_vistos:
                    st.session_state.notif_ids_vistos.add(_ak)
                    st.toast(f"⚠️ Sin devolver +{st.session_state.cfg_ventana_cb}min — {_info['num']} · {_info['resp']}",icon="🚨")
                    _notif_js.append(f"Sin devolver\\n{_info['num']}\\n{_info['resp']}")
    if _notif_js:
        _msgs=str(_notif_js).replace("'",'"')
        components.html("<script>const msgs="+_msgs+";function sn(m){if(Notification.permission==='granted')"
            "new Notification('Dashboard Central',{body:m});else if(Notification.permission!=='denied')"
            "Notification.requestPermission().then(p=>{if(p==='granted')new Notification('Dashboard Central',{body:m})})};"
            "msgs.forEach(m=>sn(m));</script>",height=0)

    # Llamadas activas
    llamadas_activas=[]
    if df_live is not None and not df_live.empty:
        df_lv=df_live.copy()
        for col in ["dnis_user","ani_user","original_callid","ref_callid","ani","dnis","connect_time","disconnect_time"]:
            if col in df_lv.columns: df_lv[col]=df_lv[col].astype(str).str.strip().replace({"None":"","nan":"","null":"","<NA>":""})
        agentes_con_anexo=set(get_agentes_con_anexo().keys())
        df_lv_trn=df_lv[df_lv["dnis_user"]==CENTRAL_ID]; df_lv_ag=df_lv[df_lv["dnis_user"].isin(agentes_con_anexo)]
        ag_by_orig={}
        for _,row in df_lv_ag.iterrows():
            orig=row.get("original_callid","")
            if not orig: continue
            if orig not in ag_by_orig or int(row.get("duration",0) or 0)>int(ag_by_orig[orig].get("duration",0) or 0): ag_by_orig[orig]=row
        procesados=set()
        dids_cfg_l=st.session_state.cfg_dids if "cfg_dids" in st.session_state else DEFAULT_DIDS
        usa_dids_l={k for k,v in dids_cfg_l.items() if "Unidos" in v.get("pais","")}
        for _,trn in df_lv_trn.iterrows():
            disc_trn=str(trn.get("disconnect_time","") or "")
            if disc_trn not in ("","None","null","nan"): continue
            ref_cid=str(trn.get("ref_callid","") or ""); trn_orig=str(trn.get("original_callid","") or "")
            if trn_orig in procesados: continue
            procesados.add(trn_orig)
            ag_row=ag_by_orig.get(ref_cid)
            if ag_row is not None:
                disc_ag=str(ag_row.get("disconnect_time","") or "")
                if disc_ag not in ("","None","null","nan"): continue
            ani_cliente=str(trn.get("ani","-") or "-"); dnis_marcado=str(trn.get("dnis","-") or "-")
            if norm_num(ani_cliente) in {norm_num(n) for n in get_nums_excluidos()}: continue
            did_inf=get_did_info(dnis_marcado)
            if ag_row is not None:
                ag_id=str(ag_row.get("dnis_user","")); ag_dur=int(ag_row.get("duration",0) or 0)
                ag_ct=str(ag_row.get("connect_time","") or ""); ag_ring=max(0,int(ag_row.get("ring_time",0) or 0))
                connected=ag_ct not in ("","None","null","nan")
                if connected and ag_dur>0: estado="en_llamada"; duracion=ag_dur; connect_time=ag_ct
                else: estado="timbrando"; duracion=0; connect_time=""
                agente_conocido=True
            else:
                ag_id=""; ag_ring=0; duracion=int(trn.get("duration",0) or 0); connect_time=str(trn.get("connect_time","") or "")
                if dnis_marcado in usa_dids_l and duracion>0:
                    ag_id=next((k for k,v in st.session_state.cfg_agentes.items() if v.get("sin_anexo") and v.get("activo",True)),ag_id)
                    estado="en_llamada"; agente_conocido=True
                else: estado="conectando"; agente_conocido=False
            llamadas_activas.append({"ag_id":ag_id,"agente":get_agentes().get(ag_id,"Por identificar") if ag_id else "Por identificar",
                "numero_cliente":ani_cliente,"dnis_marcado":dnis_marcado,"pais":did_inf["pais"],"bandera":did_inf["bandera"],
                "duracion":duracion,"ring_time":ag_ring,"estado":estado,"connect_time":connect_time,"agente_conocido":agente_conocido})

    ag_ocupados={x["ag_id"] for x in llamadas_activas if x["ag_id"]}
    n_activas=len(llamadas_activas); n_con=sum(1 for x in llamadas_activas if x["estado"]=="en_llamada")
    n_tim=sum(1 for x in llamadas_activas if x["estado"]=="timbrando")
    n_lib=len(get_agentes_sin_central())-len(ag_ocupados&set(get_agentes_sin_central()))

    # Variables de color (sin comillas dentro de f-strings con style)
    BG=c["card"]; TX=c["text"]; M2=c["muted2"]; GR=c["green"]; YL=c["yellow"]
    RD=c["red"]; BD=c["border"]; BD2=c["border2"]; MU=c["muted"]; M3=c["muted3"]
    RDM=c["red_dim"]; RBD=c["red_border"]; GDM=c["green_dim"]; YDM=c["yellow_dim"]; C2=c["card2"]

    demo_s="<span style='color:#EAB308;font-size:11px;background:rgba(234,179,8,.1);padding:2px 8px;border-radius:4px'>&#x1F9EA; DEMO</span>" if st.session_state.cfg_modo_demo else ""
    st.markdown(
        "<div style='display:flex;align-items:center;justify-content:space-between;padding:14px 18px;"
        "background:"+BG+";border:1px solid rgba(239,68,68,.3);border-radius:12px;margin-bottom:20px'>"
        "<div style='display:flex;align-items:center;gap:14px'>"
        "<div style='width:10px;height:10px;border-radius:50%;background:#EF4444;animation:blink 1s infinite'></div>"
        "<span style='color:"+TX+";font-size:17px;font-weight:300'>Monitoreo en Vivo</span>"
        "<span style='color:"+M2+";font-size:12px;font-family:JetBrains Mono,monospace'>"+lbl+"</span>"
        +demo_s+
        "</div><div style='display:flex;gap:20px;font-family:JetBrains Mono,monospace;font-size:12px'>"
        "<span style='color:"+GR+"'>"+str(n_con)+" en llamada</span>"
        "<span style='color:"+YL+"'>"+str(n_tim)+" timbrando</span>"
        "<span style='color:"+M2+"'>cada "+str(intervalo)+"s</span>"
        "</div></div>",unsafe_allow_html=True)

    kc1,kc2,kc3,kc4=st.columns(4)
    kc1.metric("Llamadas activas",n_activas); kc2.metric("En conversación",n_con)
    kc3.metric("Timbrando",n_tim);            kc4.metric("Agentes libres",n_lib)
    st.caption(f"🔍 {_debug_info}")

    if st.session_state.notif_sin_devolver:
        def _sp(v):
            t=v.get("t")
            if t is None or not pd.notna(t): return 0
            return (_ahora-pd.Timestamp(t)).total_seconds()
        _pend=sorted([(_sp(_v),_v,_k) for _k,_v in st.session_state.notif_sin_devolver.items()],reverse=True)
        st.markdown("<div style='background:"+RDM+";border:1px solid "+RBD+";border-radius:10px;padding:14px 18px;margin-bottom:16px'>"
            "<div style='color:"+RD+";font-size:13px;font-weight:600;margin-bottom:10px'>&#x1F6A8; "+str(len(_pend))+" sin resolver</div>",unsafe_allow_html=True)
        for _seg,_info,_ in _pend:
            _col=RD if _seg>st.session_state.cfg_ventana_cb*60 else YL
            _b="&#x26A0; +"+str(st.session_state.cfg_ventana_cb)+"MIN" if _seg>st.session_state.cfg_ventana_cb*60 else fmt_dur(int(_seg))
            st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid "+BD2+"'>"
                "<div style='font-family:JetBrains Mono,monospace'>"
                "<span style='color:"+TX+";font-size:13px'>"+_info["num"]+"</span>"
                "<span style='color:"+M2+";font-size:11px;margin-left:10px'>"+_info["esc"]+"</span></div>"
                "<div style='text-align:right'><div style='color:"+_col+";font-size:12px;font-weight:600'>"+_b+"</div>"
                "<div style='color:"+M2+";font-size:10px;font-family:JetBrains Mono,monospace'>"+_info["resp"]+"</div></div></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("#### &#x1F465; Estado de agentes")
    cols_ag=st.columns(3)
    for i,(ag_id,ag_nombre) in enumerate(get_agentes_sin_central().items()):
        ll=next((x for x in llamadas_activas if x["ag_id"]==ag_id),None)
        if ll is None:
            dot=GR; borde=c["green_border"]
            eh="<span style='color:"+GDM+";font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>&#x1F7E2; LIBRE</span>"
            dh="<div style='color:"+M3+";font-size:12px;margin-top:10px;font-family:JetBrains Mono,monospace'>Sin actividad</div>"
        elif ll["estado"]=="timbrando":
            dot=YL; borde="rgba(234,179,8,.3)"
            eh="<span style='color:"+YDM+";font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace;animation:blink 1s infinite'>&#x1F7E1; TIMBRANDO</span>"
            dh=("<div style='margin-top:10px;background:rgba(234,179,8,.07);border-radius:8px;padding:10px'>"
                "<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace'>"
                "<span style='color:"+M2+"'>Cliente</span><span style='color:"+TX+"'>"+ll["numero_cliente"]+"</span></div>"
                "<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>"
                "<span style='color:"+M2+"'>Canal</span><span style='color:"+MU+"'>"+ll["bandera"]+" "+ll["pais"]+"</span></div>"
                "<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>"
                "<span style='color:"+M2+"'>Timbrando</span><span style='color:"+YL+"'>"+str(ll["ring_time"])+"s</span></div></div>")
        else:
            dot=RD; borde=c["red_border"]
            eh="<span style='color:"+RDM+";font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>&#x1F534; EN LLAMADA</span>"
            m_,s_=divmod(ll["duracion"],60); dur_f=f"{m_}:{str(s_).zfill(2)}"
            badge="" if ll["agente_conocido"] else "<span style='font-size:9px;color:"+YDM+";background:rgba(234,179,8,.1);padding:2px 6px;border-radius:4px'>identificando…</span>"
            ct_div=("<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>"
                    "<span style='color:"+M2+"'>Conectó</span><span style='color:"+MU+"'>"+ll["connect_time"][:16]+"</span></div>") if ll["connect_time"] else ""
            dh=("<div style='margin-top:10px;background:rgba(239,68,68,.07);border-radius:8px;padding:10px'>"
                "<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace'>"
                "<span style='color:"+M2+"'>Cliente</span><span style='color:"+TX+"'>"+ll["numero_cliente"]+"</span></div>"
                "<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>"
                "<span style='color:"+M2+"'>Canal</span><span style='color:"+MU+"'>"+ll["bandera"]+" "+ll["pais"]+"</span></div>"
                "<div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>"
                "<span style='color:"+M2+"'>Duración</span><span style='color:"+RD+";font-weight:600'>"+dur_f+"</span></div>"
                "<div style='display:flex;justify-content:space-between;align-items:center;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>"
                "<span style='color:"+M2+"'>Agente</span><span style='color:"+MU+"'>"+ll["agente"]+" "+badge+"</span></div>"
                +ct_div+"</div>")
        with cols_ag[i%3]:
            st.markdown("<div style='background:"+BG+";border:1px solid "+borde+";border-top:3px solid "+dot+";"
                "border-radius:10px;padding:16px;margin-bottom:14px'>"
                "<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
                "<div><div style='color:"+TX+";font-size:14px;font-weight:500'>"+ag_nombre+"</div>"
                "<div style='color:"+M2+";font-size:10px;font-family:JetBrains Mono,monospace;margin-top:2px'>ID "+ag_id+"</div></div>"
                "<div>"+eh+"</div></div>"+dh+"</div>",unsafe_allow_html=True)

    sin_asignar=[x for x in llamadas_activas if not x["agente_conocido"]]
    if sin_asignar:
        st.markdown("---"); st.markdown("#### &#x1F4DE; En cola / por asignar")
        for x in sin_asignar:
            m_,s_=divmod(x["duracion"],60); df_=f"{m_}:{str(s_).zfill(2)}" if x["duracion"]>0 else "—"
            st.markdown("<div style='background:"+BG+";border:1px solid rgba(234,179,8,.3);"
                "border-left:3px solid "+YL+";border-radius:10px;padding:14px 18px;margin-bottom:8px;"
                "display:flex;justify-content:space-between;align-items:center'>"
                "<div style='font-family:JetBrains Mono,monospace'>"
                "<div style='color:"+TX+";font-size:14px'>&#x1F4DE; "+x["numero_cliente"]+"</div>"
                "<div style='color:"+M2+";font-size:11px;margin-top:4px'>DID: "+x["dnis_marcado"]+"</div></div>"
                "<div style='text-align:right;font-family:JetBrains Mono,monospace'>"
                "<div style='color:"+YL+";font-size:18px;font-weight:300'>"+df_+"</div>"
                "<div style='color:"+YDM+";font-size:10px'>identificando…</div></div></div>",unsafe_allow_html=True)
    elif n_activas==0:
        st.markdown("<div style='text-align:center;padding:40px;background:"+BG+";"
            "border:1px solid "+BD+";border-radius:12px;margin-top:8px'>"
            "<div style='font-size:36px;margin-bottom:10px'>&#x1F4F5;</div>"
            "<div style='color:"+MU+";font-size:14px'>No hay llamadas activas</div></div>",unsafe_allow_html=True)
    time.sleep(intervalo); st.rerun(); st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MODO HISTÓRICO
# ══════════════════════════════════════════════════════════════════════════════
df_ent=st.session_state.df_ent if st.session_state.df_ent is not None else pd.DataFrame()
df_sal=st.session_state.df_sal if st.session_state.df_sal is not None else pd.DataFrame()
df_raw=st.session_state.df_raw; lbl=st.session_state.label

if df_ent.empty and df_sal.empty: st.warning("Sin registros para el período."); st.stop()

# Aplicar filtro de canal ANTES de KPIs
if _did_filtro and not df_ent.empty and "dnis_marcado" in df_ent.columns:
    df_ent=df_ent[df_ent["dnis_marcado"]==_did_filtro].copy()

# ── KPIs ─────────────────────────────────────────────────────────────────────
n_ent     =len(df_ent)
n_ent_at  =int(df_ent["atendida"].sum())        if not df_ent.empty else 0
n_ent_per =n_ent-n_ent_at
pct_at    =round(n_ent_at/n_ent*100)             if n_ent else 0
n_sal     =len(df_sal); n_sal_ok=int((df_sal["atendida"]==True).sum()) if not df_sal.empty else 0
avg_dur   =safe_mean(df_ent,"duracion"); avg_esp=safe_mean(df_ent,"espera_total")
df_cb_kpi =calcular_cumplimiento(df_ent,df_sal)
n_resueltas=int(df_cb_kpi["Cumplimiento"].sum()) if not df_cb_kpi.empty and "Cumplimiento" in df_cb_kpi.columns else 0
balance_pct=round((n_ent_at+n_resueltas)/n_ent*100) if n_ent else 0
balance_delta=f"+{balance_pct-pct_at}%" if balance_pct>pct_at else None

P=dict(paper_bgcolor=c["plot_bg"],plot_bgcolor=c["plot_bg"],font=dict(color=c["muted"],family="Outfit"),margin=dict(t=10,b=30,l=5,r=5))
TX=c["text"]; M2=c["muted2"]; BD=c["border"]; M3=c["muted3"]; PR=c["primary"]
BG=c["card"]; MU=c["muted"]; GR=c["green"]; RD=c["red"]; YL=c["yellow"]
GDM=c["green_dim"]; RDM=c["red_dim"]; GBD=c["green_border"]; RBD=c["red_border"]
BD2=c["border2"]; C2=c["card2"]; YDM=c["yellow_dim"]

# Banner canal activo
if _did_filtro:
    _inf=(_did_map or {}).get(st.session_state.canal_sel,"")
    _dids_show=st.session_state.cfg_dids if "cfg_dids" in st.session_state else DEFAULT_DIDS
    _dinfo=_dids_show.get(_did_filtro,{})
    st.markdown("<div style='background:"+BG+";border:1px solid "+BD+";border-left:3px solid "+PR+";"
        "border-radius:8px;padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;gap:12px'>"
        "<span style='font-size:22px'>"+_dinfo.get("bandera","")+"</span>"
        "<div><div style='color:"+TX+";font-weight:500'>"+_dinfo.get("pais","")+" · DID "+_did_filtro+"</div>"
        "<div style='color:"+M2+";font-size:12px;font-family:JetBrains Mono,monospace'>Mostrando solo llamadas de este canal</div></div></div>",
        unsafe_allow_html=True)

demo_badge=("<span style='color:"+YL+";font-size:11px;background:rgba(234,179,8,.1);"
            "padding:2px 8px;border-radius:4px;margin-left:10px'>&#x1F9EA; DEMO</span>") if st.session_state.cfg_modo_demo else ""
st.markdown("<div style='display:flex;align-items:flex-end;justify-content:space-between;"
    "padding:0 0 18px;border-bottom:1px solid "+BD+";margin-bottom:22px'>"
    "<div><div style='font-size:22px;font-weight:300;color:"+TX+"'>Dashboard Central Telefónica"+demo_badge+"</div>"
    "<div style='font-size:11px;color:"+M2+";font-family:JetBrains Mono,monospace;margin-top:4px'>"
    +lbl+" · "+str(n_ent)+" entrantes · "+str(n_sal)+" salientes</div></div>"
    "<div style='font-size:11px;color:"+M3+";font-family:JetBrains Mono,monospace'>"+_U+" · CallMyWay</div></div>",
    unsafe_allow_html=True)

k1,k2,k3,k4,k5,k6,k7,k8,k9=st.columns(9)
k1.metric("Entrantes",       f"{n_ent:,}")
k2.metric("Atendidas",       f"{n_ent_at:,}",  f"{pct_at}%")
k3.metric("Perdidas",        f"{n_ent_per:,}", f"-{100-pct_at}%")
k4.metric("% Atención",      f"{pct_at}%")
k5.metric("Balance atención",f"{balance_pct}%",balance_delta,help=f"Incluye {n_resueltas} llamada(s) resueltas en {st.session_state.cfg_ventana_cb} min")
k6.metric("Salientes",       f"{n_sal:,}")
k7.metric("Sal. conectadas", f"{n_sal_ok:,}")
k8.metric("Dur. prom.",      fmt_dur(avg_dur))
k9.metric("Espera prom.",    fmt_dur(avg_esp))
st.markdown("<br>",unsafe_allow_html=True)

tabs=st.tabs(["VISIÓN GENERAL","ENTRANTES","SALIENTES","AGENTES","TURNOS","SEGUIMIENTO","CLIENTES","REGISTROS"])
tab_ov,tab_ent,tab_sal,tab_ag,tab_tur,tab_seg,tab_cl,tab_raw_t=tabs

# ── TAB 0: VISIÓN GENERAL ──────────────────────────────────────────────────────
with tab_ov:
    r1,r2,r3=st.columns([1.1,1.4,1.5])
    with r1:
        fig_d=go.Figure(go.Pie(labels=["Atendidas","Perdidas"],values=[n_ent_at,n_ent_per],
            hole=0.7,marker=dict(colors=[c["bar_green"],c["bar_red"]],line=dict(width=0)),textinfo="none"))
        fig_d.add_annotation(text=f"<b>{pct_at}%</b>",x=0.5,y=0.56,font=dict(size=30,color=TX),showarrow=False)
        fig_d.add_annotation(text="atención",x=0.5,y=0.40,font=dict(size=12,color=MU),showarrow=False)
        fig_d.update_layout(height=200,showlegend=False,**P); st.plotly_chart(fig_d,use_container_width=True)
        st.markdown("<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:-10px'>"
            "<div style='background:"+BG+";border:1px solid "+GBD+";border-radius:8px;padding:10px;text-align:center'>"
            "<div style='color:"+GDM+";font-size:10px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>ATENDIDAS</div>"
            "<div style='color:"+GR+";font-size:22px;font-weight:300'>"+str(n_ent_at)+"</div></div>"
            "<div style='background:"+BG+";border:1px solid "+RBD+";border-radius:8px;padding:10px;text-align:center'>"
            "<div style='color:"+RDM+";font-size:10px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>PERDIDAS</div>"
            "<div style='color:"+RD+";font-size:22px;font-weight:300'>"+str(n_ent_per)+"</div></div></div>",
            unsafe_allow_html=True)
    with r2:
        if not df_ent.empty and "hora" in df_ent.columns:
            hd=df_ent.groupby(["hora","atendida"]).size().reset_index(name="n")
            hd["estado"]=hd["atendida"].map({True:"Atendida",False:"Perdida"})
            fig_h=px.bar(hd,x="hora",y="n",color="estado",
                color_discrete_map={"Atendida":c["bar_green"],"Perdida":c["bar_red"]},barmode="stack")
            fig_h.update_layout(height=240,**P,xaxis=dict(title="Hora",dtick=1,gridcolor=c["grid"],tickfont_size=10),
                yaxis=dict(gridcolor=c["grid"],title=""),legend=dict(font_size=11,orientation="h",y=-0.2),bargap=0.15)
            fig_h.update_traces(marker_line_width=0); st.plotly_chart(fig_h,use_container_width=True)
    with r3:
        if not df_ent.empty and "escenario" in df_ent.columns:
            ec=df_ent["escenario"].value_counts().reset_index(); ec.columns=["esc","n"]
            ec["label"]=ec["esc"].apply(esc_es); ec["color"]=ec["esc"].apply(esc_color); ec=ec.sort_values("n",ascending=True)
            fig_ec=go.Figure(go.Bar(x=ec["n"],y=ec["label"],orientation="h",marker_color=ec["color"],marker_line_width=0,
                text=ec["n"],textposition="outside",textfont=dict(size=11,color=MU)))
            fig_ec.update_layout(height=240,**P,title=dict(text="Escenarios",font=dict(size=12,color=MU),x=0),
                xaxis=dict(gridcolor=c["grid"],title=""),yaxis=dict(gridcolor=c["grid"],title=""))
            st.plotly_chart(fig_ec,use_container_width=True)
    if not df_ent.empty and "fecha" in df_ent.columns:
        st.markdown("---")
        daily=df_ent.groupby(["fecha","atendida"]).size().reset_index(name="n")
        daily["estado"]=daily["atendida"].map({True:"Atendida",False:"Perdida"})
        if len(daily["fecha"].unique())>1:
            fig_ev=px.area(daily,x="fecha",y="n",color="estado",color_discrete_map={"Atendida":c["bar_green"],"Perdida":c["bar_red"]})
            fig_ev.update_traces(opacity=0.7,line_width=1.5)
            fig_ev.update_layout(height=200,**P,xaxis=dict(gridcolor=c["grid"],title=""),yaxis=dict(gridcolor=c["grid"],title=""),
                legend=dict(font_size=11,orientation="h",y=-0.25),title=dict(text="Evolución diaria",font=dict(size=12,color=MU),x=0))
            st.plotly_chart(fig_ev,use_container_width=True)

# ── TAB 1: ENTRANTES ──────────────────────────────────────────────────────────
with tab_ent:
    if df_ent.empty: st.info("Sin llamadas entrantes.")
    else:
        fc1,fc2,fc3,fc4=st.columns([2,1,1,1])
        with fc1: busq=st.text_input("🔍 Buscar número",placeholder="519…",key="busq_ent")
        with fc2: f_est=st.selectbox("Estado",["Todos","Atendidas","Perdidas"],key="fest_ent")
        with fc3:
            esc_opts=["Todos"]+(sorted(df_ent["escenario_es"].dropna().unique().tolist()) if "escenario_es" in df_ent.columns else [])
            f_esc=st.selectbox("Escenario",esc_opts,key="fesc_ent")
        with fc4:
            f_ag=st.selectbox("Agente",["Todos"]+sorted(df_ent["agente"].dropna().unique().tolist()),key="fag_ent")
        dv=df_ent.copy()
        if busq: dv=dv[dv["numero_cliente"].str.contains(busq,na=False)]
        if f_est=="Atendidas": dv=dv[dv["atendida"]==True]
        elif f_est=="Perdidas": dv=dv[dv["atendida"]==False]
        if f_esc!="Todos" and "escenario_es" in dv.columns: dv=dv[dv["escenario_es"]==f_esc]
        if f_ag!="Todos": dv=dv[dv["agente"]==f_ag]
        cols_t=[cx for cx in ["detect_time","numero_cliente","bandera","escenario_es","agente","agente_timbrando","espera_usuario","responsable","agente_turno","duracion","espera_total","n_intentos"] if cx in dv.columns]
        ds=dv[cols_t].copy()
        if "detect_time" in ds.columns: ds["detect_time"]=ds["detect_time"].apply(fmt_dt)
        for col,fn in [("duracion",fmt_dur),("espera_total",fmt_dur),("espera_usuario",fmt_dur)]:
            if col in ds.columns: ds[col]=ds[col].apply(fn)
        ds=ds.rename(columns={"detect_time":"Fecha/Hora","numero_cliente":"Número","bandera":"Canal",
            "escenario_es":"Escenario","agente":"Contestó","agente_timbrando":"Timbraba a",
            "espera_usuario":"Esperó","responsable":"Responsable","agente_turno":"Turno",
            "duracion":"Duración","espera_total":"Ring total","n_intentos":"Intentos"})
        st.caption(f"{len(dv):,} llamadas"); st.dataframe(ds,use_container_width=True,height=460,hide_index=True)
        ec1,ec2=st.columns(2)
        with ec1: st.download_button("⬇ Exportar entrantes",data=df_ent.to_csv(index=False).encode("utf-8-sig"),file_name=f"entrantes_{hoy_lima.strftime('%Y%m%d')}.csv",mime="text/csv")
        with ec2: st.download_button("⬇ Exportar perdidas",data=df_ent[df_ent["atendida"]==False].to_csv(index=False).encode("utf-8-sig"),file_name=f"perdidas_{hoy_lima.strftime('%Y%m%d')}.csv",mime="text/csv")

# ── TAB 2: SALIENTES ──────────────────────────────────────────────────────────
with tab_sal:
    if df_sal.empty: st.info("Sin llamadas salientes.")
    else:
        s1,s2,s3,s4=st.columns(4)
        dur_s=df_sal[df_sal["atendida"]==True]["duration"].dropna()
        s1.metric("Total",f"{n_sal:,}"); s2.metric("Conectadas",f"{n_sal_ok:,}",f"{round(n_sal_ok/n_sal*100) if n_sal else 0}%")
        s3.metric("No conectadas",f"{n_sal-n_sal_ok:,}"); s4.metric("Dur. prom.",fmt_dur(int(dur_s.mean()) if len(dur_s) else 0))
        sc1,sc2=st.columns(2)
        with sc1:
            ag_s=df_sal.groupby(["agente","atendida"]).size().reset_index(name="n")
            ag_s["estado"]=ag_s["atendida"].map({True:"Conectada",False:"No conectada"})
            fig_s=px.bar(ag_s,x="agente",y="n",color="estado",color_discrete_map={"Conectada":c["bar_blue"],"No conectada":c["bar_dark"]},barmode="stack")
            fig_s.update_layout(height=260,**P,xaxis_title="",yaxis=dict(gridcolor=c["grid"],title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2),title=dict(text="Salientes por agente",font=dict(size=12,color=MU),x=0))
            fig_s.update_traces(marker_line_width=0); st.plotly_chart(fig_s,use_container_width=True)
        with sc2:
            er_s=df_sal["end_reason"].value_counts().reset_index(); er_s.columns=["r","n"]
            er_s["label"]=er_s["r"].map(END_REASONS).fillna(er_s["r"])
            fig_ers=go.Figure(go.Bar(x=er_s["n"],y=er_s["label"],orientation="h",marker_color=c["bar_blue"],marker_line_width=0,
                text=er_s["n"],textposition="outside",textfont=dict(size=11,color=MU)))
            fig_ers.update_layout(height=260,**P,title=dict(text="Resultado salientes",font=dict(size=12,color=MU),x=0),
                xaxis=dict(gridcolor=c["grid"],title=""),yaxis=dict(gridcolor=c["grid"],title=""))
            st.plotly_chart(fig_ers,use_container_width=True)
        busq_s=st.text_input("🔍 Buscar número",key="busq_sal")
        dvs=df_sal[df_sal["numero_cliente"].str.contains(busq_s,na=False)].copy() if busq_s else df_sal.copy()
        cols_s=[cx for cx in ["detect_time","agente","numero_cliente","atendida","duration","end_reason_es"] if cx in dvs.columns]
        dss=dvs[cols_s].copy()
        if "detect_time" in dss.columns: dss["detect_time"]=dss["detect_time"].apply(fmt_dt)
        if "duration" in dss.columns: dss["duration"]=dss["duration"].apply(fmt_dur)
        if "atendida" in dss.columns: dss["atendida"]=dss["atendida"].map({True:"✅ Conectada",False:"❌ No conectada"})
        dss=dss.rename(columns={"detect_time":"Fecha/Hora","agente":"Agente","numero_cliente":"Número","atendida":"Estado","duration":"Duración","end_reason_es":"Resultado"})
        st.dataframe(dss,use_container_width=True,height=360,hide_index=True)

# ── TAB 3: AGENTES ────────────────────────────────────────────────────────────
with tab_ag:
    ag_data=[]
    for aid,nombre in get_agentes_sin_central().items():
        ea=df_ent[df_ent["agente"]==nombre] if not df_ent.empty else pd.DataFrame()
        durs=ea["duracion"].dropna().tolist() if "duracion" in ea.columns else []
        per_t=len(df_ent[(df_ent["responsable"]==nombre)&(df_ent["atendida"]==False)]) if not df_ent.empty and "responsable" in df_ent.columns else 0
        sal_a=df_sal[df_sal["agente"]==nombre] if not df_sal.empty else pd.DataFrame()
        ag_data.append({"id":aid,"nombre":nombre,"ent_at":len(ea),"avg_dur":int(sum(durs)/len(durs)) if durs else 0,
            "total_min":int(sum(durs)/60),"salientes":len(sal_a),"per_turno":per_t})
    ag_data.sort(key=lambda x:x["ent_at"],reverse=True)
    cols3=st.columns(3)
    for i,ag in enumerate(ag_data):
        with cols3[i%3]:
            rank=["🥇","🥈","🥉"][i] if i<3 else f"#{i+1}"
            tot=ag["ent_at"]+ag["per_turno"]; pct=round(ag["ent_at"]/tot*100) if tot else 0
            bc=GR if pct>=70 else YL if pct>=40 else RD
            bcd=GDM if pct>=70 else YDM if pct>=40 else RDM
            items="".join(["<div style='background:"+C2+";border-radius:6px;padding:6px;text-align:center'>"
                "<div style='color:"+M2+";font-size:9px'>"+l+"</div>"
                "<div style='color:"+MU+";margin-top:2px'>"+v+"</div></div>"
                for l,v in [("DUR.PROM",fmt_dur(ag["avg_dur"])),("SALIENTES",str(ag["salientes"])),("PERD.TURNO",str(ag["per_turno"]))]])
            st.markdown("<div style='background:"+BG+";border:1px solid "+BD+";border-left:3px solid "+bc+";"
                "border-radius:10px;padding:16px;margin-bottom:12px'>"
                "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:12px'>"
                "<div><div style='font-size:14px;color:"+TX+";font-weight:500'>"+rank+" "+ag["nombre"]+"</div>"
                "<div style='font-size:10px;color:"+M2+";font-family:JetBrains Mono,monospace'>ID "+ag["id"]+"</div></div>"
                "<div style='text-align:right'><div style='font-size:26px;font-weight:300;color:"+bc+"'>"+str(ag["ent_at"])+"</div>"
                "<div style='font-size:10px;color:"+M2+"'>atendidas</div></div></div>"
                "<div style='background:"+BD+";border-radius:4px;height:4px;margin-bottom:10px'>"
                "<div style='width:"+str(pct)+"%;height:100%;background:"+bc+";border-radius:4px'></div></div>"
                "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:11px;font-family:JetBrains Mono,monospace'>"+items+"</div></div>",
                unsafe_allow_html=True)
    if ag_data:
        st.markdown("---"); df_ap=pd.DataFrame(ag_data)
        gc1,gc2=st.columns(2)
        with gc1:
            fig_c=go.Figure()
            fig_c.add_trace(go.Bar(name="Atendidas",x=df_ap["nombre"],y=df_ap["ent_at"],marker_color=c["bar_green"],marker_line_width=0))
            fig_c.add_trace(go.Bar(name="Salientes",x=df_ap["nombre"],y=df_ap["salientes"],marker_color=c["bar_dark"],marker_line_width=0))
            fig_c.update_layout(height=280,barmode="group",**P,xaxis_title="",yaxis=dict(gridcolor=c["grid"],title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2),title=dict(text="Comparativa",font=dict(size=12,color=MU),x=0))
            st.plotly_chart(fig_c,use_container_width=True)
        with gc2:
            fig_d2=px.bar(df_ap[df_ap["avg_dur"]>0].sort_values("avg_dur"),x="avg_dur",y="nombre",orientation="h",
                color="avg_dur",color_continuous_scale=[c["plot_bg"],c["bar_blue"],"#93C5FD"])
            fig_d2.update_layout(height=280,coloraxis_showscale=False,**P,
                xaxis=dict(gridcolor=c["grid"],title="seg"),yaxis_title="",title=dict(text="Duración promedio",font=dict(size=12,color=MU),x=0))
            fig_d2.update_traces(marker_line_width=0); st.plotly_chart(fig_d2,use_container_width=True)

# ── TAB 4: TURNOS ─────────────────────────────────────────────────────────────
with tab_tur:
    if df_ent.empty: st.info("Sin datos.")
    else:
        DIAS_NOM={0:"Lun",1:"Mar",2:"Mié",3:"Jue",4:"Vie",5:"Sáb",6:"Dom"}
        trows=[]
        for t in st.session_state.cfg_turnos:
            h_fin_str=f"{t['h_fin']}h" if t['h_fin']<=24 else f"{t['h_fin']-24}h(+1)"
            trows.append({"Días":", ".join(DIAS_NOM.get(d,"?") for d in t.get("dias",[])),
                "Horario":f"{t['h_ini']}:00–{h_fin_str}","Agente":t["agente"],
                "Canal":", ".join(t.get("dids") or []) or "Todos","Estado":"✅" if t.get("activo",True) else "⏸"})
        st.dataframe(pd.DataFrame(trows),use_container_width=True,hide_index=True,height=280)
        st.markdown("---")
        if "responsable" in df_ent.columns:
            ts=[]
            for resp in sorted(df_ent["responsable"].dropna().unique()):
                sub=df_ent[df_ent["responsable"]==resp]; tot=len(sub); at=int((sub["atendida"]==True).sum())
                drs=sub[sub["atendida"]==True]["duracion"].dropna() if "duracion" in sub.columns else pd.Series()
                ts.append({"Responsable":resp,"Total":tot,"Atendidas":at,"Perdidas":tot-at,
                    "% Atención":round(at/tot*100) if tot else 0,"Dur. prom.":fmt_dur(int(drs.mean()) if len(drs) else 0)})
            df_ts=pd.DataFrame(ts).sort_values("% Atención",ascending=False)
            st.dataframe(df_ts,use_container_width=True,hide_index=True)
            tc1,tc2=st.columns(2)
            with tc1:
                fig_tr=go.Figure()
                fig_tr.add_trace(go.Bar(name="Atendidas",x=df_ts["Responsable"],y=df_ts["Atendidas"],marker_color=c["bar_green"],marker_line_width=0))
                fig_tr.add_trace(go.Bar(name="Perdidas",x=df_ts["Responsable"],y=df_ts["Perdidas"],marker_color=c["bar_red"],marker_line_width=0))
                fig_tr.update_layout(height=300,barmode="stack",**P,xaxis=dict(tickangle=-20,tickfont_size=11),
                    yaxis=dict(gridcolor=c["grid"],title=""),legend=dict(font_size=11,orientation="h",y=-0.2),
                    title=dict(text="Por responsable",font=dict(size=12,color=MU),x=0))
                st.plotly_chart(fig_tr,use_container_width=True)
            with tc2:
                fig_pct=px.bar(df_ts.sort_values("% Atención"),x="% Atención",y="Responsable",orientation="h",
                    color="% Atención",color_continuous_scale=[c["bar_red"],"#F59E0B",c["bar_green"]],range_color=[0,100],text="% Atención")
                fig_pct.update_traces(marker_line_width=0,texttemplate="%{text}%",textposition="outside",textfont=dict(size=11,color=MU))
                fig_pct.update_layout(height=300,coloraxis_showscale=False,**P,
                    xaxis=dict(gridcolor=c["grid"],title="",range=[0,115]),yaxis_title="",
                    title=dict(text="% Atención",font=dict(size=12,color=MU),x=0))
                st.plotly_chart(fig_pct,use_container_width=True)

# ── TAB 5: SEGUIMIENTO ────────────────────────────────────────────────────────
with tab_seg:
    st.markdown(f"#### 📋 Seguimiento — ventana de **{st.session_state.cfg_ventana_cb} min**")
    df_cb=df_cb_kpi
    if df_cb.empty: st.info("No hay llamadas perdidas con responsabilidad de agente.")
    else:
        tot_p=len(df_cb); cumpl=int(df_cb["Cumplimiento"].sum()); no_c=tot_p-cumpl
        pct_c=round(cumpl/tot_p*100) if tot_p else 0
        avg_t=df_cb[df_cb["_seg"].notna()]["_seg"].mean()
        sc1,sc2,sc3,sc4=st.columns(4)
        sc1.metric("Perdidas c/responsable",f"{tot_p:,}"); sc2.metric("✅ Con resolución",f"{cumpl:,}",f"{pct_c}%")
        sc3.metric("❌ Sin resolución",f"{no_c:,}",f"-{100-pct_c}%"); sc4.metric("T. prom.",fmt_dur(int(avg_t)) if not pd.isna(avg_t) else "—")
        if "Responsable" in df_cb.columns:
            cb_ag=df_cb.groupby(["Responsable","Cumplimiento"]).size().reset_index(name="n")
            cb_ag["estado"]=cb_ag["Cumplimiento"].map({True:"✅ Resuelto",False:"❌ Sin resolver"})
            fig_cb2=px.bar(cb_ag,x="Responsable",y="n",color="estado",barmode="stack",
                color_discrete_map={"✅ Resuelto":c["bar_green"],"❌ Sin resolver":c["bar_red"]})
            fig_cb2.update_layout(height=260,**P,xaxis_title="",yaxis=dict(gridcolor=c["grid"],title=""),
                legend=dict(font_size=11,orientation="h",y=-0.2),title=dict(text="Cumplimiento",font=dict(size=12,color=MU),x=0))
            fig_cb2.update_traces(marker_line_width=0); st.plotly_chart(fig_cb2,use_container_width=True)
        sf1,sf2,sf3=st.columns([2,1,1])
        with sf1: busq_cb=st.text_input("🔍 Buscar",key="busq_cb")
        with sf2: f_resp=st.selectbox("Responsable",["Todos"]+sorted(df_cb["Responsable"].dropna().unique().tolist()),key="fresp_cb")
        with sf3: f_cumpl=st.selectbox("Estado",["Todos","✅ Resuelto","❌ Sin resolver"],key="fcumpl_cb")
        dcb=df_cb.copy()
        if busq_cb: dcb=dcb[dcb["Número"].str.contains(busq_cb,na=False)]
        if f_resp!="Todos": dcb=dcb[dcb["Responsable"]==f_resp]
        if f_cumpl=="✅ Resuelto": dcb=dcb[dcb["Cumplimiento"]==True]
        elif f_cumpl=="❌ Sin resolver": dcb=dcb[dcb["Cumplimiento"]==False]
        dcb_show=dcb.drop(columns=["Cumplimiento","_seg"],errors="ignore").copy()
        if "Fecha/Hora" in dcb_show.columns: dcb_show["Fecha/Hora"]=dcb_show["Fecha/Hora"].apply(fmt_dt)
        st.dataframe(dcb_show,use_container_width=True,height=440,hide_index=True)
        st.download_button("⬇ Exportar",data=dcb.drop(columns=["_seg"],errors="ignore").to_csv(index=False).encode("utf-8-sig"),
            file_name=f"seguimiento_{hoy_lima.strftime('%Y%m%d')}.csv",mime="text/csv")

# ── TAB 6: CLIENTES ───────────────────────────────────────────────────────────
with tab_cl:
    if df_ent.empty: st.info("Sin datos.")
    else:
        cl=df_ent.groupby("numero_cliente").agg(total=("numero_cliente","count"),atendidas=("atendida","sum"),
            ultima=("detect_time","max"),ag_frec=("agente",lambda x: x[x!="Sin atender"].mode().iloc[0] if not x[x!="Sin atender"].empty else "—")).reset_index()
        cl["perdidas"]=cl["total"]-cl["atendidas"]; cl["pct_at"]=(cl["atendidas"]/cl["total"]*100).round(0).astype(int)
        cl=cl.sort_values("total",ascending=False)
        cp=cl[cl["perdidas"]>=2].sort_values("perdidas",ascending=False).head(10)
        if not cp.empty:
            st.markdown("#### ⚠️ Clientes con 2+ perdidas")
            for _,row in cp.iterrows():
                urg="🔴" if row["perdidas"]>=5 else "🟡" if row["perdidas"]>=3 else "🟠"
                st.markdown("<div style='background:"+BG+";border:1px solid "+RBD+";border-radius:8px;"
                    "padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between'>"
                    "<div><span style='color:"+TX+";font-family:JetBrains Mono,monospace'>"+urg+" "+str(row["numero_cliente"])+"</span>"
                    "<span style='color:"+M2+";font-size:11px;margin-left:12px'>"+(str(row["ultima"])[:16] if pd.notna(row["ultima"]) else "—")+"</span></div>"
                    "<div style='font-size:12px;font-family:JetBrains Mono,monospace'>"
                    "<span style='color:"+RD+"'>"+str(int(row["perdidas"]))+" perdidas</span>"
                    "<span style='color:"+M2+";margin-left:10px'>de "+str(int(row["total"]))+"</span></div></div>",unsafe_allow_html=True)
        fig_cl=px.bar(cl.head(15).sort_values("total"),x="total",y="numero_cliente",orientation="h",
            color="pct_at",color_continuous_scale=[c["bar_red"],"#F59E0B",c["bar_green"]],range_color=[0,100])
        fig_cl.update_layout(height=360,**P,xaxis=dict(gridcolor=c["grid"],title="Llamadas"),yaxis_title="",
            coloraxis_colorbar=dict(title="% At.",tickfont_size=10,len=0.7))
        fig_cl.update_traces(marker_line_width=0); st.plotly_chart(fig_cl,use_container_width=True)
        cl_s=cl[["numero_cliente","total","atendidas","perdidas","pct_at","ag_frec","ultima"]].copy()
        cl_s["ultima"]=cl_s["ultima"].astype(str).str[:16]
        cl_s=cl_s.rename(columns={"numero_cliente":"Número","total":"Total","atendidas":"Atendidas","perdidas":"Perdidas","pct_at":"% At.","ag_frec":"Agente frecuente","ultima":"Última"})
        st.dataframe(cl_s,use_container_width=True,height=320,hide_index=True)

# ── TAB 7: REGISTROS RAW ──────────────────────────────────────────────────────
with tab_raw_t:
    st.markdown("#### Registros sin procesar")
    if df_raw is not None and not df_raw.empty:
        busq_r=st.text_input("Buscar",key="busq_raw")
        dr=df_raw.copy()
        if busq_r:
            mask=pd.Series([False]*len(dr))
            for cx in ["ani","dnis","callid","original_callid","ani_user","dnis_user"]:
                if cx in dr.columns: mask|=dr[cx].astype(str).str.contains(busq_r,case=False,na=False)
            dr=dr[mask]
        cols_r=[cx for cx in ["detect_time","type","ani","dnis","ani_user","dnis_user","duration","ring_time","end_reason","connect_time","original_callid"] if cx in dr.columns]
        rs1,rs2,rs3,rs4=st.columns(4)
        rs1.metric("Total",f"{len(df_raw):,}"); rs2.metric("Dur>0",f"{int((df_raw['duration']>0).sum()):,}" if "duration" in df_raw.columns else "—")
        rs3.metric("Incoming",f"{int((df_raw['type']=='incoming').sum()):,}" if "type" in df_raw.columns else "—")
        rs4.metric("Outgoing",f"{int((df_raw['type']=='outgoing').sum()):,}" if "type" in df_raw.columns else "—")
        st.dataframe(dr[cols_r],use_container_width=True,height=460,hide_index=True)
        st.download_button("⬇ Exportar raw",data=dr[cols_r].to_csv(index=False).encode("utf-8-sig"),
            file_name=f"raw_{hoy_lima.strftime('%Y%m%d_%H%M')}.csv",mime="text/csv")
