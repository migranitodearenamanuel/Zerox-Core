import requests
import json
import os
from datetime import datetime
import time

# Configuración de Ollama Local
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO_LOCAL = "llama3.1" # o "mistral", "qwen2.5", etc.
TIMEOUT_SEC = 30 
LAST_ERROR_TS = 0.0 # Cooldown para evitar spam de errores
COOLDOWN_ERROR_SEC = 60 

# --- MEMORIA A CORTO PLAZO (SINAPSIS) ---
MEMORIA_SINAPTICA = [
    {
        "id": 1, 
        "timestamp": "INIT", 
        "moneda": "SISTEMA", 
        "accion": "BOOT", 
        "razon": "Cerebro Local (Ollama) Inicializado.", 
        "mensaje": "Esperando conexión neuronal..."
    }
]

import chromadb
VECTOR_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inteligencia", "memoria_vectorial")

def _recuperar_contexto_rag(query, top_k=3):
    """Búsqueda semántica usando ChromaDB (Oficial) para Mente Local."""
    try:
        if not os.path.exists(VECTOR_DB_DIR):
            return "Memoria Vectorial no inicializada."
            
        cliente = chromadb.PersistentClient(path=VECTOR_DB_DIR)
        try:
            coleccion = cliente.get_collection(name="zerox_knowledge")
        except:
            return "Colección de conocimiento vacía."

        # Generar embedding del query usando Ollama
        try:
            payload = {"model": "nomic-embed-text", "prompt": query}
            vector_query = requests.post("http://localhost:11434/api/embeddings", json=payload, timeout=2).json().get('embedding')
        except:
            return "Ollama Offline: No puedo pensar en vectores."

        if not vector_query: return "Error neural en embedding."

        resultados = coleccion.query(
            query_embeddings=[vector_query],
            n_results=top_k
        )
        
        docs = resultados['documents'][0]
        metas = resultados['metadatas'][0]
        
        contexto_formateado = []
        for i, doc in enumerate(docs):
            fuente = metas[i].get('source', 'Desconocido')
            contexto_formateado.append(f"[{fuente}] {doc}")
            
        return "\n---\n".join(contexto_formateado)

    except Exception as e:
        return f"Error accediendo a memoria a largo plazo: {e}"

def _leer_cerebro(contexto_market=None):
    """
    Lee contexto RAG basado en el símbolo y situación actual.
    Reemplaza la lectura estática de 'cerebro.txt'.
    """
    if not contexto_market: return "Esperando datos..."
    
    simbolo = contexto_market.get('symbol', 'Crypto')
    rsi = contexto_market.get('rsi', 50)
    
    # Query dinámica para buscar sabiduría relevante
    query = f"Estrategia trading {simbolo} RSI {rsi} tendencia psicologia mercado"
    
    contexto_recuperado = _recuperar_contexto_rag(query)
    return contexto_recuperado

