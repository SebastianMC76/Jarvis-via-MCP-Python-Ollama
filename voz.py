# ============================================================
#  JARVIS - Modulo de voz  (Edge TTS + STT bilingue)
#
#  ARQUITECTURA DE AUDIO:
#  _tts_activo (threading.Event) señaliza cuando el TTS está
#  reproduciendo. El STT lo consulta antes de abrir el stream
#  y espera si es necesario. Esto evita el MME error -9999
#  sin mantener un lock abierto durante el bucle de escucha.
# ============================================================

import asyncio
import threading
import edge_tts
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import numpy as np
import io, wave, tempfile, os, time, json

from config import SAMPLE_RATE
from logger import log

# ── Config runtime (cargada desde ajustes.json) ───────────────
# Antes: SILENCE_TIMEOUT, SILENCE_THRESHOLD, MAX_RECORD_SECS, IDIOMA,
# IDIOMA_ALTERNATIVO se importaban como constantes desde config.py.
# Ahora: se leen del JSON para que los cambios en AjustesPanel apliquen
# en caliente sin reiniciar.
_CFG_PATH = os.path.join(os.path.dirname(__file__), "ajustes.json")

def _cargar_runtime_cfg():
    """Lee los campos runtime desde ajustes.json. Falla suave a defaults."""
    defaults = {
        "silencio_timeout":      1.2,
        "silencio_threshold":    500,
        "max_tiempo_grabacion":  15,
        "idioma":                "es-ES",
    }
    try:
        if os.path.exists(_CFG_PATH):
            d = json.load(open(_CFG_PATH))
            for k, v in defaults.items():
                d.setdefault(k, v)
            return d
    except Exception as e:
        log.warning(f"voz.py: no pude leer ajustes.json ({e}), uso defaults")
    return defaults

_RT = _cargar_runtime_cfg()

def refrescar_runtime_cfg():
    """Recarga ajustes.json en caliente. Llamar desde main tras _aplicar_cfg."""
    global _RT
    _RT = _cargar_runtime_cfg()

# ── Estado TTS ───────────────────────────────────────────────
# Se activa justo antes de sd.play() y se limpia tras el cooldown.
# El STT espera a que esté limpio antes de abrir el micrófono.
_tts_activo = threading.Event()
_COOLDOWN_TTS = 0.8   # segundos extra tras sd.wait() antes de limpiar el flag

VOZ_EDGE     = "es-MX-JorgeNeural"
_VOICE_RATE  = "+10%"   # configurable desde ajustes
_VOICE_VOL   = "+0%"    # configurable desde ajustes

def _esperar_audio_libre(timeout=8.0):
    """Bloquea hasta que el TTS termine. Retorna True si está libre."""
    fin = time.time() + timeout
    while _tts_activo.is_set():
        if time.time() > fin:
            log.warning("Timeout esperando que TTS libere el audio.")
            return False
        time.sleep(0.05)
    return True

def esperar_fin_tts(timeout_inicio: float = 20.0,
                    stop_event=None, pausa_event=None) -> None:
    """
    Bloquea hasta que el TTS termine de hablar por completo.

    Diseñado para el modo conversación del WakeWordWorker:
      - Fase 1: espera a que _tts_activo se ACTIVE (el procesado de IA
                puede tardar varios segundos antes de que empiece el TTS).
      - Fase 2: espera a que _tts_activo se LIMPIE (incluye el cooldown
                interno de 0.8 s para liberar el dispositivo de audio).

    Parámetros
    ----------
    timeout_inicio : float
        Segundos máximos esperando que el TTS empiece. Default 20 s.
        Aumentar si las respuestas de la IA son muy lentas.
    stop_event  : threading.Event | None
        Si se activa, aborta la espera inmediatamente.
    pausa_event : threading.Event | None
        Si se activa (botón mic manual), aborta la espera.
    """
    def _abortar() -> bool:
        if stop_event  and stop_event.is_set():  return True
        if pausa_event and pausa_event.is_set(): return True
        return False

    # ── Fase 1: esperar a que TTS empiece ──────────────────────────
    t0 = time.time()
    while not _tts_activo.is_set():
        if _abortar(): return
        if time.time() - t0 > timeout_inicio:
            log.debug("esperar_fin_tts: TTS no inició dentro del tiempo límite.")
            return
        time.sleep(0.05)

    # ── Fase 2: esperar a que TTS termine (+ cooldown interno) ─────
    while _tts_activo.is_set():
        if _abortar(): return
        time.sleep(0.05)

    log.debug("esperar_fin_tts: audio libre — listo para escuchar.")

