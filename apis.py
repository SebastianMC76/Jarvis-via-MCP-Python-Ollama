# ============================================================
#  JARVIS - Todas las APIs de informacion
#  Wikipedia, Noticias, Divisas, Crypto, Chistes, IP/Ciudad
# ============================================================

import requests
from logger import log
from config import NEWSAPI_KEY, EXCHANGERATE_KEY

# ── Wikipedia ─────────────────────────────────────────────────
def wikipedia(query, oraciones=2):
    """Retorna resumen de Wikipedia. Sin API key."""
    try:
        r = requests.get(
            "https://es.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_"),
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            texto = data.get("extract", "")
            # Tomar solo las primeras N oraciones
            partes = texto.split(". ")
            return ". ".join(partes[:oraciones]) + "."
        # Intentar en inglés si no hay en español
        r2 = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_"),
            timeout=5
        )
        if r2.status_code == 200:
            texto = r2.json().get("extract", "")
            partes = texto.split(". ")
            return ". ".join(partes[:oraciones]) + "."
        return f"No encontre informacion sobre {query} en Wikipedia."
    except Exception as e:
        log.error(f"Wikipedia error: {e}")
        return "No pude consultar Wikipedia."

# ── Noticias ──────────────────────────────────────────────────
CATEGORIAS_NOTICIAS = {
    "tecnologia": "technology", "tech": "technology",
    "deportes": "sports", "deporte": "sports",
    "ciencia": "science", "salud": "health",
    "negocios": "business", "economia": "business",
    "entretenimiento": "entertainment",
    "general": "general",
}

def noticias(categoria="general", cantidad=3):
    """Retorna titulares de noticias."""
    if NEWSAPI_KEY == "PEGA_TU_KEY_DE_NEWSAPI":
        return "La API de noticias no esta configurada aun."
    cat_en = CATEGORIAS_NOTICIAS.get(categoria.lower(), "general")
    try:
        r = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"category": cat_en, "language": "es",
                    "pageSize": cantidad, "apiKey": NEWSAPI_KEY},
            timeout=5
        )
        arts = r.json().get("articles", [])
        if not arts:
            # Intentar en ingles si no hay en español
            r2 = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"category": cat_en, "language": "en",
                        "pageSize": cantidad, "apiKey": NEWSAPI_KEY},
                timeout=5
            )
            arts = r2.json().get("articles", [])
        if not arts:
            return "No encontre noticias en este momento."
        titulares = [a["title"].split(" - ")[0] for a in arts]
        return "Las noticias del momento son: " + ". ".join(titulares) + "."
    except Exception as e:
        log.error(f"NewsAPI error: {e}")
        return "No pude obtener las noticias."

# ── Divisas ───────────────────────────────────────────────────
MONEDAS = {
    "dolar": "USD", "dolares": "USD", "dollar": "USD",
    "euro": "EUR", "euros": "EUR",
    "boliviano": "BOB", "bolivianos": "BOB",
    "peso": "ARS", "pesos": "ARS",
    "sol": "PEN", "soles": "PEN",
    "real": "BRL", "reales": "BRL",
    "libra": "GBP", "libras": "GBP",
    "yen": "JPY", "yenes": "JPY",
}

def tipo_cambio(de="USD", a="BOB", cantidad=1):
    """Convierte entre monedas."""
    if EXCHANGERATE_KEY == "PEGA_TU_KEY_DE_EXCHANGERATE":
        return "La API de divisas no esta configurada aun."
    try:
        r = requests.get(
            f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_KEY}/pair/{de}/{a}/{cantidad}",
            timeout=5
        )
        data = r.json()
        if data.get("result") == "success":
            resultado = round(data["conversion_result"], 2)
            tasa      = round(data["conversion_rate"], 4)
            return (f"{cantidad} {de} equivale a {resultado} {a}. "
                    f"La tasa de cambio es {tasa}.")
        return "No pude obtener el tipo de cambio."
    except Exception as e:
        log.error(f"ExchangeRate error: {e}")
        return "Error al consultar el tipo de cambio."

