# ============================================================
#  JARVIS - Vision por computadora (OCR, captura, analisis)
#  Requiere Tesseract instalado:
#  https://github.com/UB-Mannheim/tesseract/wiki
#  Instalar en C:\Program Files\Tesseract-OCR\
# ============================================================
import os
import mss
import numpy as np
from PIL import Image
from logger import log

# Ruta de Tesseract (instalar desde link de arriba)
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def _setup_tesseract():
    import pytesseract
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    return pytesseract

def capturar_pantalla():
    """Toma una captura de pantalla y la retorna como imagen PIL."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
    return img

def leer_pantalla():
    """OCR sobre la pantalla actual. Retorna el texto detectado."""
    if not os.path.exists(TESSERACT_PATH):
        return ("Tesseract no esta instalado. "
                "Descargalo en: github.com/UB-Mannheim/tesseract/wiki "
                "e instalalo en C:/Program Files/Tesseract-OCR/")
    try:
        pytesseract = _setup_tesseract()
        img  = capturar_pantalla()
        texto = pytesseract.image_to_string(img, lang='spa+eng')
        texto = texto.strip()
        if not texto:
            return "No detecte texto en la pantalla."
        # Resumir si es muy largo
        if len(texto) > 300:
            return "Texto detectado en pantalla: " + texto[:300] + "..."
        return "Texto en pantalla: " + texto
    except Exception as e:
        log.error(f"OCR error: {e}")
        return "No pude leer el texto de la pantalla."

def leer_imagen(ruta):
    """OCR sobre una imagen especifica."""
    if not os.path.exists(TESSERACT_PATH):
        return "Tesseract no esta instalado."
    try:
        pytesseract = _setup_tesseract()
        img   = Image.open(ruta)
        texto = pytesseract.image_to_string(img, lang='spa+eng')
        return texto.strip() or "No detecte texto en la imagen."
    except Exception as e:
        log.error(f"leer_imagen error: {e}")
        return f"No pude leer la imagen: {e}"

def analizar_pantalla_con_ia(pregunta, cliente_groq, modelo):
    """
    Captura la pantalla, la envia a Groq con vision y hace una pregunta.
    Util para: que error hay en pantalla, que muestra esta ventana, etc.
    """
    try:
        import base64, io
        img = capturar_pantalla()
        # Redimensionar para no gastar tokens
        img.thumbnail((1280, 720))
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=70)
        b64 = base64.b64encode(buf.getvalue()).decode()

        # Groq con vision (llama-3.2-vision)
        response = cliente_groq.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text",
                     "text": (f"{pregunta}. "
                              "Responde en español, de forma concisa, max 3 oraciones.")}
                ]
            }],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"Vision IA error: {e}")
        return "No pude analizar la pantalla en este momento."

def ventanas_abiertas():
    """Retorna lista de ventanas visibles."""
    try:
        import pygetwindow as gw
        ventanas = [w.title for w in gw.getAllWindows() if w.title.strip()]
        return ventanas
    except Exception:
        return []

def detectar_juego_activo():
    """Detecta si hay algun juego conocido abierto."""
    juegos_conocidos = [
        'steam', 'league of legends', 'valorant', 'minecraft',
        'fortnite', 'tekken', 'brawlhalla', 'counter-strike',
        'gta', 'call of duty', 'apex', 'overwatch', 'roblox',
    ]
    ventanas = ventanas_abiertas()
    for v in ventanas:
        for j in juegos_conocidos:
            if j in v.lower():
                return v
    return None
