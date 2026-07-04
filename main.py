# ============================================================
#  JARVIS - UI Iron Man (PyQt6) + System Tray + Mini Widget
#  Ejecutar: py main.py
# ============================================================
import sys, threading, math, time, json, os, random, logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QComboBox, QFrame,
    QSlider, QCheckBox, QSystemTrayIcon, QMenu, QDialog, QGridLayout)
from PyQt6.QtCore  import (Qt, QTimer, QThread, pyqtSignal, QPointF,
                            QRectF, QElapsedTimer, QPoint)
from PyQt6.QtGui   import (QPainter, QColor, QPen, QBrush, QFont,
                            QRadialGradient, QPixmap, QIcon, QImage,
                            QAction, QCursor)
from logger import log
import voz, cerebro, comandos, memoria, arranque, historial as hist_mod

# Silenciar logs DEBUG de pycaw/comtypes que llenan el archivo
logging.getLogger("comtypes").setLevel(logging.WARNING)
logging.getLogger("pycaw").setLevel(logging.WARNING)

# ── Config ────────────────────────────────────────────────────
_CFG_FILE = os.path.join(os.path.dirname(__file__), "ajustes.json")
_CFG_DEF  = {
    "wake_word":             "jarvis",
    "voz_id":                "es-MX-JorgeNeural",
    "voz_velocidad":         "+10%",
    "voz_volumen":           "+0%",
    "silencio_timeout":      1.2,
    "timeout_silencio_wake": 3.0,
    "max_tiempo_grabacion":  15,
    "silencio_threshold":    500,
    "wake_word_activo":      True,
    "siempre_encima":        True,
    "nombre_usuario":        "senor",
    "ciudad_clima":          "",
    "idioma":                "es-ES",
    "transparencia":         230,
    "mini_pos_x":            -1,
    "mini_pos_y":            -1,
    "porcupine_access_key":  "",   # picovoice.ai → gratis
    "max_historial":         20,   # turnos historial sesion (2-50)
    "dispositivo_entrada":    -1,   # -1 = default del sistema
    "dispositivo_salida":     -1,   # -1 = default del sistema
}
def cargar_cfg():
    if os.path.exists(_CFG_FILE):
        d = json.load(open(_CFG_FILE))
        for k,v in _CFG_DEF.items(): d.setdefault(k,v)
        return d
    json.dump(_CFG_DEF, open(_CFG_FILE,"w"), indent=2)
    return _CFG_DEF.copy()
def guardar_cfg(c): json.dump(c, open(_CFG_FILE,"w"), indent=2)
CFG = cargar_cfg()

# ── Workers ───────────────────────────────────────────────────
class HablarWorker(QThread):
    terminado = pyqtSignal()
    def __init__(self, texto): super().__init__(); self.texto = texto
    def run(self):
        try:
            voz.hablar(self.texto)
        except Exception:
            import traceback
            log.critical(f"HablarWorker CRASH:\n{traceback.format_exc()}")
        finally:
            self.terminado.emit()

class ProcesarWorker(QThread):
    resultado  = pyqtSignal(str, str, str)
    estado_sig = pyqtSignal(str)
    def __init__(self, texto): super().__init__(); self.texto = texto
    def run(self):
        try:
            self.estado_sig.emit("thinking")
            ej, resp = comandos.ejecutar(self.texto)
            if not ej:
                # El cerebro responde con texto + [TAGS] de accion
                rg   = cerebro.consultar(self.texto)
                resp = comandos.ejecutar_tags(rg)   # parsea tags, ejecuta y retorna texto limpio
            hist_mod.registrar(self.texto, resp or "")
            arranque.registrar_actividad(self.texto)
            t = self.texto.lower()
            tipo = ("clima" if any(w in t for w in ["clima","tiempo","temperatura"])
                    else "datos" if any(w in t for w in ["bitcoin","crypto","dolar","cambio","divisa","precio"])
                    else "")
            self.resultado.emit(self.texto, resp or "", tipo)
        except Exception as e:
            import traceback
            log.critical(f"ProcesarWorker CRASH:\n{traceback.format_exc()}")
            self.resultado.emit(self.texto, "Ocurrió un error interno, señor.", "")

class VozWorker(QThread):
    resultado  = pyqtSignal(str)
    estado_sig = pyqtSignal(str)
    def __init__(self, sil=1.2): super().__init__(); self._sil=sil
    def run(self):
        try:
            txt = voz.escuchar(callback_estado=lambda s: self.estado_sig.emit(s),
                               timeout_silencio=self._sil)
            self.resultado.emit(txt or "")
        except Exception:
            import traceback
            log.critical(f"VozWorker CRASH:\n{traceback.format_exc()}")
            self.resultado.emit("")

class WakeWordWorker(QThread):
    activado   = pyqtSignal()
    comando    = pyqtSignal(str)
    estado_sig = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self._stop  = threading.Event()
        self._pausa = threading.Event()
    def detener(self):  self._stop.set()
    def pausar(self):   self._pausa.set()
    def reanudar(self): self._pausa.clear()
    def run(self):
        wake      = CFG.get("wake_word", "jarvis")
        modo_conv = False   # True → modo conversación: escucha directa sin wake word

        while not self._stop.is_set():
            try:
                if self._pausa.is_set():
                    time.sleep(0.2)
                    modo_conv = False   # pausa manual → salir de modo conversación
                    continue

                if modo_conv:
                    # ── Modo conversación ─────────────────────────────────────
                    # Esperar a que el TTS termine (el procesado de IA puede
                    # tardar varios segundos antes de que empiece a hablar).
                    voz.esperar_fin_tts(timeout_inicio=20.0,
                                        stop_event=self._stop,
                                        pausa_event=self._pausa)
                    if self._stop.is_set():  break
                    if self._pausa.is_set(): modo_conv = False; continue

                    # Pequeña pausa para que HablarWorker.terminado procese
                    # su cambio de estado ("wake") antes de que emitamos "listening".
                    time.sleep(0.15)

                    # Escucha directa: el usuario puede hablar sin decir "jarvis"
                    self.activado.emit()
                    self.estado_sig.emit("listening")
                    txt = voz.escuchar(
                        callback_estado=lambda s: self.estado_sig.emit(s),
                        timeout_silencio=CFG.get("timeout_silencio_wake", 3.0),
                        timeout_max=CFG.get("max_tiempo_grabacion", 15))

                    if txt and txt != "__error_red__":
                        self.comando.emit(txt)
                        modo_conv = True   # mantener modo conversación
                    else:
                        # Sin entrada → volver a esperar la wake word
                        modo_conv = False
                        self.estado_sig.emit("wake")
                else:
                    # ── Modo normal: esperando wake word ──────────────────────
                    self.estado_sig.emit("wake")
                    if voz.escuchar_wake_word(wake, self._stop):
                        if self._stop.is_set(): break
                        self.activado.emit()
                        self.estado_sig.emit("listening")
                        txt = voz.escuchar(
                            callback_estado=lambda s: self.estado_sig.emit(s),
                            timeout_silencio=CFG.get("timeout_silencio_wake", 3.0),
                            timeout_max=CFG.get("max_tiempo_grabacion", 15))
                        if txt and txt != "__error_red__":
                            self.comando.emit(txt)
                            modo_conv = True   # entrar en modo conversación
            except Exception:
                import traceback
                log.critical(f"WakeWordWorker CRASH:\n{traceback.format_exc()}")
                modo_conv = False
                time.sleep(1.0)

