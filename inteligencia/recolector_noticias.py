import requests
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
RUTA_LOGS = os.path.join(os.path.dirname(__file__), "../datos/tendencias_noticias.json")
URL_TRENDING = "https://api.coingecko.com/api/v3/search/trending"

def buscar_alertas_ballenas():
    """
    EL COTILLA: Escanea las tendencias globales en CoinGecko.
    Si Bitcoin está en Trending Top 7, significa que hay "Hype" (Euforia o Pánico).
    """
    print("\n🗞️ INICIANDO EL COTILLA (RADAR DE NOTICIAS Y TENDENCIAS)...")
    
    try:
        print("📡 Consultando API de Tendencias Globales (CoinGecko)...")
        respuesta = requests.get(URL_TRENDING, timeout=10)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            monedas_trend = datos.get('coins', [])
            
            encontrado_btc = False
            top_3 = []
            
            print("🔥 TOP TENDENCIAS AHORA MISMO:")
            for i, item in enumerate(monedas_trend[:5]):
                moneda = item['item']
                nombre = moneda['name']
                simbolo = moneda['symbol']
                rank_mercado = moneda.get('market_cap_rank', 'N/A')
                
                print(f"   #{i+1}: {nombre} ({simbolo}) - Rank #{rank_mercado}")
                top_3.append(simbolo)
                
                if 'BTC' in simbolo or 'Bitcoin' in nombre:
                    encontrado_btc = True
            
            estado_social = "NORMAL"
            if encontrado_btc:
                estado_social = "ALERTA: Bitcoin está en boca de todos (Alta Volatilidad inminente)"
                print(f"⚠️ {estado_social}")
            else:
                print("ℹ️ Bitcoin no está en el Top 7 de tendencias. El mercado minorista está tranquilo.")

            # Guardar Resultado
            registro = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "top_trends": top_3,
                "btc_en_tendencias": encontrado_btc,
                "mensaje": estado_social
            }
            
            # Guardamos como JSON Lines (un JSON por línea) para fácil lectura
            with open(RUTA_LOGS, 'a') as f:
                json.dump(registro, f)
                f.write('\n')
                
            print(f"💾 Reporte de tendencias guardado en: {RUTA_LOGS}")
            
        else:
            print(f"❌ Error API CoinGecko: Código {respuesta.status_code}")

    except Exception as e:
        print(f"❌ ERROR CRÍTICO EN EL COTILLA: {e}")

if __name__ == "__main__":
    buscar_alertas_ballenas()
