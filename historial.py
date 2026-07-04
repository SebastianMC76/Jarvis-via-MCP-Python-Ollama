# ============================================================
#  JARVIS - Historial de comandos legible
# ============================================================
import json, os
from datetime import datetime
from logger import log

_DIR  = os.path.dirname(os.path.abspath(__file__))
_FILE = os.path.join(_DIR, "historial_cmds.json")

def registrar(texto, respuesta=""):
    """Guarda un comando con timestamp."""
    try:
        data = _cargar()
        data.append({
            "ts":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cmd":      texto[:200],
            "resp":     respuesta[:200],
        })
        # Mantener solo los ultimos 500
        if len(data) > 500:
            data = data[-500:]
        _guardar(data)
    except Exception as e:
        log.error(f"historial registrar: {e}")

def obtener_recientes(n=10):
    """Retorna los N comandos mas recientes como texto."""
    data = _cargar()
    recientes = data[-n:]
    if not recientes:
        return "No hay comandos registrados aun."
    lineas = [f"{e['ts']}: {e['cmd']}" for e in reversed(recientes)]
    return "Ultimos comandos: " + ". ".join(lineas[:5]) + "."

def obtener_hoy():
    """Retorna comandos del dia de hoy."""
    hoy = datetime.now().strftime("%Y-%m-%d")
    data = [e for e in _cargar() if e["ts"].startswith(hoy)]
    if not data:
        return "No ejecutaste ningun comando hoy."
    return f"Hoy usaste {len(data)} comandos. El ultimo fue: {data[-1]['cmd']}."

def limpiar():
    _guardar([])
    return "Historial limpiado."

def _cargar():
    if os.path.exists(_FILE):
        try:
            with open(_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _guardar(data):
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