# ── Particulas ────────────────────────────────────────────────
class Particula:
    __slots__ = ('x','y','vx','vy','vida','vida_max','radio','color_h','alpha','orb_r','orb_a','orb_va')
    def __init__(self, cx, cy, estado):
        self.orb_r  = random.uniform(15, 105)
        self.orb_a  = random.uniform(0, math.tau)
        self.orb_va = random.uniform(-0.025, 0.025)
        self.x      = cx + self.orb_r * math.cos(self.orb_a)
        self.y      = cy + self.orb_r * math.sin(self.orb_a)
        self.vx     = random.uniform(-0.3, 0.3)
        self.vy     = random.uniform(-0.3, 0.3)
        self.vida_max = random.randint(80, 200)
        self.vida   = random.randint(0, self.vida_max)
        self.radio  = random.uniform(1.0, 3.2)
        self.color_h = self._hue(estado)
        self.alpha  = 0

    @staticmethod
    def _hue(e):
        return {"idle":195,"wake":215,"listening":180,"thinking":228,"speaking":142}.get(e,195)

    def update(self, cx, cy, estado, disolver):
        self.orb_a += self.orb_va
        if disolver:
            dx = self.x - cx; dy = self.y - cy
            self.vx += dx * 0.004; self.vy += dy * 0.004
            self.x += self.vx * 2.8; self.y += self.vy * 2.8
        else:
            tx = cx + self.orb_r * math.cos(self.orb_a)
            ty = cy + self.orb_r * math.sin(self.orb_a)
            self.x += (tx - self.x) * 0.07 + self.vx
            self.y += (ty - self.y) * 0.07 + self.vy
            self.vx *= 0.93; self.vy *= 0.93
        self.vida -= 1
        prog = self.vida / self.vida_max
        self.alpha = int(255 * min(prog * 4, 1.0, (1-prog)*4+0.05))
        self.color_h = self._hue(estado)
        return self.vida > 0

# ── Esfera (sin texto, solo particulas) ───────────────────────
class EsferaWidget(QWidget):
    clicked = pyqtSignal()
    def __init__(self, size=240, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.estado     = "idle"
        self._cx = self._cy = size // 2
        self._parts: list[Particula] = []
        self._tick  = 0
        self._disolver = False
        for _ in range(140):
            self._parts.append(Particula(self._cx, self._cy, self.estado))
        t = QTimer(self); t.timeout.connect(self._frame); t.start(28)

    def set_estado(self, s):
        prev = self.estado; self.estado = s
        self._disolver = (s == "speaking")
        if s != prev:
            for _ in range(50):
                self._parts.append(Particula(self._cx, self._cy, s))

    def _frame(self):
        self._tick += 1
        vivas = [p for p in self._parts if p.update(self._cx, self._cy, self.estado, self._disolver)]
        diff  = 140 - len(vivas)
        for _ in range(min(diff, 8)):
            vivas.append(Particula(self._cx, self._cy, self.estado))
        self._parts = vivas; self.update()

    def paintEvent(self, _):
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0,0,0,0))
        t  = self._tick * 0.04
        cx = self._cx; cy = self._cy
        self._core(p, t, cx, cy)
        for pt in self._parts:
            sat = {"speaking":200,"listening":220,"thinking":180,"wake":100}.get(self.estado,200)
            bri = {"speaking":255,"listening":255,"thinking":210,"wake":130,"idle":200}.get(self.estado,200)
            c = QColor.fromHsv(pt.color_h, sat, bri, pt.alpha)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(c))
            p.drawEllipse(QPointF(pt.x, pt.y), pt.radio, pt.radio)

    def _core(self, p, t, cx, cy):
        cfg = {
            "idle":     ("#001828","#00d4ff",32),
            "wake":     ("#000510","#002850",12),
            "listening":("#001830","#00ffcc",75),
            "thinking": ("#000820","#0044ff",55),
            "speaking": ("#001810","#00ff88",85),
        }
        bg, bord, ga = cfg.get(self.estado, cfg["idle"])
        pulse = 1 + 0.07 * math.sin(t * (3 if self.estado=="listening" else 1.6))
        r = 50 * pulse
        for i in range(5,0,-1):
            gr = QRadialGradient(QPointF(cx,cy), r+i*10)
            c  = QColor(bord); c.setAlpha(max(0, ga-i*13))
            gr.setColorAt(0,c); gr.setColorAt(1,QColor(0,0,0,0))
            p.setBrush(QBrush(gr)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx,cy), r+i*10, r+i*10)
        p.setBrush(QBrush(QColor(bg)))
        p.setPen(QPen(QColor(bord), 1.5))
        p.drawEllipse(QPointF(cx,cy), r, r)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.clicked.emit()

