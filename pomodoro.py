# ============================================================
#  JARVIS - Pomodoro + modo no molestar
# ============================================================
import threading, subprocess, time
from logger import log

_pomodoro_activo = False
_dnd_activo      = False
_timer_pomodoro  = None

# ── Pomodoro ─────────────────────────────────────────────────
def iniciar_pomodoro(minutos_trabajo=25, minutos_descanso=5, ciclos=4,
                     hablar_fn=None):
    """Inicia un temporizador Pomodoro en hilo separado."""
    global _pomodoro_activo, _timer_pomodoro
    if _pomodoro_activo:
        return "Ya hay un Pomodoro activo, senor."
    _pomodoro_activo = True
    def _run():
        global _pomodoro_activo
        for ciclo in range(1, ciclos + 1):
            if not _pomodoro_activo: break
            msg = f"Ciclo {ciclo} de {ciclos}. Iniciando {minutos_trabajo} minutos de trabajo."
            log.info(f"Pomodoro: {msg}")
            if hablar_fn: hablar_fn(msg)
            _esperar(minutos_trabajo * 60)
            if not _pomodoro_activo: break
            if ciclo < ciclos:
                msg2 = f"Ciclo {ciclo} completado. Descansemos {minutos_descanso} minutos."
                if hablar_fn: hablar_fn(msg2)
                _esperar(minutos_descanso * 60)
            else:
                if hablar_fn: hablar_fn("Sesion Pomodoro completada. Excelente trabajo, senor.")
        _pomodoro_activo = False

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return f"Pomodoro iniciado: {ciclos} ciclos de {minutos_trabajo} minutos."

def cancelar_pomodoro():
    global _pomodoro_activo
    _pomodoro_activo = False
    return "Pomodoro cancelado."

def _esperar(segundos):
    """Espera en intervalos de 1s para poder cancelar."""
    for _ in range(int(segundos)):
        if not _pomodoro_activo: return
        time.sleep(1)

# ── Modo no molestar ──────────────────────────────────────────
def activar_no_molestar():
    """Silencia notificaciones de Windows (Focus Assist)."""
    global _dnd_activo
    try:
        # Silenciar audio del sistema de notificaciones via PowerShell
        subprocess.run(
            ['powershell', '-Command',
             'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" '
             '-Name "NOC_GLOBAL_SETTING_ALLOW_TOASTS_ABOVE_LOCK" -Value 0 -ErrorAction SilentlyContinue'],
            capture_output=True, timeout=5)
        _dnd_activo = True
        return "Modo no molestar activado. Las notificaciones estan silenciadas."
    except Exception as e:
        log.error(f"DND activar: {e}")
        return "Modo no molestar activado. Considera cerrar aplicaciones de mensajeria manualmente."

def desactivar_no_molestar():
    global _dnd_activo
    try:
        subprocess.run(
            ['powershell', '-Command',
             'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" '
             '-Name "NOC_GLOBAL_SETTING_ALLOW_TOASTS_ABOVE_LOCK" -Value 1 -ErrorAction SilentlyContinue'],
            capture_output=True, timeout=5)
        _dnd_activo = False
        return "Modo no molestar desactivado. Las notificaciones estan activas."
    except Exception as e:
        log.error(f"DND desactivar: {e}")
        _dnd_activo = False
        return "Notificaciones reactivadas."

def estado_dnd():
    return _dnd_activo
