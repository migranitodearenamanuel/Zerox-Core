
import os
import zipfile
import re
import warnings

def extraer_texto_epub(ruta_archivo):
    """
    Intenta extraer texto de un EPUB (formato ZIP disfrazado).
    Busca archivos .html / .xhtml dentro y extrae el texto crudo.
    No requiere librerías externas pesadas (ebooklib), usa standard library.
    """
    texto_completo = ""
    try:
        with zipfile.ZipFile(ruta_archivo, 'r') as z:
            # Filtrar archivos de contenido
            archivos_html = [f for f in z.namelist() if f.endswith('.html') or f.endswith('.xhtml')]
            
            for archivo in archivos_html:
                content_bytes = z.read(archivo)
                content_str = content_bytes.decode('utf-8', errors='ignore')
                
                # Limpieza básica de tags HTML (Regex rápido)
                clean = re.sub('<[^<]+?>', ' ', content_str)
                clean = re.sub(r'\s+', ' ', clean)
                
                texto_completo += clean + "\n\n"
                
        return texto_completo
    except Exception as e:
        print(f"⚠️ Error extractor EPUB nativo: {e}")
        return None
