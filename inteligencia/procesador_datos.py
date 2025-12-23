import pandas as pd
import os

# Configuración
PRICE_FILE = '../data/btc_usdt_15m.csv'
SENTIMENT_FILE = '../data/indice_miedo_codicia.csv'
OUTPUT_FILE = '../data/conjunto_datos_maestro_v2.csv'

def process_data():
    print("⚙️ Iniciando fusión de datasets...")

    # 1. Cargar Datos de Precios
    if not os.path.exists(PRICE_FILE):
        print(f"❌ Error: No se encuentra {PRICE_FILE}")
        return
    
    print(f"📉 Cargando precios desde {PRICE_FILE}...")
    df_price = pd.read_csv(PRICE_FILE)
    # Convertir a datetime la columna 'datetime'. Si no existe, usar 'timestamp'
    if 'datetime' in df_price.columns:
        df_price['datetime'] = pd.to_datetime(df_price['datetime'])
    else:
        # Fallback si se guardó diferente
        df_price['datetime'] = pd.to_datetime(df_price['timestamp'], unit='ms')

    # Crear columna 'date_key' solo fecha para el merge
    df_price['date_key'] = df_price['datetime'].dt.strftime('%Y-%m-%d')

    # 2. Cargar Datos de Sentimiento
    if not os.path.exists(SENTIMENT_FILE):
        print(f"❌ Error: No se encuentra {SENTIMENT_FILE}")
        return

    print(f"👻 Cargando sentimiento desde {SENTIMENT_FILE}...")
    df_sentiment = pd.read_csv(SENTIMENT_FILE)
    # Asegurar que 'date' sea string formato YYYY-MM-DD para coincidir
    # La columna 'value' es el índice (0-100)

    # 3. Fusión (Left Join) con propagación
    # Queremos mantener todas las velas de precios
    print("🔄 Fusionando datos...")
    
    # Merge on date
    df_merged = pd.merge(
        df_price, 
        df_sentiment[['date', 'value']], # Solo nos interesa la fecha y el valor numérico
        left_on='date_key',
        right_on='date',
        how='left'
    )

    # 4. Limpieza
    print("🧹 Limpiando datos...")
    
    # Renombrar 'value' a 'sentiment_index'
    df_merged.rename(columns={'value': 'sentiment_index'}, inplace=True)
    
    # Eliminar filas donde el sentimiento sea NaN (días sin datos, ej: muy antiguos o faltantes)
    initial_len = len(df_merged)
    df_merged.dropna(subset=['sentiment_index', 'close'], inplace=True)
    final_len = len(df_merged)
    
    print(f"   - Filas eliminadas por falta de datos: {initial_len - final_len}")

    # Seleccionar y ordenar columnas finales
    # timestamp, open, high, low, close, volume, sentiment_index
    # (Mantenemos datetime solo si es útil para debug, pero para ML suelen sobrar timestamps absolutos si hay secuencia)
    cols_to_keep = ['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'sentiment_index']
    df_final = df_merged[cols_to_keep].copy()

    # Asegurar tipos float
    float_cols = ['open', 'high', 'low', 'close', 'volume', 'sentiment_index']
    for col in float_cols:
        df_final[col] = df_final[col].astype(float)

    # 5. Guardado
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False)
    
    print(f"🎉 Dataset Maestro v2 generado: {OUTPUT_FILE}")
    print(f"📊 Dimensiones finales: {df_final.shape} (Filas, Columnas)")
    print(f"📝 Columnas: {list(df_final.columns)}")
    print(f"📅 Rango Temporal: {df_final['datetime'].min()} -> {df_final['datetime'].max()}")

if __name__ == "__main__":
    process_data()
