import os
import gc
import logging
from typing import List
from config import settings

logger = logging.getLogger("insurewise.embeddings")

_local_fastembed_model = None
_local_st_model = None


def get_current_memory_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def preload_embedding_model():
    """
    Kept for backward compatibility.
    Models are loaded lazily on first actual inference call to ensure
    Uvicorn binds to port $PORT immediately at startup without exceeding
    Render's 512 MiB memory budget.
    """
    logger.info("Embedding model will be loaded on demand (lazy loading enabled for memory safety).")


def get_embeddings(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    provider = getattr(settings, "EMBEDDING_PROVIDER", "local").lower()
    llm_provider = getattr(settings, "LLM_PROVIDER", "").lower()

    if llm_provider == "anthropic" and provider != "local":
        provider = "local"

    batch_size = getattr(settings, "BATCH_SIZE", 32)

    # 1. OpenAI remote embeddings (0 MB local model memory)
    if provider == "openai":
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
                    import time
                    time.sleep(2 ** attempt)
        return all_embeddings

    # 2. Local embeddings: Use FastEmbed (ONNX) first to strictly keep memory under 512MB
    global _local_fastembed_model, _local_st_model

    # Try FastEmbed (uses ONNX Runtime, ~238 MB memory vs 585 MB for PyTorch)
    try:
        from fastembed import TextEmbedding
        if _local_fastembed_model is None:
            logger.info(f"Initializing lightweight FastEmbed model (Current memory: {get_current_memory_mb():.1f} MB)...")
            # BAAI/bge-small-en-v1.5 has 384 dimensions matching all-MiniLM-L6-v2
            _local_fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info(f"FastEmbed model ready. Memory: {get_current_memory_mb():.1f} MB")

        embeddings_gen = _local_fastembed_model.embed(texts, batch_size=batch_size)
        results = [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings_gen]
        return results

    except Exception as e_fast:
        logger.warning(f"FastEmbed not available or failed: {e_fast}. Falling back to SentenceTransformer...")

    # Fallback to SentenceTransformer if FastEmbed is not available
    try:
        import torch
        # Restrict threads to 1 to reduce memory fragmentation
        torch.set_num_threads(1)
        from sentence_transformers import SentenceTransformer
        if _local_st_model is None:
            logger.info(f"Loading SentenceTransformer fallback (Memory: {get_current_memory_mb():.1f} MB)...")
            _local_st_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info(f"SentenceTransformer loaded. Memory: {get_current_memory_mb():.1f} MB")

        embeddings = _local_st_model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        gc.collect()
        return embeddings.tolist()

    except Exception as e_st:
        logger.error(f"All embedding providers failed: {e_st}")
        raise RuntimeError(f"Unable to generate embeddings: {e_st}")


def get_embedding(text: str) -> List[float]:
    res = get_embeddings([text])
    return res[0] if res else []
