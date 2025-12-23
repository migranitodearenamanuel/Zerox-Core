import requests
import time
import os
import sys

# Cache de offset para no saturar API
_OFFSET_CACHE = None
_LAST_SYNC = 0
_SYNC_INTERVAL = 60 # Sincronizar cada 60s

RUTA_EVIDENCIA = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_reloj_bitget.txt")

def get_server_time_ms():
    """Consulta directa a Bitget API V2 Public Time"""
    try:
        url = "https://api.bitget.com/api/v2/public/time"
        resp = requests.get(url, timeout=3)
        data = resp.json()
        
        if data.get('code') == '00000':
            # Bitget devuelve serverTime como string numerico
            return int(data['data']['serverTime'])
        else:
            raise Exception(f"API Error: {data}")
            
    except Exception as e:
        print(f"❌ Error obteniendo tiempo Bitget: {e}")
        return None

def sincronizar():
    global _OFFSET_CACHE, _LAST_SYNC
    if time.time() - _LAST_SYNC < _SYNC_INTERVAL and _OFFSET_CACHE is not None:
        return _OFFSET_CACHE

    server_ms = get_server_time_ms()
    if server_ms is not None:
        local_ms = int(time.time() * 1000)
        offset = server_ms - local_ms
        _OFFSET_CACHE = offset
        _LAST_SYNC = time.time()
        
        # Evidencia
        log = f"SYNC: Local={local_ms} Server={server_ms} Offset={offset}ms"
        print(f"⏱️ {log}")
        try:
            os.makedirs(os.path.dirname(RUTA_EVIDENCIA), exist_ok=True)
        except Exception:
            pass
        with open(RUTA_EVIDENCIA, "a", encoding="utf-8") as f:
            f.write(f"{time.ctime()} | {log}\n")
            
        return offset
    else:
        return None

def get_offset_ms():
    """Retorna el offset actual (Server - Local). Si falla sync, retorna None o último conocido."""
    if _OFFSET_CACHE is None:
        return sincronizar()
    # Si pasó tiempo, re-sync bg
    if time.time() - _LAST_SYNC > _SYNC_INTERVAL:
        sincronizar()
    return _OFFSET_CACHE

def now_ms():
    """Retorna el timestamp corregido (Server Time aproximado)."""
    offset = get_offset_ms()
    local_now = int(time.time() * 1000)
    if offset is not None:
        return local_now + offset
    return local_now # Fallback a local si no hay sync (pero debería bloquearse el bot)

def estado_reloj():
    offset = get_offset_ms()
    if offset is None:
        return "ERROR_SYNC", 0, False
    
    # Política de Bloqueo: > 25s (Ventana de validez amplia para evitar bloqueos tontos)
    # Bitget suele aceptar ventana de recivWindow (default 5s, pero ccxt maneja esto).
    # Para el "Bloqueo x Seguridad", usamos 25s como "offset monstruoso".
    # Si CCXT usa adjustForTimeDifference, maneja el offset internamente para la firma.
    
    es_seguro = abs(offset) < 25000 
    return "OK" if es_seguro else "DESFASE_CRITICO", offset, es_seguro
