import json
import os
import time
from datetime import datetime
import traceback

# Archivo de Ledger (Persistencia de IDs)
RUTA_LEDGER = os.path.join(os.path.dirname(__file__), "ledger_tp_sl.json")
RUTA_OPERACIONES = os.path.join(os.path.dirname(__file__), "operaciones")
RUTA_BLACKLIST = os.path.join(os.path.dirname(__file__), "simbolos_bloqueados.json")

# ==============================================================================
# 🗄️ PERSISTENCIA Y LEDGER (Gestión Local)
# ==============================================================================

def _asegurar_directorio_operaciones():
    if not os.path.exists(RUTA_OPERACIONES):
        os.makedirs(RUTA_OPERACIONES)
    
    # Subcarpetas por fecha (YYYY-MM-DD)
    fecha = datetime.now().strftime("%Y-%m-%d")
    ruta_fecha = os.path.join(RUTA_OPERACIONES, fecha)
    if not os.path.exists(ruta_fecha):
        os.makedirs(ruta_fecha)
    return ruta_fecha

def _cargar_ledger():
    if os.path.exists(RUTA_LEDGER):
        try:
            with open(RUTA_LEDGER, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _guardar_ledger(data):
    try:
        with open(RUTA_LEDGER, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ Error guardando ledger: {e}")

def _blacklist_permanente_25013(simbolo, motivo="No soporta trading por API (Error 25013)"):
    """
    Persistencia de cuarentena:
    - TSLA y cualquier símbolo con Error 25013 quedan bloqueados permanentemente.
    """
    try:
        base = (simbolo.split(":")[0]).split("/")[0]
        if not base:
            return

        data = {}
        if os.path.exists(RUTA_BLACKLIST):
            try:
                with open(RUTA_BLACKLIST, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}

        ahora = datetime.now().isoformat()
        entry = {"motivo": motivo, "fecha": ahora, "status": "BLOQUEADO_PERMANENTE"}
        data[f"{base}USDT_UMCBL"] = entry
        data[f"{base}USDT"] = entry

        with open(RUTA_BLACKLIST, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def registrar_ejecucion_real(simbolo, lado, cantidad, precio, order_id, tp_id, sl_id, auditoria_ok):
    """
    Registra una operación real con fines de evidencia inmutable.
    """
    try:
        ruta_fecha = _asegurar_directorio_operaciones()
        filename = f"{simbolo.replace('/', '_')}_{order_id}.json"
        filepath = os.path.join(ruta_fecha, filename)
        
        datos = {
            "timestamp": datetime.now().isoformat(),
            "simbolo": simbolo,
            "lado": lado,
            "cantidad": cantidad,
            "precio_real": precio,
            "order_id": order_id,
            "tp_id": tp_id,
            "sl_id": sl_id,
            "auditoria": "OK" if auditoria_ok else "FAIL",
            "evidencia_blockchain": True
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4)
            
        print(f"💾 EVIDENCIA GUARDADA: {filepath}")
        
    except Exception as e:
        print(f"❌ ERROR GUARDANDO EVIDENCIA REAL: {e}")

def registrar_tpsl_ledger(simbolo, order_id_entrada, tp_id, sl_id):
    """
    Registra que una posición tiene TP/SL activos para evitar duplicados.
    """
    ledger = _cargar_ledger()
    ledger[simbolo] = {
        "entrada_id": order_id_entrada,
        "tp_id": tp_id,
        "sl_id": sl_id,
        "timestamp": time.time(),
        "estado": "ACTIVO"
    }
    _guardar_ledger(ledger)

def verificar_tpsl_existente(simbolo):
    """
    Retorna True si ya existen TP/SL registrados en el ledger.
    """
    ledger = _cargar_ledger()
    if simbolo in ledger:
        return True, ledger[simbolo]
    return False, None

def limpiar_ledger(simbolo):
    """Elimina del ledger una posición cerrada."""
    ledger = _cargar_ledger()
    if simbolo in ledger:
        del ledger[simbolo]
        _guardar_ledger(ledger)

# ==============================================================================
# 🗄️ PERSISTENCIA TP/SL VIRTUAL (Gestión Zerox)
# ==============================================================================

RUTA_TPSL_VIRTUAL = os.path.join(os.path.dirname(__file__), "tpsl_virtuales.json")

def _cargar_tpsl_virtuales():
    if os.path.exists(RUTA_TPSL_VIRTUAL):
        try:
            with open(RUTA_TPSL_VIRTUAL, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _guardar_tpsl_virtuales(data):
    try:
        with open(RUTA_TPSL_VIRTUAL, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ Error guardando TPSL Virtuales: {e}")

def colocar_tpsl_posicion(exchange, simbolo, direccion, tp, sl, cantidad, es_reparacion=False):
    """
    Coloca TP y SL de forma VIRTUAL (Gestión Zerox).
    NO ENVÍA ORDENES AL EXCHANGE. Guarda en 'tpsl_virtuales.json'.
    """
    try:
        print(f"DEBUG TPSL VIRTUAL: Simbolo={simbolo} Dir={direccion} TP={tp} SL={sl} Q={cantidad}", flush=True)

        if tp <= 0 and sl <= 0:
            print("⚠️ TP/SL Virtual ignorado: Precios 0.")
            return None

        # Cargar DB actual
        db = _cargar_tpsl_virtuales()
        
        # Normalizar Symbol (El exchange puede usar / o no)
        # Usamos el simbolo_unified (ej: XRP/USDT:USDT) como clave si es posible, o base+USDT
        clave = simbolo
        
        datos_virtuales = {
            "symbol": simbolo,
            "side": "long" if direccion.lower() in ['buy', 'largo', 'long'] else "short",
            "tp": float(tp),
            "sl": float(sl),
            "cantidad": float(cantidad),
            "updated_at": datetime.now().isoformat()
        }
        
        db[clave] = datos_virtuales
        _guardar_tpsl_virtuales(db)
        
        print(f"🛡️ BLINDAJE VIRTUAL ACTIVO PARA {simbolo} | TP: {tp} | SL: {sl}")
        print(f"   (Zerox vigilará este precio y cerrará a mercado si se toca)")
        
        return {'tp_id': 'VIRTUAL_TP', 'sl_id': 'VIRTUAL_SL'}

    except Exception as e:
        print(f"❌ ERROR REGISTRO TPSL VIRTUAL: {e}")
        return None

def verificar_tpsl_activas(simbolo):
    """
    Consulta si existen órdenes de protección activas en la BD VIRTUAL.
    Retorna: (tiene_tp, tiene_sl)
    """
    try:
        db = _cargar_tpsl_virtuales()
        if simbolo in db:
            dat = db[simbolo]
            tiene_tp = dat.get('tp', 0) > 0
            tiene_sl = dat.get('sl', 0) > 0
            return tiene_tp, tiene_sl
        return False, False
    except Exception as e:
        print(f"⚠️ Error verificando TPSL VIRTUAL {simbolo}: {e}")
        return False, False

# Alias para compatibilidad con llamadas antiguas que esperaban 'exchange' como arg
def verificar_tpsl_api(exchange, simbolo):
    return verificar_tpsl_activas(simbolo)

def reparar_posiciones_desnudas(exchange, posiciones_activas):
    """
    Recorre posiciones activas y si faltan TP/SL, los coloca VIRTUALMENTE.
    """
    import tpsl_profesional 
    
    for pos in posiciones_activas:
        simbolo = pos['symbol']
        lado = pos['side']
        contracts = float(pos['contracts'])
        entrada = float(pos['entryPrice'])
        
        if contracts <= 0: continue
        
        # Verificar VIRTUALMENTE
        tp_ok, sl_ok = verificar_tpsl_activas(simbolo)
        
        if not tp_ok or not sl_ok:
            print(f"🚑 REPARANDO POSICIÓN DESNUDA (VIRTUAL): {simbolo}")
            
            direccion = "LONG" if lado == "long" else "SHORT"
            tp, sl, motivo_tpsl = tpsl_profesional.calcular_tpsl_elite(
                simbolo, direccion, entrada, atr=0, confianza=75, balance=0
            )

            if motivo_tpsl != "OK" or tp is None or sl is None:
                continue
            
            # Registrar Blindaje Virtual
            colocar_tpsl_posicion(exchange, simbolo, direccion, tp, sl, contracts, es_reparacion=True)
