# ============================================================
#  JARVIS - Traduccion (Google Translate API gratuita via deep-translator)
#  pip install deep-translator
# ============================================================
from logger import log

IDIOMAS = {
    "español": "es", "espanol": "es", "spanish": "es",
    "ingles": "en", "inglés": "en", "english": "en",
    "frances": "fr", "francés": "fr", "french": "fr",
    "aleman": "de", "alemán": "de", "german": "de",
    "italiano": "it", "italian": "it",
    "portugues": "pt", "portugués": "pt", "portuguese": "pt",
    "chino": "zh-CN", "chinese": "zh-CN",
    "japones": "ja", "japonés": "ja", "japanese": "ja",
    "coreano": "ko", "korean": "ko",
    "ruso": "ru", "russian": "ru",
    "arabe": "ar", "árabe": "ar", "arabic": "ar",
}

def _resolver_idioma(idioma_str):
    """Convierte nombre de idioma a código ISO."""
    s = idioma_str.lower().strip()
    return IDIOMAS.get(s, s)  # Si ya es código (es, en, fr...) lo devuelve tal cual

def traducir(texto, idioma_destino="en"):
    """Traduce texto al idioma destino usando deep-translator (sin API key)."""
    try:
        from deep_translator import GoogleTranslator
        codigo = _resolver_idioma(idioma_destino)
        resultado = GoogleTranslator(source="auto", target=codigo).translate(texto)
        return f'"{texto}" en {idioma_destino} es: "{resultado}".'
    except ImportError:
        log.error("deep-translator no instalado")
        return ("El módulo de traducción no está instalado. "
                "Ejecuta: pip install deep-translator")
    except Exception as e:
        log.error(f"Traduccion error: {e}")
        # Fallback: intentar con requests directo a la API pública
        return _traducir_fallback(texto, _resolver_idioma(idioma_destino))

def _traducir_fallback(texto, codigo):
    """Fallback usando la API pública de Google Translate (sin key)."""
    try:
        import urllib.request, urllib.parse, json
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={codigo}&dt=t&q={urllib.parse.quote(texto)}"
        )
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
        resultado = "".join(seg[0] for seg in data[0] if seg[0])
        return f'"{texto}" en {codigo} es: "{resultado}".'
    except Exception as e:
        log.error(f"Traduccion fallback error: {e}")
        return "No pude realizar la traducción en este momento."
