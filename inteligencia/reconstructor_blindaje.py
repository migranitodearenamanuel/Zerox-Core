import ccxt
import os
import sys
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import configuracion as config
import gestor_riesgo
import gestor_ordenes

# Instanciar Operador Maestro (Solo para usar sus métodos de protección si es posible, 
# pero mejor reimplementamos lo necesario para ser atómicos y no arrancar todo el bot)

def reconstruir_blindaje():
    print("🛡️ INICIANDO RECONSTRUCCIÓN DE BLINDAJE (REAL MODE)...")
    
    # 1. Conexión Exchange
    try:
        exchange = ccxt.bitget({
            'apiKey': config.CLAVE_API,
            'secret': config.SECRETO_API,
            'password': config.CONTRASENA_API,
            'options': {'defaultType': 'swap', 'adjustForTimeDifference': True}
        })
        exchange.load_markets()
    except Exception as e:
        print(f"❌ ERROR CONEXIÓN EXCHANGE: {e}")
        return

    # 2. Obtener Posiciones Reales
    try:
        positions = exchange.fetch_positions()
        active_positions = [p for p in positions if float(p['contracts']) > 0]
    except Exception as e:
        print(f"❌ ERROR LEYENDO POSICIONES: {e}")
        return

    reporte_snapshot = []
    
    if not active_positions:
        print("✅ NO HAY POSICIONES ABIERTAS. SISTEMA LIMPIO.")
    else:
        print(f"⚠️ {len(active_positions)} POSICIONES ACTIVAS DETECTADAS.")

    # 3. Iterar y Verificar/Reparar
    for pos in active_positions:
        simbolo = pos['symbol']
        lado = pos['side'] # long/short
        tamano = float(pos['contracts'])
        entrada = float(pos['entryPrice'])
        
        info_pos = {
            "Simbolo": simbolo,
            "Lado": lado,
            "Tamaño": tamano,
            "Entrada": entrada,
            "TP_Existe": False,
            "SL_Existe": False,
            "TP_ID": "N/A",
            "SL_ID": "N/A",
            "Estado": "PENDIENTE"
        }

        print(f"\n🔍 ANALIZANDO {simbolo} ({lado})...")

        # Consultar Órdenes Pendientes (TP/SL son órdenes)
        # En Bitget Mix, fetch_open_orders devuelve plan orders si se soportan.
        try:
            orders = exchange.fetch_open_orders(simbolo)
            
            # Buscar TP y SL
            tp_order = None
            sl_order = None
            
            for o in orders:
                # Lógica heurística para identificar TP/SL en Bitget V2
                # Suelen tener params específicos o 'reduceOnly': True
                info = o.get('info', {})
                plan_type = info.get('planType', '') # profit_plan, loss_plan (V1/V2 mix)
                
                # Check 1: planType explícito
                if plan_type == 'profit_plan' or plan_type == 'normal_profit_plan':
                    tp_order = o
                elif plan_type == 'loss_plan' or plan_type == 'normal_loss_plan':
                    sl_order = o
                
                # Check 2: params triggerPrice/stopPrice
                # (Depende de versión CCXT, a veces lo parsea en 'stopPrice')
                
            info_pos["TP_Existe"] = (tp_order is not None)
            info_pos["SL_Existe"] = (sl_order is not None)
            
            if tp_order: info_pos["TP_ID"] = tp_order.get('id', 'UNKNOWN')
            if sl_order: info_pos["SL_ID"] = sl_order.get('id', 'UNKNOWN')

            # 4. REPARACIÓN SI FALTA (VIRTUAL)
            info_pos["TP_Existe"], info_pos["SL_Existe"] = gestor_ordenes.verificar_tpsl_activas(simbolo)
            
            if not info_pos["TP_Existe"] or not info_pos["SL_Existe"]:
                print(f"🛑 FALTAN PROTECCIONES VIRTUALES EN {simbolo}. CALCULANDO...")
                
                direccion_riesgo = "LONG" if lado == "long" else "SHORT"
                tp_calc, sl_calc = gestor_riesgo.calcular_niveles_salida(entrada, direccion_riesgo)
                
                print(f"🛠️ REGISTRANDO TP VIRTUAL: {tp_calc} | SL VIRTUAL: {sl_calc}")
                
                res = gestor_ordenes.colocar_tpsl_posicion(exchange, simbolo, direccion_riesgo, tp_calc, sl_calc, tamano, es_reparacion=True)
                
                if res:
                    print(f"✅ REPARACIÓN VIRTUAL EXITOSA.")
                    info_pos["Estado"] = "REPARADO_VIRTUAL"
                    info_pos["TP_Existe"] = True
                    info_pos["SL_Existe"] = True
                else:
                    print(f"❌ FALLO REGISTRO VIRTUAL")
                    info_pos["Estado"] = "FALLO_VIRTUAL"

            else:
                print("✅ PROTECCIÓN VIRTUAL VERIFICADA.")
                info_pos["Estado"] = "VERIFICADO_VIRTUAL"

        except Exception as e_check:
            print(f"⚠️ ERROR PROCESANDO {simbolo}: {e_check}")
            info_pos["Estado"] = "ERROR_CHECK"
        
        reporte_snapshot.append(info_pos)

    # GUARDAR SNAPSHOT
    ruta_snap = os.path.join(os.path.dirname(__file__), "..", "tmp", "zerox_snapshot_posiciones.txt")
    with open(ruta_snap, "w", encoding="utf-8") as f:
        f.write("SNAPSHOT POSICIONES REALES + VIRTUAL\n")
        f.write("======================================\n")
        f.write(f"FECHA: {time.ctime()}\n\n")
        f.write(f"{'SIMBOLO':<15} {'LADO':<10} {'TAMAÑO':<10} {'ENTRADA':<10} {'TP?':<5} {'SL?':<5} {'ESTADO'}\n")
        f.write("-" * 100 + "\n")
        for r in reporte_snapshot:
            f.write(f"{r['Simbolo']:<15} {r['Lado']:<10} {r['Tamaño']:<10} {r['Entrada']:<10} {'SI' if r['TP_Existe'] else 'NO':<5} {'SI' if r['SL_Existe'] else 'NO':<5} {r['Estado']}\n")
            
    print(f"\nSnapshot guardado en: {ruta_snap}")

if __name__ == "__main__":
    reconstruir_blindaje()
