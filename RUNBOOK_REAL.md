# RUNBOOK_REAL

## 1. Pre-requisitos
- Python >=3.11 y dependencias de `package.json`/`requirements.txt` (revisar `package-lock.json`).
- Bitget API keys de futuros USDT-FUTURES con permisos de trading.
- Verifica que no hay `MODO_MANTENIMIENTO=1` ni en `.env` ni en variables de entorno globales (el bot no abre órdenes en mantenimiento).

## 2. Variables de entorno clave
1. `TRADING_MODE=REAL` (obligatorio para operar en vivo).
2. `BACKOFF_DISABLED=0` para mantener la protección del backoff por símbolo; ponlo en 1 solo para diagnosticar bloqueos.
3. Asegura que `MODO_MANTENIMIENTO` está vacío o en `0`. Si necesitas forzar mantenimiento, hazlo desde la UI o `PARADA_EMERGENCIA.bat`.
4. `BACKOFF_DISABLED` y `RESET_BACKOFF`/`RESET_RIESGO_HOY` son banderas manuales, no cambies otros nombres de claves del exchange.

## 3. Archivos de control
- Crea `ENABLE_REAL.txt` en la raíz con exactamente la línea:
```
I UNDERSTAND THE RISKS
```
- Borra el archivo `STOP` si lo usaste para pruebas (detectado en `tmp/STOP`), porque el bot se apagará al arrancar.
- Para limpiar bloqueos por símbolo/global sin reiniciar: crea `tmp/reset_backoff.flag`. El operador reinicia los timers y borra los backoffs.
- Para resetear PAUSA_RIESGO del día: crea `tmp/reset_riesgo_hoy.flag`. Esto borra `inteligencia/estado_dia.json` y `inteligencia/riesgo_persistencia.json`, resetea la línea base y actualiza los cooldowns.

## 4. Diagnóstico continuo
- Cada ciclo principal el core imprime un resumen `POR QUÉ NO ENTRA`, combinando el estado de riesgo (`PAUSA_RIESGO`, `ACTIVO`, etc.) con el último motivo humano de `tmp/zerox_no_entra.txt` y `inteligencia/operaciones/no_entra_motivos.log`.
- Revisa `tmp/zerox_no_entra.txt` para ver el último motivo sencillo (formato `clave=valor`). Consulta el histórico JSONL en `inteligencia/operaciones/no_entra_motivos.log` para trazar patrones.
- Si el motivo es `MINIMO_SUPERA_RIESGO`, la cuenta pequeña no alcanza los `min_cost`/riesgo. No es un fallo de backoff: ajusta riesgo o fondos antes de forzar el flag.
- `tmp/zerox_watchdog.txt`, `heartbeat.json`, `tmp/zerox_core_stdout.log` y `tmp/zerox_core_stderr.log` ayudan a detectar caídas del supervisor.

## 5. Ciclo de operación
1. Arranca el supervisor: `python -m inteligencia.supervisor_zerox` o `LANZAR_TODO.bat`.
2. Espera a que el heartbeat indique `estado=ACTIVO` y `motivo` sin errores.
3. Observa que el log `POR QUÉ NO ENTRA` acompaña cada ciclo con el motivo humano y el estado de riesgo.
4. Si todo está listo, la IA ejecutará órdenes reales en Bitget USDT-FUTURES.

## 6. Parada segura
- Usa `PARADA_EMERGENCIA.bat` o `Ctrl+C` en la terminal del supervisor.
- El supervisor monitoriza latidos cada 90s y reinicia automáticamente si detecta cuelgues.
- Atención: el bot sigue procesando datos incluso en PAUSA_RIESGO; solo se bloquean las entradas.

## 7. Notas adicionales
- Los scripts `depuracion_bitget_v2.py` y `depuracion_bitget_v3.py` se mantienen vigentes; el viejo `depuracion_bitget.py` se archivó en `legacy/` para evitar mezclas.
- Si necesitas auditoría adicional, consulta los archivos bajo `tmp/` (`zerox_crash_report.txt`, `zerox_dump_request.flag`, etc.).
