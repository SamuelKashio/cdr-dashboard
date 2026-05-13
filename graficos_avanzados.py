# 📊 Ejemplos Avanzados de Gráficos Plotly para Dashboard

Este archivo contiene ejemplos listos para usar de gráficos avanzados con Plotly.

---

## 1. Gráfico de Sankey (Flujo de Llamadas)

**Visualiza cómo fluyen las llamadas de clientes → central → agentes**

```python
def create_sankey_flow(df_ent, colors):
    """
    Crea un diagrama Sankey mostrando:
    Clientes frecuentes → Central → Agentes
    """
    # Preparar datos
    origen = df_ent["numero_cliente"].value_counts().head(8).index.tolist()
    df_sankey = df_ent[df_ent["numero_cliente"].isin(origen)].copy()
    
    # Contar flujos
    flujos = df_sankey.groupby(["numero_cliente", "agente"]).size().reset_index(name="count")
    
    # Nodos únicos
    nodos = list(set(df_sankey["numero_cliente"].unique()) | set(df_sankey["agente"].unique()))
    nodos_dict = {nodo: i for i, nodo in enumerate(nodos)}
    
    # Crear Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodos,
            color=[colors["primary"] if "51" in n else colors["bar_green"] for n in nodos]
        ),
        link=dict(
            source=[nodos_dict[f] for f in flujos["numero_cliente"]],
            target=[nodos_dict[t] for t in flujos["agente"]],
            value=flujos["count"],
            color=[colors["bar_blue"] + "40" for _ in flujos]
        )
    )])
    
    fig.update_layout(
        title="Flujo de Llamadas (Cliente → Agente)",
        font_size=10,
        height=500,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font_color=colors["text"]
    )
    
    return fig

# Uso:
# fig_sankey = create_sankey_flow(df_ent, colors)
# st.plotly_chart(fig_sankey, use_container_width=True)
```

---

## 2. Gráfico de Caja (Box Plot) - Distribución de Duraciones

**Visualiza la distribución de duración de llamadas por agente**

```python
def create_duration_boxplot(df_ent, colors):
    """
    Crea un box plot mostrando distribución de duraciones por agente
    Útil para identificar patrones y anomalías
    """
    df_with_dur = df_ent[df_ent["atendida"] & (df_ent["duracion"] > 0)].copy()
    
    fig = go.Figure()
    
    for agente in df_with_dur["agente"].unique():
        duraciones = df_with_dur[df_with_dur["agente"] == agente]["duracion"]
        
        fig.add_trace(go.Box(
            y=duraciones,
            name=agente,
            marker_color=colors["primary"],
            boxmean="sd"  # Muestra media y desviación estándar
        ))
    
    fig.update_layout(
        title="Distribución de Duraciones por Agente",
        yaxis_title="Duración (segundos)",
        height=400,
        showlegend=True,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font_color=colors["text"],
        xaxis_title="",
        yaxis=dict(gridcolor=colors["grid"])
    )
    
    return fig

# Uso:
# fig_box = create_duration_boxplot(df_ent, colors)
# st.plotly_chart(fig_box, use_container_width=True)
```

---

## 3. Gráfico de Barras Agrupadas - Comparativa Completa

**Compara múltiples métricas entre agentes**

```python
def create_agent_comparison(df_ent, colors):
    """
    Crea una comparativa de agentes con múltiples métricas
    """
    stats = []
    for agente in df_ent["agente"].dropna().unique():
        sub = df_ent[df_ent["agente"] == agente]
        
        total = len(sub)
        atendidas = int((sub["atendida"] == True).sum())
        perdidas = total - atendidas
        duracion_prom = int(sub[sub["atendida"]]["duracion"].mean()) if len(sub[sub["atendida"]]) > 0 else 0
        
        stats.append({
            "Agente": agente,
            "Atendidas": atendidas,
            "Perdidas": perdidas,
            "Promedio (seg)": duracion_prom // 60  # Convertir a minutos para escala
        })
    
    df_stats = pd.DataFrame(stats)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_stats["Agente"],
        y=df_stats["Atendidas"],
        name="Atendidas",
        marker_color=colors["bar_green"]
    ))
    
    fig.add_trace(go.Bar(
        x=df_stats["Agente"],
        y=df_stats["Perdidas"],
        name="Perdidas",
        marker_color=colors["bar_red"]
    ))
    
    fig.update_layout(
        barmode="group",
        title="Comparativa de Agentes",
        height=400,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font_color=colors["text"],
        xaxis_title="",
        yaxis_title="Cantidad",
        yaxis=dict(gridcolor=colors["grid"]),
        legend=dict(orientation="h", y=-0.15)
    )
    
    return fig

# Uso:
# fig_comp = create_agent_comparison(df_ent, colors)
# st.plotly_chart(fig_comp, use_container_width=True)
```

---

## 4. Gráfico de Línea con Área - Tendencia Temporal

