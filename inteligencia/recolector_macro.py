import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "../datos/macro_diario.csv")
ACTIVOS_MACRO = {
    'SP500': '^GSPC',  # S&P 500 (Indicador salud economía USA)
    'DOLAR': 'DX-Y.NYB' # Índice Dólar (Daxy) (Fuerza del dólar vs otras monedas)
}

def obtener_datos_macro():
    """
    Descarga los datos macroeconómicos más recientes.
    El S&P 500 suele tener correlación con Bitcoin (si sube, BTC suele subir).
    El Dólar suele tener correlación inversa (si sube, BTC suele bajar).
    """
    print("\n🌍 INICIANDO ESCUDO MACRO (ANÁLISIS ECONOMÍA MUNDIAL)...")
    
    resultados = []
    
    try:
        for nombre, ticker in ACTIVOS_MACRO.items():
            print(f"📡 Descargando datos de {nombre} ({ticker})...")
            
            # Descargamos solo el último día
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="1d")
            
            if not hist.empty:
                precio_cierre = hist['Close'].iloc[-1]
                cambio_porcentual = ((precio_cierre - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1]) * 100
                
                print(f"✅ {nombre}: {precio_cierre:.2f} ({cambio_porcentual:+.2f}%)")
                
                resultados.append({
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'activo': nombre,
                    'precio': precio_cierre,
                    'cambio_pct': cambio_porcentual
                })
            else:
                print(f"⚠️ No hay datos recientes para {nombre} (¿Mercado cerrado?).")

        # Guardar en CSV
        if resultados:
            df_nuevo = pd.DataFrame(resultados)
            
            # Si el archivo existe, añadimos sin encabezado
            modo = 'a' if os.path.exists(RUTA_DATOS) else 'w'
            header = not os.path.exists(RUTA_DATOS)
            
            df_nuevo.to_csv(RUTA_DATOS, mode=modo, header=header, index=False)
            print(f"💾 Datos macro guardados en: {RUTA_DATOS}")
        else:
            print("❌ No se pudieron obtener datos macro.")
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO EN RECOLECTOR MACRO: {e}")

if __name__ == "__main__":
    # Prueba individual
    obtener_datos_macro()
