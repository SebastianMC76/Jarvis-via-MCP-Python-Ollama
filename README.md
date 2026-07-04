# J.A.R.V.I.S 🤖
Asistente de voz personal inspirado en Iron Man. Controla tu PC, responde preguntas,
abre programas, lee el clima, traduce, controla OBS y mucho más — todo por voz.

---

## Instalación (desde cero)

### Requisitos previos
- Windows 10 u 11
- Conexión a internet
- Micrófono

### Paso 1 — Instalar programas externos
Ejecuta **`INSTALAR_EXTERNO.bat`** haciendo doble clic.

Esto instala automáticamente:
- **Python 3.11** — el lenguaje en que corre Jarvis
- **ffmpeg** — necesario para que Whisper procese audio sin internet
- **Tesseract OCR** — para el comando "lee la pantalla"

> Si Windows pregunta "¿Deseas permitir que esta aplicación haga cambios?", di que **Sí**.
> Si pide reiniciar, reinicia y vuelve a ejecutar el archivo.

---

### Paso 2 — Instalar librerías de Python
Ejecuta **`INSTALAR.bat`** haciendo doble clic.

Esto instala todas las librerías que necesita Jarvis (IA, voz, interfaz gráfica, etc.).
Al final verás una lista de verificación — todos los `[OK]` significan que está bien.

---

### Paso 3 — Configurar la API key de Groq (gratis)
Jarvis usa Groq como cerebro de IA. Es completamente gratuito.

1. Ve a **https://console.groq.com/keys**
2. Crea una cuenta (o entra con Google)
3. Clic en **"Create API Key"**, copia la key
4. Abre el archivo **`config.py`** con el Bloc de notas
5. En la línea que dice `API_KEY = "..."`, reemplaza el contenido por tu key
6. Guarda el archivo (Ctrl+S)

---

### Paso 4 — Iniciar Jarvis
Ejecuta **`Iniciar Jarvis.bat`** haciendo doble clic.

Jarvis aparecerá como una esfera animada en la pantalla y un ícono en la barra de tareas.
Di **"Jarvis"** para activarlo y luego habla tu comando.

---

## Características principales

| Categoría | Ejemplos de comandos |
|-----------|----------------------|
| **Aplicaciones** | "abre Chrome", "abre Microsoft Word", "abre Spotify" |
| **Sistema** | "cuánta RAM tengo", "temperatura del CPU", "apaga la PC" |
| **Información** | "qué hora es", "cómo está el clima", "precio del Bitcoin" |
| **Entretenimiento** | "reproduce jazz en YouTube", "busca noticias de tecnología" |
| **Productividad** | "inicia un pomodoro de 45 minutos", "activa no molestar" |
| **Automatización** | "haz click en 500,300", "escribe hola mundo", "atajo ctrl+s" |
| **Traducción** | "traduce hello al español", "traduce buenas noches al inglés" |
| **OCR** | "lee la pantalla", "qué dice en pantalla" |
| **OBS** | "empieza a grabar", "cambia a la escena Gameplay" |
| **Calendario** | "qué tengo hoy", "qué tengo esta semana" |

---

## Funciones opcionales (configuración adicional)

### Google Calendar
Requiere credenciales OAuth de Google (gratuitas):
1. Ve a **https://console.cloud.google.com**
2. Crea un proyecto → habilita **"Google Calendar API"**
3. Credenciales → OAuth 2.0 → Tipo: "Aplicación de escritorio"
4. Descarga el JSON y renómbralo `credentials_calendar.json`
5. Ponlo en la carpeta de Jarvis
6. La primera vez que uses el calendario, se abrirá el navegador para autorizar

### Control de OBS Studio
1. Abre OBS → **Herramientas → Configuración del servidor WebSocket**
2. Activa "Habilitar servidor WebSocket"
3. Puerto: `4455`, sin contraseña (o edita `obs_control.py` para agregarla)
4. Listo — di "jarvis, empieza a grabar"

### Reconocimiento de voz sin internet (Whisper)
Se activa automáticamente si no hay internet. La primera vez que lo uses,
descarga el modelo (~465 MB) en segundo plano. No requiere configuración.

---

## Estructura de archivos

```
Jarvis/
├── INSTALAR_EXTERNO.bat  ← Paso 1: Python, ffmpeg, Tesseract
├── INSTALAR.bat          ← Paso 2: librerias Python
├── Iniciar Jarvis.bat    ← Ejecutar Jarvis
├── config.py             ← API keys y configuración
│
├── main.py               ← Interfaz gráfica (PyQt6)
├── cerebro.py            ← IA (Groq / LLaMA 3.3)
├── voz.py                ← Micrófono y texto a voz
├── comandos.py           ← Todos los comandos disponibles
├── memoria.py            ← Memoria de conversación
├── automatizacion.py     ← Click, teclado, ventanas
├── vision.py             ← OCR y análisis de pantalla
│
├── traduccion.py         ← Google Translate (sin key)
├── obs_control.py        ← Control de OBS via WebSocket
├── calendar_mod.py       ← Google Calendar
│
├── clima.py              ← Clima por IP o ciudad
├── apis.py               ← Wikipedia, noticias, crypto
├── sistema.py            ← Info de hardware
├── red.py                ← Monitoreo de red
├── volumen.py            ← Control de volumen nativo
├── youtube.py            ← Búsqueda y reproducción
├── pomodoro.py           ← Timer Pomodoro + no molestar
├── protocolos.py         ← Macros de voz personalizados
├── historial.py          ← Historial de conversaciones
├── guia.py               ← Guías paso a paso
│
├── ajustes.json          ← Configuración guardada
├── memoria_*.json        ← Memoria del usuario
└── jarvis.log            ← Registro de actividad
```

---

## Solución de problemas comunes

**Jarvis no me entiende bien**
→ Habla cerca del micrófono, en un lugar sin mucho ruido.
→ En Ajustes (ícono ⚙), sube el "Tiempo de silencio" para que espere más.

**Dice "No encontré el programa X"**
→ El programa debe estar instalado en la PC.
→ Puedes agregar su ruta en `comandos.py` en el diccionario `RUTAS`.

**Error al arrancar sobre PyQt6 o sounddevice**
→ Vuelve a ejecutar `INSTALAR.bat`.

**Jarvis no detecta la wake word "jarvis"**
→ Asegúrate de que el micrófono esté seleccionado correctamente en Windows.
→ Puedes cambiar la palabra clave en el ícono ⚙ de Ajustes.

**El calendario no funciona**
→ Verifica que `credentials_calendar.json` está en la carpeta de Jarvis.
→ La primera vez necesita internet para autorizar.

---

## Créditos
- **IA**: Groq (LLaMA 3.3 70B) — https://groq.com
- **Voz TTS**: Microsoft Edge TTS
- **STT online**: Google Speech Recognition
- **STT offline**: OpenAI Whisper
- **Interfaz**: PyQt6