**Visualiza la tendencia de llamadas a lo largo del día/mes**

```python
def create_temporal_trend(df_ent, colors, period="hour"):
    """
    Crea un gráfico de tendencia temporal
    period: "hour" (hora), "day" (día), "week" (semana)
    """
    df_trend = df_ent.copy()
    df_trend["detect_time"] = pd.to_datetime(df_trend["detect_time"])
    
    if period == "hour":
        df_trend["periodo"] = df_trend["detect_time"].dt.floor("H")
    elif period == "day":
        df_trend["periodo"] = df_trend["detect_time"].dt.date
    else:  # week
        df_trend["periodo"] = df_trend["detect_time"].dt.to_period("W")
    
    trend_data = df_trend.groupby("periodo").agg({
        "numero_cliente": "count",
        "atendida": lambda x: (x == True).sum()
    }).reset_index()
    
    trend_data.columns = ["periodo", "total", "atendidas"]
    trend_data["perdidas"] = trend_data["total"] - trend_data["atendidas"]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=trend_data["periodo"],
        y=trend_data["atendidas"],
        name="Atendidas",
        mode="lines+markers",
        line=dict(color=colors["bar_green"], width=2),
        fill="tozeroy",
        fillcolor=colors["green_border"]
    ))
    
    fig.add_trace(go.Scatter(
        x=trend_data["periodo"],
        y=trend_data["perdidas"],
        name="Perdidas",
        mode="lines+markers",
        line=dict(color=colors["bar_red"], width=2),
        fill="tozeroy",
        fillcolor=colors["red_border"]
    ))
    
    fig.update_layout(
        title=f"Tendencia Temporal ({period})",
        hovermode="x unified",
        height=400,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font_color=colors["text"],
        xaxis_title="",
        yaxis_title="Cantidad",
        yaxis=dict(gridcolor=colors["grid"]),
        legend=dict(orientation="h", y=-0.15)
    )
    
    return fig

# Uso:
# fig_trend = create_temporal_trend(df_ent, colors, period="hour")
# st.plotly_chart(fig_trend, use_container_width=True)
```

---

## 5. Gráfico de Dispersión (Scatter) - Duración vs Hora

**Identifica patrones entre hora del día y duración de llamadas**

```python
def create_duration_by_hour_scatter(df_ent, colors):
    """
    Scatter plot: Hora del día vs Duración de llamada
    """
    df_scatter = df_ent[df_ent["atendida"] & (df_ent["duracion"] > 0)].copy()
    df_scatter["hora"] = pd.to_datetime(df_scatter["detect_time"]).dt.hour
    df_scatter["agente_simplif"] = df_scatter["agente"].fillna("Sin atender")
    
    fig = px.scatter(
        df_scatter,
        x="hora",
        y="duracion",
        color="agente_simplif",
        size="duracion",
        hover_data=["numero_cliente", "duracion"],
        title="Duración de Llamadas por Hora",
        labels={"hora": "Hora del día", "duracion": "Duración (seg)"}
    )
    
    fig.update_traces(marker_opacity=0.6)
    fig.update_layout(
        height=400,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font_color=colors["text"],
        xaxis=dict(gridcolor=colors["grid"]),
        yaxis=dict(gridcolor=colors["grid"]),
        legend=dict(orientation="v", yanchor="top", y=0.99)
    )
    
    return fig

# Uso:
# fig_scatter = create_duration_by_hour_scatter(df_ent, colors)
# st.plotly_chart(fig_scatter, use_container_width=True)
```

---

## 6. Indicador de Tasa de Rechazo

**Gráfico estilo "número grande" mejorado**

```python
def create_rejection_rate_indicator(df_ent, colors):
    """
    Crea un indicador visual de tasa de rechazo/pérdida
    """
    total = len(df_ent)
    atendidas = int((df_ent["atendida"] == True).sum())
    perdidas = total - atendidas
    tasa = round((perdidas / total * 100) if total > 0 else 0)
    
    fig = go.Figure(data=[
        go.Indicator(
            mode="number+delta",
            value=tasa,
            title={"text": "Tasa de Pérdida (%)"},
            number={"font": {"size": 50, "color": colors["red"] if tasa > 30 else colors["yellow"] if tasa > 15 else colors["green"]}},
            delta={"reference": 20, "relative": True, "valueformat": ".0%"}
        )
    ])
    
    fig.update_layout(
        height=200,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        font_color=colors["text"]
    )
    
    return fig

# Uso:
# fig_rate = create_rejection_rate_indicator(df_ent, colors)
# st.plotly_chart(fig_rate, use_container_width=True)
```

---

## 7. Tabla con Micrográficos (Sparklines)

**Tabla de agentes con mini gráficos integrados**

