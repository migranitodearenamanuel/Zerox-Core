import os
import sys
sys.path.insert(0, os.getcwd())  # Asegurar que el proyecto está en sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'inteligencia'))  # Para imports legacy como extractor_epub

from inteligencia import ingesta_conocimiento_total

print('Iniciando ingesta profesional completa (rebuild=True). Esto puede tardar...')
res = ingesta_conocimiento_total.ingestar_conocimiento_total(
    chunk_tokens=900,
    overlap_tokens=150,
    max_docs_por_ciclo=200,
    max_chunks_por_doc=2000,
    rebuild=True,
)
print('Resultado final:', res)
