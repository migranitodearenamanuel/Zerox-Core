import feedparser
import json
import os
import time
import threading
from datetime import datetime
from deep_translator import GoogleTranslator

# ==============================================================================
# 📰 EL PERIODISTA V3.0 (TRADUCTOR UNIVERSAL)
# ==============================================================================
# Misión: Obtener noticias de Crypto y transformarlas al español en tiempo real.
# Salida: interfaz/public/noticias.json
# ==============================================================================

# RUTAS
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RUTA_JSON = os.path.join(BASE_DIR, "interfaz", "public", "noticias.json")

# CONFIGURACIÓN
TRADUCTOR = GoogleTranslator(source='auto', target='es')

# FUENTES RSS
FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/"
]

CANALES_YOUTUBE = [
    {"nombre": "Coin Bureau", "id": "UCqK_GSMbpiV8spgD3ZGloSw"},
    {"nombre": "DataDash", "id": "UCCatR7nWbYrkVXdxXb4cU8w"}, 
    {"nombre": "Ivan on Tech", "id": "UCrYmtJBtLdtm2ov84ulV-yg"},
    {"nombre": "Glassnode", "id": "UC0tqHhjpE0U4Z9sQp9vQ5rw"}
]

def traducir_texto(texto):
    """Traduce texto al español usando Deep Translator."""
    if not texto: return ""
    try:
        # Limpieza básica antes de traducir
        return TRADUCTOR.translate(texto)
    except Exception:
        return texto # Fallback

def obtener_noticias():
    noticias = []
    print("📰 Periodista: Escaneando y Traduciendo titulares...")
    
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            fuente = feed.feed.title if 'title' in feed.feed else "Fuente Cripto"
            
            # Limitar a 3 noticias por fuente para no saturar
            for entry in feed.entries[:3]:
                titulo_orig = entry.title
                summary_orig = entry.summary if 'summary' in entry else ""
                
                # Traducción
                titulo_es = traducir_texto(titulo_orig)
                
                noticias.append({
                    "titulo": titulo_es,
                    "resumen": summary_orig[:100] + "...", # Opcional: traducir resumen también si se quiere (lento)
                    "link": entry.link,
                    "fuente": fuente,
                    "fecha": entry.published if 'published' in entry else str(datetime.now())
                })
                time.sleep(0.2) # Pequeña pausa
        except Exception as e:
            print(f"⚠️ Error feed {url}: {e}")
            
    # Ordenar por fecha (truco simple, asumimos orden de llegada)
    return noticias[:20]

def obtener_videos():
    videos = []
    print("📺 Periodista: Procesando señales de video...")
    
    for canal in CANALES_YOUTUBE:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={canal['id']}"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]: # Solo el último video
                titulo_orig = entry.title
                titulo_es = traducir_texto(titulo_orig) # TRADUCIR TÍTULO VIDEO
                
                vid_id = entry.yt_videoid if 'yt_videoid' in entry else entry.link.split("v=")[-1]
                
                videos.append({
                    "titulo": titulo_es,
                    "id_youtube": vid_id,
                    "canal": canal['nombre']
                })
        except Exception:
            pass
            
    return videos

def generar_edicion():
    """Genera una edición completa del periódico."""
    try:
        datos = {
            "meta": {
                "edicion": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "estado": "ONLINE"
            },
            "noticias": obtener_noticias(),
            "videos": obtener_videos()
        }
        
        # Guardar JSON
        os.makedirs(os.path.dirname(RUTA_JSON), exist_ok=True)
        with open(RUTA_JSON, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
            
        print(f"✅ EDICIÓN ESPAÑOLA PUBLICADA EN: {RUTA_JSON}")
        
    except Exception as e:
        print(f"❌ Error Editorial: {e}")

def inicializar_dummy():
    """Crea datos falsos si no existen."""
    if not os.path.exists(RUTA_JSON):
        dummy = {
            "meta": {"edicion": "DEMO INICIAL", "estado": "ONLINE"},
            "noticias": [
                {"titulo": "Bitcoin roza los 98.000$ mientras los ETFs acumulan (Simulación)", "fuente": "Sistema Zerox", "link": "#", "fecha": str(datetime.now())},
                {"titulo": "Análisis: Ethereum podría superar a Bitcoin en rendimiento (Simulación)", "fuente": "Sistema Zerox", "link": "#", "fecha": str(datetime.now())}
            ],
            "videos": [
                {"titulo": "BITCOIN ALERTA ROJA: ¿Caída inminente? (Traducido)", "id_youtube": "dQw4w9WgXcQ", "canal": "Demo Channel"}
            ]
        }
        os.makedirs(os.path.dirname(RUTA_JSON), exist_ok=True)
        with open(RUTA_JSON, 'w', encoding='utf-8') as f:
            json.dump(dummy, f, indent=2, ensure_ascii=False)
            
if __name__ == "__main__":
    generar_edicion()
