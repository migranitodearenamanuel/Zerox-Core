import os
import sys
import shutil
import warnings
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import requests
import time
import json

# Configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "conocimiento")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "inteligencia", "memoria_vectorial")
COLLECTION_NAME = "zerox_knowledge"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Silenciar advertencias de Chroma/ebooklib
warnings.filterwarnings("ignore")

def leer_epub(ruta):
    """Extrae texto limpio de un archivo EPUB."""
    try:
        book = epub.read_epub(ruta)
        texto_completo = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                texto_completo.append(soup.get_text(separator=' ', strip=True))
        return "\n".join(texto_completo)
    except Exception as e:
        print(f"❌ Error leyendo EPUB {os.path.basename(ruta)}: {e}")
        return ""

from pypdf import PdfReader

def leer_pdf(ruta):
    """Extrae texto de PDF."""
    try:
        reader = PdfReader(ruta)
        texto = []
        for page in reader.pages:
            t = page.extract_text()
            if t: texto.append(t)
        return "\n".join(texto)
    except Exception as e:
        print(f"❌ Error leyendo PDF {os.path.basename(ruta)}: {e}")
        return ""

def leer_archivo(ruta):
    """Router de lectura según extensión."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext == '.epub':
        return leer_epub(ruta)
    elif ext == '.pdf':
        return leer_pdf(ruta)
    elif ext == '.txt' or ext == '.md':
        try:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except: return ""
    return ""

def generar_embedding_ollama(texto, modelo="nomic-embed-text"):
    """Genera embedding usando Ollama local."""
    url = "http://localhost:11434/api/embeddings"
    payload = {"model": modelo, "prompt": texto}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get('embedding')
    except:
        pass
    return None

def main():
    print("🧠 INICIANDO INGESTIÓN MASIVA DE CONOCIMIENTO (ZEROX MNEMOSYNE)")
    print(f"📂 Directorio: {KNOWLEDGE_DIR}")
    print(f"💾 Base de Datos: {VECTOR_DB_DIR}")

    # 1. Inicializar ChromaDB
    cliente = chromadb.PersistentClient(path=VECTOR_DB_DIR)
    
    # Intentar obtener o crear colección
    try:
        coleccion = cliente.get_collection(name=COLLECTION_NAME)
        print(f"ℹ️ Colección '{COLLECTION_NAME}' encontrada. Añadiendo nuevos libros...")
    except:
        print(f"🆕 Creando nueva colección '{COLLECTION_NAME}'...")
        coleccion = cliente.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    # 2. Escanear Archivos
    archivos_procesables = []
    for root, dirs, files in os.walk(KNOWLEDGE_DIR):
        for file in files:
            if file.lower().endswith(('.epub', '.pdf', '.txt', '.md')): # Prioridad EPUB/PDF
                archivos_procesables.append(os.path.join(root, file))
    
    print(f"📚 Encontrados {len(archivos_procesables)} libros/documentos.")
    
    # 3. Procesar y Vectorizar
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    
    total = len(archivos_procesables)
    for i, ruta in enumerate(archivos_procesables):
        try:
            nombre_archivo = os.path.basename(ruta)
            print(f"[{i+1}/{total}] Procesando: {nombre_archivo}...", end="", flush=True)
            contenido = leer_archivo(ruta)
            
            if not contenido or len(contenido) < 500:
                print(" ⚠️ OMITIDO (Vacío o muy corto)")
                continue
                
            chunks = text_splitter.split_text(contenido)
            print(f" 🧩 {len(chunks)} fragmentos.", end="", flush=True)
            
            # Lote de inserción para eficiencia
            ids_lote = []
            docs_lote = []
            metadatas_lote = []
            embeddings_lote = []
            
            for j, chunk in enumerate(chunks):
                chunk_id = f"{nombre_archivo}_{j}" # ID único simple
                
                emb = generar_embedding_ollama(chunk)
                if emb:
                    ids_lote.append(chunk_id)
                    docs_lote.append(chunk)
                    metadatas_lote.append({"source": nombre_archivo, "chunk_index": j})
                    embeddings_lote.append(emb)
                
                if len(ids_lote) >= 50:
                    try:
                        coleccion.upsert(ids=ids_lote, documents=docs_lote, embeddings=embeddings_lote, metadatas=metadatas_lote)
                        print(".", end="", flush=True)
                    except Exception as e:
                        print(f"x", end="", flush=True) # Error parcial visual
                    ids_lote, docs_lote, metadatas_lote, embeddings_lote = [], [], [], []
            
            # Flush final del libro
            if ids_lote:
                try:
                    coleccion.upsert(ids=ids_lote, documents=docs_lote, embeddings=embeddings_lote, metadatas=metadatas_lote)
                except Exception: pass
            
            print(" ✅")
            
        except Exception as e:
            print(f" ❌ ERROR CRÍTICO EN ARCHIVO: {e}")
            continue

    print("\n🎉 INGESTIÓN COMPLETADA. EL CEREBRO AHORA ES GIGANTE.")

if __name__ == "__main__":
    main()
