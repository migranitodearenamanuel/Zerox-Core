import requests
import pandas as pd
import os
from datetime import datetime

# Configuración
API_URL = "https://api.alternative.me/fng/?limit=0"
OUTPUT_FILE = "../data/indice_miedo_codicia.csv"

def fetch_fear_greed_data():
    print("👻 Iniciando descarga del Fear & Greed Index...")
    
    try:
        # 1. Petición a la API
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        
        if data['metadata']['error']:
            print(f"❌ Error en la API: {data['metadata']['error']}")
            return

        print(f"📥 Datos recibidos: {len(data['data'])} registros.")

        # 2. Procesamiento
        records = []
        for entry in data['data']:
            # La API devuelve timestamp en segundos
            timestamp = int(entry['timestamp'])
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            records.append({
                'date': date_str,
                'value': int(entry['value']),
                'sentiment': entry['value_classification']
            })

        # Crear DataFrame
        df = pd.DataFrame(records)
        
        # Ordenar por fecha ascendente
        df = df.sort_values('date').reset_index(drop=True)

        # 3. Guardado
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        df.to_csv(OUTPUT_FILE, index=False)
        
        print(f"🎉 Éxito! Datos guardados en {OUTPUT_FILE}")
        print(f"📊 Rango: {df['date'].min()} -> {df['date'].max()}")
        print(f"📉 Mínimo histórico: {df['value'].min()}")
        print(f"📈 Máximo histórico: {df['value'].max()}")
        
    except Exception as e:
        print(f"❌ Error fatal: {e}")

if __name__ == "__main__":
    fetch_fear_greed_data()
