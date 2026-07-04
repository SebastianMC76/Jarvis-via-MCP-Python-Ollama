# ============================================================
#  JARVIS - Recordatorios y alarmas
# ============================================================

import threading
import re
from datetime import datetime, timedelta
from logger import log

_recordatorios = []  # lista de timers activos

def _parsear_tiempo(texto):
    """
    Extrae minutos/segundos/horas del texto.
    Ej: "en 5 minutos", "en 1 hora", "en 30 segundos"
    Retorna segundos totales o None.
    """
    texto = texto.lower()
    total = 0
    m = re.search(r'(\d+)\s*hora', texto)
    if m: total += int(m.group(1)) * 3600
    m = re.search(r'(\d+)\s*minuto', texto)
    if m: total += int(m.group(1)) * 60
    m = re.search(r'(\d+)\s*segundo', texto)
    if m: total += int(m.group(1))
    return total if total > 0 else None

def crear_recordatorio(descripcion, segundos, callback_hablar):
    """Crea un recordatorio que llama callback_hablar tras N segundos."""
    log.info(f"Recordatorio: '{descripcion}' en {segundos}s")
    cuando = (datetime.now() + timedelta(seconds=segundos)).strftime("%I:%M %p")

    def _disparar():
        msg = f"Recordatorio, senor. {descripcion}"
        log.info(f"Disparando recordatorio: {msg}")
        callback_hablar(msg)

    t = threading.Timer(segundos, _disparar)
    t.daemon = True
    t.start()
    _recordatorios.append(t)
    return f"Recordatorio configurado para las {cuando}, senor."

def parsear_y_crear(texto_completo, callback_hablar):
    """
    Recibe el texto del comando RECORDATORIO:X|Y y lo procesa.
    X = descripcion, Y = texto de tiempo
    """
    m = re.match(r'\[RECORDATORIO:([^|]+)\|([^\]]+)\]', texto_completo)
    if not m:
        return "No entendi el recordatorio, senor."
    descripcion = m.group(1).strip()
    tiempo_texto = m.group(2).strip()
    segundos = _parsear_tiempo(tiempo_texto)
    if not segundos:
        return "No pude entender el tiempo indicado, senor."
    return crear_recordatorio(descripcion, segundos, callback_hablar)
