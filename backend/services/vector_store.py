import os
import json
import shutil
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

try:
    import faiss
except ImportError:
    pass

from config import settings
from services.embeddings import get_embeddings, get_embedding

_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()

def get_lock(policy_id: str) -> threading.Lock:
    with _global_lock:
        if policy_id not in _locks:
            _locks[policy_id] = threading.Lock()
        return _locks[policy_id]

def get_index_dir(policy_id: str) -> Path:
    path = settings.INDEXES_DIR / policy_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def build_index(policy_id: str, chunks: List[Dict[str, Any]]) -> None:
    if not chunks:
        raise ValueError("Cannot build index for empty document chunks.")
        
    with get_lock(policy_id):
        texts = [chunk["text"] for chunk in chunks]
        embeddings = get_embeddings(texts)
        embeddings_np = np.array(embeddings, dtype=np.float32)
        
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings_np)
        
        index_dir = get_index_dir(policy_id)
        faiss.write_index(index, str(index_dir / "index.faiss"))
        
        with open(index_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False)

def search(policy_id: str, query: str, top_k: int = 6, threshold: float = 0.3) -> List[Dict[str, Any]]:
    if not index_exists(policy_id):
        return []
        
    with get_lock(policy_id):
        index_dir = settings.INDEXES_DIR / policy_id
        faiss_file = index_dir / "index.faiss"
        meta_file = index_dir / "metadata.json"
        
        if not faiss_file.exists() or not meta_file.exists():
            return []
            
        index = faiss.read_index(str(faiss_file))
        
        with open(meta_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
            
        query_embedding = get_embedding(query)
        if not query_embedding:
            return []
            
        query_np = np.array([query_embedding], dtype=np.float32)
        
        distances, indices = index.search(query_np, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(chunks):
                similarity = 1.0 / (1.0 + float(dist))
                if similarity >= threshold:
                    chunk_data = chunks[idx].copy()
                    chunk_data["similarity"] = similarity
                    results.append(chunk_data)
                    
        return results

def delete_index(policy_id: str) -> None:
    with get_lock(policy_id):
        index_dir = settings.INDEXES_DIR / policy_id
        if index_dir.exists():
            shutil.rmtree(index_dir, ignore_errors=True)

def index_exists(policy_id: str) -> bool:
    index_dir = settings.INDEXES_DIR / policy_id
    return (index_dir / "index.faiss").exists() and (index_dir / "metadata.json").exists()

def get_policy_chunks(policy_id: str) -> List[Dict[str, Any]]:
    index_dir = settings.INDEXES_DIR / policy_id
    meta_file = index_dir / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