# ── Whisper ───────────────────────────────────────────────────
_whisper_model  = None
_whisper_loaded = False
_whisper_lock   = threading.Lock()

def _cargar_whisper():
    global _whisper_model, _whisper_loaded
    with _whisper_lock:
        if _whisper_loaded:
            return _whisper_model
        try:
            import whisper, sys, io as _io
            log.info("Cargando Whisper small (~465 MB)...")
            _so, _se = sys.stdout, sys.stderr
            sys.stdout = _io.StringIO()
            sys.stderr = _io.StringIO()
            try:
                _whisper_model = whisper.load_model("small")
            finally:
                sys.stdout, sys.stderr = _so, _se
            _whisper_loaded = True
            log.info("Whisper small listo.")
        except Exception as e:
            log.error(f"Whisper no disponible: {e}")
            _whisper_model  = None
            _whisper_loaded = True
        return _whisper_model

def precargar_whisper():
    threading.Thread(target=_cargar_whisper, daemon=True).start()

def _whisper_texto(audio_np):
    model = _cargar_whisper()
    if model is None:
        return ""
    try:
        f32 = audio_np.astype(np.float32).flatten() / 32768.0
        return model.transcribe(f32, language="es", fp16=False).get("text","").strip().lower()
    except Exception as e:
        log.error(f"Whisper transcripcion: {e}")
        return ""

# ── TTS ───────────────────────────────────────────────────────

def hablar(texto, callback=None):
    """Sintetiza y reproduce. Compatible con QThread (no usa asyncio.run)."""
    if callback:
        callback(texto)
    _tts_activo.set()
    try:
        # Crear siempre un event loop nuevo — evita conflictos con Qt
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_hablar_async(texto))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    except Exception as e:
        log.error(f"TTS error: {e}")
    finally:
        time.sleep(_COOLDOWN_TTS)
        _tts_activo.clear()

async def _hablar_async(texto):
    """
    Sintetiza con Edge TTS y reproduce desde RAM sin archivo temporal.
    Flujo: recopila chunks MP3 en io.BytesIO, decodifica con soundfile,
    reproduce con sounddevice. Fallback automatico a tempfile si
    soundfile no soporta BytesIO (garantiza que Jarvis nunca quede mudo).
    Los parametros de voz se leen de _RT en caliente.
    """
    voz_id = _RT.get("voz_id",        VOZ_EDGE)
    rate   = _RT.get("voz_velocidad",  _VOICE_RATE)
    vol    = _RT.get("voz_volumen",    _VOICE_VOL)

    communicate = edge_tts.Communicate(texto, voice=voz_id, rate=rate, volume=vol)

    # Fase 1: recopilar chunks MP3 de edge-tts en RAM
    # edge-tts >= 7.x yield dicts {"type":..,"data":..} en lugar de tuplas.
    # El primer chunk es SentenceBoundary (4 keys) y causaba:
    #   "too many values to unpack (expected 2, got 4)"
    mp3_buf = io.BytesIO()
    async for chunk in communicate.stream():
        if isinstance(chunk, dict):
            if chunk.get("type") == "audio":
                mp3_buf.write(chunk["data"])
        elif chunk[0] == "audio":
            mp3_buf.write(chunk[1])

    total = mp3_buf.tell()
    if total == 0:
        log.warning("TTS: edge-tts no genero audio.")
        return
    log.debug(f"TTS: {total} bytes de audio en RAM (cero disco).")

    # Fase 2: decodificar â€” intento principal desde BytesIO
    data = None
    sr_  = SAMPLE_RATE
    try:
        mp3_buf.seek(0)
        data, sr_ = sf.read(mp3_buf, dtype='float32')
        log.debug("TTS: decodificado desde BytesIO (sin disco).")
    except Exception as e_buf:
        log.warning(f"TTS: BytesIO fallo ({e_buf}), fallback a archivo temporal.")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(mp3_buf.getvalue())
            tmp_path = tmp.name
        try:
            data, sr_ = sf.read(tmp_path, dtype='float32')
            log.debug("TTS: decodificado desde archivo temporal (fallback).")
        finally:
            try: os.unlink(tmp_path)
            except: pass

    if data is None or len(data) == 0:
        log.error("TTS: no se pudo decodificar el audio.")
        return

    # Fase 3: reproducir
    dev_out = _RT.get("dispositivo_salida", -1)
    out_dev = None if dev_out < 0 else dev_out
    sd.play(data, sr_, device=out_dev)
    sd.wait()

