# ============================================================
#  JARVIS - Monitor de red
# ============================================================
import psutil, socket, time, subprocess
from logger import log

def info_red():
    """Retorna estado completo de la red."""
    try:
        # Velocidades
        net1 = psutil.net_io_counters()
        time.sleep(1)
        net2 = psutil.net_io_counters()
        down_mb = round((net2.bytes_recv - net1.bytes_recv) / 1024 / 1024, 2)
        up_mb   = round((net2.bytes_sent - net1.bytes_sent) / 1024 / 1024, 2)

        # Ping a Google
        ping_ms = _ping("8.8.8.8")

        # IP local
        ip = socket.gethostbyname(socket.gethostname())

        partes = [f"Descarga: {down_mb} MB/s. Subida: {up_mb} MB/s."]
        if ping_ms:
            partes.append(f"Latencia: {ping_ms} ms.")
        partes.append(f"IP local: {ip}.")
        return " ".join(partes)
    except Exception as e:
        log.error(f"info_red: {e}")
        return "No pude obtener informacion de red."

def _ping(host):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", host],
            capture_output=True, text=True, timeout=3)
        for line in result.stdout.split("\n"):
            if "ms" in line.lower() and ("tiempo" in line.lower() or "time" in line.lower()):
                import re
                m = re.search(r'(\d+)\s*ms', line)
                if m: return int(m.group(1))
    except Exception:
        pass
    return None

def velocidad_red():
    """Solo descarga/subida actual."""
    try:
        n1 = psutil.net_io_counters()
        time.sleep(0.8)
        n2 = psutil.net_io_counters()
        down = round((n2.bytes_recv - n1.bytes_recv) / 1024, 1)
        up   = round((n2.bytes_sent - n1.bytes_sent) / 1024, 1)
        return {"down_kb": down, "up_kb": up}
    except Exception:
        return {"down_kb": 0, "up_kb": 0}

def hay_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except Exception:
        return False
