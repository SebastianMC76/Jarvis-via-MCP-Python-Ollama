@echo off
cd /d "%~dp0"

:: Buscar pythonw en ubicaciones comunes
set PYTHONW=
for %%p in (
    "%LOCALAPPDATA%\Python\bin\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
    "C:\Python313\pythonw.exe"
    "C:\Python312\pythonw.exe"
    "C:\Python311\pythonw.exe"
    "C:\Python310\pythonw.exe"
) do (
    if exist %%p (
        set PYTHONW=%%p
        goto :found
    )
)

:: Fallback: usar py launcher
where py >nul 2>&1
if not errorlevel 1 (
    start "" /b py main.py
    exit /b 0
)

echo Python no encontrado. Ejecuta INSTALAR.bat primero.
pause
exit /b 1

:found
start "" /b %PYTHONW% main.py
