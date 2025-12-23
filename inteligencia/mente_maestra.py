import os
import json
from dotenv import load_dotenv

# Cargar variables
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
RUTA_CEREBRO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "conocimiento", "cerebro.txt")

# Integración con Gemini eliminada — Mente Maestra desactivada
model = None
try:
    print("MENSAJE: Integración con Gemini eliminada. Mente Maestra desactivada.")
except Exception:
    pass

import chromadb

# RAG CONFIG
VECTOR_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inteligencia", "memoria_vectorial")

def _recuperar_contexto_rag(query, top_k=3):
    """Búsqueda semántica usando ChromaDB (Oficial)."""
    try:
        if not os.path.exists(VECTOR_DB_DIR):
            return "Memoria Vectorial no inicializada."
            
        cliente = chromadb.PersistentClient(path=VECTOR_DB_DIR)
        try:
            coleccion = cliente.get_collection(name="zerox_knowledge")
        except:
            return "Colección de conocimiento vacía."

        # Generar embedding del query usando Ollama (igual que ingestor)
        try:
            vector_query = requests.post("http://localhost:11434/api/embeddings", 
                                        json={"model": "nomic-embed-text", "prompt": query}, timeout=2).json().get('embedding')
        except:
            return "Ollama Offline: No puedo pensar en vectores."

        if not vector_query: return "Error neural en embedding."

        resultados = coleccion.query(
            query_embeddings=[vector_query],
            n_results=top_k
        )
        
        # Procesar resultados
        # Chroma retorna listas de listas: {'documents': [['texto1', 'texto2']], 'metadatas': [[...]]}
        docs = resultados['documents'][0]
        metas = resultados['metadatas'][0]
        
        contexto_formateado = []
        for i, doc in enumerate(docs):
            fuente = metas[i].get('source', 'Desconocido')
            contexto_formateado.append(f"[{fuente}] {doc}")
            
        return "\n---\n".join(contexto_formateado)

    except Exception as e:
        return f"Error accediendo a memoria a largo plazo: {e}"

def analizar_oportunidad(contexto):
    """
    Analiza oportunidad usando RAG + LLM.
    Retorna JSON estricto: { decision, razon, confianza, apalancamiento, ... }
    """
    simbolo = contexto.get('symbol', 'MERCADO')
    rsi = contexto.get('rsi', 50)
    
    # 1. RECUPERAR CONTEXTO (RAG)
    # Buscamos conocimiento sobre el setup o gestión de riesgo
    query_rag = f"Estrategia trading RSI {rsi} tendencia {contexto.get('trend')} gestion riesgo"
    conocimiento_rag = _recuperar_contexto_rag(query_rag)
    
    # 2. CONSTRUIR PROMPT
    prompt = f"""
    ERES UNA IA DE TRADING QUANT. ANALIZA:
    {json.dumps(contexto, indent=2)}

    CONOCIMIENTO EXPERTO RECUPERADO (RAG):
    {conocimiento_rag[:2500]}

    TU MISIÓN:
    Decidir si operar LONG, SHORT o ESPERAR.
    
    REGLAS:
    - Salida JSON VÁLIDO ESTRICTO.
    - Campos obligatorios: "decision" (COMPRA/VENTA/ESPERAR), "razon", "confianza" (0-100), "apalancamiento" (1-15).
    - Apalancamiento: Sé conservador. Máx 5x normal, 10x solo setups de oro.
    - Si la confianza es < 60, decision debe ser ESPERAR.

    EJEMPLO JSON:
    {{
        "decision": "COMPRA",
        "razon": "RSI sobrevendido en tendencia alcista + Divergencia.",
        "confianza": 85,
        "apalancamiento": 5,
        "setup_id": "RSI_PULLBACK"
    }}
    """
    
    respuesta_default = {
        "decision": "ESPERAR",
        "razon": "Fallo en conexión cerebral o incertidumbre.",
        "confianza": 0,
        "apalancamiento": 1,
        # Compatibilidad UI
        "tecnico": "Modo seguro activado.",
        "accion_sugerida": "ESPERAR"
    }

    if not model:
        # Mente Maestra desactivada (integración con Gemini eliminada)
        return respuesta_default

# --- MEMORIA A CORTO PLAZO (SINAPSIS) ---
MEMORIA_SINAPTICA = [
    {
        "id": 1, 
        "timestamp": "INIT", 
        "moneda": "SISTEMA", 
        "accion": "BOOT", 
        "razon": "Núcleo Cognitivo Iniciado.", 
        "mensaje": "Esperando datos de mercado..."
    }
]

def _registrar_pensamiento(simbolo, data):
    """Guarda un pensamiento estructurado para la Terminal Neuronal."""
    global MEMORIA_SINAPTICA
    from datetime import datetime
    
    # Inferir acción basada en texto (simple heurística)
    accion = "ESPERAR"
    if "alcista" in data.get('tecnico', '').lower(): accion = "COMPRA"
    elif "bajista" in data.get('tecnico', '').lower(): accion = "VENTA"
    
    pensamiento = {
        "id": int(datetime.now().timestamp() * 1000),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "moneda": simbolo,
        "accion": accion,
        "razon": data.get('tecnico', 'Analizando...'),
        "mensaje": f"[{simbolo}] {accion}: {data.get('psicologia', '')}" # Fallback para legacy
    }
    
    MEMORIA_SINAPTICA.insert(0, pensamiento)
    MEMORIA_SINAPTICA = MEMORIA_SINAPTICA[:20] # Mantener últimos 20

def obtener_pensamientos_recientes():
    """Interfaz para que el Operador Maestro recupere el flujo."""
    return MEMORIA_SINAPTICA