# ── Popup de stats ────────────────────────────────────────────
class StatsPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 220)
        self._drag = None; self._build()
        t = QTimer(self); t.timeout.connect(self._refresh); t.start(1500)
        self._refresh()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0)
        fr  = QFrame()
        fr.setStyleSheet("QFrame{background:rgba(5,8,20,245);border:1px solid #1a3a5a;border-radius:14px;}")
        fl  = QVBoxLayout(fr); fl.setContentsMargins(16,12,16,12); fl.setSpacing(6)
        hdr = QHBoxLayout()
        tl  = QLabel("◈  SISTEMA"); tl.setStyleSheet("color:#00d4ff;font:bold 11px 'Courier New';")
        cb  = QPushButton("✕"); cb.setFixedSize(20,20)
        cb.setStyleSheet("QPushButton{color:#334455;background:transparent;border:none;font:12px;}"
                         "QPushButton:hover{color:#ff3355;}")
        cb.clicked.connect(self.hide)
        hdr.addWidget(tl); hdr.addStretch(); hdr.addWidget(cb)
        fl.addLayout(hdr)
        self._grid = QGridLayout(); self._grid.setSpacing(4)
        fl.addLayout(self._grid)
        fl.addStretch(); lay.addWidget(fr)

    def _bar(self, val, color="#00d4ff"):
        w = QWidget(); w.setFixedHeight(8)
        w.setStyleSheet(f"background:#0a1520;border-radius:4px;")
        lw = QWidget(w); lw.setFixedHeight(8)
        lw.setFixedWidth(max(1, int(160 * val / 100)))
        lw.setStyleSheet(f"background:{color};border-radius:4px;")
        return w

    def _refresh(self):
        import psutil, volumen as vol
        # Limpiar grid
        for i in reversed(range(self._grid.count())):
            w = self._grid.itemAt(i).widget()
            if w: w.deleteLater()

        ST = "color:#a8d8f0;font:10px 'Courier New';"
        DIM= "color:#334455;font:9px 'Courier New';"

        try:
            cpu  = psutil.cpu_percent()
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage('C:\\')
            v    = vol.obtener()
            bat  = psutil.sensors_battery()

            rows = [
                ("CPU",  f"{cpu:.0f}%",  cpu,  "#00d4ff"),
                ("RAM",  f"{ram.percent:.0f}%  {ram.used//1024**3}/{ram.total//1024**3}GB",
                         ram.percent, "#00ff88"),
                ("DISCO",f"{disk.free//1024**3}GB libres",
                         100-disk.percent, "#ffaa00"),
                ("VOL",  f"{v}%",  v, "#aa88ff"),
            ]
            if bat:
                rows.append(("BAT", f"{int(bat.percent)}%  {'⚡' if bat.power_plugged else '🔋'}",
                             bat.percent, "#ff8844"))

            for i,(lbl,val_s,val_n,col) in enumerate(rows):
                l = QLabel(lbl); l.setStyleSheet(DIM)
                v2= QLabel(val_s); v2.setStyleSheet(ST)
                self._grid.addWidget(l,  i, 0)
                self._grid.addWidget(v2, i, 1)
                bar = self._bar(val_n, col)
                self._grid.addWidget(bar, i, 2)
        except Exception as e:
            log.error(f"StatsPopup refresh: {e}")

    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self._drag=e.globalPosition().toPoint()
    def mouseMoveEvent(self,e):
        if self._drag:
            self.move(self.pos()+(e.globalPosition().toPoint()-self._drag))
            self._drag=e.globalPosition().toPoint()
    def mouseReleaseEvent(self,_): self._drag=None

