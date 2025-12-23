import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

import extractor_epub
import extractor_pdf


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROYECTO_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Forzar salida UTF-8 (evita crash de Windows con caracteres no ASCII)
try:
    if getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DIR_CONOCIMIENTO = os.path.join(PROYECTO_DIR, "conocimiento")
DIR_FUENTES_ACADEMIA = os.path.join(BASE_DIR, "academia", "fuentes")
DIR_INDICE = os.path.join(BASE_DIR, "academia", "indice")
DIR_ESTADO = os.path.join(BASE_DIR, "academia", "estado")

RUTA_VECTORES = os.path.join(DIR_INDICE, "vectores.npy")
RUTA_META = os.path.join(DIR_INDICE, "metadatos.json")
RUTA_INFO = os.path.join(DIR_INDICE, "indice_info.json")
RUTA_DB = os.path.join(DIR_ESTADO, "academia_estado.json")


def _asegurar_dirs():
    for d in (DIR_FUENTES_ACADEMIA, DIR_INDICE, DIR_ESTADO):
        os.makedirs(d, exist_ok=True)


def _hash_archivo(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.replace("\x00", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _extraer_texto(path: str) -> Optional[str]:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".txt", ".md"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return _limpiar_texto(f.read())
        if ext == ".pdf":
            return _limpiar_texto(extractor_pdf.extraer_texto_pdf(path) or "")
        if ext == ".epub":
            return _limpiar_texto(extractor_epub.extraer_texto_epub(path) or "")
    except Exception:
        return None
    return None


def _chunk_por_palabras(texto: str, chunk_tokens: int = 900, overlap: int = 150, min_chars: int = 200) -> List[str]:
    """
    Chunking aproximado por "tokens" (palabras). Objetivo: 700–1200 tokens con solape.
    """
    try:
        chunk_tokens = int(chunk_tokens)
        overlap = int(overlap)
    except Exception:
        chunk_tokens = 900
        overlap = 150

    chunk_tokens = max(300, min(1500, chunk_tokens))
    overlap = max(0, min(chunk_tokens - 1, overlap))

    palabras = (texto or "").split()
    if len(palabras) < 50:
        return []

    paso = max(1, chunk_tokens - overlap)
    chunks = []
    for i in range(0, len(palabras), paso):
        chunk = " ".join(palabras[i : i + chunk_tokens]).strip()
        if len(chunk) >= min_chars:
            chunks.append(chunk)
    return chunks


@dataclass
class InfoIndice:
    embedding_provider: str  # "OLLAMA" | "SENTENCE_TRANSFORMERS"
    embedding_model: str
    embedding_dim: int
    chunk_tokens: int
    overlap_tokens: int
    docs_indexados: Dict[str, Any]


class Embedder:
    """
    Embeddings locales:
    - Preferencia: Ollama (nomic-embed-text) si está disponible.
    - Fallback: SentenceTransformer (all-MiniLM-L6-v2).
    """

    def __init__(self, prefer_ollama: bool = True, modelo_ollama: str = "nomic-embed-text", modelo_st: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.provider = None
        self.model = None
        self._st_model = None
        self._ollama_url = "http://localhost:11434/api/embeddings"
        self._ollama_model = modelo_ollama
        self._st_name = modelo_st

        if prefer_ollama and self._probar_ollama():
            self.provider = "OLLAMA"
            self.model = self._ollama_model
            return

        # Verificar si hay modelo local descargado de forma segura
        ruta_modelo_local = os.path.join(os.path.dirname(__file__), "modelos", "minilm_local")
        if os.path.exists(ruta_modelo_local) and "config.json" in os.listdir(ruta_modelo_local):
            abs_path = os.path.abspath(ruta_modelo_local).replace(os.sep, '/')
            print(f"ACADEMIA: Usando modelo local blindado desde {abs_path}")
            self.model = abs_path
            self._st_name = abs_path
        else:
            self.provider = "SENTENCE_TRANSFORMERS"
            self.model = self._st_name

    def _probar_ollama(self) -> bool:
        try:
            import requests

            r = requests.post(self._ollama_url, json={"model": self._ollama_model, "prompt": "test"}, timeout=2)
            if r.status_code == 200 and isinstance(r.json().get("embedding"), list):
                return True
        except Exception:
            return False
        return False

    def _cargar_st(self):
        if self._st_model is not None:
            return
        
        from sentence_transformers import SentenceTransformer
        # Intentar carga normal (o desde cache local si existe)
        print(f"ACADEMIA: Cargando embeddings desde: {self._st_name}")
        if os.path.exists(self._st_name):
             print("ACADEMIA: (Ruta verificada existe)")
        self._st_model = SentenceTransformer(self._st_name)

    def embedding_dim(self) -> int:
        v = self.embed("dimension_test")
        return len(v) if isinstance(v, list) else 0

    def embed(self, texto: str) -> List[float]:
        if self.provider == "OLLAMA":
            try:
                import requests

                r = requests.post(self._ollama_url, json={"model": self._ollama_model, "prompt": texto}, timeout=30)
                if r.status_code == 200:
                    emb = r.json().get("embedding")
                    if isinstance(emb, list) and len(emb) > 0:
                        return emb
            except Exception:
                return []
            return []

        self._cargar_st()
        try:
            emb = self._st_model.encode([texto], convert_to_tensor=False)[0]
            return emb.tolist() if hasattr(emb, "tolist") else list(emb)
        except Exception:
            return []

    def embed_batch(self, textos: List[str], batch_size: int = 16) -> List[List[float]]:
        if not textos:
            return []
        if self.provider == "OLLAMA":
            return [self.embed(t) for t in textos]

        self._cargar_st()
        out: List[List[float]] = []
        for i in range(0, len(textos), batch_size):
            lote = textos[i : i + batch_size]
            emb = self._st_model.encode(lote, convert_to_tensor=False)
            for v in emb:
                out.append(v.tolist() if hasattr(v, "tolist") else list(v))
        return out


def _cargar_indice_actual() -> Tuple[Optional[np.ndarray], List[Dict[str, Any]], Dict[str, Any]]:
    vectors = None
    meta: List[Dict[str, Any]] = []
    info: Dict[str, Any] = {}
    try:
        if os.path.exists(RUTA_VECTORES) and os.path.exists(RUTA_META):
            vectors = np.load(RUTA_VECTORES)
            with open(RUTA_META, "r", encoding="utf-8") as f:
                meta = json.load(f) or []
            if not isinstance(meta, list):
                meta = []
        if os.path.exists(RUTA_INFO):
            with open(RUTA_INFO, "r", encoding="utf-8") as f:
                info = json.load(f) or {}
            if not isinstance(info, dict):
                info = {}
    except Exception:
        vectors = None
        meta = []
        info = {}
    return vectors, meta, info


def _guardar_indice(vectors: np.ndarray, meta: List[Dict[str, Any]], info: Dict[str, Any]):
    """Guarda vectores, meta e info en disco. Sanitiza texto para evitar errores de codificación."""
    def _sanitize_text(s: str) -> str:
        if not isinstance(s, str):
            return s
        # Reemplaza caracteres inválidos por el caracter � para que json dump no falle
        try:
            return s.encode('utf-8', 'replace').decode('utf-8')
        except Exception:
            return ''.join([c if ord(c) < 0xDC00 or ord(c) > 0xDFFF else '\uFFFD' for c in s])

    def _sanitize_obj(o):
        if isinstance(o, dict):
            return {k: _sanitize_obj(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_sanitize_obj(v) for v in o]
        if isinstance(o, str):
            return _sanitize_text(o)
        return o

    _asegurar_dirs()
    np.save(RUTA_VECTORES, vectors.astype("float32"))

    sanitized_meta = _sanitize_obj(meta)
    sanitized_info = _sanitize_obj(info)

    with open(RUTA_META, "w", encoding="utf-8") as f:
        json.dump(sanitized_meta, f, ensure_ascii=False)
    with open(RUTA_INFO, "w", encoding="utf-8") as f:
        json.dump(sanitized_info, f, indent=2, ensure_ascii=False)
    try:
        estado = {
            "chunks_totales": int(len(sanitized_meta)),
            "docs_procesados": int((sanitized_info or {}).get("docs_totales") or 0),
            "ultima_actualizacion": (sanitized_info or {}).get("ultima_actualizacion") or datetime.now().isoformat(),
        }
        with open(RUTA_DB, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False)
    except Exception:
        pass


def _iter_documentos(directorio: str) -> Iterable[str]:
    if not directorio or not os.path.exists(directorio):
        return []
    for root, _, files in os.walk(directorio):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in (".txt", ".md", ".pdf", ".epub"):
                yield os.path.join(root, name)


def ingestar_conocimiento_total(
    chunk_tokens: int = 900,
    overlap_tokens: int = 150,
    max_docs_por_ciclo: int = 2,
    max_chunks_por_doc: int = 300,
    rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Ingesta incremental para evitar bloquear el bot:
    - Procesa hasta `max_docs_por_ciclo` documentos por llamada.
    - Cap por doc para evitar explotar la RAM en una sola tanda.
    """
    _asegurar_dirs()

    vectors, meta, info_prev = _cargar_indice_actual()

    # Elegir embedder: si hay info previa, respetarla; si no, autodetectar.
    provider_prev = (info_prev.get("embedding_provider") or "").upper() if isinstance(info_prev, dict) else ""
    model_prev = info_prev.get("embedding_model") if isinstance(info_prev, dict) else None
    embedder = Embedder(prefer_ollama=(provider_prev != "SENTENCE_TRANSFORMERS"))

    if provider_prev in ("OLLAMA", "SENTENCE_TRANSFORMERS") and model_prev:
        # Si el índice ya existe, intentamos respetar el proveedor/modelo que indica.
        if provider_prev == "SENTENCE_TRANSFORMERS":
            embedder = Embedder(prefer_ollama=False, modelo_st=str(model_prev))
        elif provider_prev == "OLLAMA":
            embedder = Embedder(prefer_ollama=True, modelo_ollama=str(model_prev))

    emb_dim = embedder.embedding_dim()

    if rebuild or vectors is None or (isinstance(vectors, np.ndarray) and vectors.ndim != 2):
        vectors = None
        meta = []
        info_prev = {}

    if vectors is not None and isinstance(vectors, np.ndarray) and vectors.shape[1] != emb_dim:
        print(f"ACADEMIA: Rebuild forzado por cambio de embeddings ({vectors.shape[1]} -> {emb_dim}).")
        vectors = None
        meta = []
        info_prev = {}

    if vectors is None:
        vectors = np.zeros((0, emb_dim), dtype="float32")

    docs_indexados = (info_prev.get("docs_indexados") or {}) if isinstance(info_prev, dict) else {}
    if not isinstance(docs_indexados, dict):
        docs_indexados = {}

    # Listado de documentos: conocimiento/ + academia/fuentes
    docs = list(_iter_documentos(DIR_CONOCIMIENTO)) + list(_iter_documentos(DIR_FUENTES_ACADEMIA))

    procesados = 0
    chunks_nuevos = 0
    docs_nuevos = 0

    for path in docs:
        if procesados >= int(max_docs_por_ciclo):
            break

        try:
            h = _hash_archivo(path)
        except Exception:
            continue

        key = os.path.relpath(path, PROYECTO_DIR)
        if isinstance(docs_indexados.get(key), dict) and docs_indexados[key].get("hash") == h:
            continue

        texto = _extraer_texto(path)
        if not texto or len(texto) < 500:
            continue

        chunks = _chunk_por_palabras(texto, chunk_tokens=chunk_tokens, overlap=overlap_tokens, min_chars=200)
        if not chunks:
            continue

        if len(chunks) > int(max_chunks_por_doc):
            chunks = chunks[: int(max_chunks_por_doc)]

        print(f"ACADEMIA: Indexando {key} -> {len(chunks)} chunks (provider={embedder.provider}).")

        embeddings = embedder.embed_batch(chunks, batch_size=16)
        vecs = []
        meta_add: List[Dict[str, Any]] = []
        now = datetime.now().isoformat()

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            if not isinstance(emb, list) or len(emb) != emb_dim:
                continue
            vecs.append(emb)
            meta_add.append(
                {
                    "texto": chunk,
                    "fuente": os.path.basename(path),
                    "ruta_relativa": key,
                    "doc_hash": h,
                    "chunk_id": i,
                    "fecha": now,
                }
            )

        if not vecs:
            continue

        matriz = np.array(vecs, dtype="float32")
        vectors = np.vstack([vectors, matriz])
        meta.extend(meta_add)

        docs_indexados[key] = {"hash": h, "chunks": len(meta_add), "fecha": now}
        procesados += 1
        docs_nuevos += 1
        chunks_nuevos += len(meta_add)

        # Guardado incremental (resistente a cortes)
        info = {
            "version": "v3",
            "embedding_provider": embedder.provider,
            "embedding_model": embedder.model,
            "embedding_dim": emb_dim,
            "chunk_tokens": int(chunk_tokens),
            "overlap_tokens": int(overlap_tokens),
            "docs_indexados": docs_indexados,
            "chunks_totales": int(len(meta)),
            "docs_totales": int(len(docs_indexados)),
            "ultima_actualizacion": now,
        }
        _guardar_indice(vectors, meta, info)

    return {
        "docs_procesados": procesados,
        "docs_nuevos": docs_nuevos,
        "chunks_nuevos": chunks_nuevos,
        "chunks_totales": int(len(meta)),
    }


if __name__ == "__main__":
    # Ejecución manual: intenta avanzar el índice por tandas.
    _asegurar_dirs()
    print("ACADEMIA: Ingesta profesional iniciada (modo manual).")
    res = ingestar_conocimiento_total(chunk_tokens=900, overlap_tokens=150, max_docs_por_ciclo=10, max_chunks_por_doc=500, rebuild=False)
    print(f"ACADEMIA: Ingesta completada: {json.dumps(res, ensure_ascii=False)}")
