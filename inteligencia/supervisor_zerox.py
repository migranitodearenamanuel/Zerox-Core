import subprocess
import time
import os
import sys
import subprocess
import json
import psutil
from datetime import datetime

# ------------------------------------------------------------------------------
# Robustez de consola (Windows): evitar crashes por Unicode/emoji en stdout/stderr
# ------------------------------------------------------------------------------
def _forzar_utf8_salida():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# CONFIGURACIÓN
SCRIPT_NUCLEO = os.path.join(os.path.dirname(__file__), "operador_maestro.py")
RUTA_LATIDO = os.path.join(os.path.dirname(__file__), "heartbeat.json")
RUTA_LOG_VIGILANTE = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_watchdog.txt")
RUTA_EJECUCION = os.path.join(os.path.dirname(__file__), "estado_runtime.json")
RUTA_STDOUT = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_core_stdout.log")
RUTA_STDERR = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_core_stderr.log")
RUTA_REPORTE_FALLO = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_crash_report.txt")

# UMBRALES (Aumentados por Hilo Independiente)
MAX_SEGUNDOS_SILENCIO = 90  # Si no hay latido en 90s, el proceso murió de verdad.
MAX_SEGUNDOS_ATASCADO = 120   # Si el paso no cambia en 120s, está colgado.

def cargar_runtime():
    if os.path.exists(RUTA_EJECUCION):
        try:
            with open(RUTA_EJECUCION, "r") as f: return json.load(f)
        except: pass
    return {"reinicios_totales": 0, "cuelgues_detectados": 0}

def guardar_runtime(data):
    try:
        with open(RUTA_EJECUCION, "w") as f: json.dump(data, f)
    except: pass

def registrar_vigilancia(mensaje):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ts}] {mensaje}\n"
    try:
        print(f"[SUPERVISOR] {linea.strip()}")
    except Exception:
        pass
    try:
        with open(RUTA_LOG_VIGILANTE, "a", encoding="utf-8") as f:
            f.write(linea)
    except: pass

def leer_latido():
    try:
        with open(RUTA_LATIDO, "r") as f:
            return json.load(f)
    except:
        return None

def solicitar_dump():
    flag = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_dump_request.flag")
    with open(flag, "w") as f: f.write("DUMP")
    log_watchdog("SOLICITADO STACK DUMP POR CUELGUE...")
    time.sleep(5) # Dar tiempo a faulthandler

def generar_reporte_fallo(process):
    """Genera un reporte detallado cuando el proceso muere (Exit Code != 0)"""
    try:
        exit_code = process.poll()
        if exit_code == 0: return # Salida limpia, rara vez ocurre

        registrar_vigilancia(f"GENERANDO REPORTE DE CRASH (Código de salida: {exit_code})...")
        
        # Leer colas de logs
        stderr_tail = []
        stdout_tail = []
        
        if os.path.exists(RUTA_STDERR):
            with open(RUTA_STDERR, 'r', encoding='utf-8', errors='ignore') as f:
                stderr_tail = f.readlines()[-200:] # Ultimas 200 lineas
        
        if os.path.exists(RUTA_STDOUT):
             with open(RUTA_STDOUT, 'r', encoding='utf-8', errors='ignore') as f:
                stdout_tail = f.readlines()[-50:]

        timestamp = datetime.now().isoformat()
        
        reporte = f"""========================================
ZEROX CRASH REPORT
TIMESTAMP: {timestamp}
EXIT CODE: {exit_code}
SCRIPT: {SCRIPT_NUCLEO}
========================================

=== STDERR (LAST 200 LINES) ===
{''.join(stderr_tail)}

=== STDOUT (LAST 50 LINES) ===
{''.join(stdout_tail)}
========================================
"""
        with open(RUTA_REPORTE_FALLO, "w", encoding="utf-8") as f:
            f.write(reporte)
            
        registrar_vigilancia(f"Reporte de crash guardado en: {RUTA_REPORTE_FALLO}")
        
    except Exception as e:
        registrar_vigilancia(f"⚠️ Fallo generando Crash Report: {e}")

def matar_proceso(process):
    try:
        pid = process.pid
        registrar_vigilancia(f"MATANDO PROCESO PID: {pid}")
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except Exception as e:
        registrar_vigilancia(f"⚠️ Error matando proceso: {e}")

    except Exception as e:
        registrar_vigilancia(f"⚠️ Error matando proceso: {e}")

def _garantizar_ollama():
    """Verifica si Ollama corre. Si no, lo arranca en background."""
    try:
        # 1. Check rapido via tasklist (Lightweight)
        # Solo chequeamos nombre de imagen, es rapido en Windows
        output = subprocess.check_output('tasklist /fi "imagename eq ollama.exe"', shell=True).decode('utf-8', errors='ignore')
        
        if "ollama.exe" not in output.lower():
            registrar_vigilancia("🧠 OLLAMA NO DETECTADO. Arrancando servidor neuronal automático...")
            
            # 2. Arrancar Detached
            # Usamos creationflags=subprocess.CREATE_NEW_CONSOLE para que tenga su propia ventana 
            # y no muera si el supervisor muere (o para ver logs si se quiere). 
            # Si el usuario quiere ocultarlo, podriamos usar DETACHED_PROCESS pero mejor visible para debug.
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                shell=False
            )
            # Dar tiempo a boot
            time.sleep(5)
            registrar_vigilancia("✅ Servidor Neuronal (Ollama) INICIADO.")
    except Exception as e:
        registrar_vigilancia(f"⚠️ Fallo gestionando Ollama: {e}")