def obtener_voces():
    return [
        ("Jorge (Mexico) - Masculino ES",  "es-MX-JorgeNeural"),
        ("Alvaro (Espana) - Masculino ES",  "es-ES-AlvaroNeural"),
        ("Dalia (Mexico) - Femenino ES",    "es-MX-DaliaNeural"),
        ("Elena (Espana) - Femenino ES",    "es-ES-ElenaNeural"),
        ("Guy (EEUU) - Masculino EN",       "en-US-GuyNeural"),
        ("Jenny (EEUU) - Femenino EN",      "en-US-JennyNeural"),
        ("Ryan (UK) - Masculino EN",        "en-GB-RyanNeural"),
    ]

def cambiar_voz(voz_id):
    global VOZ_EDGE
    VOZ_EDGE = voz_id

# ── STT ───────────────────────────────────────────────────────
_recognizer = sr.Recognizer()

def _np_a_texto(audio_np):
    """Convierte int16 ndarray a texto. Google primero, Whisper como fallback."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE); wf.writeframes(audio_np.tobytes())
    for idioma in [_RT["idioma"], "en-US"]:
        try:
            buf.seek(0)
            with sr.AudioFile(buf) as src:
                audio = _recognizer.record(src)
            texto = _recognizer.recognize_google(audio, language=idioma).lower()
            log.debug(f"Google STT ({idioma}): '{texto}'")
            return texto
        except sr.UnknownValueError:
            continue
        except sr.RequestError:
            log.warning("Google STT offline -> Whisper")
            return _whisper_texto(audio_np)
        except Exception as e:
            log.debug(f"STT exc ({idioma}): {e}")
            continue
    return ""



def listar_dispositivos():
    """
    Enumera dispositivos de audio del sistema.
    Retorna (entradas, salidas): listas de (indice, nombre).
    indice == -1 significa dispositivo por defecto del sistema.
    """
    try:
        devs    = sd.query_devices()
        entradas = [(-1, "Dispositivo por defecto del sistema")]
        salidas  = [(-1, "Dispositivo por defecto del sistema")]
        for i, d in enumerate(devs):
            nombre = d["name"][:52].strip()
            if d["max_input_channels"] > 0:
                entradas.append((i, nombre))
            if d["max_output_channels"] > 0:
                salidas.append((i, nombre))
        return entradas, salidas
    except Exception as e:
        log.warning(f"listar_dispositivos error: {e}")
        return [(-1, "Dispositivo por defecto")], [(-1, "Dispositivo por defecto")]


def _abrir_input_stream(device=None):
    """
    Abre sd.InputStream esperando que TTS libere el audio.
    device: indice sounddevice o None para default del sistema.
    Fallback automatico al default si el dispositivo es invalido.
    """
    for intento in range(10):
        if not _esperar_audio_libre(timeout=8.0):
            raise RuntimeError("TTS no libero el audio a tiempo.")
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=device
            )
            stream.start()
            return stream
        except Exception as e:
            if device is not None and intento == 0:
                log.warning(
                    f"Dispositivo entrada [{device}] no disponible ({e}). "
                    "Reintentando con default del sistema."
                )
                device = None
                continue
            log.warning(f"Abrir microfono intento {intento+1}: {e}")
            time.sleep(0.5)
    raise RuntimeError("No se pudo abrir el microfono tras 10 intentos.")


def escuchar(callback_estado=None, timeout_silencio=2.0, timeout_max=15):
    """
    Graba voz del usuario y la convierte a texto (STT).

    Flujo:
      1. Espera que TTS libere el audio.
      2. Abre el microfono configurado en Ajustes.
      3. Graba con deteccion de silencio dinamica.
      4. Convierte a texto via Google STT / Whisper offline.

    Retorna str con el texto reconocido, o None si no hubo audio.
    """
    CHUNK      = 1024
    threshold  = _RT.get("silencio_threshold", 500)
    dev_in     = _RT.get("dispositivo_entrada", -1)
    device     = None if dev_in < 0 else dev_in
    silencio_n = max(1, int(SAMPLE_RATE / CHUNK * timeout_silencio))
    max_chunks = int(SAMPLE_RATE / CHUNK * timeout_max)

    if callback_estado:
        callback_estado("listening")

    try:
        stream = _abrir_input_stream(device=device)
    except Exception as e:
        log.error(f"escuchar() no pudo abrir mic: {e}")
        if callback_estado:
            callback_estado("wake")
        return None

    buf            = []
    silencio_count = 0
    hablo          = False

    try:
        for _ in range(max_chunks):
            if _tts_activo.is_set():
                break
            block, _ = stream.read(CHUNK)
            nivel = float(np.abs(block).mean())
            if nivel > threshold:
                buf.append(block.copy())
                silencio_count = 0
                hablo = True
            elif hablo:
                buf.append(block.copy())
                silencio_count += 1
                if silencio_count >= silencio_n:
                    break
    except Exception as e:
        log.warning(f"escuchar() stream error: {e}")
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    if callback_estado:
        callback_estado("processing")

    if not hablo or not buf:
        log.debug("escuchar(): sin audio detectado sobre el umbral.")
        if callback_estado:
            callback_estado("wake")
        return None

    audio = np.concatenate(buf, axis=0)
    texto = _np_a_texto(audio)

    if callback_estado:
        callback_estado("wake")
    return texto if texto else None

# ══════════════════════════════════════════════════════════════
#  WAKE WORD — dos backends, uno público
#
#  BACKEND A (default): _escuchar_wake_word_google()
#    • Requiere internet, ~800 ms de latencia por chunk.
#    • Usado cuando NO hay access key de Porcupine configurada.
#
#  BACKEND B (recomendado): _escuchar_wake_word_porcupine()
#    • 100 % offline, ~32 ms de latencia (512 muestras a 16 kHz).
#    • "jarvis" es keyword integrado y gratuito en Porcupine.
#    • Requiere una access key GRATUITA de picovoice.ai.
#    • Configurar en Ajustes → Activación → Porcupine Access Key.
#
#  La función pública escuchar_wake_word() elige automáticamente
#  el backend según si la access key está configurada o no.
# ══════════════════════════════════════════════════════════════

# ── Porcupine — gestión de instancia global ───────────────────
_porc_inst       = None   # pvporcupine.Porcupine activo
_porc_keyword    = None   # keyword con la que fue creado
_porc_key_cached = None   # access_key con la que fue creado
_porc_lock       = threading.Lock()

def _get_porcupine(access_key: str, keyword: str):
    """
    Devuelve (y si es necesario crea) la instancia global de Porcupine.
    Thread-safe. Retorna None si pvporcupine no está instalado
    o la access_key está vacía.
    """
    global _porc_inst, _porc_keyword, _porc_key_cached

    with _porc_lock:
        kw = keyword.strip().lower() or "jarvis"

        # Reutilizar si los parámetros no cambiaron
        if (_porc_inst is not None
                and _porc_keyword    == kw
                and _porc_key_cached == access_key):
            return _porc_inst

        # Parámetros cambiaron: liberar instancia anterior
        _liberar_porcupine_sin_lock()

        if not access_key:
            return None

        try:
            import pvporcupine
            # Validar keyword contra el catálogo integrado
            disponibles = [k.lower() for k in pvporcupine.KEYWORDS]
            if kw not in disponibles:
                log.warning(
                    f"Porcupine: '{kw}' no es keyword integrado. "
                    f"Usando 'jarvis'. Disponibles: {pvporcupine.KEYWORDS}"
                )
                kw = "jarvis"

            _porc_inst       = pvporcupine.create(access_key=access_key,
                                                   keywords=[kw])
            _porc_keyword    = kw
            _porc_key_cached = access_key
            log.info(
                f"Porcupine OK — keyword='{kw}', "
                f"sample_rate={_porc_inst.sample_rate} Hz, "
                f"frame_length={_porc_inst.frame_length} muestras "
                f"({_porc_inst.frame_length/_porc_inst.sample_rate*1000:.0f} ms)"
            )
            return _porc_inst

        except ImportError:
            log.warning("pvporcupine no instalado — usa: pip install pvporcupine")
            return None
        except Exception as e:
            log.error(f"Porcupine init error: {e}")
            return None

def _liberar_porcupine_sin_lock():
    """Libera recursos de Porcupine. Llamar DENTRO de _porc_lock."""
    global _porc_inst, _porc_keyword, _porc_key_cached
    if _porc_inst is not None:
        try:
            _porc_inst.delete()
        except Exception:
            pass
        _porc_inst       = None
        _porc_keyword    = None
        _porc_key_cached = None

def liberar_porcupine():
    """Libera la instancia Porcupine. Llamar al cerrar la aplicación."""
    with _porc_lock:
        _liberar_porcupine_sin_lock()
    log.debug("Porcupine liberado.")

# ── Backend A: Google STT (fallback, requiere internet) ───────

def _escuchar_wake_word_google(wake_word: str, stop_event) -> bool:
    """
    Detecta wake word enviando chunks de 0.8 s a Google STT.
    Latencia real: 800 ms + round-trip de red (~200-500 ms).
    Fallback automático cuando Porcupine no está disponible.
    """
    chunk_n = int(SAMPLE_RATE * 0.8)
    ventana: list = []

    while True:
        if stop_event and stop_event.is_set():
            return False
        if _tts_activo.is_set():
            time.sleep(0.1); continue

        try:
            stream = _abrir_input_stream()
        except Exception as e:
            log.error(f"Wake (Google) no puede abrir mic: {e}")
            time.sleep(1.0); continue

        try:
            while True:
                if stop_event and stop_event.is_set(): return False
                if _tts_activo.is_set():               break   # cierra y espera

                bloque, _ = stream.read(chunk_n)
                nivel = np.abs(bloque).mean()
                if nivel < 80:
                    ventana = []; continue

                ventana.append(bloque.copy())
                if len(ventana) > 2:
                    ventana.pop(0)

                texto = _np_a_texto(np.concatenate(ventana, axis=0))
                if texto:
                    log.debug(f"Wake (Google) escuchó: '{texto}'")
                    if wake_word in texto:
                        log.info(f"Wake word detectada (Google STT): '{texto}'")
                        ventana = []
                        return True
        except Exception as e:
            log.warning(f"Wake (Google) stream error: {e}")
        finally:
            try: stream.stop(); stream.close()
            except: pass

# ── Backend B: Porcupine (offline, ~32 ms latencia) ──────────

def _escuchar_wake_word_porcupine(porc, stop_event) -> bool:
    """
    Detecta wake word con pvporcupine procesando frames de 32 ms.
    Ultra-bajo consumo de CPU, 100 % offline.

    Parámetros
    ----------
    porc       : pvporcupine.Porcupine — instancia ya inicializada.
    stop_event : threading.Event | None
    """
    frame_len = porc.frame_length   # 512 muestras a 16 kHz = 32 ms

    while True:
        if stop_event and stop_event.is_set():
            return False
        if _tts_activo.is_set():
            time.sleep(0.05); continue

        # Abrir stream con los parámetros exactos que Porcupine necesita
        try:
            stream = sd.InputStream(
                samplerate=porc.sample_rate,   # 16000
                channels=1,
                dtype='int16',
                blocksize=frame_len,           # exactamente 512
            )
            stream.start()
        except Exception as e:
            log.error(f"Porcupine no puede abrir mic: {e}")
            time.sleep(0.5); continue

        try:
            while True:
                if stop_event and stop_event.is_set(): return False
                if _tts_activo.is_set():               break   # cierra y espera

                pcm, _ = stream.read(frame_len)
                # Porcupine.process() necesita una lista de exactamente frame_len int16
                pcm_flat = pcm.flatten()
                if len(pcm_flat) < frame_len:
                    continue   # chunk incompleto (arranque del stream)

                resultado = porc.process(pcm_flat[:frame_len].tolist())
                if resultado >= 0:
                    log.info("Wake word detectada (Porcupine offline ✓).")
                    return True
        except Exception as e:
            log.warning(f"Porcupine stream error: {e}")
        finally:
            try: stream.stop(); stream.close()
            except: pass

# ── Función pública: dispatcher automático ────────────────────

# â”€â”€ openWakeWord â€” gestiÃ³n de instancia global â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 100 % offline, sin cuenta ni API key.
# Modelo preentrenado: "hey_jarvis" (frase: "hey jarvis").
# Descarga ~5 MB de modelos la primera vez (via Hugging Face).
_oww_model    = None
_oww_lock     = threading.Lock()
OWW_FRAME_LEN = 1280   # muestras @ 16 kHz = 80 ms por frame
OWW_THRESHOLD = 0.5    # umbral de confianza (0-1)

def _get_oww_model():
    """
    Crea (lazy) la instancia global de openWakeWord.
    Thread-safe. Retorna None si openwakeword no esta instalado.
    La descarga del modelo ocurre solo la primera vez (~5 MB).
    """
    global _oww_model
    with _oww_lock:
        if _oww_model is not None:
            return _oww_model
        try:
            from openwakeword.model import Model
            log.info("OWW: cargando modelo hey_jarvis_v0.1 (descarga ~5 MB si es la primera vez)...")
            import openwakeword.utils as _oww_utils
            _oww_utils.download_models(["hey_jarvis_v0.1"])
            _oww_model = Model(wakeword_models=["hey_jarvis_v0.1"], inference_framework="onnx")
            log.info("OWW: listo. Frase de activacion: 'hey jarvis'.")
            return _oww_model
        except ImportError:
            log.warning("openwakeword no instalado â€” pip install openwakeword")
            return None
        except Exception as e:
            log.error(f"OWW init error: {e}")
            return None

def liberar_oww():
    """Libera la instancia OWW al cerrar la aplicacion."""
    global _oww_model
    with _oww_lock:
        _oww_model = None
    log.debug("openWakeWord liberado.")


# â”€â”€ Backend B2: openWakeWord (offline, ~80 ms latencia) â”€â”€â”€â”€â”€â”€

def _escuchar_wake_word_oww(stop_event) -> bool:
    """
    Detecta 'hey jarvis' con openWakeWord.
    100 % offline, sin cuenta, sin API key.
    PrecisiÃ³n: <5 % false-reject, <0.5 activaciones falsas/hora.
    """
    oww = _get_oww_model()
    if oww is None:
        return False   # No disponible, el dispatcher usarÃ¡ el siguiente backend

    while True:
        if stop_event and stop_event.is_set(): return False
        if _tts_activo.is_set(): time.sleep(0.05); continue

        try:
            dev_in = _RT.get("dispositivo_entrada", -1)
            in_dev = None if dev_in < 0 else dev_in
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=OWW_FRAME_LEN,
                device=in_dev,
            )
            stream.start()
        except Exception as e:
            log.error(f"OWW no puede abrir mic: {e}")
            time.sleep(0.5); continue

        try:
            # Warm-up: descartar frames iniciales para estabilizar
            # el buffer interno del modelo tras reconectar el stream.
            for _ in range(8):
                if stop_event and stop_event.is_set(): return False
                frame, _ = stream.read(OWW_FRAME_LEN)
                pcm = frame.flatten()
                if len(pcm) >= OWW_FRAME_LEN:
                    with _oww_lock:
                        if _oww_model:
                            _oww_model.predict(pcm)

            # Bucle de deteccion
            while True:
                if stop_event and stop_event.is_set(): return False
                if _tts_activo.is_set():               break

                frame, _ = stream.read(OWW_FRAME_LEN)
                pcm = frame.flatten()
                if len(pcm) < OWW_FRAME_LEN: continue

                with _oww_lock:
                    if _oww_model is None: break
                    pred = _oww_model.predict(pcm)

                score = float(pred.get("hey_jarvis_v0.1", 0.0))
                if score >= OWW_THRESHOLD:
                    log.info(f"Wake word detectada (OWW offline, confianza={score:.2f}).")
                    return True
        except Exception as e:
            log.warning(f"OWW stream error: {e}")
        finally:
            try: stream.stop(); stream.close()
            except: pass


# â”€â”€ FunciÃ³n pÃºblica: dispatcher automÃ¡tico â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def escuchar_wake_word(wake_word: str = "jarvis", stop_event=None) -> bool:
    """
    Detecta la wake word. Orden de prioridad de backend:

      1. Porcupine  â€” si access_key configurada en Ajustes.
                       Frase: la wake word configurada (ej. 'jarvis').
                       Latencia: ~32 ms. Requiere key gratuita en picovoice.ai.

      2. openWakeWord â€” sin cuenta, 100 % offline.
                        Frase: 'hey jarvis'.
                        Latencia: ~80 ms. Default cuando no hay key Porcupine.

      3. Google STT   â€” fallback (requiere internet).
                        Frase: la wake word configurada.
                        Latencia: ~800 ms + red.
    """
    # Backend 1: Porcupine
    access_key = _RT.get("porcupine_access_key", "").strip()
    porc = _get_porcupine(access_key, wake_word)
    if porc is not None:
        return _escuchar_wake_word_porcupine(porc, stop_event)

    # Backend 2: openWakeWord (sin cuenta, offline)
    if _get_oww_model() is not None:
        return _escuchar_wake_word_oww(stop_event)

    # Backend 3: Google STT (fallback)
    log.debug("OWW no disponible -> Google STT fallback.")
    return _escuchar_wake_word_google(wake_word, stop_event)
