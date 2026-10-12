import os
import time
from typing import List
from config import settings

_local_model = None

def preload_embedding_model():
    """Preloads the local sentence transformer model once at startup."""
    global _local_model
    provider = getattr(settings, "EMBEDDING_PROVIDER", "local")
    if provider == "local" and _local_model is None:
        try:
            print("Preloading local SentenceTransformer embedding model...")
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Embedding model loaded successfully.")
        except Exception as e:
            print(f"Warning: Failed to preload SentenceTransformer: {e}")

def get_embeddings(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
        
    provider = getattr(settings, "EMBEDDING_PROVIDER", "local")
    llm_provider = getattr(settings, "LLM_PROVIDER", "")
    
    if llm_provider == "anthropic" and provider != "local":
        provider = "local"
        
    batch_size = getattr(settings, "BATCH_SIZE", 32)
        
    if provider == "local":
        global _local_model
        if _local_model is None:
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = _local_model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return embeddings.tolist()
    elif provider == "openai":
        import openai
        client = openai.OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", ""))
        retries = 3
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for attempt in range(retries):
                try:
                    response = client.embeddings.create(
                        input=batch,
                        model=getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                    )
                    all_embeddings.extend([d.embedding for d in response.data])
                    break
                except Exception as e:
                    if attempt == retries - 1:
                        raise e
                    time.sleep(2 ** attempt)
        return all_embeddings
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")

def get_embedding(text: str) -> List[float]:
    res = get_embeddings([text])
    return res[0] if res else []
