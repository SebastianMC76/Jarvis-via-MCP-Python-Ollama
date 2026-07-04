# ============================================================
#  JARVIS - Configuracion central
#  Pon tus API keys aqui
# ============================================================

# ── IA principal ──────────────────────────────────────────────
API_KEY   = ""
WAKE_WORD = "jarvis"
MODELO    = "llama-3.3-70b-versatile"

# ── Porcupine — wake word offline (RECOMENDADO) ───────────────
# Obtener access key GRATUITA en: https://picovoice.ai
#   → Console → AccessKey → Create AccessKey → copiar
# Con key: detección 100 % offline, latencia ~32 ms, sin internet.
# Sin key (campo vacío): Jarvis usa Google STT como fallback.
# La key se guarda en ajustes.json al configurarla desde la UI.
PORCUPINE_ACCESS_KEY = ""  # Configurar desde Ajustes → Porcupine

# ── Voz ───────────────────────────────────────────────────────
IDIOMA             = "es-ES"
IDIOMA_ALTERNATIVO = "en-US"

# ── Audio ─────────────────────────────────────────────────────
SAMPLE_RATE       = 16000
SILENCE_TIMEOUT   = 1.8
SILENCE_THRESHOLD = 500
MAX_RECORD_SECS   = 20

# ── APIs (reemplaza los valores con tus keys reales) ──────────

# YouTube Data API v3
# Como obtenerla: console.cloud.google.com
#   -> Selecciona tu proyecto -> APIs y servicios -> Biblioteca
#   -> Busca "YouTube Data API v3" -> Habilitar
#   -> Credenciales -> Crear credencial -> Clave de API
YOUTUBE_API_KEY = ""

# OpenWeatherMap - clima actual
# Como obtenerla: openweathermap.org/api
#   -> Sign Up gratis -> My API Keys -> copia la key
#   -> Espera 10 minutos antes de usarla (activacion)
OWM_API_KEY  = ""
CIUDAD_CLIMA = ""   # dejar vacio para detectar automaticamente por IP

# NewsAPI - noticias del dia
# Como obtenerla: newsapi.org
#   -> Get API Key -> registro gratis -> copia la key
NEWSAPI_KEY = ""

# ExchangeRate-API - tipo de cambio de divisas
# Como obtenerla: exchangerate-api.com
#   -> Get Free Key -> registro gratis -> copia la key
#   -> Plan gratuito: 1500 solicitudes/mes
EXCHANGERATE_KEY = ""

# Google Translation API (opcional)
# Como obtenerla: console.cloud.google.com
#   -> APIs y servicios -> Biblioteca -> "Cloud Translation API" -> Habilitar
#   -> Credenciales -> Crear credencial -> Clave de API
#   -> Plan gratuito: 500,000 caracteres/mes
GOOGLE_TRANSLATE_KEY = "PEGA_TU_KEY_DE_GOOGLE_TRANSLATE"

# Spotify Web API (opcional - control real del reproductor)
# Como obtenerla: developer.spotify.com
#   -> Log in -> Create App -> copia Client ID y Client Secret
SPOTIFY_CLIENT_ID     = "PEGA_TU_SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "PEGA_TU_SPOTIFY_CLIENT_SECRET"

# NOTA: CoinGecko, Wikipedia, JokeAPI e IPApi no requieren key
