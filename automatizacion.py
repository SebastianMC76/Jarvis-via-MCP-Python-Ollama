# ============================================================
#  JARVIS - Automatizacion, macros y protocolos
# ============================================================
import subprocess, webbrowser, time, os, json
import pyautogui
import pygetwindow as gw
from difflib import SequenceMatcher
from logger import log

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.3

# ─────────────────────────────────────────────────────────────
# Busqueda de archivos (fuzzy)
# ─────────────────────────────────────────────────────────────

# Carpetas donde siempre buscar primero (alta prioridad)
CARPETAS_PRIORITARIAS = [
    os.path.join(os.environ.get("USERPROFILE",""), "Desktop"),
    os.path.join(os.environ.get("USERPROFILE",""), "OneDrive", "Desktop"),
    os.path.join(os.environ.get("USERPROFILE",""), "Documents"),
    os.path.join(os.environ.get("USERPROFILE",""), "OneDrive", "Documents"),
    os.path.join(os.environ.get("USERPROFILE",""), "Downloads"),
    os.path.join(os.environ.get("USERPROFILE",""), "Pictures"),
    os.path.join(os.environ.get("USERPROFILE",""), "Videos"),
    os.path.join(os.environ.get("USERPROFILE",""), "Music"),
]

# Carpetas del sistema que no tiene sentido buscar
IGNORAR = {
    'windows', 'program files', 'program files (x86)',
    '$recycle.bin', 'appdata', 'programdata', '.git',
    '__pycache__', 'node_modules', 'venv', '.venv',
}

