import ccxt
import time
import os
import sys
from datetime import datetime

# Importar config para credenciales
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import configuracion as config

RUTA_REPORTE = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_tiempo_salud.txt")

def log_tiempo(mensaje):
    timestamp = datetime.now().isoformat()
    linea = f"[{timestamp}] {mensaje}"
    print(linea)
    with open(RUTA_REPORTE, "a", encoding="utf-8") as f:
        f.write(linea + "\n")

def verificar_tiempo():
    log_tiempo("⏳ VERIFICANDO SINCRONIZACIÓN DE TIEMPO...")
    
    try:
        # Usar ajuste nativo de CCXT para medir
        exchange = ccxt.bitget({
            'apiKey': config.CLAVE_API,
            'secret': config.SECRETO_API,
            'password': config.CONTRASENA_API,
            'options': {'adjustForTimeDifference': True} 
        })
        
        # Medir offset "crudo"
        # fetch_time llama al server. time.time() es local.
        # CCXT hace esto internamente con load_time_difference() pero queremos ver el dato.
        
        local_ms = int(time.time() * 1000)
        server_ms = exchange.fetch_time()
        offset = server_ms - local_ms
        
        log_tiempo(f"🕒 Servidor: {server_ms} | Local: {local_ms} | Offset V1: {offset} ms")
        
        # Nueva medición tras load_time_difference
        # load_time_difference retorna la diferencia en ms
        try:
            offset_ccxt = exchange.load_time_difference()
        except:
             # Fallback manual calculation if returns None or fails
             local_ms = int(time.time() * 1000)
             server_ms = exchange.fetch_time()
             offset_ccxt = server_ms - local_ms
        
        log_tiempo(f"⏱️ Offset calculado: {offset_ccxt} ms")
        
        if abs(offset_ccxt) > 1000:
            log_tiempo("⚠️ DESFASE CRÍTICO (>1000ms). Intentando RESYNC OS (w32tm)...")
            try:
                import subprocess
                # Requiere privilegios. Intentamos runas/admin si es posible o directo.
                # w32tm /resync
                res = subprocess.run("w32tm /resync", shell=True, capture_output=True, text=True)
                log_tiempo(f"CMD RESYNC: {res.stdout} | {res.stderr}")
                if res.returncode == 0:
                    log_tiempo("✅ RELOJ WINDOWS SINCRONIZADO.")
                    # Re-verificar
                    exchange.load_time_difference()
                    new_offset = exchange.time_difference
                    log_tiempo(f"⏱️ Nuevo Offset: {new_offset} ms")
                    if abs(new_offset) < 1000:
                        return True, new_offset
                else:
                    log_tiempo("❌ FALLO RESYNC WINDOWS. (Posible falta de Admin)")
            except Exception as e_os:
                log_tiempo(f"❌ ERROR EJECUTANDO RESYNC: {e_os}")

            return False, offset_ccxt
        else:
            log_tiempo("✅ TIEMPO ACEPTABLE (Dentro de margen seguro).")
            return True, offset_ccxt
            
    except Exception as e:
        log_tiempo(f"❌ ERROR VERIFICANDO TIEMPO: {e}")
        return False, 0

if __name__ == "__main__":
    verificar_tiempo()