def analizar_oportunidad(contexto):
    """
    Analiza oportunidad de trading usando Ollama (Llama 3.1) OFFLINE + RAG.
    Devuelve dict con claves: tecnico, psicologia, fuentes.
    """
    
    # 1. Preparar Prompt
    global LAST_ERROR_TS
    
    # Healthcheck rápido (Circuit Breaker)
    if (time.time() - LAST_ERROR_TS) < COOLDOWN_ERROR_SEC:
        return _ejecutar_fallback(contexto, razon_override="IA_OFFLINE (Cooldown)")

    conocimiento = _leer_cerebro(contexto) # AHORA USA RAG
    rsi = contexto.get('rsi', 50)
    simbolo = contexto.get('symbol', 'UNKNOWN')
    
    prompt_sistema = f"""
    Eres ZeroX, una IA de trading experta, fría y calculadora.
    Tu objetivo es analizar el mercado y decidir: COMPRA, VENTA o ESPERAR.
    
    Responde ÚNICAMENTE con un JSON válido. Sin markdown, sin explicaciones extra.
    
    Formato JSON Requerido:
    {{
      "tecnico": "Análisis técnico breve (ej. RSI {rsi}, Soporte X, Resistencia Y)",
      "psicologia": "Estado mental del mercado (ej. Miedo, Codicia, Calma)",
      "fuentes": "Referencia a patrones clásicos o datos del contexto",
      "accion_sugerida": "COMPRA" | "VENTA" | "ESPERAR",
      "confianza": 0-100
    }}
    """
    
    prompt_usuario = f"""
    DATOS ACTUALES:
    {json.dumps(contexto, indent=2)}
    
    CONTEXTO MEMORIA:
    {conocimiento[:1000]}
    
    Analiza y decide.
    """
    
    payload = {
        "model": MODELO_LOCAL,
        "prompt": prompt_sistema + "\n" + prompt_usuario,
        "stream": False,
        "format": "json", # Ollama soporta modo JSON nativo
        "options": {
            "temperature": 0.2, # Baja temperatura para precisión
            "num_predict": 200
        }
    }

    try:
        # 2. Llamada a Ollama
        print(f"🧠 [LOCAL] Pensando sobre {simbolo}...")
        inicio = time.time()
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SEC)
        response.raise_for_status()
        
        resultado_raw = response.json()['response']
        datos = json.loads(resultado_raw)
        
        tiempo_pensamiento = time.time() - inicio
        print(f"⚡ [LOCAL] Respuesta en {tiempo_pensamiento:.2f}s")
        
        # Guardar en memoria
        _registrar_pensamiento(simbolo, datos)
        return datos

    except Exception as e:
        LAST_ERROR_TS = time.time()
        print(f"⚠️ [FALLBACK] Error Ollama (Pausando 60s): {e}")
        return _ejecutar_fallback(contexto, razon_override="IA_FAIL")

def _ejecutar_fallback(contexto, razon_override=None):
    """Lógica Heurística si falla la IA (Cerebro de Reptil)."""
    rsi = contexto.get('rsi', 50)
    
    accion = "ESPERAR"
    razon = f"RSI Neutral ({rsi})"
    
    if razon_override:
         razon = f"{razon} | {razon_override}"
    
    if rsi < 30:
        accion = "COMPRA"
        razon = f"Sobreventa detectada (RSI {rsi} < 30). Rebote probable."
    elif rsi > 70:
        accion = "VENTA"
        razon = f"Sobrecompra detectada (RSI {rsi} > 70). Corrección probable."
        
    respuesta = {
        "tecnico": razon,
        "psicologia": "Modo Supervivencia (Fallback)",
        "fuentes": "Algoritmo Heurístico de Emergencia",
        "accion_sugerida": accion,
        "confianza": 50
    }
    
    _registrar_pensamiento(contexto.get('symbol', 'MERCADO'), respuesta)
    return respuesta

def _registrar_pensamiento(simbolo, data):
    """Guarda el pensamiento en la memoria para el Frontend."""
    global MEMORIA_SINAPTICA
    
    # Normalizar acción
    accion_raw = data.get('accion_sugerida', 'ESPERAR').upper()
    if "COMPRA" in accion_raw: accion = "COMPRA"
    elif "VENTA" in accion_raw: accion = "VENTA"
    else: accion = "ESPERAR"
    
    pensamiento = {
        "id": int(datetime.now().timestamp() * 1000),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "moneda": simbolo,
        "accion": accion, # COMPRA / VENTA / ESPERAR
        "razon": data.get('tecnico', 'Sin datos'),
        "mensaje": f"[{simbolo}] {data.get('psicologia', '')}"
    }
    
    MEMORIA_SINAPTICA.insert(0, pensamiento)
    MEMORIA_SINAPTICA = MEMORIA_SINAPTICA[:20]

def obtener_pensamientos_recientes():
    return MEMORIA_SINAPTICA