# ── Mini Widget (esquina de pantalla, arrastrable) ────────────
class MiniWidget(QWidget):
    """Esfera pequeña siempre visible en esquina. Drag + click separados."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent,
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(72, 72)
        self._drag      = None
        self._moved     = False   # distingue drag de click

        self._esfera = EsferaWidget(72, self)
        # Instalar eventFilter para interceptar mouse ANTES que EsferaWidget
        self._esfera.installEventFilter(self)

        x = CFG.get("mini_pos_x", -1)
        y = CFG.get("mini_pos_y", -1)
        # Si no hay posición guardada, o si quedó fuera del área visible
        # (ej. cambió la resolución / desconectó un monitor), usar default.
        if x < 0 or y < 0 or not self._pos_en_pantalla(x, y):
            screen = QApplication.primaryScreen().geometry()
            x = screen.width()  - 88
            y = screen.height() - 88
        self.move(x, y)

    @staticmethod
    def _pos_en_pantalla(x, y):
        """True si (x,y) cae dentro de alguna pantalla conectada."""
        for screen in QApplication.screens():
            g = screen.geometry()
            if g.left() <= x <= g.right() and g.top() <= y <= g.bottom():
                return True
        return False

    def set_estado(self, s):
        self._esfera.set_estado(s)

    def _guardar_pos(self):
        CFG["mini_pos_x"] = self.pos().x()
        CFG["mini_pos_y"] = self.pos().y()
        guardar_cfg(CFG)

    def eventFilter(self, obj, event):
        """Intercepta eventos de EsferaWidget para manejar drag vs click."""
        from PyQt6.QtCore import QEvent
        if obj is self._esfera:
            t = event.type()
            if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag  = event.globalPosition().toPoint()
                self._moved = False
                return True   # consumir — no propagar a EsferaWidget
            elif t == QEvent.Type.MouseMove and self._drag is not None:
                delta = event.globalPosition().toPoint() - self._drag
                if delta.manhattanLength() > 4:
                    self._moved = True
                    self.move(self.pos() + delta)
                    self._drag = event.globalPosition().toPoint()
                return True
            elif t == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if not self._moved:
                    self.clicked.emit()   # fue un click, no drag
                self._drag = None
                self._moved = False
                self._guardar_pos()
                return True
        return super().eventFilter(obj, event)

# ── Paneles Chat y Ajustes (compactos) ────────────────────────
class ChatPanel(QWidget):
    send_signal = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window|Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420,500); self._drag=None; self._build()
    def _build(self):
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0)
        fr=QFrame(); fr.setStyleSheet("QFrame{background:rgba(5,8,15,240);border:1px solid #1a3a5a;border-radius:14px;}")
        fl=QVBoxLayout(fr); fl.setContentsMargins(14,12,14,12); fl.setSpacing(8)
        hdr=QHBoxLayout()
        tl=QLabel("◈  HISTORIAL"); tl.setStyleSheet("color:#00d4ff;font:bold 12px 'Courier New';")
        cb=QPushButton("✕"); cb.setFixedSize(22,22)
        cb.setStyleSheet("QPushButton{color:#334455;background:transparent;border:none;font:13px;}QPushButton:hover{color:#ff3355;}")
        cb.clicked.connect(self.hide)
        hdr.addWidget(tl); hdr.addStretch(); hdr.addWidget(cb); fl.addLayout(hdr)
        self.chat=QTextEdit(); self.chat.setReadOnly(True)
        self.chat.setStyleSheet("QTextEdit{background:#020507;color:#a8d8f0;border:1px solid #0d2035;border-radius:8px;font:12px 'Courier New';padding:8px;}")
        fl.addWidget(self.chat)
        row=QHBoxLayout()
        self.entry=QLineEdit(); self.entry.setPlaceholderText("Escribe...")
        self.entry.setStyleSheet("QLineEdit{background:#020507;color:#a8d8f0;border:1px solid #1a3a5a;border-radius:8px;padding:8px;font:12px 'Courier New';}")
        self.entry.returnPressed.connect(self._send)
        sb=QPushButton("▶"); sb.setFixedSize(36,36)
        sb.setStyleSheet("QPushButton{background:#0055ff;color:white;border-radius:8px;font:16px;}QPushButton:hover{background:#0077ff;}")
        sb.clicked.connect(self._send)
        row.addWidget(self.entry); row.addWidget(sb); fl.addLayout(row); lay.addWidget(fr)
    def _send(self):
        t=self.entry.text().strip()
        if t: self.entry.clear(); self.send_signal.emit(t)
    def agregar(self, quien, texto):
        col,pre=("#00d4ff","▶ TÚ") if quien=="usuario" else ("#00ff88","◈ JARVIS")
        self.chat.append(f'<p style="margin:4px 0;"><span style="color:{col};font-weight:bold;">{pre}</span><br><span style="color:#a8d8f0;">{texto}</span></p>')
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self._drag=e.globalPosition().toPoint()
    def mouseMoveEvent(self,e):
        if self._drag:
            self.move(self.pos()+(e.globalPosition().toPoint()-self._drag)); self._drag=e.globalPosition().toPoint()
    def mouseReleaseEvent(self,_): self._drag=None

class AjustesPanel(QWidget):
    cerrado = pyqtSignal(dict)
    def __init__(self, cfg, parent=None):
        super().__init__(parent, Qt.WindowType.Window|Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 620); self._cfg = cfg.copy(); self._drag = None; self._build()

    # ── Helpers de estilo ─────────────────────────────────────
    def _inp(self, val=""):
        w = QLineEdit(val)
        w.setStyleSheet("QLineEdit{background:#020507;color:#a8d8f0;border:1px solid #1a3a5a;"
                        "border-radius:6px;padding:6px;font:11px 'Courier New';}"); return w
    def _lbl(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("color:#334455;font:9px 'Courier New';letter-spacing:1px;"); return l
    def _hint(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("color:#1a3a5a;font:8px 'Courier New';"); return l
    def _sec(self, layout, titulo):
        sp = QFrame(); sp.setFrameShape(QFrame.Shape.HLine)
        sp.setStyleSheet("QFrame{color:#0d2035;margin:2px 0;}"); layout.addWidget(sp)
        l = QLabel(f"— {titulo}")
        l.setStyleSheet("color:#00d4ff;font:bold 9px 'Courier New';letter-spacing:2px;")
        layout.addWidget(l)
    def _slider(self, layout, mn, mx, val, fmt_fn):
        row = QHBoxLayout()
        sl  = QSlider(Qt.Orientation.Horizontal); sl.setRange(mn, mx); sl.setValue(val)
        sl.setStyleSheet(
            "QSlider::groove:horizontal{background:#0a1520;height:6px;border-radius:3px;}"
            "QSlider::handle:horizontal{background:#00d4ff;width:14px;height:14px;"
            "border-radius:7px;margin:-4px 0;}"
            "QSlider::sub-page:horizontal{background:#0055ff;border-radius:3px;}")
        lb = QLabel(fmt_fn(val)); lb.setStyleSheet("color:#00d4ff;font:10px 'Courier New';")
        lb.setFixedWidth(62)
        sl.valueChanged.connect(lambda v, l=lb, f=fmt_fn: l.setText(f(v)))
        row.addWidget(sl); row.addWidget(lb); layout.addLayout(row)
        return sl, lb
    @staticmethod
    def _pct_int(s):
        try: return int(str(s).replace("%","").replace("+",""))
        except: return 10

    # ── Build UI ──────────────────────────────────────────────
    def _build(self):
        from PyQt6.QtWidgets import QScrollArea
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0)
        fr  = QFrame()
        fr.setStyleSheet("QFrame{background:rgba(5,8,15,245);border:1px solid #1a3a5a;border-radius:14px;}")
        fl  = QVBoxLayout(fr); fl.setContentsMargins(18,14,18,12); fl.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        tl  = QLabel("⚙  AJUSTES"); tl.setStyleSheet("color:#00d4ff;font:bold 13px 'Courier New';")
        cb  = QPushButton("✕"); cb.setFixedSize(24,24)
        cb.setStyleSheet("QPushButton{color:#334455;background:transparent;border:none;font:14px;}"
                         "QPushButton:hover{color:#ff3355;}")
        cb.clicked.connect(self._guardar)
        hdr.addWidget(tl); hdr.addStretch(); hdr.addWidget(cb); fl.addLayout(hdr)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#0d2035;"); fl.addWidget(sep)

        # Scroll area
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:#020507;width:5px;border-radius:2px;}"
            "QScrollBar::handle:vertical{background:#1a3a5a;border-radius:2px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        cont = QWidget(); cont.setStyleSheet("background:transparent;")
        cl   = QVBoxLayout(cont); cl.setContentsMargins(0,2,6,2); cl.setSpacing(6)

        CB = ("QCheckBox{color:#a8d8f0;font:11px 'Courier New';spacing:8px;}"
              "QCheckBox::indicator{width:15px;height:15px;border:1px solid #1a3a5a;"
              "border-radius:4px;background:#020507;}"
              "QCheckBox::indicator:checked{background:#00d4ff;}")
        COMBO = ("QComboBox{background:#020507;color:#a8d8f0;border:1px solid #1a3a5a;"
                 "border-radius:6px;padding:6px;font:10px 'Courier New';}"
                 "QComboBox QAbstractItemView{background:#020507;color:#a8d8f0;"
                 "selection-background-color:#0d2035;}")

        # ── GENERAL ───────────────────────────────────────────
        self._sec(cl, "GENERAL")
        cl.addWidget(self._lbl("PALABRA CLAVE (wake word)"))
        self._ww = self._inp(self._cfg.get("wake_word","jarvis")); cl.addWidget(self._ww)
        cl.addWidget(self._lbl("NOMBRE DEL USUARIO"))
        self._nm = self._inp(self._cfg.get("nombre_usuario","senor")); cl.addWidget(self._nm)
        cl.addWidget(self._lbl("CIUDAD PARA CLIMA (vacío = auto)"))
        self._ci = self._inp(self._cfg.get("ciudad_clima","")); cl.addWidget(self._ci)

        cl.addWidget(self._lbl("IDIOMA PRINCIPAL DE STT"))
        self._idcb = QComboBox(); self._idcb.setStyleSheet(COMBO)
        self._idiomas = [
            ("Español (España)",      "es-ES"),
            ("Español (México)",      "es-MX"),
            ("English (US)",          "en-US"),
            ("English (UK)",          "en-GB"),
            ("Português (Brasil)",    "pt-BR"),
            ("Français",              "fr-FR"),
        ]
        cur_id = self._cfg.get("idioma","es-ES")
        for i,(n,code) in enumerate(self._idiomas):
            self._idcb.addItem(n)
            if code == cur_id: self._idcb.setCurrentIndex(i)
        cl.addWidget(self._idcb)

        # ── VOZ ───────────────────────────────────────────────
        self._sec(cl, "VOZ")
        cl.addWidget(self._lbl("PERFIL DE VOZ"))
        self._vcb = QComboBox(); self._vcb.setStyleSheet(COMBO)
        self._voces = voz.obtener_voces(); cur = self._cfg.get("voz_id","")
        for i,(n,vid) in enumerate(self._voces):
            self._vcb.addItem(n)
            if vid == cur: self._vcb.setCurrentIndex(i)
        cl.addWidget(self._vcb)

        cl.addWidget(self._lbl("VELOCIDAD DE VOZ"))
        self._vel, _ = self._slider(cl, -50, 50,
            self._pct_int(self._cfg.get("voz_velocidad","+10%")),
            lambda v: f"{'+' if v>=0 else ''}{v}%")

        cl.addWidget(self._lbl("VOLUMEN DE VOZ"))
        self._vol_v, _ = self._slider(cl, -50, 50,
            self._pct_int(self._cfg.get("voz_volumen","+0%")),
            lambda v: f"{'+' if v>=0 else ''}{v}%")

        # ── AUDIO / MICRÓFONO ──────────────────────────────────
        self._sec(cl, "AUDIO / MICROFONO")
        cl.addWidget(self._lbl("SILENCIO PARA CORTAR (al hablar directamente)"))
        self._sl, _ = self._slider(cl, 400, 4000,
            int(self._cfg.get("silencio_timeout",1.2)*1000),
            lambda v: f"{v}ms")

        cl.addWidget(self._lbl("TIEMPO DE ESCUCHA TRAS WAKE WORD"))
        cl.addWidget(self._hint("  Si Jarvis se cierra antes de que termines, sube este valor"))
        self._sl_wk, _ = self._slider(cl, 1000, 8000,
            int(self._cfg.get("timeout_silencio_wake",3.0)*1000),
            lambda v: f"{v/1000:.1f}s")

        cl.addWidget(self._lbl("TIEMPO MAXIMO DE GRABACION"))
        self._sl_mx, _ = self._slider(cl, 5, 30,
            int(self._cfg.get("max_tiempo_grabacion",15)),
            lambda v: f"{v}s")

        cl.addWidget(self._lbl("SENSIBILIDAD DEL MICROFONO (umbral de silencio)"))
        cl.addWidget(self._hint("  Baja = más sensible (capta voces bajas)   Sube = menos (ignora ruido)"))
        self._sl_th, _ = self._slider(cl, 100, 1500,
            int(self._cfg.get("silencio_threshold",500)),
            lambda v: str(v))

        # ── APARIENCIA ────────────────────────────────────────
        self._sec(cl, "APARIENCIA")
        cl.addWidget(self._lbl("TRANSPARENCIA DE LA VENTANA"))
        self._sl_tr, _ = self._slider(cl, 100, 255,
            int(self._cfg.get("transparencia",230)),
            lambda v: f"{int(v/255*100)}%")

        self._chk_top = QCheckBox("Ventana siempre encima")
        self._chk_top.setChecked(self._cfg.get("siempre_encima",True))
        self._chk_top.setStyleSheet(CB); cl.addWidget(self._chk_top)

        # ── DISPOSITIVOS DE AUDIO ────────────────────────────────────────────────
        self._sec(cl, "DISPOSITIVOS DE AUDIO")
        cl.addWidget(self._hint("  Microfono y altavoz que usa Jarvis para escuchar y hablar."))
        cl.addWidget(self._hint("  'Dispositivo por defecto' usa el que Windows tiene configurado."))
        try:
            _entradas, _salidas = voz.listar_dispositivos()
        except Exception:
            _entradas = [(-1, "Dispositivo por defecto")]
            _salidas  = [(-1, "Dispositivo por defecto")]
        cl.addWidget(self._lbl("MICROFONO (ENTRADA)"))
        self._cb_entrada = QComboBox()
        self._cb_entrada.setStyleSheet(
            "QComboBox{background:#0a1520;color:#00d4ff;border:1px solid #1a3a5a;"
            "border-radius:6px;padding:4px;font:9px 'Courier New';min-width:280px;}"
            "QComboBox::drop-down{border:0;}"
            "QComboBox QAbstractItemView{background:#0a1520;color:#00d4ff;"
            "selection-background-color:#1a3a5a;}")
        self._entradas_data = _entradas
        for idx_d, nombre in _entradas:
            self._cb_entrada.addItem(f"[{idx_d}] {nombre}")
        cur_in = self._cfg.get("dispositivo_entrada", -1)
        cur_in_idx = next((i for i,(idx_d,_) in enumerate(_entradas) if idx_d==cur_in), 0)
        self._cb_entrada.setCurrentIndex(cur_in_idx)
        cl.addWidget(self._cb_entrada)

        cl.addWidget(self._lbl("ALTAVOZ (SALIDA)"))
        self._cb_salida = QComboBox()
        self._cb_salida.setStyleSheet(
            "QComboBox{background:#0a1520;color:#00d4ff;border:1px solid #1a3a5a;"
            "border-radius:6px;padding:4px;font:9px 'Courier New';min-width:280px;}"
            "QComboBox::drop-down{border:0;}"
            "QComboBox QAbstractItemView{background:#0a1520;color:#00d4ff;"
            "selection-background-color:#1a3a5a;}")
        self._salidas_data = _salidas
        for idx_d, nombre in _salidas:
            self._cb_salida.addItem(f"[{idx_d}] {nombre}")
        cur_out = self._cfg.get("dispositivo_salida", -1)
        cur_out_idx = next((i for i,(idx_d,_) in enumerate(_salidas) if idx_d==cur_out), 0)
        self._cb_salida.setCurrentIndex(cur_out_idx)
        cl.addWidget(self._cb_salida)

        # ── MEMORIA DE SESION───────────────────────────────
        self._sec(cl, "MEMORIA DE SESION")
        cl.addWidget(self._hint("  Cuantos turnos (pregunta + respuesta) recuerda Jarvis"))
        cl.addWidget(self._hint("  en la conversacion actual. Mas turnos = mas contexto,"))
        cl.addWidget(self._hint("  pero mas tokens por consulta a la IA."))
        cl.addWidget(self._lbl("PROFUNDIDAD DE HISTORIAL"))
        self._sl_hist, _ = self._slider(cl, 2, 50,
            int(self._cfg.get("max_historial", 20)),
            lambda v: f"{v} turnos")

        # ── ACTIVACION ─────────────────────────────────────────────
        self._sec(cl, "ACTIVACION")
        self._chk_ww = QCheckBox("Wake word siempre activo")
        self._chk_ww.setChecked(self._cfg.get("wake_word_activo",True))
        self._chk_ww.setStyleSheet(CB); cl.addWidget(self._chk_ww)

        # ── PORCUPINE (wake word offline) ─────────────────────────
        self._sec(cl, "PORCUPINE — WAKE WORD OFFLINE")
        cl.addWidget(self._hint("  OPCIONAL: mejora precision y reduce latencia a ~32 ms."))
        cl.addWidget(self._hint("  Sin key: usa openWakeWord offline (frase: 'hey jarvis')."))
        cl.addWidget(self._hint("  Obtener key GRATUITA: picovoice.ai -> Console -> AccessKey"))
        cl.addWidget(self._lbl("ACCESS KEY (dejar vacio = Google STT)"))
        self._porc_key = self._inp(self._cfg.get("porcupine_access_key",""))
        self._porc_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._porc_key.setPlaceholderText("Pegar aqui tu Picovoice Access Key...")
        cl.addWidget(self._porc_key)
        _btn_show = QPushButton("Mostrar / Ocultar key")
        _btn_show.setStyleSheet(
            "QPushButton{background:#0a1520;color:#334455;border:1px solid #1a3a5a;"
            "border-radius:6px;padding:4px;font:9px 'Courier New';}"
            "QPushButton:hover{color:#00d4ff;}")
        _btn_show.clicked.connect(
            lambda: self._porc_key.setEchoMode(
                QLineEdit.EchoMode.Normal
                if self._porc_key.echoMode() == QLineEdit.EchoMode.Password
                else QLineEdit.EchoMode.Password))
        cl.addWidget(_btn_show)

        cl.addStretch()
        scroll.setWidget(cont); fl.addWidget(scroll)

        sv = QPushButton("◈  GUARDAR Y APLICAR")
        sv.setStyleSheet(
            "QPushButton{background:#0055ff;color:white;border-radius:8px;"
            "padding:10px;font:bold 12px 'Courier New';}"
            "QPushButton:hover{background:#0077ff;}")
        sv.clicked.connect(self._guardar); fl.addWidget(sv)
        lay.addWidget(fr)

    # ── Guardar ───────────────────────────────────────────────
    def _guardar(self):
        idx = self._vcb.currentIndex()
        vel = self._vel.value()
        vol = self._vol_v.value()
        id_idx = self._idcb.currentIndex()
        self._cfg.update({
            "wake_word":             self._ww.text().strip().lower() or "jarvis",
            "nombre_usuario":        self._nm.text().strip() or "senor",
            "ciudad_clima":          self._ci.text().strip(),
            "idioma":                self._idiomas[id_idx][1] if id_idx < len(self._idiomas) else "es-ES",
            "voz_id":                self._voces[idx][1] if idx < len(self._voces) else self._cfg.get("voz_id",""),
            "voz_velocidad":         f"{'+' if vel >= 0 else ''}{vel}%",
            "voz_volumen":           f"{'+' if vol >= 0 else ''}{vol}%",
            "silencio_timeout":      self._sl.value()    / 1000,
            "timeout_silencio_wake": self._sl_wk.value() / 1000,
            "max_tiempo_grabacion":  self._sl_mx.value(),
            "silencio_threshold":    self._sl_th.value(),
            "transparencia":         self._sl_tr.value(),
            "wake_word_activo":      self._chk_ww.isChecked(),
            "siempre_encima":        self._chk_top.isChecked(),
            "porcupine_access_key":  self._porc_key.text().strip(),
            "max_historial":         self._sl_hist.value(),
            "dispositivo_entrada":   self._entradas_data[self._cb_entrada.currentIndex()][0],
            "dispositivo_salida":    self._salidas_data [self._cb_salida.currentIndex() ][0],
        })
        guardar_cfg(self._cfg); self.cerrado.emit(self._cfg); self.hide()

    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self._drag=e.globalPosition().toPoint()
    def mouseMoveEvent(self,e):
        if self._drag:
            self.move(self.pos()+(e.globalPosition().toPoint()-self._drag))
            self._drag=e.globalPosition().toPoint()
    def mouseReleaseEvent(self,_): self._drag=None

# ── Ventana principal ──────────────────────────────────────────
class JarvisWindow(QMainWindow):
    _sig_estado = pyqtSignal(str)
    _sig_chat   = pyqtSignal(str, str)
    _sig_hablar = pyqtSignal(str)
    _sig_info   = pyqtSignal(str, str)

    def __init__(self, app: QApplication):
        super().__init__()
        self._app        = app
        self.setWindowTitle("JARVIS")
        self.setFixedSize(360, 540)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        flags = Qt.WindowType.FramelessWindowHint
        if CFG.get("siempre_encima", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self._drag        = None
        self._escuchando  = False
        self._workers: list[QThread] = []
        self._chat_win    = None
        self._ajustes_win = None
        self._stats_popup = None
        self._mini        = None
        self._wake_w: WakeWordWorker | None = None

        self._sig_estado.connect(self._on_estado)
        self._sig_chat.connect(self._on_chat)
        self._sig_hablar.connect(self._on_hablar)
        self._sig_info.connect(self._on_info)

        self._build_ui()
        self._build_tray()
        self._build_mini()
        comandos.set_hablar_callback(lambda t: self._sig_hablar.emit(t))
        self._aplicar_cfg(CFG)
        QTimer.singleShot(1800, self._saludo)

    # ── UI principal ─────────────────────────────────────────
    def _mkbtn(self, txt, bg="#0a1520", hov="#0d2035", w=28, h=28):
        b = QPushButton(txt); b.setFixedSize(w, h)
        b.setStyleSheet(f"QPushButton{{background:{bg};color:#a8d8f0;border-radius:7px;font:12px;}}"
                        f"QPushButton:hover{{background:{hov};color:#00d4ff;}}"); return b

    def _build_ui(self):
        cw = QWidget(); self.setCentralWidget(cw)
        cw.setStyleSheet("background:rgba(5,8,15,225);border-radius:18px;")
        root = QVBoxLayout(cw); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Titlebar
        tb = QWidget(); tb.setFixedHeight(44)
        tb.setStyleSheet("background:rgba(8,13,24,200);border-radius:18px 18px 0 0;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(14,0,8,0)
        lbl = QLabel("◈  J.A.R.V.I.S")
        lbl.setStyleSheet("color:#00d4ff;font:bold 13px 'Courier New';letter-spacing:2px;")
        tbl.addWidget(lbl); tbl.addStretch()
        for txt, fn, bg, hov in [
            ("💬", self._toggle_chat,    "#0a1520", "#0d2035"),
            ("⚙",  self._toggle_ajustes,"#0a1520", "#0d2035"),
            ("📊", self._toggle_stats,  "#0a1520", "#0d2035"),
            ("─",  self._minimizar,     "#0a1520", "#0d2035"),
            ("✕",  self._cerrar,        "#1a0a10", "#3a0a15"),
        ]:
            b = self._mkbtn(txt, bg, hov); b.clicked.connect(fn); tbl.addWidget(b)
        root.addWidget(tb)

        # Esfera
        ec = QWidget(); ec.setStyleSheet("background:transparent;")
        el = QVBoxLayout(ec); el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._esfera = EsferaWidget(220)
        self._esfera.clicked.connect(self._toggle_escucha)
        el.addWidget(self._esfera); root.addWidget(ec)

        # Estado
        self._lbl_estado = QLabel("◈  En espera, señor")
        self._lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_estado.setStyleSheet("color:#335566;font:11px 'Courier New';letter-spacing:1px;")
        root.addWidget(self._lbl_estado)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#0a1a2a;margin:0 8px;"); root.addWidget(sep)

        # Botones inferiores
        br = QWidget(); br.setStyleSheet("background:rgba(8,13,24,130);border-radius:0 0 18px 18px;")
        brl = QHBoxLayout(br); brl.setContentsMargins(12,6,12,10)
        BS = ("QPushButton{background:#0a1520;color:#334455;border:1px solid #1a3a5a;"
              "border-radius:8px;padding:5px;font:9px 'Courier New';}"
              "QPushButton:hover{background:#0d2035;color:#00d4ff;}")
        for txt, fn in [("🧠 Nueva sesión", self._nueva_sesion), ("📋 Logs", self._abrir_logs)]:
            b = QPushButton(txt); b.setStyleSheet(BS); b.clicked.connect(fn); brl.addWidget(b)
        root.addWidget(br)
        self._cargar_voces()

    # ── System Tray ───────────────────────────────────────────
    def _build_tray(self):
        # Icono generado como circulo cian
        pix = QPixmap(32, 32); pix.fill(QColor(0,0,0,0))
        p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#00d4ff"))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, 24, 24); p.end()
        icon = QIcon(pix)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("J.A.R.V.I.S")

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#05080f;color:#a8d8f0;border:1px solid #1a3a5a;border-radius:8px;}"
            "QMenu::item{padding:6px 20px;}QMenu::item:selected{background:#0d2035;color:#00d4ff;}")

        act_show   = QAction("◈  Mostrar Jarvis",  self)
        act_chat   = QAction("💬  Chat",            self)
        act_stats  = QAction("📊  Sistema",         self)
        act_nueva  = QAction("🧠  Nueva sesión",    self)
        act_quit   = QAction("✕   Salir",           self)

        act_show.triggered.connect(self._mostrar_desde_tray)
        act_chat.triggered.connect(self._toggle_chat)
        act_stats.triggered.connect(self._toggle_stats)
        act_nueva.triggered.connect(self._nueva_sesion)
        act_quit.triggered.connect(self._salir_completo)

        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_chat)
        menu.addAction(act_stats)
        menu.addSeparator()
        menu.addAction(act_nueva)
        menu.addSeparator()
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_click)
        self._tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._mostrar_desde_tray()

    def _mostrar_desde_tray(self):
        self.showNormal(); self.activateWindow(); self.raise_()

    # ── Mini widget esquina ───────────────────────────────────
    def _build_mini(self):
        self._mini = MiniWidget()
        self._mini.clicked.connect(self._toggle_escucha)
        self._mini.show()

    # ── Voces (solo para uso interno) ────────────────────────
    def _cargar_voces(self): pass
    def _cambiar_voz(self, nombre):
        for n, v in voz.obtener_voces():
            if n == nombre: voz.cambiar_voz(v); break

    # ── Config ────────────────────────────────────────────────
    def _aplicar_cfg(self, cfg):
        global CFG; CFG = cfg
        # Recarga voz.py desde ajustes.json (timeouts, threshold, idioma).
        # Antes los valores se sobrescribían en config.py, pero voz.py
        # ya los lee directamente del JSON.
        voz.refrescar_runtime_cfg()
        # Mantener config.py sincronizado para módulos externos
        # (comandos.py, cerebro.py) que aún importan las constantes.
        import config as cm
        cm.SILENCE_TIMEOUT   = cfg.get("silencio_timeout",      1.2)
        cm.SILENCE_THRESHOLD = cfg.get("silencio_threshold",    500)
        cm.MAX_RECORD_SECS   = cfg.get("max_tiempo_grabacion",  15)
        voz.cambiar_voz(cfg.get("voz_id", "es-MX-JorgeNeural"))
        voz._VOICE_RATE = cfg.get("voz_velocidad", "+10%")
        voz._VOICE_VOL  = cfg.get("voz_volumen",   "+0%")
        self.setWindowOpacity(cfg.get("transparencia", 230) / 255)
        nombre = cfg.get("nombre_usuario", "senor")
        if nombre != memoria.get_nombre_usuario():
            memoria.set_nombre_usuario(nombre)
        if cfg.get("wake_word_activo", True):
            self._iniciar_wake()
        else:
            self._detener_wake()

    # ── Estado ────────────────────────────────────────────────
    def _on_estado(self, s):
        MAP = {
            "idle":      ("◈  En espera, señor",   "#335566"),
            "wake":      ("◉  Escucha activa...",  "#1a4060"),
            "listening": ("◉  Escuchando...",       "#00d4ff"),
            "thinking":  ("⚙  Procesando...",       "#ffaa00"),
            "speaking":  ("◈  Hablando...",          "#00ff88"),
            "error":     ("⚠  Error",               "#ff3355"),
        }
        txt, col = MAP.get(s, (s, "#a8d8f0"))
        self._lbl_estado.setText(txt)
        self._lbl_estado.setStyleSheet(f"color:{col};font:11px 'Courier New';letter-spacing:1px;")
        self._esfera.set_estado(s)
        if self._mini: self._mini.set_estado(s)

    # ── Chat ──────────────────────────────────────────────────
    def _on_chat(self, quien, txt):
        if not self._chat_win:
            self._chat_win = ChatPanel()
            self._chat_win.send_signal.connect(self._procesar)
        self._chat_win.agregar(quien, txt)

    def _toggle_chat(self):
        if not self._chat_win:
            self._chat_win = ChatPanel()
            self._chat_win.send_signal.connect(self._procesar)
            self._chat_win.agregar("jarvis", f"Hola, {memoria.get_nombre_usuario()}.")
        p = self.pos()
        self._chat_win.move(p.x() + self.width() + 10, p.y())
        self._chat_win.setVisible(not self._chat_win.isVisible())

    # ── Ajustes ───────────────────────────────────────────────
    def _toggle_ajustes(self):
        if not self._ajustes_win:
            self._ajustes_win = AjustesPanel(CFG)
            self._ajustes_win.cerrado.connect(self._aplicar_cfg)
        p = self.pos()
        self._ajustes_win.move(p.x() + self.width() + 10, p.y())
        self._ajustes_win.setVisible(not self._ajustes_win.isVisible())

    # ── Stats popup ───────────────────────────────────────────
    def _toggle_stats(self):
        if not self._stats_popup:
            self._stats_popup = StatsPopup(self)
        p = self.pos()
        self._stats_popup.move(p.x() + self.width() + 10, p.y())
        self._stats_popup.setVisible(not self._stats_popup.isVisible())

    # ── Info visual ───────────────────────────────────────────
    def _on_info(self, tipo, resp):
        pass  # Placeholder para panel de info clima/crypto si se necesita

    # ── TTS ───────────────────────────────────────────────────
    def _on_hablar(self, txt):
        self._sig_estado.emit("speaking")
        w = HablarWorker(txt)
        w.terminado.connect(lambda: self._sig_estado.emit(
            "wake" if CFG.get("wake_word_activo") else "idle"))
        self._track(w); w.start()

    # ── Procesar ──────────────────────────────────────────────
    def _procesar(self, txt):
        if not txt or txt == "__error_red__":
            self._sig_estado.emit("idle"); self._escuchando = False; return
        self._sig_chat.emit("usuario", txt)
        w = ProcesarWorker(txt)
        w.estado_sig.connect(self._sig_estado)
        w.resultado.connect(self._on_resultado)
        self._track(w); w.start()

    def _on_resultado(self, usuario, resp, tipo):
        self._sig_chat.emit("jarvis", resp)
        if tipo: self._sig_info.emit(tipo, resp)
        if resp: self._sig_hablar.emit(resp)
        self._escuchando = False

    # ── Micrófono manual ─────────────────────────────────────
    def _toggle_escucha(self):
        if self._escuchando: return
        if self._wake_w: self._wake_w.pausar()
        self._escuchando = True
        sil = CFG.get("silencio_timeout", 1.2)
        w = VozWorker(sil)
        w.estado_sig.connect(self._sig_estado)
        w.resultado.connect(self._after_mic)
        self._track(w); w.start()

    def _after_mic(self, txt):
        self._procesar(txt)
        # Reanudar inmediatamente: WakeWordWorker espera el TTS
        # internamente via esperar_fin_tts() / _tts_activo.
        if CFG.get("wake_word_activo", True) and self._wake_w:
            self._wake_w.reanudar()

    # ── Wake word ─────────────────────────────────────────────
    def _iniciar_wake(self):
        self._detener_wake()
        w = WakeWordWorker()
        w.activado.connect(lambda: self._sig_estado.emit("listening"))
        w.comando.connect(self._procesar)
        w.estado_sig.connect(self._sig_estado)
        self._wake_w = w; self._track(w); w.start()
        log.info("Wake word activo.")

    def _detener_wake(self):
        if self._wake_w: self._wake_w.detener(); self._wake_w = None

    # ── Arranque ──────────────────────────────────────────────
    def _saludo(self):
        def _run():
            try:
                s = arranque.construir_saludo()
                self._sig_chat.emit("jarvis", s)
                self._sig_hablar.emit(s)
            except Exception as e:
                log.error(f"Saludo: {e}")
        threading.Thread(target=_run, daemon=True).start()

    # ── Utilidades ────────────────────────────────────────────
    def _nueva_sesion(self):
        cerebro.limpiar_historial()
        self._sig_chat.emit("jarvis", "Nueva sesión iniciada.")

    def _abrir_logs(self):
        from logger import _LOG_FILE
        os.startfile(_LOG_FILE)

    def _track(self, w):
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)

    def _minimizar(self):
        """Minimizar al tray en lugar de a la barra de tareas."""
        self.hide()
        self._tray.showMessage("J.A.R.V.I.S",
                               "Jarvis sigue activo en segundo plano.",
                               QSystemTrayIcon.MessageIcon.Information, 2000)

    def _salir_completo(self):
        self._detener_wake()
        voz.liberar_porcupine()       # liberar recursos C de Porcupine
        voz.liberar_oww()             # liberar openWakeWord
        arranque.guardar_cierre()
        self._tray.hide()
        QApplication.quit()

    def _cerrar(self):
        """El boton X oculta la ventana (Jarvis sigue en tray)."""
        self._minimizar()

    def closeEvent(self, e):
        """Interceptar cierre de ventana — ir al tray."""
        e.ignore()
        self._minimizar()

    # ── Arrastrar ─────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self._drag:
            self.move(self.pos() + (e.globalPosition().toPoint() - self._drag))
            self._drag = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, _):
        self._drag = None


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    # ── Exception hooks globales ─────────────────────────────
    # Sin esto, una excepcion no capturada en cualquier QThread
    # mata el proceso silenciosamente sin escribir al log.
    def _hook_excepcion(tipo, valor, tb):
        import traceback
        log.critical("EXCEPCION NO CAPTURADA:\n" +
                     "".join(traceback.format_exception(tipo, valor, tb)))
    sys.excepthook = _hook_excepcion

    # Hook para excepciones en QThreads (PyQt6 especifico)
    from PyQt6.QtCore import qInstallMessageHandler
    def _qt_msg_handler(mode, ctx, msg):
        if "error" in msg.lower() or "exception" in msg.lower():
            log.error(f"Qt: {msg}")
    qInstallMessageHandler(_qt_msg_handler)

    log.info("Iniciando Jarvis...")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    voz.precargar_whisper()
    win = JarvisWindow(app)
    win.show()
    sys.exit(app.exec())
