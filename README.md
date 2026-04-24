# 📞 Dashboard CDRs — CallMyWay

Dashboard de análisis de llamadas telefónicas conectado directamente a la API de CallMyWay. Muestra métricas, gráficos y tabla de registros con filtros y exportación a CSV.

---

## ✨ Funcionalidades

- **Métricas en tiempo real** — total de llamadas, respondidas, no respondidas, duración promedio y minutos totales
- **Gráfico de distribución** — estado de llamadas (respondidas / no respuesta / ocupado)
- **Gráfico por hora** — volumen de llamadas por hora del día
- **Tabla interactiva** — con búsqueda, filtro por estado y paginación
- **Exportar CSV** — descarga los registros filtrados
- **Modo en vivo** — muestra llamadas activas, se actualiza cada 10 segundos

---

## 🚀 Cómo correrlo localmente (Windows)

### Requisitos
- Python 3.8 o superior → [descargar aquí](https://www.python.org/downloads/)

### Pasos

**1. Clonar o descargar este repositorio**

Opción A — Con Git:
```bash
git clone https://github.com/TU_USUARIO/cdr-dashboard.git
cd cdr-dashboard
```

Opción B — Sin Git:
- Haz clic en el botón verde **Code** → **Download ZIP**
- Descomprime la carpeta
- Abre la carpeta descomprimida

**2. Instalar las dependencias**

Abre una terminal (cmd o PowerShell) dentro de la carpeta y ejecuta:
```bash
pip install -r requirements.txt
```

**3. Iniciar el dashboard**
```bash
streamlit run app.py
```

El navegador se abrirá automáticamente en `http://localhost:8501`

---

## 🔐 Credenciales

Ingresa directamente en el panel izquierdo del dashboard:

| Campo | Descripción |
|-------|-------------|
| **Usuario** | Entero de 7 dígitos (endpoint de tu cuenta) |
| **Contraseña** | Entero de 11 dígitos (enviado por correo por CallMyWay) |

Las credenciales **no se guardan** en ningún archivo. Se ingresan cada vez que abres el dashboard.

---

## 📁 Estructura del proyecto

```
cdr-dashboard/
├── app.py               # Aplicación principal (Streamlit)
├── requirements.txt     # Dependencias de Python
└── README.md            # Este archivo
```

---

## 🌐 Publicarlo en Streamlit Cloud (opcional — gratis)

Si quieres acceder al dashboard desde cualquier computadora sin instalar nada:

1. Crea una cuenta gratis en [streamlit.io](https://streamlit.io)
2. Conecta tu cuenta de GitHub
3. Haz clic en **New app** → selecciona este repositorio → `app.py`
4. Haz clic en **Deploy**

En 2 minutos tendrás una URL pública. Puedes protegerla con contraseña desde la configuración de Streamlit Cloud.

---

## ⚙️ API utilizada

Este dashboard consume la API de [CallMyWay](https://www.callmyway.com):

| Endpoint | Uso |
|----------|-----|
| `getCdrs.php?dateStart=...&dateEnd=...` | Historial por rango de fechas |
| `getCdrs.php?recent=1` | Últimas 24 horas |
| `getCdrs.php?live=1` | Llamadas activas en tiempo real |

---

## 🛠️ Solución de problemas

**"streamlit no se reconoce como comando"**
→ Cierra y vuelve a abrir la terminal después de instalar Python

**"No se pudo conectar con la API"**
→ Verifica que tu usuario y contraseña sean correctos y que tengas conexión a internet

**La tabla aparece vacía**
→ Prueba con un rango de fechas más amplio o usa el botón "Últimas 24h"

---

## 📄 Licencia

Uso interno. Los datos de llamadas son propiedad de tu cuenta en CallMyWay.
