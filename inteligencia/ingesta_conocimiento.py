"""
INGESTA (LEGACY)

Este script se mantiene como compatibilidad, pero la ingesta profesional recomendada
es `inteligencia/ingesta_conocimiento_total.py`, que construye el índice de Academia
con chunking real + embeddings locales y persistencia estable.

REGLA: Prohibido `sys.exit(1)` en el core. Este script nunca mata el proceso.
"""

import os
import sys

# Asegurar que `inteligencia/` está en sys.path si se ejecuta desde otra ruta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ingesta_conocimiento_total


def main():
    print("ACADEMIA: Ejecutando ingesta profesional (wrapper legacy).")
    try:
        res = ingesta_conocimiento_total.ingestar_conocimiento_total(
            chunk_tokens=900,
            overlap_tokens=150,
            max_docs_por_ciclo=10,
            max_chunks_por_doc=500,
            rebuild=False,
        )
        print(f"ACADEMIA: Ingesta finalizada. Resultado: {res}")
        return True
    except Exception as e:
        print(f"ACADEMIA: Error en ingesta: {e}")
        return False


if __name__ == "__main__":
    main()

