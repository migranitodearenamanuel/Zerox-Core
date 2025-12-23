
import os
from sentence_transformers import SentenceTransformer

# Ruta puramente absoluta y normalizada
base = os.path.dirname(os.path.abspath(__file__))
ruta = os.path.join(base, "inteligencia", "modelos", "minilm_local")
ruta = os.path.normpath(ruta)

print(f"PATH: {ruta}")
print(f"EXISTS: {os.path.exists(ruta)}")
print(f"ISDIR: {os.path.isdir(ruta)}")

try:
    model = SentenceTransformer(ruta)
    print("SUCCESS")
except Exception as e:
    print(f"FAIL: {e}")
