# ============================================================
#  JARVIS - Google Calendar (OAuth2)
#  Setup: pip install google-auth google-auth-oauthlib google-api-python-client
#
#  Primera vez: ejecutar setup_calendar() manualmente o decir "jarvis configura calendario"
#  Esto abre el navegador para autenticar con tu cuenta Google.
#  El token se guarda en token_calendar.json para usos futuros.
# ============================================================
import os, json
from datetime import datetime, timedelta, timezone
from logger import log

_DIR       = os.path.dirname(os.path.abspath(__file__))
_TOKEN_FILE = os.path.join(_DIR, "token_calendar.json")
_CREDS_FILE = os.path.join(_DIR, "credentials_calendar.json")
_SCOPES     = ["https://www.googleapis.com/auth/calendar"]

def _get_service():
    """Obtiene el servicio de Google Calendar autenticado."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("El módulo de Google Calendar no está disponible en este momento, señor.")

    creds = None
    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDS_FILE):
                raise FileNotFoundError(
                    "El calendario de Google no está configurado aún, señor. "
                    "Dígame 'configura el calendario' cuando quiera activarlo."
                )
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS_FILE, _SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

def _formato_evento(ev):
    """Formatea un evento de Google Calendar para leer en voz."""
    inicio = ev["start"].get("dateTime", ev["start"].get("date", ""))
    titulo = ev.get("summary", "Sin título")
    try:
        dt = datetime.fromisoformat(inicio)
        hora_str = dt.strftime("%H:%M")
        return f"{titulo} a las {hora_str}"
    except Exception:
        return titulo

def _calendario_listo():
    """Retorna True si el calendario está autenticado y listo."""
    return os.path.exists(_TOKEN_FILE)

def setup_calendar():
    """Inicia el flujo OAuth para autenticar Google Calendar. Llámalo una vez."""
    try:
        _get_service()
        return "Calendario de Google autenticado correctamente, señor."
    except Exception as e:
        return str(e)

def obtener_eventos_hoy():
    """Obtiene los eventos del día actual."""
    if not _calendario_listo():
        return ("El calendario de Google no está vinculado aún, señor. "
                "Dígame 'configura el calendario' para autenticarlo.")
    try:
        service = _get_service()
        ahora = datetime.now(timezone.utc)
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia    = ahora.replace(hour=23, minute=59, second=59, microsecond=0)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=inicio_dia.isoformat(),
            timeMax=fin_dia.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=10,
        ).execute()

        eventos = events_result.get("items", [])
        if not eventos:
            return "No tiene eventos programados para hoy, señor."

        resumen = ", ".join(_formato_evento(ev) for ev in eventos[:5])
        return f"Hoy tiene {len(eventos)} evento{'s' if len(eventos)>1 else ''}: {resumen}."
    except ImportError as e:
        return str(e)
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        log.error(f"Calendar hoy: {e}")
        return "No pude acceder al calendario en este momento."

def obtener_eventos_semana():
    """Obtiene los eventos de los próximos 7 días."""
    if not _calendario_listo():
        return ("El calendario de Google no está vinculado aún, señor. "
                "Dígame 'configura el calendario' para autenticarlo.")
    try:
        service = _get_service()
        ahora   = datetime.now(timezone.utc)
        fin     = ahora + timedelta(days=7)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=ahora.isoformat(),
            timeMax=fin.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=15,
        ).execute()

        eventos = events_result.get("items", [])
        if not eventos:
            return "No tiene eventos en los próximos 7 días."

        return f"Tiene {len(eventos)} eventos esta semana. El próximo: {_formato_evento(eventos[0])}."
    except Exception as e:
        log.error(f"Calendar semana: {e}")
        return "No pude consultar la agenda semanal."

def crear_evento(titulo, fecha, hora):
    """Crea un evento en Google Calendar."""
    try:
        service = _get_service()
        # Parsear fecha: acepta 'hoy', 'mañana', o 'DD/MM'
        hoy = datetime.now()
        if fecha.lower() in ("hoy", "today"):
            dt_fecha = hoy
        elif fecha.lower() in ("mañana", "manana", "tomorrow"):
            dt_fecha = hoy + timedelta(days=1)
        else:
            partes = fecha.replace("-", "/").split("/")
            dt_fecha = hoy.replace(day=int(partes[0]), month=int(partes[1]))

        h, m = (hora.split(":") + ["0"])[:2]
        inicio = dt_fecha.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        fin_ev = inicio + timedelta(hours=1)

        evento = {
            "summary": titulo,
            "start":   {"dateTime": inicio.isoformat(), "timeZone": "America/La_Paz"},
            "end":     {"dateTime": fin_ev.isoformat(),  "timeZone": "America/La_Paz"},
        }
        service.events().insert(calendarId="primary", body=evento).execute()
        return f"Evento '{titulo}' creado para el {inicio.strftime('%d/%m a las %H:%M')}."
    except Exception as e:
        log.error(f"Calendar crear: {e}")
        return f"No pude crear el evento: {e}"
