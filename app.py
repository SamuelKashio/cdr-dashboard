# 🔌 Guía: Conectar API de CallMyWay

## ✅ Solución al problema

Si ves **"Configura las credenciales y conecta la API de CallMyWay"** pero ya las configuraste, es porque:

1. **El código no está haciendo la llamada real a la API** ← Solucionado ✓
2. **Necesitas ajustar el endpoint de la API** ← Instrucciones aquí

---

## 📦 Archivos

### Versión original
- `app_mejorado.py` - Solo modo demostración (sin API)

### Versión NUEVA con API ⭐
- `app_mejorado_v2_api.py` - **Con conexión real a CallMyWay**

**Reemplaza `app_mejorado.py` por `app_mejorado_v2_api.py`**

```bash
# Opción 1: Renombrar
mv app_mejorado.py app_mejorado_old.py
mv app_mejorado_v2_api.py app_mejorado.py

# Opción 2: Copiar
cp app_mejorado_v2_api.py app_mejorado.py
```

---

## 🔧 Configurar el Endpoint correcto

El código intenta conectar a esta URL:
```python
url = "https://api.callmyway.com/cdr"
```

**Pero necesitas verificar cuál es tu endpoint real.**

### Paso 1: Encontrar tu endpoint

Opción A: **Si tienes documentación de CallMyWay**
- Busca en tu documentación API la ruta para obtener CDRs
- Ejemplo: `https://api.callmyway.com/v1/cdr` o `https://api.tudominio.com/cdr`

Opción B: **Si usabas curl o Postman antes**
- Abre Postman o tu cliente HTTP
- Busca la petición GET que hacías a CallMyWay
- Copia la URL completa

Opción C: **Contacta a CallMyWay support**
- Pregunta cuál es el endpoint para obtener CDRs
- Deben darte algo como: `https://api.callmyway.com/cdr`

### Paso 2: Actualizar en el código

**En `app_mejorado.py`, busca la función `cargar_datos_api()` (línea ~157):**

```python
def cargar_datos_api(fecha_ini, fecha_fin):
    """Carga datos reales de CallMyWay API"""
    try:
        # ← CAMBIA ESTA LÍNEA
        url = "https://api.callmyway.com/cdr"  
        
        params = {
            "from": fecha_ini.isoformat(),
            "to": fecha_fin.isoformat(),
            "limit": 1000
        }
```

**Reemplaza la URL:**
```python
# Si tu endpoint es diferente:
url = "https://tu-endpoint-real-aqui.com/cdr"
```

---

## 📝 Ejemplos de endpoints comunes

| Proveedor | Endpoint típico |
|-----------|-----------------|
| CallMyWay | `https://api.callmyway.com/cdr` |
| CallMyWay v2 | `https://api.callmyway.com/v1/cdr` |
| API local | `http://localhost:8000/cdr` |
| Genérico | `https://tu-dominio.com/api/cdrs` |

---

## 🧪 Probar la API

### Opción 1: cURL (en terminal)

```bash
curl -u aaaaaaaa:xxxxxxxx \
  "https://api.callmyway.com/cdr?from=2026-05-13T00:00:00&to=2026-05-13T23:59:59&limit=10"
```

Reemplaza:
- `aaaaaaaa` → Tu CMW_USER
- `xxxxxxxx` → Tu CMW_PASS
- URL según tu endpoint

**Si funciona:** Recibirás datos JSON con `cdrs: [...]`
**Si falla:** Recibiras error (código HTTP)

### Opción 2: Python (en tu máquina)

```python
import requests

CMW_USER = "aaaaaaaa"
CMW_PASS = "xxxxxxxx"
url = "https://api.callmyway.com/cdr"

response = requests.get(
    url,
    params={
        "from": "2026-05-13T00:00:00",
        "to": "2026-05-13T23:59:59",
        "limit": 10
    },
    auth=(CMW_USER, CMW_PASS)
)

print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")
```

---

## ✅ Si la API funciona correctamente

