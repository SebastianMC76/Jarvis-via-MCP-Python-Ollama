# ============================================================
#  JARVIS - Control de OBS Studio via WebSocket
#  pip install obsws-python
#
#  En OBS: Herramientas -> WebSocket Server Settings
#  -> Enable WebSocket server (puerto 4455, contraseña opcional)
# ============================================================
import os
from logger import log

_HOST     = "localhost"
_PORT     = 4455
_PASSWORD = ""   # Dejar vacío si OBS no tiene contraseña configurada

def _get_client():
    try:
        import obsws_python as obs
        return obs.ReqClient(host=_HOST, port=_PORT, password=_PASSWORD, timeout=3)
    except ImportError:
        raise ImportError("Instala obsws-python: pip install obsws-python")
    except Exception as e:
        raise ConnectionError(
            f"No pude conectar con OBS ({_HOST}:{_PORT}). "
            "Asegúrate de que OBS esté abierto y WebSocket activado."
        ) from e

def iniciar_stream():
    try:
        cl = _get_client()
        cl.start_stream()
        return "Transmisión iniciada, señor."
    except (ImportError, ConnectionError) as e:
        return str(e)
    except Exception as e:
        log.error(f"OBS iniciar stream: {e}")
        return "No pude iniciar la transmisión."

def detener_stream():
    try:
        cl = _get_client()
        cl.stop_stream()
        return "Transmisión detenida."
    except (ImportError, ConnectionError) as e:
        return str(e)
    except Exception as e:
        log.error(f"OBS detener stream: {e}")
        return "No pude detener la transmisión."

def iniciar_grabacion():
    try:
        cl = _get_client()
        cl.start_record()
        return "Grabación iniciada."
    except (ImportError, ConnectionError) as e:
        return str(e)
    except Exception as e:
        log.error(f"OBS iniciar grabacion: {e}")
        return "No pude iniciar la grabación."

def detener_grabacion():
    try:
        cl = _get_client()
        cl.stop_record()
        return "Grabación detenida y guardada."
    except (ImportError, ConnectionError) as e:
        return str(e)
    except Exception as e:
        log.error(f"OBS detener grabacion: {e}")
        return "No pude detener la grabación."

def cambiar_escena(nombre_escena):
    try:
        cl = _get_client()
        # Listar escenas para buscar por nombre parcial
        resp   = cl.get_scene_list()
        escenas = [s["sceneName"] for s in resp.scenes]
        destino = None
        for e in escenas:
            if nombre_escena.lower() in e.lower():
                destino = e
                break
        if not destino:
            return f"No encontré ninguna escena con el nombre '{nombre_escena}'. Escenas disponibles: {', '.join(escenas)}."
        cl.set_current_program_scene(destino)
        return f"Escena cambiada a '{destino}'."
    except (ImportError, ConnectionError) as e:
        return str(e)
    except Exception as e:
        log.error(f"OBS cambiar escena: {e}")
        return f"No pude cambiar la escena: {e}"

def obtener_escenas():
    """Retorna lista de escenas disponibles."""
    try:
        cl = _get_client()
        resp = cl.get_scene_list()
        return [s["sceneName"] for s in resp.scenes]
    except Exception as e:
        log.error(f"OBS obtener escenas: {e}")
        return []
