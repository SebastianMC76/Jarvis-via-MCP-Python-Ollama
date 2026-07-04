# ============================================================
#  JARVIS - Modo guia/narrador paso a paso
# ============================================================
import threading, time
from logger import log

_guias = {
    "word a pdf": [
        "Abra su documento de Word.",
        "Espere a que el documento este completamente cargado.",
        "Haga clic en el menu Archivo en la esquina superior izquierda.",
        "Seleccione la opcion Guardar como.",
        "En el menu de tipo de archivo, elija PDF.",
        "Elija la carpeta donde desea guardar el archivo.",
        "Haga clic en Guardar. El PDF se ha creado correctamente.",
    ],
    "comprimir archivo": [
        "Localice el archivo o carpeta que desea comprimir.",
        "Haga clic derecho sobre el archivo.",
        "Seleccione Enviar a y luego Carpeta comprimida.",
        "Espere a que Windows cree el archivo ZIP.",
        "El archivo comprimido aparecera en la misma ubicacion.",
    ],
    "cambiar fondo de pantalla": [
        "Haga clic derecho en el escritorio.",
        "Seleccione Personalizar.",
        "Haga clic en Fondo de pantalla.",
        "Elija una imagen de las opciones disponibles o haga clic en Explorar fotos.",
        "Seleccione la imagen deseada. El fondo cambiara automaticamente.",
    ],
    "limpiar disco": [
        "Presione la tecla Windows y escriba Liberador de espacio en disco.",
        "Abra la aplicacion y espere a que calcule el espacio.",
        "Seleccione las categorias que desea limpiar.",
        "Haga clic en Aceptar y confirme la eliminacion.",
        "Windows limpiara los archivos seleccionados.",
    ],
    "instalar programa": [
        "Descargue el instalador del programa desde la pagina oficial.",
        "Busque el archivo descargado en su carpeta de Descargas.",
        "Haga doble clic en el instalador.",
        "Si aparece una ventana de permisos, haga clic en Si.",
        "Siga los pasos del asistente de instalacion.",
        "Haga clic en Instalar y espere a que termine.",
        "Al finalizar, haga clic en Finalizar. El programa esta instalado.",
    ],
}

_sesion_activa = {"activa": False, "pasos": [], "paso_actual": 0, "nombre": ""}

def iniciar_guia(nombre_guia, hablar_fn=None):
    """Inicia una guia paso a paso."""
    nombre = nombre_guia.lower().strip()
    # Busqueda flexible
    guia = None
    for key in _guias:
        if key in nombre or nombre in key or any(w in nombre for w in key.split()):
            guia = _guias[key]
            _sesion_activa["nombre"] = key
            break

    if not guia:
        disponibles = ", ".join(_guias.keys())
        return f"No tengo esa guia. Guias disponibles: {disponibles}."

    _sesion_activa["activa"]      = True
    _sesion_activa["pasos"]       = guia
    _sesion_activa["paso_actual"] = 0

    primer_paso = guia[0]
    _sesion_activa["paso_actual"] = 1
    total = len(guia)
    return f"Iniciando guia: {_sesion_activa['nombre']}. {total} pasos en total. Paso 1: {primer_paso}"

def siguiente_paso(hablar_fn=None):
    """Avanza al siguiente paso de la guia activa."""
    if not _sesion_activa["activa"]:
        return "No hay ninguna guia activa. Dime que quieres aprender."
    idx   = _sesion_activa["paso_actual"]
    pasos = _sesion_activa["pasos"]
    if idx >= len(pasos):
        _sesion_activa["activa"] = False
        return "Guia completada. Espero haber sido de ayuda, senor."
    paso = pasos[idx]
    _sesion_activa["paso_actual"] += 1
    restantes = len(pasos) - _sesion_activa["paso_actual"]
    sufijo = f" Quedan {restantes} pasos." if restantes > 0 else " Este es el ultimo paso."
    return f"Paso {idx + 1}: {paso}{sufijo}"

def cancelar_guia():
    _sesion_activa["activa"] = False
    return "Guia cancelada."

def hay_guia_activa():
    return _sesion_activa["activa"]

def agregar_guia(nombre, pasos):
    """Agrega una guia personalizada."""
    _guias[nombre.lower()] = pasos
    return f"Guia '{nombre}' agregada con {len(pasos)} pasos."
