# ============================================================
#  JARVIS - Protocolos y macros (secuencias de acciones)
#  "modo gaming", "modo estudio", o protocolos personalizados
# ============================================================
import json, os, time, subprocess, webbrowser
from logger import log

_DIR      = os.path.dirname(os.path.abspath(__file__))
_ARCHIVO  = os.path.join(_DIR, "protocolos.json")

# ── Protocolos predefinidos ───────────────────────────────────
PROTOCOLOS_DEFAULT = {
    "modo gaming": {
        "descripcion": "Optimiza la PC para jugar",
        "acciones": [
            {"tipo": "sistema",  "cmd": "rendimiento_alto"},
            {"tipo": "sistema",  "cmd": "limpiar_temp"},
            {"tipo": "app",      "cmd": "steam"},
            {"tipo": "cerrar",   "cmd": "discord"},
            {"tipo": "hablar",   "cmd": "Modo gaming activado. Sistema optimizado para maximo rendimiento."},
        ]
    },
    "modo estudio": {
        "descripcion": "Entorno de trabajo y estudio",
        "acciones": [
            {"tipo": "app",      "cmd": "chrome"},
            {"tipo": "url",      "cmd": "https://chat.openai.com"},
            {"tipo": "url",      "cmd": "https://www.youtube.com"},
            {"tipo": "app",      "cmd": "notepad"},
            {"tipo": "hablar",   "cmd": "Modo estudio activado. Su entorno esta listo, senor."},
        ]
    },
    "modo trabajo": {
        "descripcion": "Herramientas de trabajo",
        "acciones": [
            {"tipo": "app",      "cmd": "chrome"},
            {"tipo": "app",      "cmd": "notepad"},
            {"tipo": "hablar",   "cmd": "Modo trabajo activado. Listo para ser productivo, senor."},
        ]
    },
    "modo descanso": {
        "descripcion": "Cierra todo y pone musica",
        "acciones": [
            {"tipo": "url",      "cmd": "https://www.youtube.com/results?search_query=musica+relajante&sp=EgIQAQ%3D%3D"},
            {"tipo": "sistema",  "cmd": "volumen_50"},
            {"tipo": "hablar",   "cmd": "Modo descanso activado. Relájese, senor."},
        ]
    },
}

def _cargar():
    if os.path.exists(_ARCHIVO):
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Mergear con defaults (no sobreescribir los del usuario)
        for k, v in PROTOCOLOS_DEFAULT.items():
            if k not in data:
                data[k] = v
        return data
    _guardar(PROTOCOLOS_DEFAULT.copy())
    return PROTOCOLOS_DEFAULT.copy()

def _guardar(data):
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ejecutar_protocolo(nombre, hablar_fn=None):
    """Ejecuta un protocolo por nombre. hablar_fn(texto) para TTS."""
    protos = _cargar()

    # Busqueda flexible
    nombre_lower = nombre.lower().strip()
    proto = None
    for key in protos:
        if key in nombre_lower or nombre_lower in key:
            proto = protos[key]
            break

    if not proto:
        return f"No encontre el protocolo '{nombre}'. Protocolos disponibles: {', '.join(protos.keys())}."

    log.info(f"Ejecutando protocolo: {nombre}")
    msgs = []

    for accion in proto["acciones"]:
        tipo = accion["tipo"]
        cmd  = accion["cmd"]
        log.info(f"  Accion: {tipo} -> {cmd}")

        try:
            if tipo == "app":
                from comandos import RUTAS, _abrir_app
                _abrir_app(cmd)
                time.sleep(1.5)

            elif tipo == "url":
                webbrowser.open(cmd)
                time.sleep(1)

            elif tipo == "cerrar":
                from sistema import cerrar_proceso
                cerrar_proceso(cmd)

            elif tipo == "sistema":
                from sistema import (modo_rendimiento, limpiar_temporales,
                                     suspender)
                import volumen
                if cmd == "rendimiento_alto":
                    modo_rendimiento(True)
                elif cmd == "equilibrado":
                    modo_rendimiento(False)
                elif cmd == "limpiar_temp":
                    limpiar_temporales()
                elif cmd == "suspender":
                    suspender()
                elif cmd.startswith("volumen_"):
                    nivel = int(cmd.split("_")[1]) / 100
                    try:
                        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                        from comtypes import CLSCTX_ALL
                        d = AudioUtilities.GetSpeakers()
                        i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                        v = i.QueryInterface(IAudioEndpointVolume)
                        v.SetMasterVolumeLevelScalar(nivel, None)
                    except Exception:
                        pass

            elif tipo == "atajo":
                from automatizacion import atajo
                atajo(cmd)

            elif tipo == "hablar":
                msgs.append(cmd)
                if hablar_fn:
                    hablar_fn(cmd)

            elif tipo == "esperar":
                time.sleep(float(cmd))

        except Exception as e:
            log.error(f"Error en accion {tipo}/{cmd}: {e}")

    return msgs[0] if msgs else f"Protocolo '{nombre}' completado."

def crear_protocolo(nombre, acciones, descripcion=""):
    """Guarda un protocolo nuevo creado por el usuario."""
    protos = _cargar()
    protos[nombre.lower()] = {
        "descripcion": descripcion,
        "acciones": acciones
    }
    _guardar(protos)
    return f"Protocolo '{nombre}' guardado con {len(acciones)} acciones."

def listar_protocolos():
    protos = _cargar()
    lista = [f"{k}: {v.get('descripcion','')}" for k, v in protos.items()]
    return "Protocolos disponibles: " + ". ".join(lista) + "."

def eliminar_protocolo(nombre):
    protos = _cargar()
    if nombre.lower() in protos:
        del protos[nombre.lower()]
        _guardar(protos)
        return f"Protocolo '{nombre}' eliminado."
    return f"No encontre el protocolo '{nombre}'."
