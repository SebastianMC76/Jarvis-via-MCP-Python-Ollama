# ============================================================
#  JARVIS - Memoria persistente (JSON local, escalable por PC)
#  Cada PC tiene su propio archivo memoria.json
# ============================================================

import json
import os
import socket
from datetime import datetime

# El archivo vive junto a los scripts, identificado por nombre de PC
_DIR      = os.path.dirname(os.path.abspath(__file__))
_PC_ID    = socket.gethostname()
_ARCHIVO  = os.path.join(_DIR, f"memoria_{_PC_ID}.json")

_ESTRUCTURA = {
    "pc":        _PC_ID,
    "creado":    "",
    "usuario":   "señor",        # nombre con el que Jarvis llama al usuario
    "hechos":    [],             # lista de strings: cosas que Jarvis recuerda
    "preferencias": {},          # dict libre: {"voz": "Jorge", ...}
}

def _cargar():
    if os.path.exists(_ARCHIVO):
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    datos = _ESTRUCTURA.copy()
    datos["creado"] = datetime.now().isoformat()
    _guardar(datos)
    return datos

def _guardar(datos):
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

# ── API pública ───────────────────────────────────────────────

def obtener_contexto():
    """Retorna un string con la memoria para incluir en el prompt."""
    datos = _cargar()
    lineas = [f"- PC: {datos['pc']}",
              f"- Nombre del usuario: {datos['usuario']}"]
    if datos["hechos"]:
        lineas.append("- Recuerdas estos hechos sobre el usuario:")
        for h in datos["hechos"][-20:]:   # máx últimos 20
            lineas.append(f"  • {h}")
    if datos["preferencias"]:
        lineas.append("- Preferencias conocidas:")
        for k, v in datos["preferencias"].items():
            lineas.append(f"  • {k}: {v}")
    return "\n".join(lineas)

def recordar(hecho: str):
    """Agrega un hecho a la memoria."""
    datos = _cargar()
    timestamp = datetime.now().strftime("%Y-%m-%d")
    entrada = f"[{timestamp}] {hecho}"
    if entrada not in datos["hechos"]:
        datos["hechos"].append(entrada)
    _guardar(datos)

def olvidar_todo():
    """Borra todos los hechos recordados."""
    datos = _cargar()
    datos["hechos"] = []
    _guardar(datos)

def set_nombre_usuario(nombre: str):
    datos = _cargar()
    datos["usuario"] = nombre
    _guardar(datos)

def get_nombre_usuario():
    return _cargar()["usuario"]

def set_preferencia(clave: str, valor: str):
    datos = _cargar()
    datos["preferencias"][clave] = valor
    _guardar(datos)

def get_preferencia(clave: str, default=None):
    return _cargar()["preferencias"].get(clave, default)
