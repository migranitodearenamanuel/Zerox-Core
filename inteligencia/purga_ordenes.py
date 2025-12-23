import ccxt
import time
import sys
# FORCE UTF-8 OUTPUT
if sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

from configuracion_total import API_KEY, API_SECRET, API_PASSPHRASE

def purgar_todo():
    print("🦈 INICIANDO PURGA DE EMERGENCIA DE ÓRDENES...")
    
    exchange = ccxt.bitget({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'password': API_PASSPHRASE,
        'enableRateLimit': True,
        'options': { 'defaultType': 'swap' }
    })
    
    # 1. Cancelar Órdenes Normales (Limit/Market pendientes)
    try:
        open_orders = exchange.fetch_open_orders()
        print(f"📋 Órdenes Normales Pendientes: {len(open_orders)}")
        if open_orders:
            print("   🧨 Cancelando órdenes normales...")
            exchange.cancel_all_orders()
            print("   ✅ Órdenes normales eliminadas.")
    except Exception as e:
        print(f"   ⚠️ Error cancelando normales: {e}")

    # 2. Cancelar Órdenes Plan (Trigger/Stop)
    # Bitget tiene endpoint específico para plan orders
    print("📋 Buscando Órdenes Plan (TP/SL)...")
    try:
        # Recuperar trigger orders es complejo en CCXT genérico, intentamos cancelAll con params
        # O iterar por simbolos activos.
        # Fallback: Usar private_mix_post_v2_mix_order_cancel_plan_order o similar
        # Simplificación: Usar exchange.cancel_all_orders(params={'stop': True}) si CCXT lo soporta
        # O: private_mix_post_v2_mix_order_cancel_all_plan_order({ productType: 'USDT-FUTURES' })
        
        params = {'productType': 'USDT-FUTURES'} 
        res = exchange.private_mix_post_v2_mix_order_cancel_all_plan_order(params)
        print(f"   ✅ Respuesta Purga Plan: {res}")
        
    except Exception as e:
        print(f"   ⚠️ Error cancelando Plan Orders: {e}")
        # Intento V2: Iterar por simbolos de posiciones abiertas? No, purge global.

    print("🏁 PURGA COMPLETADA.")

if __name__ == "__main__":
    purgar_todo()
