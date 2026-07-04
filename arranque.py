# ============================================================
#  JARVIS - Sistema de arranque y estado de sesion
#  Guarda lo que estaba haciendo el usuario y saluda al inicio
# ============================================================

import json, os
from datetime import datetime
from logger import log

_DIR     = os.path.dirname(os.path.abspath(__file__))
_ARCHIVO = os.path.join(_DIR, "sesion.json")

_ESTADO_BASE = {
    "ultimo_cierre": "",
    "ultima_actividad": [],   # lista de strings con lo que hizo
    "sesiones_totales": 0,
    "primera_vez": True,
}

def _cargar():
    if os.path.exists(_ARCHIVO):
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return _ESTADO_BASE.copy()

def _guardar(datos):
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def registrar_actividad(texto):
    """Guarda lo que le pidio el usuario (max 5 ultimas)."""
    datos = _cargar()
    datos["ultima_actividad"].append(texto)
    datos["ultima_actividad"] = datos["ultima_actividad"][-5:]
    _guardar(datos)

def guardar_cierre():
    """Llamar al cerrar Jarvis."""
    datos = _cargar()
    datos["ultimo_cierre"] = datetime.now().isoformat()
    datos["primera_vez"]   = False
    _guardar(datos)
    log.info("Estado de sesion guardado.")

def construir_saludo(nombre="senor"):
    """
    Construye el mensaje de bienvenida con:
    - Hora actual
    - Clima (si esta configurado)
    - Referencia a ultima actividad
    """
    from datetime import datetime
    from clima import obtener_clima
    from apis import obtener_ciudad
    import memoria

    datos   = _cargar()
    nombre  = memoria.get_nombre_usuario()
    hora    = datetime.now()
    h       = hora.hour

    # Saludo segun hora
    if 5 <= h < 12:
        saludo_hora = "Buenos dias"
    elif 12 <= h < 19:
        saludo_hora = "Buenas tardes"
    else:
        saludo_hora = "Buenas noches"

    hora_str = hora.strftime("%I:%M %p")
    partes   = [f"{saludo_hora}, {nombre}. Son las {hora_str}."]

    # Clima
    try:
        ciudad = obtener_ciudad()
        clima  = obtener_clima(ciudad)
        partes.append(clima)
    except Exception:
        pass

    # Primera vez vs regreso
    if datos["primera_vez"]:
        partes.append("Soy Jarvis, su asistente personal. Listo para servirle.")
    else:
        ultimo = datos.get("ultimo_cierre", "")
        if ultimo:
            try:
                dt = datetime.fromisoformat(ultimo)
                diff = datetime.now() - dt
                horas = int(diff.total_seconds() // 3600)
                if horas < 1:
                    tiempo = "hace unos minutos"
                elif horas < 24:
                    tiempo = f"hace {horas} horas"
                else:
                    dias = horas // 24
                    tiempo = f"hace {dias} dia{'s' if dias > 1 else ''}"
                partes.append(f"Bienvenido de nuevo. Nos vimos {tiempo}.")
            except Exception:
                pass

        # Recordar ultima actividad
        actividad = datos.get("ultima_actividad", [])
        if actividad:
            ultima = actividad[-1]
            partes.append(f"La ultima vez me pidio: {ultima}. ?Desea continuar con algo similar?")

    datos["sesiones_totales"] = datos.get("sesiones_totales", 0) + 1
    _guardar(datos)
    return " ".join(partes)
