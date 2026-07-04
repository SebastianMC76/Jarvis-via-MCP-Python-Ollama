# ============================================================
#  JARVIS - Reproductor de YouTube (video directo)
#  Requiere API key de YouTube Data v3 (gratuita)
#  https://console.cloud.google.com -> YouTube Data API v3
# ============================================================

import webbrowser
import requests
from logger import log
from config import YOUTUBE_API_KEY

def reproducir(query):
    """
    Busca el primer video en YouTube y abre la URL directa de reproduccion.
    Si no hay API key, hace fallback a busqueda normal.
    """
    if YOUTUBE_API_KEY in ("PEGA_TU_KEY_DE_YOUTUBE", "PEGA_TU_KEY_DE_YOUTUBE_DATA_API_V3", ""):
        # Fallback sin API key: busqueda filtrada por videos
        url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAQ%3D%3D"
        webbrowser.open(url)
        log.info(f"YouTube fallback (sin API key): {url}")
        return f"Buscando {query} en YouTube."

    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 1,
                "key": YOUTUBE_API_KEY,
            },
            timeout=5,
        )
        data = resp.json()
        items = data.get("items", [])
        if not items:
            log.warning("YouTube API: sin resultados")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"No encontre resultados exactos, abriendo busqueda de {query}."

        video_id = items[0]["id"]["videoId"]
        titulo   = items[0]["snippet"]["title"]
        url      = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        webbrowser.open(url)
        log.info(f"YouTube directo: {url} | {titulo}")
        return f"Reproduciendo {titulo}."

    except Exception as e:
        log.error(f"YouTube API error: {e}")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        return f"Hubo un problema, abriendo busqueda de {query}."
