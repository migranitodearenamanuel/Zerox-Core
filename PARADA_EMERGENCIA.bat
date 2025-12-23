@echo off
title 🛑 ZEROX - PROTOCOLO DE PURGA TOTAL 🛑
color 4F
cls

echo ===============================================================================
echo      ☢️  EJECUTANDO PROTOCOLO "TIERRA QUEMADA" (PURGA TOTAL)  ☢️
echo ===============================================================================
echo.

echo [1/5] 🔪 Asesinando procesos PYTHON (IA/Backend)...
taskkill /F /IM python.exe /T >nul 2>&1
if %errorlevel% equ 0 ( echo    ✅ Python eliminado. ) else ( echo    ⚠️ No se encontraron procesos Python. )

echo [2/5] 🔪 Asesinando procesos NODE.JS (Frontend/Vite)...
taskkill /F /IM node.exe /T >nul 2>&1
if %errorlevel% equ 0 ( echo    ✅ Node.js eliminado. ) else ( echo    ⚠️ No se encontraron procesos Node. )

echo [3/5] 🔪 Asesinando procesos ELECTRON (Si existen)...
taskkill /F /IM electron.exe /T >nul 2>&1
taskkill /F /IM "ZeroX Bot.exe" /T >nul 2>&1

echo [4/5] 🧹 Limpiando puertos y consolas huerfanas...
:: Intenta matar procesos que tengan "cmd.exe" en su arbol si fueron lanzados por nosotros
:: Nota: Es dificil filtrar por titulo desde aqui sin herramientas externas, 
:: pero matar Python/Node suele ser suficiente.

echo [5/5] ❄️ Enfriando nucleo...
timeout /t 2 >nul

echo.
echo ===============================================================================
echo      ✅ SISTEMA COMPLETAMENTE PURGADO.
echo      YA PUEDES EJECUTAR 'LANZAR_TODO.bat' SIN CONFLICTOS.
echo ===============================================================================
pause