```python
def create_agent_table_with_sparklines(df_ent, colors):
    """
    Crea una tabla con mini gráficos de tendencia por agente
    """
    # Datos de ejemplo (en producción, usar datos reales)
    agentes_data = []
    
    for agente in df_ent["agente"].dropna().unique():
        sub = df_ent[df_ent["agente"] == agente]
        total = len(sub)
        atendidas = int((sub["atendida"] == True).sum())
        
        agentes_data.append({
            "Agente": agente,
            "Total": total,
            "Atendidas": atendidas,
            "Perdidas": total - atendidas,
            "% Atención": round(atendidas / total * 100) if total > 0 else 0,
            "Dur. Prom.": fmt_dur(int(sub[sub["atendida"]]["duracion"].mean()) if len(sub[sub["atendida"]]) > 0 else 0)
        })
    
    df_table = pd.DataFrame(agentes_data).sort_values("% Atención", ascending=False)
    
    # Crear tabla interactiva con Plotly
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["<b>" + col + "</b>" for col in df_table.columns],
            fill_color=colors["primary"],
            align="center",
            font=dict(color=colors["card"], size=12)
        ),
        cells=dict(
            values=[df_table[col] for col in df_table.columns],
            fill_color=colors["card2"],
            align="center",
            font=dict(color=colors["text"], size=11),
            line_color=colors["border"]
        )
    )])
    
    fig.update_layout(
        height=len(df_table) * 40 + 100,
        plot_bgcolor=colors["plot_bg"],
        paper_bgcolor=colors["card"],
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    return fig, df_table

# Uso:
# fig_table, df_table = create_agent_table_with_sparklines(df_ent, colors)
# st.plotly_chart(fig_table, use_container_width=True)
# st.dataframe(df_table, use_container_width=True)
```

---

## 8. Gráfico de Radar - Desempeño Multidimensional

**Compara múltiples dimensiones de desempeño de agentes**

```python
def create_radar_chart(df_ent, colors):
    """
    Crea un gráfico radar con múltiples métricas de agentes
    """
    agentes = df_ent["agente"].dropna().unique()[:5]  # Top 5
    
    metrics = []
    for agente in agentes:
        sub = df_ent[df_ent["agente"] == agente]
        
        tasa_atencion = int((sub["atendida"] == True).sum() / len(sub) * 100) if len(sub) > 0 else 0
        duracion_prom = int(sub[sub["atendida"]]["duracion"].mean()) if len(sub[sub["atendida"]]) > 0 else 0
        volumen = min(len(sub) * 2, 100)  # Normalizar
        
        metrics.append({
            "agente": agente,
            "Atención": tasa_atencion,
            "Duración": min(duracion_prom // 3, 100),  # Normalizar
            "Volumen": volume,
            "Consistencia": 100 - abs(tasa_atencion - 80)  # Métrica ficticia
        })
    
    df_radar = pd.DataFrame(metrics)
    
    fig = go.Figure()
    
    for _, row in df_radar.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[row["Atención"], row["Duración"], row["Volumen"], row["Consistencia"]],
            theta=["Tasa Atención", "Duración", "Volumen", "Consistencia"],
            fill="toself",
            name=row["agente"]
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor=colors["grid"]
            ),
            bgcolor=colors["plot_bg"]
        ),
        height=500,
        paper_bgcolor=colors["card"],
        font_color=colors["text"],
        title="Desempeño Multidimensional de Agentes"
    )
    
    return fig

# Uso:
# fig_radar = create_radar_chart(df_ent, colors)
# st.plotly_chart(fig_radar, use_container_width=True)
```

---

## 📌 Cómo Integrar Estos Gráficos

### Opción 1: Agregarlo a tu código principal
```python
# En tu archivo app_mejorado.py, después de las funciones existentes

def create_sankey_flow(df_ent, colors):
    # ... código aquí ...
    pass

# Luego en tu sección de tabs:
with tab_analisis:
    st.markdown("#### 📊 Análisis Avanzado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_sankey = create_sankey_flow(df_ent, colors)
        st.plotly_chart(fig_sankey, use_container_width=True)
    
    with col2:
        fig_box = create_duration_boxplot(df_ent, colors)
        st.plotly_chart(fig_box, use_container_width=True)
```

### Opción 2: Crear un archivo separado
```python
# gráficos_avanzados.py
import plotly.graph_objects as go
import plotly.express as px

def create_sankey_flow(df_ent, colors):
    # ... código ...
    pass

# En tu app principal:
from graficos_avanzados import create_sankey_flow

fig = create_sankey_flow(df_ent, colors)
st.plotly_chart(fig, use_container_width=True)
```

---

## 🎯 Recomendaciones

1. **Para KPIs**: Usa `create_gauge_chart()`
2. **Para tendencias**: Usa `create_temporal_trend()`
3. **Para patrones**: Usa `create_duration_by_hour_scatter()` o `create_heatmap_by_hour()`
4. **Para comparativas**: Usa `create_agent_comparison()` o `create_radar_chart()`
5. **Para flujos**: Usa `create_sankey_flow()`

---

**¡Éxito con tu dashboard! 🚀**
