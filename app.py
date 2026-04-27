# ─── Reemplaza la función cargar() existente ──────────────────────────────────
def cargar(df_raw, label):
    df_e, df_s, df_r = procesar(df_raw)
    st.session_state.df_ent  = df_e
    st.session_state.df_sal  = df_s
    st.session_state.df_raw  = df_r
    st.session_state.label   = label
    st.session_state.error   = None
    st.session_state.loaded  = True

def cargar_live(df_raw, label):
    """Carga para modo en vivo: guarda CDRs crudos sin procesar con procesar()."""
    st.session_state.df_live_raw = df_raw  # DataFrame crudo de llamadas activas
    st.session_state.label       = label
    st.session_state.error       = None
    st.session_state.loaded      = True


# ─── Reemplaza el bloque de carga (if live_mode / btn_ok / btn_hoy) ───────────
if live_mode:
    df_raw, err = fetch_cdrs(username, password, live=True)
    if err:
        st.error(f"⚠ {err}")
        st.stop()
    cargar_live(df_raw, f"EN VIVO · {datetime.now().strftime('%H:%M:%S')}")
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
    st.error(f"⚠ {st.session_state.error}")
    st.stop()
if not st.session_state.loaded:
    st.info("Configura el período y pulsa **Consultar**.")
    st.stop()