_TRIGGERS_DIVISA = [
    "convierte", "convertir", "cambio de", "cambiar", "a cuanto", "a cuánto",
    "tipo de cambio", "cuánto es", "cuanto es", "cuantos son", "cuántos son",
    "valor de", "cuanto vale", "cuánto vale", "cuanto cuesta", "cuánto cuesta",
    "de dólar", "de dolar", "de euro", "de peso", "de boliviano",
    "en dólar", "en dolar", "en boliviano", "en euro", "en peso",
    "a dólar", "a dolar", "a boliviano", "a euro", "a peso",
    "precio del dolar", "precio del euro",
]

def parsear_conversion(texto):
    """
    Solo dispara si el texto contiene palabras de moneda Y un verbo de conversión.
    Retorna None si no hay intención clara de conversión.
    """
    import re
    texto_lower = texto.lower()

    # Debe tener al menos un trigger de conversión
    if not any(t in texto_lower for t in _TRIGGERS_DIVISA):
        return None

    # Y al menos una palabra de moneda conocida
    if not any(p in texto_lower for p in MONEDAS):
        return None

    cantidad = 1
    m = re.search(r'(\d+(?:\.\d+)?)', texto)
    if m:
        cantidad = float(m.group(1))

    codigos_encontrados = []
    for palabra, codigo in MONEDAS.items():
        if palabra in texto_lower and codigo not in codigos_encontrados:
            codigos_encontrados.append(codigo)

    if not codigos_encontrados:
        return None

    if len(codigos_encontrados) == 1:
        cod = codigos_encontrados[0]
        moneda_de, moneda_a = ("USD", cod) if cod == "BOB" else (cod, "BOB")
    else:
        moneda_de, moneda_a = codigos_encontrados[0], codigos_encontrados[1]

    return tipo_cambio(moneda_de, moneda_a, cantidad)

# ── Crypto ────────────────────────────────────────────────────
CRYPTO_IDS = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "cardano": "cardano", "ada": "cardano",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "ripple": "ripple", "xrp": "ripple",
}

def precio_crypto(moneda="bitcoin", divisa="usd"):
    """Precio de criptomoneda via CoinGecko (sin API key)."""
    coin_id = CRYPTO_IDS.get(moneda.lower(), moneda.lower())
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": divisa,
                    "include_24hr_change": "true"},
            timeout=5
        )
        data = r.json()
        if coin_id in data:
            precio  = data[coin_id][divisa]
            cambio  = round(data[coin_id].get(f"{divisa}_24h_change", 0), 2)
            tendencia = "subio" if cambio > 0 else "bajo"
            return (f"{moneda.capitalize()} esta a {precio:,.2f} {divisa.upper()}. "
                    f"Ha {tendencia} un {abs(cambio)}% en las ultimas 24 horas.")
        return f"No encontre datos para {moneda}."
    except Exception as e:
        log.error(f"CoinGecko error: {e}")
        return "No pude consultar el precio de la criptomoneda."

# ── Chistes ───────────────────────────────────────────────────
def chiste(idioma="es"):
    """Chiste aleatorio via JokeAPI (sin API key)."""
    try:
        lang = idioma if idioma in ["es", "en", "de", "fr"] else "en"
        r = requests.get(
            f"https://v2.jokeapi.dev/joke/Any",
            params={"lang": lang, "blacklistFlags": "nsfw,racist,sexist",
                    "type": "single"},
            timeout=5
        )
        data = r.json()
        if data.get("type") == "single":
            return data["joke"]
        if data.get("type") == "twopart":
            return data["setup"] + "... " + data["delivery"]
        return "No se me ocurre ningun chiste ahora mismo."
    except Exception as e:
        log.error(f"JokeAPI error: {e}")
        return "No pude traer un chiste en este momento."

# ── Ubicacion automatica ──────────────────────────────────────
def obtener_ciudad():
    """Detecta la ciudad del usuario por IP. Sin API key."""
    try:
        r = requests.get("https://ipapi.co/json/", timeout=5)
        data = r.json()
        ciudad = data.get("city", "")
        pais   = data.get("country_name", "")
        log.info(f"Ciudad detectada: {ciudad}, {pais}")
        return ciudad or "Santa Cruz de la Sierra"
    except Exception as e:
        log.error(f"GeoIP error: {e}")
        return "Santa Cruz de la Sierra"
