@echo off
title ZEROX - GOD MODE v2.0
color 0A
cls

REM ---------------------------------------------------------------------------
REM FIX: Evitar "fatal: bad revision 'HEAD'" en repos git sin commits.
REM Si existe .git pero no hay HEAD válido (repo recién creado), creamos un
REM commit vacío local (sin requerir configuración global) para estabilizar.
REM ---------------------------------------------------------------------------
if exist ".git" (
    where git >nul 2>nul
    if errorlevel 1 (
        REM Git no disponible en PATH: no bloquear el arranque.
    ) else (
        git rev-parse --verify HEAD >nul 2>nul
        if errorlevel 1 (
            echo [FIX] Repo git sin commits: creando commit inicial local...
            git -c user.email=zerox@local -c user.name=ZEROX commit --allow-empty -m "init" >nul 2>nul
        )
    )
)

echo =======================================================
echo     ZEROX CORE - PROTOCOLO DE LANZAMIENTO AUTOMATICO
echo =======================================================
echo.

echo [LIMPIEZA] Cerrando procesos antiguos...
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

echo [PASO 1] Iniciando Frontend (Minimizado)...
start /min cmd /c "npm run dev"

echo [PASO 2] Esperando carga de modulos...
timeout /t 5 >nul

echo [PASO 3] Abriendo Centro de Mando...
start http://localhost:3000

echo [PASO 4] Activando Perro Guardian (IA)...
python iniciador_automatico.py
pause