# ─── MODO EN VIVO: renderizado completo (reemplaza toda la lógica de tabs) ────
if live_mode:
    df_live = st.session_state.get("df_live_raw", pd.DataFrame())
    lbl     = st.session_state.label

    # Parsear llamadas activas
    llamadas_activas = []
    if df_live is not None and not df_live.empty:
        for _, row in df_live.iterrows():
            dur  = int(row.get("duration",  0) or 0)
            ring = int(row.get("ring_time", 0) or 0)
            tipo = str(row.get("type", "") or "")  # puede venir null → ""

            dnis_user = str(row.get("dnis_user", "") or "")
            ani_user  = str(row.get("ani_user",  "") or "")

            # Identificar agente real: si ambos son Central Virtual (8668106)
            # la llamada aún no fue asignada a un agente específico
            CENTRAL_ID = "8668106"
            if dnis_user != CENTRAL_ID:
                ag_id = dnis_user
            elif ani_user != CENTRAL_ID:
                ag_id = ani_user
            else:
                ag_id = ""   # solo tronco — agente aún no identificado

            # Número del cliente: siempre en ani (quien origina la llamada)
            numero_cliente = str(row.get("ani", "-") or "-")
            dnis_marcado   = str(row.get("dnis", "-") or "-")

            # Estado: priorizar disconnect_time=null + duration>0 = activa
            disconnect = row.get("disconnect_time")
            if disconnect is None or str(disconnect).strip() in ("", "None", "null"):
                if dur > 0:
                    estado = "en_llamada"
                elif ring > 0:
                    estado = "timbrando"
                else:
                    estado = "conectando"  # connect_time seteado pero dur=0
            else:
                estado = "finalizada"  # no debería aparecer en live, pero por si acaso

            llamadas_activas.append({
                "ag_id":          ag_id,
                "agente":         AGENTES.get(ag_id, "Agente por identificar") if ag_id else "Agente por identificar",
                "numero_cliente": numero_cliente,
                "dnis_marcado":   dnis_marcado,
                "duracion":       dur,
                "ring_time":      ring,
                "tipo":           tipo,
                "estado":         estado,
                "connect_time":   str(row.get("connect_time", "") or ""),
                "agente_conocido": ag_id != "" and ag_id != CENTRAL_ID,
            })

    # Mapa agente_id → llamada activa
    ag_llamada = {c["ag_id"]: c for c in llamadas_activas}

    # ── Header en vivo ────────────────────────────────────────────────────────
    n_activas    = len(llamadas_activas)
    n_timbrando  = sum(1 for c in llamadas_activas if c["estado"] == "timbrando")
    n_conectadas = sum(1 for c in llamadas_activas if c["estado"] == "en_llamada")

    st.markdown(f"""
    <style>
      @keyframes blink {{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
      @keyframes pulse_ring {{0%{{box-shadow:0 0 0 0 rgba(234,179,8,0.4)}}100%{{box-shadow:0 0 0 10px rgba(234,179,8,0)}}}}
      @keyframes pulse_call {{0%{{box-shadow:0 0 0 0 rgba(34,197,94,0.4)}}100%{{box-shadow:0 0 0 10px rgba(34,197,94,0)}}}}
    </style>
    <div style='display:flex;align-items:center;justify-content:space-between;
                padding:14px 18px;background:#0C0F1C;border:1px solid rgba(239,68,68,0.2);
                border-radius:12px;margin-bottom:20px'>
      <div style='display:flex;align-items:center;gap:14px'>
        <div style='width:10px;height:10px;border-radius:50%;background:#EF4444;
                    animation:blink 1s infinite'></div>
        <span style='color:#C8D8E8;font-size:17px;font-weight:300'>Monitoreo en Vivo</span>
        <span style='color:#1A3050;font-size:12px;font-family:JetBrains Mono,monospace'>{lbl}</span>
      </div>
      <div style='display:flex;gap:20px;font-family:JetBrains Mono,monospace;font-size:12px'>
        <span style='color:#22C55E'>{n_conectadas} en llamada</span>
        <span style='color:#EAB308'>{n_timbrando} timbrando</span>
        <span style='color:#1A3050'>refresca cada {intervalo}s</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPIs rápidos ──────────────────────────────────────────────────────────
    kc1, kc2, kc3, kc4 = st.columns(4)
    kc1.metric("Llamadas activas",  n_activas)
    kc2.metric("En conversación",   n_conectadas)
    kc3.metric("Timbrando / cola",  n_timbrando)
    kc4.metric("Agentes libres",    len(AGENTES_SIN_CENTRAL) - len(set(c["ag_id"] for c in llamadas_activas if c["ag_id"] in AGENTES)))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tarjetas por agente ───────────────────────────────────────────────────
    st.markdown("#### 👥 Estado de agentes")
    cols_ag = st.columns(3)

    for i, (ag_id, ag_nombre) in enumerate(AGENTES_SIN_CENTRAL.items()):
        llamada = ag_llamada.get(ag_id)

        if llamada is None:
            # LIBRE
            dot_color   = "#22C55E"
            bg_border   = "rgba(34,197,94,0.12)"
            borde_color = "rgba(34,197,94,0.2)"
            estado_html = "<span style='color:#166534;font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>🟢 LIBRE</span>"
            detalle_html = "<div style='color:#0F2030;font-size:12px;margin-top:10px;font-family:JetBrains Mono,monospace'>Sin actividad</div>"
        elif llamada["estado"] == "timbrando":
            # TIMBRANDO
            dot_color   = "#EAB308"
            bg_border   = "rgba(234,179,8,0.1)"
            borde_color = "rgba(234,179,8,0.3)"
            estado_html = "<span style='color:#92400E;font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace;animation:blink 1s infinite'>🟡 TIMBRANDO</span>"
            detalle_html = f"""
            <div style='margin-top:10px;background:rgba(234,179,8,0.07);border-radius:8px;padding:10px'>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace'>
                <span style='color:#0F2030'>Cliente</span>
                <span style='color:#C8D8E8'>{llamada['numero_cliente']}</span>
              </div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>DID marcado</span>
                <span style='color:#7A9ABA'>{llamada['dnis_marcado']}</span>
              </div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Timbrando</span>
                <span style='color:#EAB308'>{llamada['ring_time']}s</span>
              </div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Tipo</span>
                <span style='color:#7A9ABA'>{"📥 Entrante" if llamada["tipo"]=="incoming" else "📤 Saliente" if llamada["tipo"]=="outgoing" else "📞 En curso"}</span>
              </div>
            </div>"""
        else:
            # EN LLAMADA
            dot_color   = "#EF4444"
            bg_border   = "rgba(239,68,68,0.1)"
            borde_color = "rgba(239,68,68,0.3)"
            estado_html = "<span style='color:#7F1D1D;font-size:11px;letter-spacing:1px;font-family:JetBrains Mono,monospace'>🔴 EN LLAMADA</span>"
            minutos, segs = divmod(llamada["duracion"], 60)
            dur_fmt = f"{minutos}:{str(segs).zfill(2)}"
            ag_badge = "" if llamada["agente_conocido"] else \
                "<span style='font-size:9px;color:#92400E;background:rgba(234,179,8,0.1);padding:2px 6px;border-radius:4px;margin-left:6px'>identificando…</span>"
            detalle_html = f"""
            <div style='margin-top:10px;background:rgba(239,68,68,0.07);border-radius:8px;padding:10px'>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace'>
                <span style='color:#0F2030'>Cliente</span>
                <span style='color:#C8D8E8'>{llamada['numero_cliente']}</span>
              </div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>DID marcado</span>
                <span style='color:#7A9ABA'>{llamada['dnis_marcado']}</span>
              </div>
              <div style='display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Duración</span>
                <span style='color:#EF4444;font-weight:600'>{dur_fmt}</span>
              </div>
              <div style='display:flex;justify-content:space-between;align-items:center;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px'>
                <span style='color:#0F2030'>Agente</span>
                <span style='color:#7A9ABA'>{llamada['agente']}{ag_badge}</span>
              </div>
              {'<div style="display:flex;justify-content:space-between;font-size:12px;font-family:JetBrains Mono,monospace;margin-top:6px"><span style="color:#0F2030">Conectó</span><span style="color:#7A9ABA">' + str(llamada["connect_time"])[:16] + '</span></div>' if llamada["connect_time"] else ""}
            </div>"""

        with cols_ag[i % 3]:
            st.markdown(f"""
            <div style='background:#0C0F1C;border:1px solid {borde_color};
                        border-top:3px solid {dot_color};
                        border-radius:10px;padding:16px;margin-bottom:14px'>
              <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                <div>
                  <div style='color:#C8D8E8;font-size:14px;font-weight:500'>{ag_nombre}</div>
                  <div style='color:#1A3050;font-size:10px;font-family:JetBrains Mono,monospace;margin-top:2px'>ID {ag_id}</div>
                </div>
                <div>{estado_html}</div>
              </div>
              {detalle_html}
            </div>
            """, unsafe_allow_html=True)

    # ── Tabla de llamadas activas ─────────────────────────────────────────────
    if llamadas_activas:
        st.markdown("---")
        st.markdown("#### 📋 Detalle de llamadas activas")
        df_activas = pd.DataFrame(llamadas_activas)
        df_activas["estado_fmt"] = df_activas["estado"].map({
            "en_llamada": "🔴 En llamada",
            "timbrando":  "🟡 Timbrando",
            "conectando": "🟡 Conectando",
        })
        df_activas["duracion_fmt"] = df_activas["duracion"].apply(
            lambda s: f"{s//60}:{str(s%60).zfill(2)}" if s > 0 else "—"
        )
        df_activas["tipo_fmt"] = df_activas["tipo"].map({
            "incoming": "📥 Entrante",
            "outgoing": "📤 Saliente",
        }).fillna(df_activas["tipo"])

        cols_show = ["agente","numero_cliente","tipo_fmt","estado_fmt","duracion_fmt","ring_time","connect_time"]
        df_show = df_activas[[c for c in cols_show if c in df_activas.columns]].rename(columns={
            "agente":         "Agente",
            "numero_cliente": "Número cliente",
            "tipo_fmt":       "Tipo",
            "estado_fmt":     "Estado",
            "duracion_fmt":   "Duración",
            "ring_time":      "Ring (s)",
            "connect_time":   "Conectó",
        })
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div style='text-align:center;padding:40px;background:#0C0F1C;
                    border:1px solid rgba(255,255,255,0.04);border-radius:12px;margin-top:8px'>
          <div style='font-size:36px;margin-bottom:10px'>📵</div>
          <div style='color:#1A3050;font-size:14px'>No hay llamadas activas en este momento</div>
          <div style='color:#0F2030;font-size:11px;margin-top:6px;font-family:JetBrains Mono,monospace'>
            Todos los agentes están libres · Próximo refresco en {intervalo}s
          </div>
        </div>
        """.replace("{intervalo}", str(intervalo)), unsafe_allow_html=True)

    # ── Auto refresco ─────────────────────────────────────────────────────────
    time.sleep(intervalo)
    st.rerun()

    st.stop()  # Detener aquí — no renderizar los tabs históricos en modo live


# ─── A partir de aquí, solo se ejecuta en modo histórico ─────────────────────
df_ent = st.session_state.df_ent
df_sal = st.session_state.df_sal
df_raw = st.session_state.df_raw
lbl    = st.session_state.label
# ... (resto del código sin cambios desde los KPIs hacia abajo)
