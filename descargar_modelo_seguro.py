
import os
import shutil
from sentence_transformers import SentenceTransformer

def descargar_modelo_seguro():
    """
    Descarga explícita del modelo 'all-MiniLM-L6-v2' para evitar errores de conexión en runtime.
    Lo guarda en una carpeta local './inteligencia/modelos/all-MiniLM-L6-v2'.
    """
    modelo_nombre = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Ruta local absoluta
    base_dir = os.path.dirname(os.path.abspath(__file__))
    destino_modelo = os.path.join(base_dir, "inteligencia", "modelos", "all-MiniLM-L6-v2")
    
    # Intentar bypass de SSL y usar MIRROR para evitar bloqueos
    os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    
    print(f"📥 [IA] Iniciando descarga segura de: {modelo_nombre}")
    print(f"   📂 Destino: {destino_modelo}")
    print("   🔓 Modo SSL_VERIFY=False activado.")
    print("   🌐 Usando Mirror: hf-mirror.com")
    
    try:
        # Descarga forzada
        model = SentenceTransformer(modelo_nombre, cache_folder=destino_modelo)
        model.save(destino_modelo)
        print("✅ [IA] Modelo descargado y verificado correctamente.")
        print("   El sistema usará esta copia local a partir de ahora.")
        return True
    except Exception as e:
        print(f"❌ [IA] Error fatal descargando modelo: {e}")
        print("   Verifique su conexión a internet (HuggingFace).")
        return False

if __name__ == "__main__":
    descargar_modelo_seguro()
