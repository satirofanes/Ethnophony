@echo off
title Lanzador de SoundMap Studio
:: Cambia 'app.py' por el nombre exacto de tu archivo de Python
set FILE_NAME=app.py

echo.
echo ========================================
echo   Iniciando SoundMap Studio Pro...
echo ========================================
echo.

:: Opcional: Activar entorno virtual si se llama 'venv'
if exist venv\Scripts\activate (
    echo [INFO] Activando entorno virtual...
    call venv\Scripts\activate
)

:: Ejecutar Streamlit
streamlit run %FILE_NAME%

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar la aplicacion.
    pause
)