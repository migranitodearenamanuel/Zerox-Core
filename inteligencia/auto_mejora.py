import ccxt
import json
import os
import time
from datetime import datetime
import configuracion as config


# Archivo de memoria a largo plazo
ARCHIVO_LECCIONES = os.path.join(os.path.dirname(__file__), "lecciones.json")

def inicializar_memoria():
    if not os.path.exists(ARCHIVO_LECCIONES):
        with open(ARCHIVO_LECCIONES, 'w', encoding='utf-8') as f:
            json.dump([], f)

def obtener_historial_y_analizar(exchange):
    """
    Descarga operaciones recientes, busca pérdidas y pide consejo a la IA.
    """
    try:
        inicializar_memoria()
        
        # 1. Obtener los últimos trades cerrados (si la API lo permite)
        # Nota: fetch_my_trades a veces requiere symbol. Probamos genérico o BTC.
        # Para evitar errores en 'Depredador', lo hacemos fail-safe.
        trades = []
        try:
            # Intentamos obtener trades de los últimos 24h
            since = int(time.time() * 1000) - (24 * 60 * 60 * 1000)
            trades = exchange.fetch_my_trades(symbol=None, since=since, limit=20)
        except:
            # Fallback a un símbolo común si falla el genérico
            try:
                trades = exchange.fetch_my_trades(symbol=config.SIMBOLO, since=since, limit=10)
            except:
                pass

        nuevas_lecciones = []
        
        for trade in trades:
            # Analizar solo si es una venta (cierre) con PnL negativo
            # Bitget devuelve 'profit' en la estructura del trade si está disponible
            pnl = float(trade.get('info', {}).get('profit', 0))
            if pnl == 0 and 'fee' in trade:
                # Estimación si no hay pnl directo
                costo = float(trade['cost']) if 'cost' in trade else 0
                if costo > 0: 
                    pass # Lógica compleja omitida para brevedad

            # SIMULACIÓN PARA DEMO SI NO HAY DATOS REALES DE PÉRDIDA:
            # Si detectamos una pérdida real (pnl < 0), activamos el análisis.
            if pnl < 0:
                print(f"📉 Analizando derrota en {trade['symbol']} (PnL: {pnl} USDT)...")
                
                contexto = {
                    "Simbolo": trade['symbol'],
                    "Tipo": trade['side'],
                    "Precio": trade['price'],
                    "Resultado": f"PERDIDA DE {pnl} USDT",
                    "Mensaje": "La operación se fue en contra rápidamente."
                }
                
                # Pedir consejo a Mente Maestra (DESACTIVADO — integración eliminada)
                consejo = "Pérdida registrada. Revisar estrategia manual." 
                
                nuevas_lecciones.append({
                    "fecha": datetime.now().isoformat(),
                    "activo": trade['symbol'],
                    "leccion": consejo
                })

        # Si hubo lecciones nuevas, guardar
        if nuevas_lecciones:
            guardar_lecciones(nuevas_lecciones)
            return [l['leccion'] for l in nuevas_lecciones]
        
        return []

    except Exception as e:
        print(f"⚠️ Error en Auto-Mejora: {e}")
        return []

def guardar_lecciones(nuevas):
    """Añade lecciones al archivo JSON sin borrar las anteriores."""
    try:
        with open(ARCHIVO_LECCIONES, 'r', encoding='utf-8') as f:
            historial = json.load(f)
        
        # Añadir y limitar a las últimas 50
        historial.extend(nuevas)
        historial = historial[-50:] 
        
        with open(ARCHIVO_LECCIONES, 'w', encoding='utf-8') as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)
            
        print(f"🧠 {len(nuevas)} Nuevas lecciones integradas en el córtex.")
    except Exception as e:
        print(f"⚠️ No se pudo guardar lección: {e}")

def leer_ultimas_lecciones(n=3):
    """Devuelve las últimas N lecciones aprendidas (strings)."""
    try:
        if not os.path.exists(ARCHIVO_LECCIONES): return []
        with open(ARCHIVO_LECCIONES, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [item['leccion'] for item in data[-n:]]
    except:
        return []

if __name__ == "__main__":
    # Test
    print("Probando sistema de auto-mejora...")
    # Mock de exchange para probar lógica
    class MockExchange:
        def fetch_my_trades(self, symbol=None, since=None, limit=None):
            return [{
                'symbol': 'BTC/USDT', 'side': 'sell', 'price': 90000,
                'info': {'profit': -15.5}
            }]
    
    obtener_historial_y_analizar(MockExchange())
