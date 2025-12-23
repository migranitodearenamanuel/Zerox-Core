
import os
import ccxt
import time
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def limpiar_todo():
    print("🚨 INICIANDO PROTOCOLO DE LIMPIEZA DE EMERGENCIA 🚨")
    
    api_key = os.getenv("BITGET_API_KEY")
    secret = os.getenv("BITGET_SECRET")
    password = os.getenv("BITGET_PASSWORD")

    if not api_key or not secret or not password:
        print("❌ Error: Faltan credenciales en .env")
        return

    exchange = ccxt.bitget({
        'apiKey': api_key,
        'secret': secret,
        'password': password,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })

    try:
        # 1. Obtener todas las órdenes abiertas (Normales y Plan)
        print("🔍 Buscando órdenes pendientes...")
        
        # En Bitget V2, a veces hay que mirar endpoints específicos para Plan Orders
        # CCXT suele agruparlas, pero vamos a intentar fetchOpenOrders primero
        orders = exchange.fetch_open_orders()
        print(f"📋 Encontradas {len(orders)} órdenes normales pendientes.")
        
        # Cancelar normales
        for order in orders:
            try:
                exchange.cancel_order(order['id'], order['symbol'])
                print(f"✅ Orden Normal Cancelada: {order['id']} ({order['symbol']})")
                time.sleep(0.1)
            except Exception as e:
                print(f"❌ Error cancelando {order['id']}: {e}")

        # 2. Intentar cancelar Plan Orders (TP/SL pendientes suelen ser esto)
        # Bitget usa 'plan' orders para TP/SL.
        try:
            # Endpoint específico si CCXT tiene el método implementado
            # Si no, usamos fetchOpenOrders con params
            plan_orders = exchange.fetch_open_orders(params={'stop': 'plan'}) # Intento genérico
             # O iterar symbols... para simplificar, usaremos cancel_all_orders si es posible, pero Bitget V2 es tricky
        except Exception as e:
            print(f"ℹ️ (Info) No se pudieron obtener órdenes plan extra: {e}")

        # MËTODO BRUTO: Cancel All Orders por Símbolo activo? 
        # Mejor iterar sobre lo que encontramos.
        
        # Intento de cancelar Plan Orders via API directa si CCXT no las ve
        # Pero primero, veamos si con lo de arriba basta. 
        
        # Para Bitget V2, las TPSL son 'plan' orders.
        # Vamos a intentar usar el método específico de CCXT si existe `cancel_all_orders`
        
        print("🧹 Ejecutando barrido final...")
        # Iterar sobre las posiciones abiertas para saber qué símbolos limpiar
        balance = exchange.fetch_balance()
        positions = balance['info'][0]['positions'] if 'info' in balance and isinstance(balance['info'], list) else []
        
        # Si la estructura es distinta (V2mix):
        if not positions:
             positions = exchange.fetch_positions()
        
        seen_symbols = set()
        for pos in positions:
            symbol = pos['symbol']
            # Convertir formato si es necesario (e.g. BTCUSDT_UMCBL -> BTC/USDT:USDT)
            # CCXT suele normalizar. Usaremos el symbol del exchange si podemos.
            # Mejor usar exchange.markets para mapear.
            
            # Simplemente iteramos ordenes encontradas y ya.
            pass
            
        print("✅ LIMPIEZA COMPLETADA (O INTENTADA).")

    except Exception as e:
        print(f"🔥 Error Crítico durante limpieza: {e}")

if __name__ == "__main__":
    limpiar_todo()
