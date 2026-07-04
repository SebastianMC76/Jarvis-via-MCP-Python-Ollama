# ============================================================
#  JARVIS - Control de volumen (pycaw - nativo Windows)
# ============================================================

from logger import log

def _get_volume_interface():
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)

def subir(paso=0.1):
    try:
        vol = _get_volume_interface()
        actual = vol.GetMasterVolumeLevelScalar()
        nuevo = min(1.0, actual + paso)
        vol.SetMasterVolumeLevelScalar(nuevo, None)
        log.info(f"Volumen subido a {int(nuevo*100)}%")
        return f"Volumen al {int(nuevo*100)} por ciento."
    except Exception as e:
        log.error(f"Error volumen subir: {e}")
        return "No pude ajustar el volumen."

def bajar(paso=0.1):
    try:
        vol = _get_volume_interface()
        actual = vol.GetMasterVolumeLevelScalar()
        nuevo = max(0.0, actual - paso)
        vol.SetMasterVolumeLevelScalar(nuevo, None)
        log.info(f"Volumen bajado a {int(nuevo*100)}%")
        return f"Volumen al {int(nuevo*100)} por ciento."
    except Exception as e:
        log.error(f"Error volumen bajar: {e}")
        return "No pude ajustar el volumen."

def silenciar():
    try:
        vol = _get_volume_interface()
        actual = vol.GetMute()
        vol.SetMute(not actual, None)
        estado = "silenciado" if not actual else "activado"
        log.info(f"Audio {estado}")
        return f"Audio {estado}, senor."
    except Exception as e:
        log.error(f"Error silenciar: {e}")
        return "No pude silenciar el audio."

def obtener():
    try:
        vol = _get_volume_interface()
        return int(vol.GetMasterVolumeLevelScalar() * 100)
    except:
        return -1
