import os
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from datetime import datetime
import time
import random
import warnings

# Silenciar warning de renombrado de paquete (DuckDuckGo)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")

# Intentar importar DDGS (soportando nombre nuevo 'ddgs' y antiguo 'duckduckgo_search')
try:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    print("⚠️ 'duckduckgo-search' (o 'ddgs') no instalado. Usando solo lista maestra.")

# ==============================================================================
# 🦆 SINCRONIZADOR WEB V3 (MASTER SOURCES + DUCKDUCKGO)
# ==============================================================================

# CONFIGURACIÓN
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) # Raíz del proyecto
RUTA_CEREBRO = os.path.join(BASE_DIR, "conocimiento", "cerebro.txt")
RUTA_FUENTES = os.path.join(BASE_DIR, "fuentes_inteligencia.txt")

MAX_WORKERS = 15 # Aumentamos workers pues ahora tenemos muchas URLs
TIMEOUT = 10

# QUERIES SUPLEMENTARIAS (Para lo que no cubran las fuentes fijas)
QUERIES = [
    "Crypto breaking news today",
    "Bitcoin price analysis latest",
    "Altcoin season indicators 2025"
]

HEADERS_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

def cargar_fuentes_maestras():
    """Lee el archivo de fuentes de inteligencia."""
    urls = []
    if os.path.exists(RUTA_FUENTES):
        print(f"📜 Cargando Fuentes Maestras desde: {RUTA_FUENTES}")
        with open(RUTA_FUENTES, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        print(f"✅ {len(urls)} Fuentes Maestras cargadas.")
    else:
        print(f"⚠️ No se encontró {RUTA_FUENTES}. Usando solo búsqueda.")
    return urls

def buscar_ddg():
    """Busca URLs nuevas en DuckDuckGo (Limitado)."""
    urls_encontradas = set()
    if DDG_AVAILABLE:
        print(f"🦆 Consultando DuckDuckGo ({len(QUERIES)} queries suplementarias)...")
        try:
            with DDGS() as ddgs:
                for q in QUERIES:
                    # Limita a 5 por query para no saturar
                    results = ddgs.text(q, max_results=5) 
                    if results:
                        for r in results:
                            urls_encontradas.add(r['href'])
        except Exception as e:
            print(f"⚠️ Error DuckDuckGo: {e}")
            
    return list(urls_encontradas)

def scrapear_url(url):
    """Extrae texto de una URL con headers rotativos."""
    try:
        header_random = {"User-Agent": random.choice(HEADERS_LIST)}
        
        # 1. Request
        response = requests.get(url, headers=header_random, timeout=TIMEOUT)
        if response.status_code != 200:
            return None
            
        # 2. Parsing
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Limpieza
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]):
            element.decompose()
            
        # 4. Extracción
        textos = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
            lt = tag.get_text().strip()
            if len(lt) > 60: # Solo frases con sustancia
                textos.append(lt)
        
        contenido = "\n".join(textos)
        
        # Truncar para no explotar memoria (3000 chars por web)
        if len(contenido) > 3000:
            contenido = contenido[:3000] + "... [TRUNCADO]"
            
        if len(contenido) < 200:
            return None
            
        return f"\n>>> FUENTE: {url}\n{contenido}\n"

    except Exception:
        return None

def sincronizar():
    print("\n" + "="*60)
    print("🕸️ SINCRONIZADOR WEB V3 (MASTER SOURCES + DDG)")
    print("="*60)
    
    # 1. OBTENER URLS (Combinar Maestras + Búsqueda)
    urls_maestras = cargar_fuentes_maestras()
    urls_busqueda = buscar_ddg()
    
    # Combinar y quitar duplicados
    todas_urls = list(set(urls_maestras + urls_busqueda))
    random.shuffle(todas_urls) # Mezclar para no golpear mismo dominio seguido
    
    total = len(todas_urls)
    
    if total == 0:
        print("❌ ERROR FATAL: Sin objetivos. Revisa fuentes_inteligencia.txt.")
        return

    print(f"\n✅ OBJETIVOS BLINDADOS: {total} URLs. Iniciando extracción masiva...")
    
    # 2. SCRAPING
    conocimiento_nuevo = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrapear_url, url): url for url in todas_urls}
        
        completados = 0
        for future in concurrent.futures.as_completed(futures):
            completados += 1
            try:
                res = future.result()
            except Exception:
                res = None
            url_raw = futures[future]
            # Extraer dominio para log limpio
            try:
                dominio = url_raw.split('/')[2]
            except:
                dominio = url_raw[:20]

            if res:
                conocimiento_nuevo.append(res)
                print(f"   [{completados}/{total}] 📥 ASIMILADO: {dominio}")
            else:
                # Fallo silencioso visual para no spammear, solo mostramos si debug
                pass

    # 3. GUARDADO
    if conocimiento_nuevo:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bloque = f"\n\n\n=== 🧠 CONCIENCIA DE MERCADO ({fecha}) ===\n" + "".join(conocimiento_nuevo)
        
        os.makedirs(os.path.dirname(RUTA_CEREBRO), exist_ok=True)
        
        with open(RUTA_CEREBRO, 'a', encoding='utf-8') as f:
            f.write(bloque)
            
        print("\n" + "="*60)
        print(f"🧠 SINCRONIZACIÓN EXITOSA. {len(conocimiento_nuevo)} fuentes procesadas.")
        print(f"📁 Conocimiento inyectado en: {RUTA_CEREBRO}")
        print("="*60)
    else:
        print("\n⚠️ El escaneo no obtuvo datos útiles. Revisa tu conexión.")

if __name__ == "__main__":
    sincronizar()
