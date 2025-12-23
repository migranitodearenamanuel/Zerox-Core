import os
import glob
from pathlib import Path

# Configuración
RUTA_CONOCIMIENTO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "conocimiento")
ARCHIVO_SALIDA = os.path.join(RUTA_CONOCIMIENTO, "cerebro.txt")

def extraer_texto_pdf(ruta):
    try:
        import fitz # PyMuPDF
        doc = fitz.open(ruta)
        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        return texto
    except ImportError:
        return f"[ERROR] Falta librería PyMuPDF. Instala: pip install pymupdf"
    except Exception as e:
        return f"[ERROR] Leyendo PDF {ruta}: {e}"

def extraer_texto_epub(ruta):
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        
        book = epub.read_epub(ruta)
        texto = ""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                texto += soup.get_text() + "\n"
        return texto
    except ImportError:
        return f"[ERROR] Falta ebooklib/bs4. Instala: pip install EbookLib beautifulsoup4"
    except Exception as e:
        return f"[ERROR] Leyendo EPUB {ruta}: {e}"

def procesar_biblioteca():
    print(f"📚 Escaneando biblioteca en: {RUTA_CONOCIMIENTO}")
    
    contenido_total = "--- BASE DE CONOCIMIENTO TÉCNICO (ZEROX) ---\n\n"
    archivos = []
    archivos.extend(glob.glob(os.path.join(RUTA_CONOCIMIENTO, "*.pdf")))
    archivos.extend(glob.glob(os.path.join(RUTA_CONOCIMIENTO, "*.epub")))
    
    if not archivos:
        print("⚠️ No se encontraron libros (.pdf, .epub).")
        return

    for archivo in archivos:
        nombre = os.path.basename(archivo)
        print(f"📖 Procesando: {nombre}...")
        
        texto = ""
        if archivo.endswith(".pdf"):
            texto = extraer_texto_pdf(archivo)
        elif archivo.endswith(".epub"):
            texto = extraer_texto_epub(archivo)
            
        # Limpieza básica
        texto_limpio = ' '.join(texto.split()) # Quitar saltos excesivos
        
        contenido_total += f"=== LIBRO: {nombre} ===\n"
        contenido_total += texto_limpio[:50000] # Límite por libro para no saturar tokens hoy
        contenido_total += "\n\n"

    # Guardar
    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        f.write(contenido_total)
        
    print(f"✅ Ingesta completada. Cerebro guardado en: {ARCHIVO_SALIDA}")
    print(f"🧠 Tamaño total: {len(contenido_total)} caracteres.")

if __name__ == "__main__":
    procesar_biblioteca()
