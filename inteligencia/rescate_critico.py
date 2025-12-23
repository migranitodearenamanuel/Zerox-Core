import ccxt
import time
import os
import sys
import json
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import configuracion as config

# Configuraciones
ARCHIVO_SNAPSHOT = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_snapshot_posiciones.txt")
DIRECTORIO_TMP = os.path.join(os.path.dirname(__file__), "..", "tmp")

def normalizar_simbolo(ccxt_symbol):
    """Convierte PIPPUN/USDT:USDT a PIPPINUSDT para Bitget V2"""
    # Regla: Quitar '/' y quitar ':USDT'
    return ccxt_symbol.split(':')[0].replace('/', '')

def log_error_json(simbolo, error_data, context):
    filename = os.path.join(DIRECTORIO_TMP, f"zerox_error_tpsl_{simbolo}_{int(time.time())}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(error_data, f, indent=2)
    print(f"❌ [EMERGENCIA] Error guardado en: {filename}")

def ejecutar_rescate():
    print("🚑 INICIANDO RESCATE CRÍTICO DE POSICIONES (REAL)...")
    
    try:
        # A. CONEXIÓN
        exchange = ccxt.bitget({
            'apiKey': config.CLAVE_API,
            'secret': config.SECRETO_API,
            'password': config.CONTRASENA_API,
            'options': {'adjustForTimeDifference': True} 
        })
        exchange.load_markets()
        
        # Sincronización Tiempo
        exchange.load_time_difference()
        print(f"⏱️ Time Sync OK.")

        # B. DETECTAR POSICIONES
        positions = exchange.fetch_positions()
        active_positions = [p for p in positions if float(p['contracts']) > 0]
        
        snapshot_rows = []
        
        if not active_positions:
            print("✅ NO SE DETECTAN POSICIONES ABIERTAS. (Sistema Limpio)")
        else:
            print(f"⚠️ {len(active_positions)} POSICIONES EN RIESGO DETECTADAS.")

        for pos in active_positions:
            simbolo_ccxt = pos['symbol']
            simbolo_bitget = normalizar_simbolo(simbolo_ccxt)
            lado = "long" if pos['side'] == "long" else "short"
            tamano = float(pos['contracts'])
            entrada = float(pos['entryPrice'])
            
            print(f"\n🔍 ANALIZANDO: {simbolo_ccxt} -> {simbolo_bitget} | {lado.upper()} | Entrada: {entrada}")
                "tamano": tamano,
                "entrada": entrada,
                "tp": tp_id if tp_id != "N/A" else "NO",
                "sl": sl_id if sl_id != "N/A" else "NO",
                "estado_rescate": estado_rescate
            })

        # E. GENERAR SNAPSHOT
        with open(ARCHIVO_SNAPSHOT, "w", encoding="utf-8") as f:
            f.write("SNAPSHOT POST-RESCATE (REAL)\n")
            f.write("============================\n")
            f.write(f"FECHA: {time.ctime()}\n\n")
            f.write(f"{'SIMBOLO':<15} {'LADO':<6} {'TAM':<8} {'ENTRADA':<10} {'ID TP':<15} {'ID SL':<15} {'ESTADO'}\n")
            f.write("-" * 90 + "\n")
            for r in snapshot_rows:
                f.write(f"{r['simbolo']:<15} {r['lado']:<6} {r['tamano']:<8} {r['entrada']:<10} {str(r['tp'])[:12]:<15} {str(r['sl'])[:12]:<15} {r['estado_rescate']}\n")
        
        print(f"\nSnapshot guardado en: {ARCHIVO_SNAPSHOT}")

    except Exception as e_main:
        print(f"💀 CRASH CRÍTICO DEL SCRIPT: {e_main}")
        traceback.print_exc()

if __name__ == "__main__":
    ejecutar_rescate()
