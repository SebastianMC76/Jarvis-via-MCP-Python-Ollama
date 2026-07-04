@echo off
setlocal EnableDelayedExpansion
title J.A.R.V.I.S - Instalador de Programas Externos
color 0B

echo.
echo  +======================================================+
echo  ^|         J.A.R.V.I.S  --  Paso 1 de 2               ^|
echo  ^|       Instalador de Programas Externos               ^|
echo  +======================================================+
echo.
echo  Este instalador descargara e instalara automaticamente:
echo.
echo    [1] Python 3.11  (lenguaje base de Jarvis)
echo    [2] ffmpeg       (procesamiento de audio para Whisper)
echo    [3] Tesseract    (lectura de texto en pantalla - OCR)
echo.
echo  NOTA: Necesitas conexion a internet.
echo  Tiempo estimado: 5-10 minutos segun tu velocidad.
echo.
pause

:: ---------------------------------------------------------
:: VERIFICAR WINGET
:: ---------------------------------------------------------
echo.
echo  Verificando winget (gestor de paquetes de Windows)...
winget --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] winget no esta disponible en este equipo.
    echo.
    echo  Solucion: Abre Microsoft Store, busca
    echo  "App Installer" e instalalo. Luego vuelve a ejecutar.
    echo.
    pause
    exit /b 1
)
echo  [OK] winget disponible.

:: ---------------------------------------------------------
:: PASO 1 -- PYTHON
:: ---------------------------------------------------------
echo.
echo  ==================================================
echo   [1/3] Instalando Python 3.11...
echo  ==================================================
echo.

py --version >nul 2>&1
if not errorlevel 1 (
    echo  [OK] Python ya esta instalado. Saltando...
    goto ffmpeg
)

python --version >nul 2>&1
if not errorlevel 1 (
    echo  [OK] Python ya esta instalado. Saltando...
    goto ffmpeg
)

echo  Descargando Python 3.11 desde winget...
winget install --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo.
    echo  [ERROR] No se pudo instalar Python automaticamente.
    echo.
    echo  Instalalo manualmente:
    echo    1. Ve a: https://www.python.org/downloads/
    echo    2. Descarga Python 3.11
    echo    3. En el instalador, MARCA "Add Python to PATH"
    echo    4. Vuelve a ejecutar este instalador
    echo.
    pause
    exit /b 1
)

echo.
echo  [OK] Python instalado.
echo  IMPORTANTE: Cierra esta ventana, abre una nueva
echo  y vuelve a ejecutar INSTALAR_EXTERNO.bat para
echo  que Windows reconozca Python correctamente.
echo.
pause
exit /b 0

:: ---------------------------------------------------------
:: PASO 2 -- FFMPEG
:: ---------------------------------------------------------
:ffmpeg
echo.
echo  ==================================================
echo   [2/3] Instalando ffmpeg (audio para Whisper)...
echo  ==================================================
echo.

ffmpeg -version >nul 2>&1
if not errorlevel 1 (
    echo  [OK] ffmpeg ya esta instalado. Saltando...
    goto tesseract
)

echo  Descargando ffmpeg...
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo.
    echo  [AVISO] No se pudo instalar ffmpeg automaticamente.
    echo.
    echo  Instalalo manualmente:
    echo    1. Ve a: https://ffmpeg.org/download.html
    echo    2. Descarga la version Windows
    echo    3. Extrae y agrega la carpeta bin al PATH
    echo.
    echo  Jarvis funcionara igualmente, pero Whisper
    echo  (reconocimiento de voz offline) no estara disponible.
    echo.
) else (
    echo  [OK] ffmpeg instalado.
)

:: ---------------------------------------------------------
:: PASO 3 -- TESSERACT OCR
:: ---------------------------------------------------------
:tesseract
echo.
echo  ==================================================
echo   [3/3] Instalando Tesseract OCR (leer pantalla)...
echo  ==================================================
echo.

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo  [OK] Tesseract ya esta instalado. Saltando...
    goto fin
)

echo  Descargando Tesseract OCR...
winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo.
    echo  [AVISO] No se pudo instalar Tesseract automaticamente.
    echo.
    echo  Instalalo manualmente:
    echo    1. Ve a: https://github.com/UB-Mannheim/tesseract/wiki
    echo    2. Descarga el instalador .exe
    echo    3. Instalalo en: C:\Program Files\Tesseract-OCR\
    echo.
    echo  Jarvis funcionara igualmente, pero el comando
    echo  "lee la pantalla" no estara disponible.
    echo.
) else (
    echo  [OK] Tesseract instalado.
)

:: ---------------------------------------------------------
:: FIN
:: ---------------------------------------------------------
:fin
echo.
echo  +======================================================+
echo  ^|  Paso 1 completado.                                  ^|
echo  ^|                                                      ^|
echo  ^|  Siguiente paso:                                     ^|
echo  ^|  Ejecuta INSTALAR.bat para instalar                  ^|
echo  ^|  las librerias de Python de Jarvis.                  ^|
echo  +======================================================+
echo.
pause
