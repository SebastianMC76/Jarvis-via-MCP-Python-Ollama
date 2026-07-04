# ============================================================
#  JARVIS - Monitor del sistema (CPU, RAM, GPU, bateria, temp)
# ============================================================
import psutil, os, subprocess, shutil
from logger import log

def info_sistema():
    """Retorna resumen completo del sistema."""
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage('C:\\')

    ram_usada = round(ram.used / 1024**3, 1)
    ram_total = round(ram.total / 1024**3, 1)
    ram_pct   = ram.percent
    disco_libre = round(disk.free / 1024**3, 1)

    partes = [
        f"CPU al {cpu} por ciento.",
        f"RAM: {ram_usada} de {ram_total} GB usada, {ram_pct} por ciento.",
        f"Disco C: {disco_libre} GB libres.",
    ]

    # Bateria
    bat = psutil.sensors_battery()
    if bat:
        estado = "cargando" if bat.power_plugged else "descargando"
        partes.append(f"Bateria al {int(bat.percent)} por ciento, {estado}.")

    return " ".join(partes)

def info_ram():
    r = psutil.virtual_memory()
    return (f"RAM: {round(r.used/1024**3,1)} GB usada de "
            f"{round(r.total/1024**3,1)} GB. {r.percent} por ciento ocupada.")

def info_cpu():
    cpu = psutil.cpu_percent(interval=1)
    freq = psutil.cpu_freq()
    cores = psutil.cpu_count()
    return f"CPU al {cpu} por ciento. {cores} nucleos a {round(freq.current)} MHz."

def info_disco():
    d = psutil.disk_usage('C:\\')
    return (f"Disco C: {round(d.used/1024**3,1)} GB usados, "
            f"{round(d.free/1024**3,1)} GB libres de "
            f"{round(d.total/1024**3,1)} GB totales.")

def info_bateria():
    bat = psutil.sensors_battery()
    if not bat:
        return "Esta PC no tiene bateria o no se pudo detectar."
    estado = "cargando" if bat.power_plugged else "descargando"
    mins   = int(bat.secsleft // 60) if bat.secsleft > 0 else 0
    base   = f"Bateria al {int(bat.percent)} por ciento, {estado}."
    if mins > 0 and not bat.power_plugged:
        base += f" Aproximadamente {mins} minutos restantes."
    return base

def procesos_top(n=5):
    """Retorna los N procesos con mas uso de CPU."""
    procs = []
    for p in psutil.process_iter(['pid','name','cpu_percent','memory_info']):
        try:
            procs.append(p.info)
        except Exception:
            pass
    procs.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
    top = procs[:n]
    nombres = [f"{p['name']} ({p['cpu_percent']}%)" for p in top]
    return "Los procesos con mas CPU son: " + ", ".join(nombres) + "."

def cerrar_proceso(nombre):
    """Cierra un proceso por nombre."""
    cerrados = 0
    for p in psutil.process_iter(['name','pid']):
        try:
            if nombre.lower() in p.info['name'].lower():
                p.kill()
                cerrados += 1
        except Exception:
            pass
    if cerrados:
        return f"Cerre {cerrados} proceso(s) de {nombre}."
    return f"No encontre ningun proceso llamado {nombre}."

def limpiar_temporales():
    """Elimina archivos temporales de Windows."""
    rutas = [
        os.environ.get('TEMP', ''),
        os.environ.get('TMP', ''),
        r"C:\Windows\Temp",
    ]
    total = 0
    for ruta in rutas:
        if not ruta or not os.path.exists(ruta):
            continue
        for f in os.listdir(ruta):
            try:
                fp = os.path.join(ruta, f)
                if os.path.isfile(fp):
                    os.remove(fp)
                    total += 1
                elif os.path.isdir(fp):
                    shutil.rmtree(fp, ignore_errors=True)
                    total += 1
            except Exception:
                pass
    return f"Elimine {total} archivos temporales."

def modo_rendimiento(activar=True):
    """Cambia el plan de energia a alto rendimiento o equilibrado."""
    if activar:
        subprocess.run("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                       shell=True)
        return "Modo alto rendimiento activado."
    else:
        subprocess.run("powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e",
                       shell=True)
        return "Modo equilibrado activado."

def suspender():
    subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
    return "Suspendiendo el equipo."
