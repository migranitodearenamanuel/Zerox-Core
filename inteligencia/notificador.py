import requests
import json
import configuracion as config
from datetime import datetime
import puente_visual # Conexión a la UI

class Notificador:
    def __init__(self):
        self.webhook_url = config.DISCORD_WEBHOOK_URL

    def enviar(self, tipo, mensaje, detalles=None):
        """
        Envía alerta a Discord Y actualiza la interfaz web.
        """
        # 1. ACTUALIZAR INTERFAZ (PRIORIDAD ALTA)
        puente_visual.actualizar_estado({
            "ultima_notificacion": f"[{tipo}] {mensaje}",
            "tipo_notificacion": tipo,
            "color_notificacion": "verde" if tipo == "COMPRA" else "rojo" if tipo == "VENTA" else "amarillo"
        })

        # 2. ENVIAR A DISCORD
        if not self.webhook_url:
            return

        estilos = {
            'COMPRA':  {'icono': '🟢', 'color': 5763719},
            'VENTA':   {'icono': '🔴', 'color': 15548997},
            'ERROR':   {'icono': '⚠️', 'color': 16776960},
            'RESUMEN': {'icono': '💰', 'color': 15844367},
            'INFO':    {'icono': 'ℹ️', 'color': 3447003}
        }
        
        estilo = estilos.get(tipo, {'icono': '📢', 'color': 0})
        
        hora = datetime.now().strftime('%H:%M:%S')
        embed = {
            "title": f"{estilo['icono']} ZEROX: {tipo}",
            "description": mensaje,
            "color": estilo['color'],
            "footer": {"text": f"GOD MODE ACTIVE | {hora}"}
        }

        if detalles:
            embed["fields"] = []
            for k, v in detalles.items():
                embed["fields"].append({"name": k, "value": str(v), "inline": True})

        try:
            requests.post(self.webhook_url, json={"username": "ZEROX CORE", "embeds": [embed]})
        except Exception as e:
            print(f"❌ Error Discord: {e}")

notificador = Notificador()