def main():
    # Asegurar carpeta tmp
    tmp_dir = os.path.join(os.path.dirname(__file__), "..", "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    _forzar_utf8_salida()
    registrar_vigilancia("SUPERVISOR V2 INICIADO (REPORTEADOR DE CRASHES)")
    process = None
    
    while True:
        try:
            # 0. Garantizar Servicios Core (IA)
            _garantizar_ollama()

            # 1. Verificar si el proceso existe
            if process is None or process.poll() is not None:
                # Si murió y no es el primer inicio, generar reporte
                if process is not None:
                     generar_reporte_fallo(process)
                
                # CHECK LOOP DE MUERTE
                rt = cargar_runtime()
                crashes = rt.get("consecutive_crashes", 0)
                last_ts = rt.get("last_crash_ts", 0)
                ahora = time.time()
                
                # Reset contador si ha pasado tiempo (ej. 5 min sin crash)
                if (ahora - last_ts) > 300:
                    crashes = 0
                
                crashes += 1
                
                if crashes >= 5:
                    registrar_vigilancia(f"BLOQUEO DE SEGURIDAD: {crashes} CRASHES CONSECUTIVOS.")
                    rt["estado_global"] = "BLOQUEO POR CRASH"
                    rt["consecutive_crashes"] = crashes
                    rt["last_crash_ts"] = ahora
                    guardar_runtime(rt)
                    
                    registrar_vigilancia("PAUSANDO 60s ANTES DE REINTENTO...")
                    time.sleep(60)
                    
                    # Intentar arranque diagnóstico (Solo si existiera flag, por ahora reintentamos lento)
                    # Resetear para permitir intento controlado
                    # crashes = 4 # Dar un slot mas? No, forzamos espera
                    
                rt["consecutive_crashes"] = crashes
                rt["last_crash_ts"] = ahora
                rt["reinicios_totales"] += 1
                rt["ultimo_motivo_reinicio"] = "CRASH_OR_START"
                guardar_runtime(rt)

                registrar_vigilancia(f"(RE)INICIANDO ZeroX Core: {SCRIPT_NUCLEO} (Intento {crashes}/5)")
                
                # Redirección de logs
                stdout_f = open(RUTA_STDOUT, "w", encoding="utf-8") # Sobrescribir en cada run para no llenar disco infinito
                stderr_f = open(RUTA_STDERR, "w", encoding="utf-8")

                # Forzar UTF-8 en el proceso hijo (core) para evitar mojibake en consola/logs.
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                
                process = subprocess.Popen(
                    [sys.executable, SCRIPT_NUCLEO],
                    stdout=stdout_f,
                    stderr=stderr_f,
                    env=env,
                    encoding='utf-8', 
                    errors='replace'
                )
                
                # Esperar arranque
                time.sleep(10)
                continue

            # 2. Verificar Salud (Heartbeat)
            hb = leer_latido()
            reinicio_necesario = False
            motivo_reinicio = ""
            
            if hb:
                ts_hb = hb.get("timestamp", 0)
                ts_paso = hb.get("inicio_paso_ts", 0)
                paso_actual = hb.get("ultima_accion", "?")
                ahora = time.time()
                
                # A. CHEQUEO MUERTE (Latido detenido)
                delta_latido = ahora - ts_hb
                if delta_latido > MAX_SEGUNDOS_SILENCIO:
                    registrar_vigilancia(f"MUERTE DETECTADA: Sin latido hace {delta_latido:.1f}s")
                    reinicio_necesario = True
                    motivo_reinicio = "MUERTE_SILENCIOSA"

                # B. CHEQUEO CUELGUE (Latido vivo, pero paso atascado)
                elif ts_paso > 0:
                    delta_paso = ahora - ts_paso
                    if delta_paso > MAX_SEGUNDOS_ATASCADO:
                        registrar_vigilancia(f"CONGELAMIENTO: Atascado en '{paso_actual}' hace {delta_paso:.1f}s")
                        solicitar_dump()
                        reinicio_necesario = True
                        motivo_reinicio = f"STUCK: {paso_actual}"
                        
                        # Runtime update
                        rt = cargar_runtime()
                        rt["cuelgues_detectados"] += 1
                        guardar_runtime(rt)
            else:
                pass

            # 3. Ejecutar Reinicio si aplica
            if reinicio_necesario:
                if process: generar_reporte_fallo(process) # Generar antes de matar si es posible (aunque si está pegado no tendrá exit code aun, pero bueno)
                matar_proceso(process)
                process = None # Forzará start en siguiente ciclo
                
                rt = cargar_runtime()
                rt["ultimo_motivo_reinicio"] = motivo_reinicio
                guardar_runtime(rt)
                
            time.sleep(5)

        except Exception as e:
            registrar_vigilancia(f"⚠️ ERROR WATCHDOG: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
