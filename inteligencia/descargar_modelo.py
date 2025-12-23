import os
import sys

# --- CONFIGURACIÓN CRÍTICA PARA WINDOWS ---
# Desactiva los symlinks para evitar el Error 1314
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
# Fuerza modo online
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

print("📡 INICIANDO PROTOCOLO DE DESCARGA SEGURA (SIN SYMLINKS)...")

try:
    from sentence_transformers import SentenceTransformer
    
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"⬇️  Descargando modelo maestro: {model_name} ...")
    print("    (Esto descargará copias reales de los archivos, puede tardar un poco)")
    
    # Al instanciarlo, se descarga automáticamente respetando la config de arriba
    model = SentenceTransformer(model_name)
    
    print("\n✅ ÉXITO TOTAL: Modelo descargado y verificado.")
    print("🔓 El sistema de archivos ya no rechazará la IA.")

except Exception as e:
    print("\n❌ ERROR DURANTE LA DESCARGA:")
    print(e)
