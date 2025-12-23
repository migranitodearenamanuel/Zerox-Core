
import sys
import os
import time

# Forzar codificación UTF-8 para evitar errores en consola Windows
sys.stdout.reconfigure(encoding='utf-8')

# Ajustar path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'inteligencia')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    import configuracion as config
except ImportError:
    # Si falla, intentar cargar desde inteligencia
    sys.path.append(os.path.join(os.getcwd(), 'inteligencia'))
    import configuracion as config

import ccxt
from datetime import datetime

def verificar_modo_real():
    print("\n" + "="*60)
    print("🕵️  AUDITORÍA DE MODO REAL - ZEROX PRE-FLIGHT CHECK")
    print("="*60)

    # 1. VERIFICAR VARIABLES DE ENTORNO
    api_key = config.CLAVE_API
    secret = config.SECRETO_API
    password = config.CONTRASENA_API
    
    if not api_key or not secret or not password:
        print("❌ ERROR CRÍTICO: Faltan CLAVES API en .env o configuración.")
        print(f"   API_KEY: {'******' if api_key else 'FALTA'}")
        print(f"   SECRET:  {'******' if secret else 'FALTA'}")
        print(f"   PASS:    {'******' if password else 'FALTA'}")
        sys.exit(1)
    else:
        print("✅ Credenciales detectadas en memoria (ocultas).")

    # 2. CONEXIÓN A BITGET REAL
    print("\n📡 Iniciando conexión de prueba a BITGET (FUTUROS)...")
    try:
        exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret,
            'password': password,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        
        # Sincronizar tiempo
        exchange.load_markets()
        print("✅ Mercados cargados correctamente.")
        
        # 3. LEER SALDO REAL
        balance = exchange.fetch_balance()
        usdt = balance.get('USDT', {})
        total = usdt.get('total', 0.0)
        free = usdt.get('free', 0.0)
        
        print(f"\n💰 SALDO REAL CONFIRMADO:")
        print(f"   EQUITY TOTAL: {total:.2f} USDT")
        print(f"   DISPONIBLE:   {free:.2f} USDT")
        
        if total < 10:
            print("⚠️  ADVERTENCIA: Saldo bajo para operar agresivamente.")
        
        # 4. CONFIRMACIÓN FINAL
        print("\n" + "="*60)
        print("🚀 EL SISTEMA ESTÁ LISTO PARA MODO REAL.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {str(e)}")
        print("Revisa tu conexión a internet y las claves API.")
        sys.exit(1)

if __name__ == "__main__":
    verificar_modo_real()
