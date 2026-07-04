@echo off
setlocal EnableDelayedExpansion
title J.A.R.V.I.S - Instalador de Librerias Python
color 0B

echo.
echo  +======================================================+
echo  ^|         J.A.R.V.I.S  --  Paso 2 de 2               ^|
echo  ^|       Instalador de Librerias Python                 ^|
echo  +======================================================+
echo.

:: ---------------------------------------------------------
:: VERIFICAR PYTHON
:: ---------------------------------------------------------
py --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo.
    echo  Ejecuta primero INSTALAR_EXTERNO.bat
    echo  y luego vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('py --version 2^>^&1') do set PYVER=%%i
echo  [OK] %PYVER% encontrado.
echo.

:: ---------------------------------------------------------
:: ACTUALIZAR PIP
:: ---------------------------------------------------------
echo  Actualizando pip...
py -m pip install --upgrade pip --quiet
echo  [OK] pip actualizado.
echo.

:: ---------------------------------------------------------
:: LIBRERIAS PRINCIPALES (requeridas siempre)
:: ---------------------------------------------------------
echo  ==================================================
echo   Instalando librerias principales...
echo  ==================================================
echo.
py -m pip install ^
    groq ^
    edge-tts ^
    sounddevice ^
    soundfile ^
    numpy ^
    speechrecognition ^
    requests ^
    pycaw ^
    comtypes ^
    pywin32 ^
    pillow ^
    psutil ^
    mss ^
    pyautogui ^
    pygetwindow ^
    PyQt6 ^
    --quiet

if errorlevel 1 (
    echo.
    echo  [ERROR] Fallo la instalacion de librerias principales.
    echo  Revisa tu conexion a internet e intenta de nuevo.
    echo.
    pause
    exit /b 1
)
echo  [OK] Librerias principales instaladas.
echo.

:: ---------------------------------------------------------
:: LIBRERIAS OPCIONALES
:: ---------------------------------------------------------
echo  ==================================================
echo   Instalando librerias opcionales...
echo   (Whisper, traduccion, OBS, Google Calendar)
echo  ==================================================
echo.

echo  - Whisper (reconocimiento de voz offline)...
echo    AVISO: descarga ~500MB la primera vez que uses Jarvis.
py -m pip install openai-whisper --quiet
if errorlevel 1 (echo    [AVISO] Whisper no se pudo instalar.) else (echo    [OK] Whisper instalado.)

echo  - openWakeWord (wake word offline, sin cuenta, frase: hey jarvis)...
py -m pip install openwakeword --quiet
if errorlevel 1 (echo    [AVISO] openWakeWord no se pudo instalar.) else (echo    [OK] openWakeWord instalado.)

echo  - Porcupine (wake word offline OPCIONAL, mejor precision)...
py -m pip install pvporcupine --quiet
if errorlevel 1 (echo    [AVISO] Porcupine no se pudo instalar.) else (echo    [OK] Porcupine instalado.)

echo  - Traduccion (sin API key)...
py -m pip install deep-translator --quiet
if errorlevel 1 (echo    [AVISO] Traductor no instalado.) else (echo    [OK] Traductor instalado.)

echo  - Control de OBS Studio...
py -m pip install obsws-python --quiet
if errorlevel 1 (echo    [AVISO] Control OBS no instalado.) else (echo    [OK] Control OBS instalado.)

echo  - Google Calendar...
py -m pip install google-auth google-auth-oauthlib google-api-python-client --quiet
if errorlevel 1 (echo    [AVISO] Google Calendar no instalado.) else (echo    [OK] Google Calendar instalado.)

echo  - APIs adicionales...
py -m pip install pytesseract wikipedia-api --quiet >nul 2>&1

echo.
echo  [OK] Librerias opcionales procesadas.
echo.

:: ---------------------------------------------------------
:: VERIFICAR INSTALACION
:: ---------------------------------------------------------
echo  ==================================================
echo   Verificando instalacion...
echo  ==================================================
echo.

py -c "import groq; print('  [OK] groq')" 2>nul || echo  [FALTA] groq
py -c "import edge_tts; print('  [OK] edge_tts')" 2>nul || echo  [FALTA] edge_tts
py -c "import sounddevice; print('  [OK] sounddevice')" 2>nul || echo  [FALTA] sounddevice
py -c "import PyQt6; print('  [OK] PyQt6')" 2>nul || echo  [FALTA] PyQt6
py -c "import whisper; print('  [OK] whisper')" 2>nul || echo  [AVISO] whisper (opcional)
py -c "import pvporcupine; print('  [OK] pvporcupine')" 2>nul || echo  [AVISO] pvporcupine (opcional)
py -c "import deep_translator; print('  [OK] deep_translator')" 2>nul || echo  [AVISO] deep_translator (opcional)

echo.

:: ---------------------------------------------------------
:: FIN
:: ---------------------------------------------------------
echo  +======================================================+
echo  ^|  Instalacion completada.                             ^|
echo  ^|                                                      ^|
echo  ^|  Paso 1: Abre config.py con el Bloc de notas y      ^|
echo  ^|  pega tu API key de Groq (gratis):                  ^|
echo  ^|  https://console.groq.com/keys                      ^|
echo  ^|                                                      ^|
echo  ^|  Paso 2 (recomendado): activa wake word offline      ^|
echo  ^|  - Ve a https://picovoice.ai                        ^|
echo  ^|  - Console -> AccessKey -> Create -> Copiar la key  ^|
echo  ^|  - En Jarvis: boton Ajustes -> Porcupine -> pegar   ^|
echo  ^|  - Guardar: deteccion offline ultra-rapida activa   ^|
echo  ^|                                                      ^|
echo  ^|  Paso 3: Ejecuta Iniciar Jarvis.bat                  ^|
echo  +======================================================+
echo.
pause
