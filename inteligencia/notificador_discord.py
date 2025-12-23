import requests
import json
import configuracion as config
from datetime import datetime

def enviar_alerta(tipo, mensaje, detalles=None):
    """
    Envía una alerta formateada a Discord.
    Tipos: 'COMPRA', 'VENTA', 'ERROR', 'INFO', 'PROFIT'.
    """
    if not config.DISCORD_WEBHOOK_URL:
        print("⚠️ ALERTA: No hay Webhook de Discord configurado.")
        return

    colores = {
        'COMPRA': 5763719, # Verde (Decimal)
        'VENTA': 15548997, # Rojo
        'ERROR': 16776960, # Amarillo (Warning)
        'INFO': 3447003,   # Azul
        'PROFIT': 15844367 # Dorado
    }

    iconos = {
        'COMPRA': '🟢',
        'VENTA': '🔴',
        'ERROR': '⚠️',
        'INFO': 'ℹ️',
        'PROFIT': '💰'
    }

    icono = iconos.get(tipo, '📢')
    color = colores.get(tipo, 0)
    
    hora = datetime.now().strftime('%H:%M:%S')

    embed = {
        "title": f"{icono} ALERTA ZEROX: {tipo}",
        "description": mensaje,
        "color": color,
        "footer": {
            "text": f"ZEROX CORE v2.5 | {hora}"
        }
    }

    if detalles:
        embed["fields"] = []
        for llave, valor in detalles.items():
            embed["fields"].append({
                "name": llave.upper(),
                "value": str(valor),
                "inline": True
            })

    payload = {
        "username": "Comandante ZEROX",
        "avatar_url": "https://i.imgur.com/AfFp7pu.png", # Icono genérico robótico o logo usuario
        "embeds": [embed]
    }

    try:
        requests.post(config.DISCORD_WEBHOOK_URL, json=payload)
        print(f"📨 Notificación Discord enviada: {tipo} - {mensaje}")
    except Exception as e:
        print(f"❌ Error enviando a Discord: {e}")

if __name__ == "__main__":
    enviar_alerta("INFO", "Prueba de sistema de notificaciones.", {"Estado": "Online", "Latencia": "20ms"})
