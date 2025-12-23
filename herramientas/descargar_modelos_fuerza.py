
import os
import requests
import sys

# Lista de archivos esenciales para all-MiniLM-L6-v2
FILES = [
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
    "modules.json",
    "sentence_bert_config.json",
    "1_Pooling/config.json"
]

BASE_URL = "https://hf-mirror.com/sentence-transformers/all-MiniLM-L6-v2/resolve/main/"
DEST_DIR = os.path.join(os.getcwd(), "inteligencia", "modelos", "minilm_local")

def descargar_manual():
    print("🔧 [MANUAL] Iniciando descarga quirúrgica de archivos...")
    print(f"   URL Base: {BASE_URL}")
    print(f"   Destino: {DEST_DIR}")
    
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        
    session = requests.Session()
    session.verify = False # STRICT BYPASS
    session.trust_env = False # Ignore system proxies
    
    for archivo in FILES:
        url = BASE_URL + archivo
        ruta_local = os.path.join(DEST_DIR, archivo)
        
        # Asegurar subdir
        os.makedirs(os.path.dirname(ruta_local), exist_ok=True)
        
        if os.path.exists(ruta_local) and os.path.getsize(ruta_local) > 0:
            print(f"   ⏭️  Saltando {archivo} (Ya existe)")
            continue
            
        print(f"   ⬇️  Descargando {archivo}...", end="")
        try:
            r = session.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with open(ruta_local, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(" OK")
            else:
                print(f" ERROR {r.status_code}")
                # Fallback a pytorch_model.bin si safetensors falla
                if archivo == "model.safetensors":
                    print("   🔄 Intentando fallback a pytorch_model.bin...")
                    FILES.append("pytorch_model.bin")
        except Exception as e:
            print(f" FAIL ({e})")

if __name__ == "__main__":
    descargar_manual()
