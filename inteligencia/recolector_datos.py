import ccxt
import pandas as pd
import time
from datetime import datetime, timedelta
import os

# Configuración
SYMBOL = 'BTC/USDT:USDT' # Futuros
TIMEFRAME = '15m'
YEARS_BACK = 2
OUTPUT_FILE = '../data/btc_usdt_15m.csv'
LIMIT = 1000 # Máximo por request en Bitget

def fetch_historical_data():
    print(f"🚀 Iniciando recolección de datos para {SYMBOL} ({TIMEFRAME})...")
    
    # Inicializar exchange
    exchange = ccxt.bitget({
        'enableRateLimit': True,
    })

    # Calcular timestamp de inicio (hace 2 años)
    since = exchange.parse8601((datetime.now() - timedelta(days=365*YEARS_BACK)).isoformat())
    
    all_candles = []
    
    while True:
        try:
            print(f"📥 Descargando desde: {exchange.iso8601(since)}")
            candles = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=LIMIT)
            
            if not candles:
                print("✅ No hay más datos disponibles.")
                break
            
            all_candles.extend(candles)
            
            # Actualizar 'since' al tiempo de la última vela + 1 milisegundo
            last_candle_time = candles[-1][0]
            since = last_candle_time + 1
            
            # Guardado parcial por seguridad
            if len(all_candles) % 5000 == 0:
                print(f"💾 Progreso: {len(all_candles)} velas recolectadas...")
            
            # Si la última vela es muy reciente (cerca de ahora), paramos
            now = exchange.milliseconds()
            if last_candle_time >= (now - 15 * 60 * 1000): # Menos de 15 min de antigüedad
                print("✅ Llegamos al presente.")
                break
                
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            print("🔄 Reintentando en 5 segundos...")
            time.sleep(5)
            continue

    # Procesar y Guardar
    if all_candles:
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Guardar CSV
        # Asegurar que el directorio existe (aunque ya lo creamos)
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"🎉 Éxito! Datos guardados en {OUTPUT_FILE}")
        print(f"📊 Total de velas: {len(df)}")
        print(f"📅 Rango: {df['datetime'].min()} -> {df['datetime'].max()}")
    else:
        print("⚠️ No se descargaron datos.")

if __name__ == "__main__":
    fetch_historical_data()
