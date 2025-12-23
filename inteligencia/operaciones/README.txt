DIRECTORIO DE EVIDENCIA FORENSE (REAL ONLY)
==============================================
Este directorio almacena logs inmutables en formato JSON de cada operación REAL ejecutada por ZeroX.

ESTRUCTURA:
/operaciones
    /AAAA-MM-DD
        /SIMBOLO_ORDERID.json

CONTENIDO DE EVIDENCIA:
- ID Orden Entrada (Exchange)
- IDs de Protección (TP/SL)
- Timestamp exacto
- Precios y Cantidades reales
- Resultado de Auditoría

POLÍTICA DE RETENCIÓN:
- Estos archivos son la prueba de ejecución. No deben borrarse manualmente.
- Si no hay archivos, el bot no ha ejecutado operaciones reales con éxito.

NOTA: Si este directorio está vacío, significa que el sistema está en espera de una oportunidad clara o que el mercado no cumple las condiciones de entrada de la IA.
