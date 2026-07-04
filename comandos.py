# ============================================================
#  JARVIS - Comandos del sistema (version completa)
# ============================================================
import subprocess, webbrowser, os, re, winreg
from datetime import datetime
from difflib import SequenceMatcher
from logger import log
import volumen, youtube
from clima import obtener_clima
from apis import wikipedia, noticias, precio_crypto, chiste, parsear_conversion
from sistema import (info_sistema, info_ram, info_cpu, info_disco, info_bateria,
                     procesos_top, cerrar_proceso, limpiar_temporales,
                     modo_rendimiento, suspender)
from automatizacion import buscar_archivo, abrir_archivo_encontrado, listar_ventanas, cerrar_ventana
import protocolos, historial, red, pomodoro, guia
from config import CIUDAD_CLIMA

RUTAS = {
    "chrome":       r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "calc":         r"C:\Windows\System32\calc.exe",
    "notepad":      r"C:\Windows\System32\notepad.exe",
    "explorer":     r"C:\Windows\explorer.exe",
    "snippingtool": r"C:\Windows\System32\SnippingTool.exe",
    "spotify":      r"C:\Users\colqu\AppData\Roaming\Spotify\Spotify.exe",
    "steam":        r"C:\Program Files (x86)\Steam\steam.exe",
    "battlenet":    r"C:\Program Files (x86)\Battle.net\Battle.net.exe",
    "lghub":        r"C:\Program Files\LGHUB\lghub.exe",
    "taskmgr":      r"C:\Windows\System32\Taskmgr.exe",
    "mspaint":      r"C:\Windows\System32\mspaint.exe",
    "vscode":       r"C:\Users\colqu\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "discord":      r"C:\Users\colqu\AppData\Local\Discord\Update.exe",
    "obs":          r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    "streamlabs":   r"C:\Program Files\Streamlabs OBS\Streamlabs OBS.exe",
}

JUEGOS_STEAM = {
    "tekken 8": "1778820", "tekken 7": "389730", "tekken": "1778820",
    "cs2": "730", "counter strike": "730", "brawlhalla": "393380",
}

# ─────────────────────────────────────────────────────────────
# Utilidades de apertura
# ─────────────────────────────────────────────────────────────

def _sim(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def _abrir_app(nombre):
    ruta = RUTAS.get(nombre, nombre)
    log.info(f"Abriendo: {ruta}")
    try:
        subprocess.Popen([ruta],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        return True
    except Exception as e:
        log.error(f"[FAIL] Popen: {e}")
    try:
        os.startfile(ruta)
        return True
    except Exception as e:
        log.error(f"[FAIL] startfile: {e}")
    return False

def _buscar_en_registro_fuzzy(nombre):
    claves = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
    ]
    candidatos = []
    for clave_base in claves:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, clave_base) as base:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(base, i)
                        sub_norm = sub.lower().replace(".exe","").replace("-"," ").replace("_"," ")
                        s = _sim(nombre, sub_norm)
                        if nombre in sub_norm or s > 0.65:
                            with winreg.OpenKey(base, sub) as k:
                                ruta, _ = winreg.QueryValueEx(k, "")
                                if ruta and os.path.exists(ruta):
                                    candidatos.append((s, ruta))
                        i += 1
                    except OSError:
                        break
        except OSError:
            continue
    candidatos.sort(reverse=True)
    return [r for _, r in candidatos]

def _buscar_en_carpetas_fuzzy(nombre):
    carpetas = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.join(os.environ.get("LOCALAPPDATA",""), "Programs"),
        os.path.join(os.environ.get("APPDATA",""), ""),
    ]
    nombre_sin_sp = nombre.replace(" ","")
    candidatos = []
    for carpeta in carpetas:
        if not os.path.isdir(carpeta):
            continue
        for root, dirs, files in os.walk(carpeta):
            depth = root.replace(carpeta,"").count(os.sep)
            if depth > 3:
                dirs[:] = []
                continue
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                f_norm   = f.lower().replace(".exe","").replace("-"," ").replace("_"," ")
                f_sin_sp = f_norm.replace(" ","")
                if nombre_sin_sp in f_sin_sp or f_sin_sp in nombre_sin_sp:
                    candidatos.append((1.0, os.path.join(root, f)))
                    continue
                s = _sim(nombre, f_norm)
                if s > 0.60:
                    candidatos.append((s, os.path.join(root, f)))
    if not candidatos:
        return None
    candidatos.sort(reverse=True)
    return candidatos[0][1]

