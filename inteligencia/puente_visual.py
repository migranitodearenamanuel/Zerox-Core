import json
import os
import threading
import time

# Calcula la ruta absoluta a la carpeta /interfaz/public
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_JSON = os.path.join(BASE_DIR, 'interfaz', 'public', 'estado_bot.json')
LOCK_VISUAL = threading.Lock()

def actualizar_estado(datos):
    with LOCK_VISUAL:
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(RUTA_JSON), exist_ok=True)
            
            # 1. LEER ESTADO PREVIO (Merge Strategy)
            estado_actual = {}
            if os.path.exists(RUTA_JSON):
                try:
                    with open(RUTA_JSON, 'r', encoding='utf-8') as f:
                        estado_actual = json.load(f)
                except:
                    estado_actual = {} # Corrupto o vacío
            
            # 2. ACTUALIZAR (Sobrescribir solo claves nuevas)
            estado_actual.update(datos)
            
            # 3. ESCRIBIR (Atomic)
            ruta_tmp = RUTA_JSON + ".tmp"
            with open(ruta_tmp, 'w', encoding='utf-8') as f:
                json.dump(estado_actual, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Reintento robusto para rename (Windows Fix)
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    os.replace(ruta_tmp, RUTA_JSON)
                    break 
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(0.05)
                    else:
                        print(f"⚠️ UI Lock: No se pudo actualizar estado (Interfaz ocupada).")
                except OSError:
                     time.sleep(0.05)
            
        except Exception as e:
            print(f"⚠️ Error visual crítico: {e}")
