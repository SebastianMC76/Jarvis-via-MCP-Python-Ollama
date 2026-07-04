# ============================================================
#  JARVIS - Módulo de clima (OpenWeatherMap - gratis)
#  API key gratuita en: https://openweathermap.org/api
# ============================================================

import requests
from logger import log
from config import OWM_API_KEY, CIUDAD_CLIMA

def obtener_clima(ciudad=None):
    """Retorna string con el clima actual."""
    ciudad = ciudad or CIUDAD_CLIMA or "Santa Cruz de la Sierra"
    if OWM_API_KEY == "PEGA_TU_KEY_DE_OPENWEATHERMAP":
        return "El clima no esta configurado aun. Agrega tu key de OpenWeatherMap en config.py."
    try:
        url = (f"https://api.openweathermap.org/data/2.5/weather"
               f"?q={ciudad}&appid={OWM_API_KEY}&units=metric&lang=es")
        r = requests.get(url, timeout=5)
        d = r.json()
        if r.status_code != 200:
            log.error(f"Clima error: {d}")
            return "No pude obtener el clima en este momento."
        temp     = round(d["main"]["temp"])
        sensacion= round(d["main"]["feels_like"])
        desc     = d["weather"][0]["description"].capitalize()
        humedad  = d["main"]["humidity"]
        return (f"{desc} en {ciudad}. {temp} grados, "
                f"sensacion termica de {sensacion}. Humedad {humedad} por ciento.")
    except Exception as e:
        log.error(f"Clima excepcion: {e}")
        return "No pude conectarme al servicio del clima."
