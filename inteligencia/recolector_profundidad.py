import ccxt
import pandas as pd
import os
import time
from datetime import datetime

# Importamos configuración para usar las mismas claves si fuera necesario (aunque depth suele ser público)
try:
    import configuracion as config
except ImportError:
    # Fallback si se ejecuta aislado
    class config:
        SIMBOLO = 'BTC/USDT' # Spot por defecto para análisis de profundidad general

# --- CONFIGURACIÓN ---
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "../datos/presion_mercado.csv")
PARAMETRO_PROFUNDIDAD = 20 # Cuántos niveles del libro de órdenes analizamos

def analizar_profundidad_mercado():
    """
    VISIÓN DE RAYOS X: Analiza el Libro de Órdenes (Order Book).
    Calcula si hay más dinero esperando para COMPRAR (Soporte) o para VENDER (Resistencia).
    """
    print("\n👁️ INICIANDO VISIÓN RAYOS X (ANÁLISIS DE PROFUNDIDAD)...")
    
    # Usamos instancia pública para no exponer claves si no es necesario, 
    # pero Bitget puede requerir auth para rate limits altos. Usamos público por ahora.
    exchange = ccxt.bitget()
    
    try:
        simbolo = "BTC/USDT" # Usamos Spot para ver la liquidez real subyacente
        print(f"📡 Escaneando Libro de Órdenes de {simbolo}...")
        
        # Descargar Order Book
        libro = exchange.fetch_order_book(simbolo, limit=PARAMETRO_PROFUNDIDAD)
        
        bids = libro['bids'] # Órdenes de COMPRA (Gente que quiere comprar barato) -> SOPORTE
        asks = libro['asks'] # Órdenes de VENTA (Gente que quiere vender caro) -> RESISTENCIA
        
        # Calcular volumen total en ambos lados
        volumen_compra = sum([orden[1] for orden in bids]) # orden[1] es la cantidad
        volumen_venta = sum([orden[1] for orden in asks])
        
        # Calcular Ratio de Presión
        # Si ratio > 1: Más fuerza compradora (Bullish)
        # Si ratio < 1: Más fuerza vendedora (Bearish)
        ratio_presion = volumen_compra / volumen_venta if volumen_venta > 0 else 0
        
        estado = "NEUTRAL"
        if ratio_presion > 1.2: estado = "ALCISTA (Muro de Compra)"
        elif ratio_presion < 0.8: estado = "BAJISTA (Muro de Venta)"
        
        print(f"📊 RESULTADOS:")
        print(f"   - Volumen Compra (Soporte): {volumen_compra:.4f} BTC")
        print(f"   - Volumen Venta (Resistencia): {volumen_venta:.4f} BTC")
        print(f"   - Ratio Presión: {ratio_presion:.2f} -> {estado}")
        
        # Guardar Log
        datos = {
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'volumen_bid': volumen_compra,
            'volumen_ask': volumen_venta,
            'ratio': ratio_presion,
            'estado': estado
        }
        
        df_nuevo = pd.DataFrame([datos])
        modo = 'a' if os.path.exists(RUTA_DATOS) else 'w'
        header = not os.path.exists(RUTA_DATOS)
        
        df_nuevo.to_csv(RUTA_DATOS, mode=modo, header=header, index=False)
        print(f"💾 Análisis de profundidad guardado en: {RUTA_DATOS}")
        
        return ratio_presion

    except Exception as e:
        print(f"❌ ERROR CRÍTICO EN VISIÓN RAYOS X: {e}")
        return None

if __name__ == "__main__":
    analizar_profundidad_mercado()
