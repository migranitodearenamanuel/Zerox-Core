@echo off
chcp 65001 > nul
title ZEROX MNEMOSYNE - INGESTIÓN DE CONOCIMIENTO
color 0B
cls
echo ========================================================
echo   ZEROX PROTOCOLO DE APRENDIZAJE MASIVO (EPUB/PDF/TXT)
echo   "Memorizando conocimiento para siempre..."
echo ========================================================
echo.
echo [INFO] Escaneando carpeta 'conocimiento' y actualizando cerebro...
echo [NOTA] Este proceso puede tardar dependiendo de la cantidad de libros.
echo.

python inteligencia/ingestor_biblioteca.py

echo.
echo ========================================================
echo   APRENDIZAJE COMPLETADO
echo   El conocimiento ahora es parte de la memoria permanente.
echo ========================================================
pause