def _abrir_programa_por_nombre(nombre):
    """Abre un programa buscándolo por nombre con fuzzy matching en múltiples fuentes."""
    nombre_norm = nombre.lower().strip()

    # 1. Alias exactos en RUTAS
    for alias, ruta in RUTAS.items():
        if alias in nombre_norm or nombre_norm in alias:
            return _abrir_app(alias)

    # 2. Alias fuzzy en RUTAS
    mejor_alias, mejor_s = None, 0.0
    for alias in RUTAS:
        s = _sim(nombre_norm, alias)
        if s > mejor_s:
            mejor_s, mejor_alias = s, alias
    if mejor_s > 0.72:
        log.info(f"Alias fuzzy: '{nombre_norm}' -> '{mejor_alias}' ({mejor_s:.2f})")
        return _abrir_app(mejor_alias)

    # 3. Exe directo en PATH
    exe_name = nombre_norm.replace(" ","") + ".exe"
    try:
        subprocess.Popen(exe_name,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        return True
    except Exception:
        pass

    # 4. Registro de Windows (fuzzy)
    candidatos = _buscar_en_registro_fuzzy(nombre_norm)
    if candidatos:
        try:
            subprocess.Popen([candidatos[0]],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            return True
        except Exception:
            pass

    # 5. Carpetas de instalación (fuzzy)
    ruta = _buscar_en_carpetas_fuzzy(nombre_norm)
    if ruta:
        try:
            subprocess.Popen([ruta],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            return True
        except Exception:
            pass

    # 6. Menú inicio (fuzzy en .lnk)
    for start_menu in [
        os.path.join(os.environ.get("APPDATA",""), "Microsoft","Windows","Start Menu","Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]:
        for root, dirs, files in os.walk(start_menu):
            for f in files:
                if f.lower().endswith(".lnk"):
                    lnk = f.lower().replace(".lnk","").replace("-"," ").replace("_"," ")
                    if nombre_norm in lnk or _sim(nombre_norm, lnk) > 0.68:
                        try:
                            os.startfile(os.path.join(root, f))
                            return True
                        except Exception:
                            pass

    log.warning(f"No se encontro el programa: {nombre}")
    return False

def _abrir_url(url):
    webbrowser.open(url)

def _juego_steam(nombre):
    n = nombre.lower().strip()
    for key, app_id in JUEGOS_STEAM.items():
        if key in n or n in key:
            _abrir_url(f"steam://rungameid/{app_id}")
            return
    _abrir_url(f"https://store.steampowered.com/search/?term={n}")

_hablar_callback = None
def set_hablar_callback(fn):
    global _hablar_callback
    _hablar_callback = fn


# ─────────────────────────────────────────────────────────────
# ejecutar_tags(texto_cerebro) — parsea [TAGS] del cerebro
# ─────────────────────────────────────────────────────────────

def ejecutar_tags(texto_cerebro):
    """
    Extrae y ejecuta los [COMMAND_TAGS] de la respuesta del cerebro.
    Devuelve el texto hablado limpio (sin tags), combinado con
    el resultado de los tags que producen información (hora, clima, RAM…).
    """
    import re, memoria as _mem
    if not texto_cerebro:
        return texto_cerebro

    nombre = _mem.get_nombre_usuario() if hasattr(_mem, "get_nombre_usuario") else "señor"

    # Extraer todos los [TAG] o [TAG:arg]
    tags = re.findall(r'\[([A-Z_]+)(?::([^\]]+))?\]', texto_cerebro)

    # Texto hablado = respuesta sin los tags
    texto_hablado = re.sub(r'\[[A-Z_]+(?::[^\]]+)?\]', '', texto_cerebro)
    texto_hablado = re.sub(r'\s{2,}', ' ', texto_hablado).strip()

    resultados_info = []
    for tag, arg in tags:
        try:
            res = _ejecutar_tag(tag, arg.strip() if arg else "", nombre)
            if res:
                resultados_info.append(res)
        except Exception as e:
            log.error(f"[TAG:{tag}] error: {e}")

    if resultados_info:
        info = " ".join(resultados_info)
        return (texto_hablado + " " + info).strip() if texto_hablado else info

    return texto_hablado or texto_cerebro


def _ejecutar_tag(tag, arg, nombre):
    """
    Ejecuta un tag individual del cerebro.
    Retorna texto hablable si el tag produce info; None si es acción silenciosa.
    """
    import subprocess as _sp
    from apis import wikipedia, noticias, precio_crypto, chiste, tipo_cambio, parsear_conversion

    # ── Apps ──────────────────────────────────────────────────
    _APP = {
        "ABRIR_CHROME":      "chrome",      "ABRIR_SPOTIFY":   "spotify",
        "ABRIR_STEAM":       "steam",       "ABRIR_BATTLENET": "battlenet",
        "ABRIR_VSCODE":      "vscode",      "ABRIR_DISCORD":   "discord",
        "ABRIR_OBS":         "obs",         "ABRIR_LGHUB":     "lghub",
        "ABRIR_CALCULADORA": "calc",        "ABRIR_NOTEPAD":   "notepad",
        "ABRIR_EXPLORADOR":  "explorer",    "ABRIR_PAINT":     "mspaint",
        "ABRIR_TASKMGR":     "taskmgr",
    }
    if tag in _APP:
        _abrir_app(_APP[tag]); return None
    if tag == "ABRIR_GOOGLE":   _abrir_url("https://www.google.com");  return None
    if tag == "ABRIR_YOUTUBE":  _abrir_url("https://www.youtube.com"); return None
    if tag == "CERRAR_APP":     return cerrar_proceso(arg) if arg else None
    if tag == "ABRIR_WEB":      _abrir_url(arg); return None
    if tag == "ABRIR_JUEGO":    _juego_steam(arg); return None
    if tag == "ABRIR_PROGRAMA": _abrir_programa_por_nombre(arg); return None

    # ── Sistema ───────────────────────────────────────────────
    if tag == "INFO_SISTEMA":    return info_sistema()
    if tag == "INFO_RAM":        return info_ram()
    if tag == "INFO_CPU":        return info_cpu()
    if tag == "INFO_DISCO":      return info_disco()
    if tag == "INFO_BATERIA":    return info_bateria()
    if tag == "TOP_PROCESOS":    return procesos_top()
    if tag == "LIMPIAR_TEMP":    return limpiar_temporales()
    if tag == "RENDIMIENTO_ALTO":  modo_rendimiento(True);  return None
    if tag == "MODO_EQUILIBRADO":  modo_rendimiento(False); return None
    if tag == "SUSPENDER":         suspender();             return None
    if tag == "APAGAR_PC":
        _sp.run(["shutdown", "/s", "/t", "30"], shell=True)
        return f"El equipo se apagará en 30 segundos, {nombre}."
    if tag == "REINICIAR_PC":
        _sp.run(["shutdown", "/r", "/t", "30"], shell=True)
        return f"Reiniciando en 30 segundos, {nombre}."
    if tag == "CANCELAR_APAGADO":
        _sp.run(["shutdown", "/a"], shell=True)
        return f"Apagado cancelado, {nombre}."

    # ── Ventanas / Protocolos ─────────────────────────────────
    if tag == "LISTAR_VENTANAS":   return listar_ventanas()
    if tag == "LISTAR_PROTOCOLOS": return protocolos.listar_protocolos()
    if tag == "PROTOCOLO":
        return protocolos.ejecutar_protocolo(arg, hablar_fn=_hablar_callback) if arg else None
    if tag == "CREAR_PROTOCOLO":
        partes = arg.split("|", 1)
        if len(partes) == 2 and hasattr(protocolos, "crear_protocolo"):
            return protocolos.crear_protocolo(partes[0].strip(),
                                              [a.strip() for a in partes[1].split(",")])
        return None

    # ── Volumen ───────────────────────────────────────────────
    if tag == "SUBIR_VOLUMEN": return volumen.subir()
    if tag == "BAJAR_VOLUMEN": return volumen.bajar()
    if tag == "SILENCIAR":     return volumen.silenciar()
    if tag == "VOL_INFO":
        return f"El volumen está al {volumen.obtener()} por ciento, {nombre}."

    # ── Fecha / hora ─────────────────────────────────────────
    if tag == "QUE_HORA":
        h = datetime.now()
        return f"Son las {h.strftime('%H:%M')}, {nombre}."
    if tag == "QUE_FECHA":
        d = datetime.now()
        dias  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
        meses = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
        return f"Hoy es {dias[d.weekday()]}, {d.day} de {meses[d.month-1]} de {d.year}, {nombre}."

    # ── Información ───────────────────────────────────────────
    if tag == "CLIMA":       return obtener_clima(CIUDAD_CLIMA)
    if tag == "NOTICIAS":    return noticias(arg or "general")
    if tag == "WIKIPEDIA":   return wikipedia(arg) if arg else None
    if tag == "CRYPTO":      return precio_crypto(arg) if arg else None
    if tag == "DIVISA":      return parsear_conversion(arg) if arg else None
    if tag == "CHISTE":      return chiste()
    if tag == "INFO_RED":    return red.info_red()
    if tag == "HAY_INTERNET":
        hay = red.hay_internet()
        return (f"Hay conexión a internet, {nombre}." if hay
                else f"No hay conexión a internet, {nombre}.")

    # ── Historial ─────────────────────────────────────────────
    if tag == "HISTORIAL":
        return historial.obtener_recientes()
    if tag == "HISTORIAL_HOY":
        fn = getattr(historial, "obtener_hoy", historial.obtener_recientes)
        return fn()

    # ── Pomodoro ──────────────────────────────────────────────
    if tag == "NO_MOLESTAR_ON":  return pomodoro.activar_no_molestar()
    if tag == "NO_MOLESTAR_OFF": return pomodoro.desactivar_no_molestar()
    if tag == "POMODORO":
        kw = {"hablar_fn": _hablar_callback}
        if arg and arg.isdigit(): kw["minutos"] = int(arg)
        return pomodoro.iniciar_pomodoro(**kw)
    if tag == "POMODORO_CANCEL": return pomodoro.cancelar_pomodoro()

    # ── Guías ─────────────────────────────────────────────────
    if tag == "GUIA":         return guia.iniciar_guia(arg) if arg else None
    if tag == "SIGUIENTE_PASO": return guia.siguiente_paso()
    if tag == "CANCELAR_GUIA": return guia.cancelar_guia()

    # ── Archivos ──────────────────────────────────────────────
    if tag == "BUSCAR_ARCHIVO": return buscar_archivo(arg) if arg else None
    if tag == "ABRIR_ARCHIVO":  return abrir_archivo_encontrado(arg) if arg else None

    # ── Búsqueda web ─────────────────────────────────────────
    if tag == "BUSCAR_GOOGLE":
        _abrir_url(f"https://www.google.com/search?q={arg.replace(' ','+')}"); return None
    if tag == "BUSCAR_YOUTUBE":
        _abrir_url(f"https://www.youtube.com/results?search_query={arg.replace(' ','+')}"); return None
    if tag == "REPRODUCIR_YOUTUBE":
        return youtube.reproducir(arg) if arg else None
    if tag == "REPRODUCIR_SPOTIFY":
        _abrir_url(f"https://open.spotify.com/search/{arg.replace(' ','%20')}"); return None

    # ── Captura / Visión ──────────────────────────────────────
    if tag == "CAPTURA_PANTALLA":
        _abrir_app("snippingtool"); return None
    if tag == "LEER_PANTALLA":
        try:
            from vision import leer_pantalla as _leer
            return _leer()
        except Exception as e:
            return f"No pude leer la pantalla: {e}"
    if tag == "ANALIZAR_PANTALLA":
        try:
            from vision import analizar_pantalla_con_ia
            from groq import Groq
            from config import API_KEY, MODELO
            return analizar_pantalla_con_ia(
                arg or "¿Qué hay en esta pantalla?", Groq(api_key=API_KEY), MODELO)
        except Exception as e:
            return f"No pude analizar la pantalla: {e}"

    # ── Traducción ────────────────────────────────────────────
    if tag == "TRADUCIR":
        partes = arg.split("|", 1)
        if len(partes) == 2:
            try:
                from traduccion import traducir
                return traducir(partes[0].strip(), partes[1].strip())
            except Exception as e:
                return f"No pude traducir: {e}"
        return None

    # ── Calendario ────────────────────────────────────────────
    if tag == "CALENDAR_SETUP":
        try:
            from calendar_mod import setup_calendar
            return setup_calendar()
        except Exception as e:
            return f"Error configurando calendario: {e}"
    if tag == "CALENDAR_HOY":
        try:
            from calendar_mod import obtener_eventos_hoy
            return obtener_eventos_hoy()
        except Exception as e:
            return f"Error en calendario: {e}"
    if tag == "CALENDAR_SEMANA":
        try:
            from calendar_mod import obtener_eventos_semana
            return obtener_eventos_semana()
        except Exception as e:
            return f"Error en calendario: {e}"
    if tag == "CALENDAR_CREAR":
        try:
            from calendar_mod import crear_evento
            partes = arg.split("|")
            if len(partes) == 3:
                return crear_evento(partes[0].strip(), partes[1].strip(), partes[2].strip())
        except Exception as e:
            return f"Error en calendario: {e}"

    # ── OBS ───────────────────────────────────────────────────
    if tag == "OBS_INICIAR_STREAM":
        try:
            from obs_control import iniciar_stream; return iniciar_stream()
        except Exception as e: return f"Error OBS: {e}"
    if tag == "OBS_DETENER_STREAM":
        try:
            from obs_control import detener_stream; return detener_stream()
        except Exception as e: return f"Error OBS: {e}"
    if tag == "OBS_INICIAR_GRABACION":
        try:
            from obs_control import iniciar_grabacion; return iniciar_grabacion()
        except Exception as e: return f"Error OBS: {e}"
    if tag == "OBS_DETENER_GRABACION":
        try:
            from obs_control import detener_grabacion; return detener_grabacion()
        except Exception as e: return f"Error OBS: {e}"
    if tag == "OBS_ESCENA":
        try:
            from obs_control import cambiar_escena; return cambiar_escena(arg)
        except Exception as e: return f"Error OBS: {e}"

    # ── Automatización (click, teclado) ───────────────────────
    if tag == "CLICK":
        try:
            import pyautogui; x, y = map(int, arg.split(","))
            pyautogui.click(x, y)
        except Exception: pass
        return None
    if tag == "ESCRIBIR_EN":
        try:
            import pyautogui; pyautogui.typewrite(arg, interval=0.05)
        except Exception: pass
        return None
    if tag == "ATAJO":
        try:
            import pyautogui; pyautogui.hotkey(*[t.strip() for t in arg.split("+")])
        except Exception: pass
        return None

    # ── Recordatorio ──────────────────────────────────────────
    if tag == "RECORDATORIO":
        try:
            from recordatorios import parsear_y_crear
            return parsear_y_crear(f"[RECORDATORIO:{arg}]", _hablar_callback)
        except Exception as e:
            return f"Error recordatorio: {e}"

    log.warning(f"Tag desconocido: [{tag}:{arg}]")
    return None


# ─────────────────────────────────────────────────────────────
# Función principal: ejecutar(texto)
# Retorna (ejecutado: bool, respuesta: str)
# ─────────────────────────────────────────────────────────────

def ejecutar(texto):
    """
    Interpreta y ejecuta un comando de voz/texto.
    Retorna (ejecutado: bool, respuesta: str).
    Si no reconoce el comando, retorna (False, "").
    """
    import memoria as _mem

    if not texto:
        return False, ""

    t      = texto.lower().strip()
    nombre = _mem.get_nombre_usuario() if hasattr(_mem, "get_nombre_usuario") else "señor"

    # ── Guía activa: prioridad máxima ─────────────────────────
    if guia.hay_guia_activa():
        if any(w in t for w in ["siguiente", "continúa", "continua", "adelante",
                                 "próximo", "proximo", "siguiente paso"]):
            return True, guia.siguiente_paso()
        if "cancelar" in t and "guia" in t:
            return True, guia.cancelar_guia()
        if "cancela" in t and "guia" in t:
            return True, guia.cancelar_guia()

    # ── Fecha y hora ─────────────────────────────────────────
    if any(w in t for w in ["qué hora", "que hora", "hora es", "hora actual",
                             "dime la hora", "qué horas son", "que horas son"]):
        h = datetime.now()
        return True, f"Son las {h.strftime('%H:%M')}, {nombre}."

    if any(w in t for w in ["qué día", "que dia", "qué fecha", "que fecha",
                             "fecha de hoy", "día es hoy", "dia es hoy"]):
        d = datetime.now()
        dias   = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
        meses  = ["enero","febrero","marzo","abril","mayo","junio",
                  "julio","agosto","septiembre","octubre","noviembre","diciembre"]
        return True, (f"Hoy es {dias[d.weekday()]}, "
                      f"{d.day} de {meses[d.month-1]} de {d.year}, {nombre}.")

    # ── YouTube / música ──────────────────────────────────────
    m = re.search(r'(?:reproduce|pon|coloca|busca en youtube|buscar en youtube)\s+(.+)', t)
    if m:
        return True, youtube.reproducir(m.group(1).strip())

    # ── Abrir aplicaciones / sitios web ───────────────────────
    m = re.search(r'(?:abre|inicia|ejecuta|lanza|arranca|abrir|iniciar)\s+(.+)', t)
    if m:
        app = m.group(1).strip()

        # Juego de Steam
        for key in JUEGOS_STEAM:
            if key in app:
                _juego_steam(app)
                return True, f"Abriendo {app} en Steam, {nombre}."

        # Sitios web comunes
        sitios = {
            "google":   "https://www.google.com",
            "youtube":  "https://www.youtube.com",
            "twitch":   "https://www.twitch.tv",
            "github":   "https://www.github.com",
            "chatgpt":  "https://chat.openai.com",
            "chat gpt": "https://chat.openai.com",
            "netflix":  "https://www.netflix.com",
            "spotify":  "https://open.spotify.com",
            "reddit":   "https://www.reddit.com",
        }
        for nombre_sitio, url in sitios.items():
            if nombre_sitio in app:
                _abrir_url(url)
                return True, f"Abriendo {nombre_sitio.capitalize()}, {nombre}."

        # App local (con fallback fuzzy)
        ok = _abrir_programa_por_nombre(app)
        if ok:
            return True, f"Abriendo {app}, {nombre}."
        return True, f"No encontré '{app}' en el sistema, {nombre}."

    # ── Volumen ───────────────────────────────────────────────
    if any(w in t for w in ["sube el volumen", "subir volumen", "volumen arriba",
                             "aumenta el volumen", "aumentar volumen", "sube volumen"]):
        return True, volumen.subir()

    if any(w in t for w in ["baja el volumen", "bajar volumen", "volumen abajo",
                             "reduce el volumen", "bajar el volumen", "baja volumen"]):
        return True, volumen.bajar()

    if any(w in t for w in ["silencia", "silenciar", "mute", "mutea",
                             "sin sonido", "quita el sonido"]):
        return True, volumen.silenciar()

    if re.search(r'\bvolumen\b', t) and not any(
            w in t for w in ["sube","baja","aumenta","reduce","silencia"]):
        v = volumen.obtener()
        return True, f"El volumen está al {v} por ciento, {nombre}."

    # ── Clima ─────────────────────────────────────────────────
    if any(w in t for w in ["clima", "tiempo", "temperatura",
                             "lluvia", "pronóstico", "pronostico", "va a llover",
                             "hace calor", "hace frío", "hace frio"]):
        return True, obtener_clima(CIUDAD_CLIMA)

    # ── Sistema / hardware ────────────────────────────────────
    if any(w in t for w in ["ram", "memoria ram", "uso de memoria", "uso ram"]):
        return True, info_ram()

    if any(w in t for w in ["cpu", "procesador", "uso del procesador", "uso de cpu",
                             "uso cpu", "carga del procesador"]):
        return True, info_cpu()

    if any(w in t for w in ["disco", "almacenamiento", "espacio en disco",
                             "espacio disco", "espacio libre"]):
        return True, info_disco()

    if any(w in t for w in ["batería", "bateria", "carga del equipo",
                             "nivel de batería", "nivel de bateria"]):
        return True, info_bateria()

    if any(w in t for w in ["estado del sistema", "info del sistema",
                             "resumen del sistema", "estado sistema"]):
        return True, info_sistema()

    if any(w in t for w in ["procesos", "qué se está ejecutando", "que se esta ejecutando",
                             "procesos activos", "top procesos"]):
        return True, procesos_top()

    if any(w in t for w in ["limpiar temporales", "limpia temporales",
                             "borrar temporales", "limpiar archivos temporales"]):
        return True, limpiar_temporales()

    if any(w in t for w in ["modo rendimiento", "alto rendimiento",
                             "rendimiento alto", "máximo rendimiento", "maximo rendimiento"]):
        modo_rendimiento(True)
        return True, f"Modo de alto rendimiento activado, {nombre}."

    if any(w in t for w in ["modo equilibrado", "rendimiento equilibrado",
                             "modo normal"]):
        modo_rendimiento(False)
        return True, f"Modo equilibrado activado, {nombre}."

    if any(w in t for w in ["suspender", "suspende el equipo",
                             "modo suspensión", "modo suspension", "poner en suspensión"]):
        suspender()
        return True, f"Suspendiendo el equipo, {nombre}."

    # ── Cerrar proceso ────────────────────────────────────────
    m = re.search(r'(?:cierra|cerrar|mata|termina|finaliza|kill)\s+'
                  r'(?:el\s+)?(?:proceso\s+)?(.+)', t)
    if m and any(k in t for k in ["proceso","programa","aplicación","aplicacion"]):
        return True, cerrar_proceso(m.group(1).strip())

    # ── Red / internet ────────────────────────────────────────
    if any(w in t for w in ["estado de la red", "info de red", "velocidad de red",
                             "velocidad internet", "latencia", "ip local"]):
        return True, red.info_red()

    if any(w in t for w in ["hay internet", "tengo internet", "hay conexión",
                             "hay conexion", "conexión a internet"]):
        hay = red.hay_internet()
        return True, ("Hay conexión a internet, " + nombre + ".") if hay \
               else ("No hay conexión a internet, " + nombre + ".")

    # ── Wikipedia ─────────────────────────────────────────────
    m = re.search(r'(?:wikipedia|busca en wikipedia|qué es|que es|'
                  r'quién es|quien es|define|definición de|definicion de)\s+(.+)', t)
    if m:
        return True, wikipedia(m.group(1).strip())

    # ── Noticias ──────────────────────────────────────────────
    if any(w in t for w in ["noticias", "noticias de hoy", "últimas noticias",
                             "ultimas noticias", "novedades", "que hay de nuevo"]):
        return True, noticias()

    # ── Precio crypto / divisas ───────────────────────────────
    m = re.search(r'(?:precio de|cuánto vale|cuanto vale|valor de|'
                  r'cotización de|cotizacion de)\s+(.+?)(?:\s+en\s+|\s*$)', t)
    if m:
        coin = m.group(1).strip()
        cryptos = ["bitcoin","btc","ethereum","eth","doge","dogecoin",
                   "litecoin","ltc","solana","sol","bnb","xrp","cardano","ada"]
        if any(c in coin for c in cryptos):
            return True, precio_crypto(coin)

    # ── Conversión de divisas / monedas ───────────────────────
    conv = parsear_conversion(t)
    if conv:
        return True, conv

    # ── Chiste ────────────────────────────────────────────────
    if any(w in t for w in ["chiste", "cuéntame un chiste", "cuentame un chiste",
                             "hazme reír", "hazme reir", "algo gracioso"]):
        return True, chiste()

    # ── Pomodoro ──────────────────────────────────────────────
    if any(w in t for w in ["pomodoro", "temporizador pomodoro",
                             "iniciar pomodoro", "modo pomodoro", "técnica pomodoro"]):
        return True, pomodoro.iniciar_pomodoro(hablar_fn=_hablar_callback)

    if any(w in t for w in ["cancela pomodoro", "cancelar pomodoro",
                             "detener pomodoro", "para el pomodoro", "parar pomodoro"]):
        return True, pomodoro.cancelar_pomodoro()

    if any(w in t for w in ["no molestar", "modo no molestar", "activar no molestar",
                             "activar dnd"]):
        return True, pomodoro.activar_no_molestar()

    if any(w in t for w in ["desactivar no molestar", "reactivar notificaciones",
                             "desactivar dnd"]):
        return True, pomodoro.desactivar_no_molestar()

    # ── Protocolos ────────────────────────────────────────────
    if any(w in t for w in ["listar protocolos", "qué protocolos", "que protocolos",
                             "protocolos disponibles"]):
        return True, protocolos.listar_protocolos()

    m = re.search(r'(?:activa|ejecuta|inicia|modo)\s+'
                  r'(?:el\s+)?(?:protocolo\s+|modo\s+)?(.+)', t)
    if m:
        proto_nombre = m.group(1).strip()
        resp = protocolos.ejecutar_protocolo(proto_nombre,
                                             hablar_fn=_hablar_callback)
        if "No encontre" not in resp:
            return True, resp

    # ── Buscar / abrir archivo ────────────────────────────────
    m = re.search(r'(?:abre el archivo|abre archivo|abrir archivo|'
                  r'abre el fichero|busca el archivo|busca archivo)\s+(.+)', t)
    if m:
        return True, abrir_archivo_encontrado(m.group(1).strip())

    m = re.search(r'(?:busca|encuentra|dónde está|donde esta)\s+'
                  r'(?:el\s+)?(?:archivo|fichero)\s+(.+)', t)
    if m:
        return True, buscar_archivo(m.group(1).strip())

    # ── Ventanas ──────────────────────────────────────────────
    if any(w in t for w in ["ventanas abiertas", "qué ventanas hay",
                             "que ventanas hay", "listar ventanas",
                             "qué está abierto", "que esta abierto"]):
        return True, listar_ventanas()

    m = re.search(r'(?:cierra la ventana|cerrar ventana|cierra ventana)\s+(?:de\s+)?(.+)', t)
    if m:
        return True, cerrar_ventana(m.group(1).strip())

    # ── Guía paso a paso ─────────────────────────────────────
    m = re.search(r'(?:guía de|guia de|cómo hago|como hago|'
                  r'cómo se hace|como se hace|enseñame a|ensenme a|'
                  r'guía para|guia para)\s+(.+)', t)
    if m:
        resp = guia.iniciar_guia(m.group(1).strip())
        if "No tengo esa guia" not in resp:
            return True, resp

    if "siguiente" in t and guia.hay_guia_activa():
        return True, guia.siguiente_paso()

    # ── Historial de comandos ─────────────────────────────────
    if any(w in t for w in ["historial", "últimos comandos", "ultimos comandos",
                             "qué le dije", "que le dije", "comandos recientes"]):
        return True, historial.obtener_recientes()

    # ── Cálculos matemáticos ──────────────────────────────────
    m = re.search(r'(?:cuánto es|cuanto es|calcula|calcular|'
                  r'cuánto son|cuanto son|cuánto da|cuanto da)\s+(.+)', t)
    if m:
        expr = (m.group(1).strip()
                .replace("más","+").replace("mas","+")
                .replace("menos","-")
                .replace(" por "," * ").replace(" entre "," / ")
                .replace(" dividido entre "," / ")
                .replace("al cuadrado","**2").replace("al cubo","**3"))
        try:
            expr_safe = re.sub(r'[^0-9\+\-\*\/\.\(\)\*\* ]', '', expr)
            resultado = eval(expr_safe)  # noqa: S307
            return True, f"El resultado es {resultado}, {nombre}."
        except Exception:
            pass

    # ── Captura de pantalla ───────────────────────────────────
    if any(w in t for w in ["captura de pantalla", "screenshot",
                             "toma una captura", "recorte de pantalla"]):
        _abrir_app("snippingtool")
        return True, f"Abriendo la herramienta de captura, {nombre}."

    # ── Búsqueda web general ──────────────────────────────────
    m = re.search(r'(?:busca|googlea|buscar|busca en google)\s+(.+)', t)
    if m:
        query = m.group(1).strip()
        _abrir_url(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return True, f"Buscando '{query}' en Google, {nombre}."

    # ── No se reconoció ningún comando ────────────────────────
    return False, ""
