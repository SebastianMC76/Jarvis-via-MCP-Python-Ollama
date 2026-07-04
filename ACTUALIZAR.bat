@echo off
REM ============================================================
REM  JARVIS - Sincronizador local
REM
REM  Copia los archivos de código (.py / .bat) desde la carpeta
REM  actual de Jarvis hacia "instalacion binaria\", preservando
REM  los datos del usuario (ajustes, memoria, historial, sesión,
REM  credenciales de calendario, logs).
REM
REM  Uso: doble clic en ACTUALIZAR.bat desde la raíz de Jarvis.
REM  Requiere que la PC destino ya tenga "instalacion binaria\"
REM  creada (típicamente la primera vez se copia la carpeta
REM  completa por USB / red y luego se actualiza con este .bat).
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul

set "ROOT=%~dp0"
set "BIN=%ROOT%instalacion binaria\"
set "BACKUP=%TEMP%\jarvis_backup_%RANDOM%"

cls
echo.
echo ============================================================
echo   J.A.R.V.I.S  -  Sincronizador local
echo ============================================================
echo.
echo   Origen : %ROOT%
echo   Destino: %BIN%
echo.

:: ── 0. Verificar destino ─────────────────────────────────────
if not exist "%BIN%" (
    echo [ERROR] No se encontro la carpeta "instalacion binaria\".
    echo         Coloca este .bat en la raiz de Jarvis, junto a
    echo         la carpeta "instalacion binaria\".
    echo.
    pause
    exit /b 1
)

:: ── 1. Cerrar Jarvis si esta corriendo ───────────────────────
echo [1/6] Cerrando Jarvis si esta en ejecucion...
taskkill /IM python.exe  /FI "WINDOWTITLE eq J.A.R.V.I.S*" >nul 2>&1
taskkill /IM pythonw.exe /FI "WINDOWTITLE eq J.A.R.V.I.S*" >nul 2>&1
taskkill /IM python.exe  /FI "WINDOWTITLE eq JARVIS*"      >nul 2>&1
taskkill /IM pythonw.exe /FI "WINDOWTITLE eq JARVIS*"      >nul 2>&1
timeout /t 2 /nobreak >nul
echo       OK.
echo.

:: ── 2. Respaldar datos de usuario de la instalacion binaria ─
echo [2/6] Respaldando datos del usuario...
mkdir "%BACKUP%" 2>nul
set "COUNT=0"
for %%f in ("%BIN%ajustes.json"
            "%BIN%protocolos.json"
            "%BIN%memoria_*.json"
            "%BIN%historial_cmds.json"
            "%BIN%sesion.json"
            "%BIN%credentials_calendar.json"
            "%BIN%jarvis.log") do (
    if exist "%%f" (
        copy /Y "%%f" "%BACKUP%\" >nul
        set /a "COUNT+=1"
    )
)
echo       !COUNT! archivo(s) respaldado(s) en %BACKUP%
echo.

:: ── 3. Sincronizar archivos de codigo (.py) ──────────────────
echo [3/6] Sincronizando modulos .py...
set "PY=0"
for %%f in ("%ROOT%*.py") do (
    if /i not "%%~nxf"=="ACTUALIZAR.bat" (
        copy /Y "%%f" "%BIN%" >nul
        set /a "PY+=1"
    )
)
echo       !PY! archivo(s) .py copiado(s).
echo.

:: ── 4. Sincronizar scripts .bat de inicio ────────────────────
echo [4/6] Sincronizando scripts de inicio...
set "BAT=0"
for %%f in ("%ROOT%Iniciar Jarvis.bat"
            "%ROOT%INSTALAR.bat"
            "%ROOT%INSTALAR_EXTERNO.bat") do (
    if exist "%%f" (
        copy /Y "%%f" "%BIN%" >nul
        set /a "BAT+=1"
    )
)
echo       !BAT! archivo(s) .bat copiado(s).
echo.

:: ── 5. Restaurar datos del usuario ───────────────────────────
echo [5/6] Restaurando datos del usuario...
set "RES=0"
for %%f in ("%BACKUP%\*") do (
    copy /Y "%%f" "%BIN%" >nul
    set /a "RES+=1"
)
rd /S /Q "%BACKUP%" 2>nul
echo       !RES! archivo(s) restaurado(s).
echo.

:: ── 6. Verificacion y opcion de iniciar ──────────────────────
echo [6/6] Verificando integridad...
if not exist "%BIN%main.py" (
    echo       [ERROR] main.py no se encuentra en el destino.
    pause
    exit /b 1
)
echo       main.py OK.
echo.
echo ============================================================
echo   Sincronizacion completada.
echo ============================================================
echo.
set /p "RESP=Iniciar Jarvis ahora? [S/N]: "
if /i "!RESP!"=="S" (
    start "" "%BIN%Iniciar Jarvis.bat"
)

endlocal
exit /b 0
