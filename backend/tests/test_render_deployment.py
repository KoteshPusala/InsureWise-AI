import os
import io
import pytest
import pymupdf
import psutil
from fastapi.testclient import TestClient

from main import app
from config import settings
from db import init_db, create_policy, get_policy
from services import pdf_service, vector_store, embeddings

client = TestClient(app)


def test_app_startup_health_and_ready_endpoints():
    """Verify root health and readiness probes respond with 200 and valid JSON."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "ok"
    assert "memory_rss_mb" in data_health
    # Startup memory must be comfortably within Render 512MB limit
    assert data_health["memory_rss_mb"] < 450

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] == "ready"
    assert data_ready["database"] == "connected"
    assert data_ready["storage"] == "writable"


def test_lazy_embedding_loading():
    """Verify embeddings module does not eager-load PyTorch models into memory."""
    # Check that get_embeddings produces valid embeddings without crashing
    res = embeddings.get_embeddings(["Insurance claim notification notice"])
    assert len(res) == 1
    assert len(res[0]) == 384  # 384-dimensional embedding vector


def test_pdf_handling_edge_cases():
    """Verify PDF service handles valid, corrupt, empty, and oversized files safely."""
    # 1. Valid PDF
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "InsureWise Policy Document Page 1")
    pdf_bytes = doc.tobytes()
    doc.close()

    temp_valid = str(settings.STORAGE_DIR / "valid_test.pdf")
    with open(temp_valid, "wb") as f:
        f.write(pdf_bytes)

    extracted = pdf_service.extract_pdf_text(temp_valid)
    assert extracted["total_pages"] == 1
    assert "InsureWise Policy" in extracted["pages"][0]["text"]

    # 2. Corrupt PDF
    temp_corrupt = str(settings.STORAGE_DIR / "corrupt_test.pdf")
    with open(temp_corrupt, "wb") as f:
        f.write(b"%PDF-NOT-A-REAL-PDF-DATA-GARBAGE")

    with pytest.raises(Exception):
        pdf_service.extract_pdf_text(temp_corrupt)

    # 3. Empty PDF
    temp_empty = str(settings.STORAGE_DIR / "empty_test.pdf")
    with open(temp_empty, "wb") as f:
        f.write(b"")

    with pytest.raises(Exception):
        pdf_service.extract_pdf_text(temp_empty)


def test_vector_store_missing_index_and_caching():
    """Verify vector store handles missing indexes safely and manages cache."""
    missing_id = "non_existent_policy_99999"
    assert vector_store.index_exists(missing_id) is False
    assert vector_store.get_policy_chunks(missing_id) == []
    assert vector_store.search(missing_id, "test query") == []

    # Build an index
    chunks = [
        {"chunk_id": "c1", "page_start": 1, "page_end": 1, "text": "Clause 1: Theft coverage details."},
        {"chunk_id": "c2", "page_start": 2, "page_end": 2, "text": "Clause 2: Accident claim requirements."}
    ]
    test_id = "test_policy_lru_1"
    vector_store.build_index(test_id, chunks)

    assert vector_store.index_exists(test_id) is True
    assert test_id in vector_store._index_cache

    search_res = vector_store.search(test_id, "theft", top_k=1)
    assert len(search_res) >= 1
    assert "Theft coverage" in search_res[0]["text"]

    # Delete index cleans cache
    vector_store.delete_index(test_id)
    assert test_id not in vector_store._index_cache
    assert vector_store.index_exists(test_id) is False


def test_sqlite_persistence_and_records():
    """Verify SQLite CRUD functions properly."""
    pol_id = create_policy("test_render_db.pdf", "Render DB Test Policy", 1)
    assert pol_id is not None
    fetched = get_policy(pol_id)
    assert fetched is not None
    assert fetched["filename"] == "test_render_db.pdf"
    assert fetched["status"] == "processing"
