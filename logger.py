# ============================================================
#  JARVIS - Sistema de logs
# ============================================================

import os
import logging
from datetime import datetime

_DIR      = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_DIR, "jarvis.log")

# Silenciar modulos ruidosos ANTES de basicConfig
for _mod in ("comtypes", "pycaw", "httpcore", "httpx",
             "urllib3", "asyncio", "websockets", "sounddevice"):
    logging.getLogger(_mod).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
    ]
)

log = logging.getLogger("jarvis")
log.info("=" * 60)
log.info(f"Jarvis iniciado - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log.info("=" * 60)
