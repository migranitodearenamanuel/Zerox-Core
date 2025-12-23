import os
import time
import json
import requests
import numpy as np
import threading
from datetime import datetime
import hashlib
import glob
import re
from urllib.parse import urlparse

import ingesta_conocimiento_total

# CONFIGURACIÓN
BASE_DIR = os.path.dirname(__file__)
DIR_FUENTES = os.path.join(BASE_DIR, "academia", "fuentes")
DIR_PROCESADOS = os.path.join(BASE_DIR, "academia", "procesados")
DIR_INDICE = os.path.join(BASE_DIR, "academia", "indice")
DIR_ESTADO = os.path.join(BASE_DIR, "academia", "estado")
RUTA_DB = os.path.join(DIR_ESTADO, "academia_estado.json")
RUTA_VECTORES = os.path.join(DIR_INDICE, "vectores.npy")
RUTA_META = os.path.join(DIR_INDICE, "metadatos.json")
RUTA_INFO = os.path.join(DIR_INDICE, "indice_info.json")

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
MODELO_EMBEDDING = "nomic-embed-text" # Fallback a nomic o mxbai

class AcademiaZeroX:
    def __init__(self):
        self.vectors = None
        self.metadata = []
        self.indice_info = {}
        self.lock = threading.Lock()
        self.running = False
        
        # Crear directorios si no existen
        for d in [DIR_FUENTES, DIR_PROCESADOS, DIR_INDICE, DIR_ESTADO]:
            os.makedirs(d, exist_ok=True)
            
        self.cargar_indice()
        
        # Inicializar Embedder unificado (usa logica blindada de ingesta_conocimiento_total)
        prov = str((self.indice_info or {}).get("embedding_provider") or "").upper()
        mod = (self.indice_info or {}).get("embedding_model")
        
        if prov == "SENTENCE_TRANSFORMERS" and mod:
            self.embedder = ingesta_conocimiento_total.Embedder(prefer_ollama=False, modelo_st=str(mod))
        elif prov == "OLLAMA" and mod:
            self.embedder = ingesta_conocimiento_total.Embedder(prefer_ollama=True, modelo_ollama=str(mod))
        else:
            self.embedder = ingesta_conocimiento_total.Embedder()  # Autodetectar

    def cargar_indice(self):
        with self.lock:
            if os.path.exists(RUTA_VECTORES) and os.path.exists(RUTA_META):
                try:
                    self.vectors = np.load(RUTA_VECTORES)
                    with open(RUTA_META, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                    try:
                        if os.path.exists(RUTA_INFO):
                            with open(RUTA_INFO, "r", encoding="utf-8") as f:
                                self.indice_info = json.load(f) or {}
                    except Exception:
                        self.indice_info = {}
                    print(f"ACADEMIA: Índice cargado. {len(self.metadata)} chunks.")
                except Exception as e:
                    print(f"⚠️ Error cargando índice Academia: {e}")
                    self.vectors = None
                    self.metadata = []
                    self.indice_info = {}
            else:
                print("ACADEMIA: Índice vacío/nuevo.")
                self.indice_info = {}

    def guardar_indice(self):
        with self.lock:
            if self.vectors is not None:
                np.save(RUTA_VECTORES, self.vectors)
                with open(RUTA_META, "w", encoding="utf-8") as f:
                    json.dump(self.metadata, f)
                
                # Actualizar estado global
                estado = {
                    "chunks_totales": len(self.metadata),
                    "ultima_actualizacion": datetime.now().isoformat(),
                    "docs_procesados": len(set(m['fuente'] for m in self.metadata))
                }
                with open(RUTA_DB, "w") as f:
                    json.dump(estado, f)

    def get_embedding(self, texto):
        try:
            # Delegar al embedder centralizado
            return self.embedder.embed(texto)
        except Exception as e:
            # Fallback de emergencia si embedder no está listo
            try:
                emb_temp = ingesta_conocimiento_total.Embedder(prefer_ollama=True)
                return emb_temp.embed(texto)
            except:
                return None

    def procesar_texto(self, texto, fuente):
        # Chunking simple (overlap)
        CHUNK_SIZE = 500
        OVERLAP = 50
        chunks = []
        
        palabras = texto.split()
        for i in range(0, len(palabras), CHUNK_SIZE - OVERLAP):
            chunk = " ".join(palabras[i:i+CHUNK_SIZE])
            if len(chunk) > 50:
                chunks.append(chunk)
                
        print(f"📄 {fuente}: Generados {len(chunks)} chunks.")
        
        nuevos_vecs = []
        nuevos_meta = []
        
        for i, chunk in enumerate(chunks):
            emb = self.get_embedding(chunk)
            if emb:
                nuevos_vecs.append(emb)
                nuevos_meta.append({
                    "texto": chunk,
                    "fuente": fuente,
                    "chunk_id": i,
                    "fecha": datetime.now().isoformat()
                })
        
        if nuevos_vecs:
            with self.lock:
                matriz_nueva = np.array(nuevos_vecs, dtype='float32')
                if self.vectors is None:
                    self.vectors = matriz_nueva
                else:
                    self.vectors = np.vstack([self.vectors, matriz_nueva])
                self.metadata.extend(nuevos_meta)
            self.guardar_indice()

    def ingesta_automatica(self):
        """
        Ingesta profesional incremental:
        - Escanea `conocimiento/` (root del proyecto) y `inteligencia/academia/fuentes/`.
        - Chunking real con solape.
        - Embeddings locales (Ollama si existe; fallback SentenceTransformers).
        """
        try:
            res = ingesta_conocimiento_total.ingestar_conocimiento_total(
                chunk_tokens=900,
                overlap_tokens=150,
                max_docs_por_ciclo=2,
                max_chunks_por_doc=300,
                rebuild=False,
            )
            if (res or {}).get("docs_procesados", 0) > 0:
                # Recargar índice en memoria para reflejar nuevos chunks
                self.cargar_indice()
        except Exception as e:
            print(f"⚠️ Error en ingesta profesional: {e}")

    def buscar(self, query, k=5):
        emb_q = self.get_embedding(query)
        if not emb_q or self.vectors is None:
            return []

        vec_q = np.array(emb_q, dtype='float32')

        # Cosine Similarity: (A . B) / (|A| * |B|)
        norm_q = np.linalg.norm(vec_q)
        norm_v = np.linalg.norm(self.vectors, axis=1)

        dot_prod = np.dot(self.vectors, vec_q)
        sims = dot_prod / (norm_v * norm_q + 1e-10)

        # --- Pesos por calidad de fuente ---
        pesos_por_dominio = {}
        try:
            ruta_pesos = os.path.abspath(os.path.join(BASE_DIR, "..", "conocimiento", "fuentes_calidad.json"))
            if os.path.exists(ruta_pesos):
                with open(ruta_pesos, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for it in data:
                        if not isinstance(it, dict):
                            continue
                        url = str(it.get("url") or "").strip()
                        try:
                            peso = float(it.get("peso", 1.0))
                        except Exception:
                            peso = 1.0
                        if not url:
                            continue
                        u = urlparse(url if "://" in url else ("https://" + url))
                        dom = (u.netloc or "").lower()
                        if dom:
                            pesos_por_dominio[dom] = max(pesos_por_dominio.get(dom, 0.0), float(peso))
        except Exception:
            pesos_por_dominio = {}

        def _extraer_source_url(texto: str) -> str:
            try:
                m = re.search(r">>>\\s*FUENTE:\\s*(\\S+)", texto or "", flags=re.IGNORECASE)
                if m:
                    return str(m.group(1)).strip()
            except Exception:
                pass
            return ""

        def _peso_fuente(meta: dict) -> float:
            try:
                source_url = str(meta.get("source_url") or "").strip()
            except Exception:
                source_url = ""
            if not source_url:
                source_url = _extraer_source_url(str(meta.get("texto") or ""))
            if not source_url:
                return 0.6  # desconocida => peso conservador

            try:
                u = urlparse(source_url if "://" in source_url else ("https://" + source_url))
                dom = (u.netloc or "").lower()
            except Exception:
                dom = ""

            if dom and dom in pesos_por_dominio:
                return float(pesos_por_dominio[dom])
            return 0.7  # web no catalogada => peso medio

        # Seleccionar mÁs candidatos para reordenar con score ponderado
        try:
            k = int(k)
        except Exception:
            k = 5
        k = max(1, min(20, k))
        top_n = min(len(sims), max(k * 5, 30))
        indices = np.argsort(sims)[::-1][:top_n]

        candidatos = []
        for idx in indices:
            try:
                meta = self.metadata[idx] if isinstance(self.metadata, list) and idx < len(self.metadata) else {}
                texto = str((meta or {}).get("texto") or "")
                fuente = str((meta or {}).get("fuente") or "")
                fecha = str((meta or {}).get("fecha") or "")
                ruta_rel = (meta or {}).get("ruta_relativa")

                source_url = str((meta or {}).get("source_url") or "").strip()
                if not source_url:
                    source_url = _extraer_source_url(texto)

                peso = _peso_fuente(meta or {})
                score_raw = float(sims[idx])
                score_pond = float(score_raw * peso)

                candidatos.append({
                    "texto": texto,
                    "fuente": fuente,
                    "score": score_raw,
                    "peso_fuente": float(round(peso, 3)),
                    "score_ponderado": float(round(score_pond, 6)),
                    "cita": {
                        "source_url": source_url or None,
                        "titulo": fuente or None,
                        "fecha": fecha or None,
                        "ruta_relativa": str(ruta_rel) if ruta_rel else None,
                    },
                })
            except Exception:
                continue

        candidatos.sort(key=lambda x: float(x.get("score_ponderado", 0.0)), reverse=True)
        return candidatos[:k]

    def bucle_aprendizaje(self):
        """Hilo de fondo"""
        print("ACADEMIA: Loop de aprendizaje iniciado.")
        self.running = True
        backoff_s = 600  # 10 min base
        while self.running:
            try:
                self.ingesta_automatica()
            except Exception as e:
                print(f"ACADEMIA: error en ingesta: {e} | Reintento en {backoff_s}s")
                backoff_s = min(int(backoff_s * 2), 3600)  # cap 60m
            else:
                backoff_s = 600  # reset tras éxito
             
            # Dormir 10 min
            time.sleep(backoff_s)

if __name__ == "__main__":
    # Test manual
    aca = AcademiaZeroX()
    aca.ingesta_automatica()
    res = aca.buscar("trading psicologia")
    for r in res:
        print(f"[{r['score']:.2f}] {r['texto'][:100]}...")