def _similitud(a, b):
    """Retorna ratio de similitud entre 0 y 1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def _puntaje_archivo(nombre_buscado, nombre_archivo):
    """
    Calcula un puntaje de relevancia entre lo que dijo el usuario
    y el nombre real del archivo. Combina varias estrategias:
    - Coincidencia exacta de subcadena (máximo puntaje)
    - Similitud fuzzy global
    - Cuántas palabras del query están en el nombre
    """
    nb  = nombre_buscado.lower().strip()
    nf  = nombre_archivo.lower().replace("_", " ").replace("-", " ")
    # Sin extension para comparar
    nf_sin_ext = os.path.splitext(nf)[0]

    # Coincidencia exacta de subcadena -> puntaje 1.0
    if nb in nf_sin_ext:
        return 1.0

    # Similitud global
    sim = _similitud(nb, nf_sin_ext)

    # Bonus por palabras individuales que coincidan
    palabras_query  = nb.split()
    palabras_nombre = nf_sin_ext.split()
    hits = sum(
        1 for pw in palabras_query
        if any(_similitud(pw, pn) > 0.75 for pn in palabras_nombre)
    )
    bonus = hits / max(len(palabras_query), 1) * 0.4

    return min(sim + bonus, 1.0)

def _buscar_en_dir(directorio, nombre, resultados, limite, profundidad_max=4):
    """Recorre directorio recursivamente acumulando resultados con puntaje."""
    if not os.path.isdir(directorio):
        return
    directorio = os.path.normpath(directorio)
    for root, dirs, files in os.walk(directorio):
        root = os.path.normpath(root)
        # Respetar profundidad — comparar niveles reales
        nivel = root[len(directorio):].count(os.sep)
        if nivel >= profundidad_max:
            dirs[:] = []
            continue
        # Filtrar carpetas ignoradas
        dirs[:] = [d for d in dirs if d.lower() not in IGNORAR]

        for f in files:
            puntaje = _puntaje_archivo(nombre, f)
            if puntaje > 0.35:
                ruta = os.path.join(root, f)
                resultados.append((puntaje, ruta, f))
                if len(resultados) >= limite * 6:
                    return

def _buscar_archivos_fuzzy(nombre, limite=5):
    """
    Busca archivos con coincidencia fuzzy.
    Primero revisa carpetas prioritarias, luego el home completo.
    Retorna lista de (puntaje, ruta) ordenada de mayor a menor.
    """
    resultados = []

    # 1. Carpetas prioritarias (escritorio, documentos, descargas, etc.)
    for carpeta in CARPETAS_PRIORITARIAS:
        _buscar_en_dir(carpeta, nombre, resultados, limite, profundidad_max=5)

    # 2. Si no encontramos nada bueno, ampliar al home completo
    if not resultados or max(r[0] for r in resultados) < 0.6:
        home = os.path.expanduser("~")
        _buscar_en_dir(home, nombre, resultados, limite, profundidad_max=3)

    # Ordenar por puntaje, desduplicar por ruta
    vistas = set()
    unicos = []
    for p, ruta, f in sorted(resultados, reverse=True):
        if ruta not in vistas:
            vistas.add(ruta)
            unicos.append((p, ruta, f))

    return unicos[:limite]

def buscar_archivo(nombre):
    """Busca archivos y reporta los resultados más parecidos."""
    resultados = _buscar_archivos_fuzzy(nombre, limite=5)

    if not resultados:
        return f"No encontré ningún archivo parecido a '{nombre}'."

    mejor_p, mejor_ruta, mejor_f = resultados[0]

    if mejor_p >= 0.85:
        # Muy buena coincidencia — reportar directo
        if len(resultados) == 1:
            return f"Encontré: {mejor_ruta}"
        otros = ", ".join(f[2] for f in resultados[1:3])
        return f"Encontré '{mejor_f}' en {os.path.dirname(mejor_ruta)}. También hay: {otros}."

    if mejor_p >= 0.5:
        # Coincidencia razonable — mostrar los mejores
        lista = ", ".join(f"'{r[2]}'" for r in resultados[:3])
        return f"No estoy seguro, pero los archivos más parecidos son: {lista}. El primero está en {os.path.dirname(resultados[0][1])}."

    return f"No encontré ningún archivo claramente parecido a '{nombre}'. ¿Puede ser más específico?"

def abrir_archivo_encontrado(nombre):
    """Busca y abre el archivo más parecido al nombre dado."""
    resultados = _buscar_archivos_fuzzy(nombre, limite=3)

    if not resultados:
        return f"No encontré ningún archivo parecido a '{nombre}'."

    mejor_p, mejor_ruta, mejor_f = resultados[0]

    if mejor_p < 0.25:
        # Mostrar los candidatos más cercanos aunque sean débiles
        if resultados:
            lista = ", ".join(f"'{r[2]}'" for r in resultados[:3])
            return f"No encontré '{nombre}' exactamente. Los más parecidos son: {lista}. ¿Cuál quiere?"
        return f"No encontré ningún archivo que se parezca a '{nombre}'."

    try:
        os.startfile(mejor_ruta)
        if mejor_p >= 0.85:
            return f"Abriendo '{mejor_f}'."
        else:
            return f"Abriendo '{mejor_f}', que es lo más parecido a '{nombre}'."
    except Exception as e:
        log.error(f"abrir_archivo: {e}")
        return f"Encontré el archivo pero no pude abrirlo: {e}"

# ─────────────────────────────────────────────────────────────
# Ventanas
# ─────────────────────────────────────────────────────────────

def listar_ventanas():
    """Lista ventanas abiertas."""
    try:
        ventanas = [w.title for w in gw.getAllWindows() if w.title.strip()]
        if not ventanas:
            return "No detecté ventanas abiertas."
        return "Ventanas abiertas: " + ", ".join(ventanas[:8]) + "."
    except Exception as e:
        log.error(f"listar_ventanas: {e}")
        return "No pude listar las ventanas."

def cerrar_ventana(nombre):
    """Cierra una ventana por nombre parcial."""
    try:
        for w in gw.getAllWindows():
            if nombre.lower() in w.title.lower():
                w.close()
                return f"Cerré la ventana de {nombre}."
        return f"No encontré ninguna ventana de {nombre}."
    except Exception as e:
        return f"No pude cerrar {nombre}: {e}"

def enfocar_ventana(nombre):
    """Trae al frente una ventana."""
    try:
        for w in gw.getAllWindows():
            if nombre.lower() in w.title.lower():
                w.activate()
                return f"Enfocando {w.title}."
        return f"No encontré la ventana de {nombre}."
    except Exception as e:
        return f"Error: {e}"

# ─────────────────────────────────────────────────────────────
# Control del teclado
# ─────────────────────────────────────────────────────────────

def escribir(texto):
    pyautogui.write(texto, interval=0.05)
    return f"Escribí: {texto}"

def atajo(keys):
    """Ejecuta un atajo de teclado. keys = 'ctrl+c', 'win+d', etc."""
    partes = keys.lower().split('+')
    pyautogui.hotkey(*partes)
    return f"Atajo {keys} ejecutado."