Verás en el dashboard:
- ✅ Mensaje `"✅ X registros cargados de la API"`
- ✅ Datos reales en los gráficos
- ✅ KPIs actualizados con tus datos

---

## ❌ Si hay error

### Error: "Connection refused"
```
❌ Error: [Errno 111] Connection refused
```
**Causa:** El endpoint es incorrecto o CallMyWay no responde

**Solución:**
1. Verifica la URL del endpoint
2. Comprueba que tienes internet
3. Verifica si CallMyWay está en mantenimiento

### Error: "401 Unauthorized"
```
⚠️ API respondió con código 401
```
**Causa:** Credenciales incorrectas

**Solución:**
1. Verifica CMW_USER en Streamlit Cloud → Settings → Secrets
2. Verifica CMW_PASS en Streamlit Cloud → Settings → Secrets
3. Copia exactamente (sin espacios)

### Error: "404 Not Found"
```
⚠️ API respondió con código 404
```
**Causa:** URL del endpoint incorrecta

**Solución:**
1. Verifica que la URL es correcta
2. Comprueba el path (ruta) en la documentación
3. Prueba con cURL primero

### Error: "Timeout"
```
❌ Timeout: La API tardó demasiado
```
**Causa:** La API es lenta o está saturada

**Solución:**
1. Intenta reducir el rango de fechas
2. Reduce el `limit` en los params
3. Prueba en otra hora

---

## 🔧 Parámetros de la API

El código envía estos parámetros:

```python
params = {
    "from": "2026-05-13T10:30:00",    # Fecha/hora inicio
    "to": "2026-05-13T23:59:59",      # Fecha/hora fin
    "limit": 1000                      # Máximo registros
}
```

**Si tu API necesita parámetros diferentes:**

Por ejemplo, si usa `start_date` y `end_date` en lugar de `from` y `to`:

```python
params = {
    "start_date": fecha_ini.isoformat(),
    "end_date": fecha_fin.isoformat(),
    "max_results": 1000
}
```

Cambia esa línea en la función `cargar_datos_api()`.

---

## 📊 Qué espera el código

El API debe devolver JSON con este formato:

```json
{
  "status": 200,
  "message": "",
  "cdrs": [
    {
      "callid": "123456789",
      "original_callid": "123456789",
      "ani": "51912345678",
      "dnis": "5116429375",
      "detect_time": "2026-05-13 10:30:00",
      "connect_time": "2026-05-13 10:30:05",
      "disconnect_time": "2026-05-13 10:35:00",
      "duration": 295,
      "ani_user": "8668109",
      "dnis_user": "8668106",
      "end_reason": "NORMAL_CLEARING",
      "name_endpoint_ani": "Edwin Loyola",
      "name_endpoint_dnis": "Central Virtual"
    },
    ...
  ]
}
```

**Lo importante:**
- ✅ Tiene clave `"cdrs"` con array de registros
- ✅ Cada CDR tiene `callid`, `ani`, `dnis`, `duration`, etc.

Si tu API devuelve otra estructura, hay que adaptar el código.

---

## 🚀 Paso a paso para hacerlo funcionar

1. **Reemplaza** `app_mejorado.py` por `app_mejorado_v2_api.py`
2. **Verifica** el endpoint en la documentación de CallMyWay
3. **Actualiza** la URL en la función `cargar_datos_api()`
4. **Prueba** con cURL primero
5. **Sube** a GitHub y redeploy en Streamlit Cloud
6. **Haz clic** en "⟳ Consultar" o "Hoy"
7. **Verifica** que carga datos reales ✅

---

## 💬 Si sigue sin funcionar

1. **Comparte el error exacto** que ves en el dashboard
2. **Verifica tus credenciales** en Streamlit Cloud
3. **Prueba con cURL** para aislar el problema
4. **Revisa la documentación** de CallMyWay
5. **Contacta a CallMyWay support**

---

## ✨ Una vez que funcione

- ✅ Datos reales en tiempo real
- ✅ Gráficos con información actual
- ✅ KPIs actualizados automáticamente
- ✅ Sin necesidad de modo demostración

¡Que disfrutes tu dashboard! 🚀
