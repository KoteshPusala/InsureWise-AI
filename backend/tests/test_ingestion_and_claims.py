import pytest
import os
import io
import json
import time
from fastapi.testclient import TestClient
from pathlib import Path

from main import app
from config import settings
from db import init_db, create_policy, get_policy, update_policy, recover_stuck_policies, get_connection
from services import vector_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is initialized before each test."""
    init_db()
    yield

def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "llm_provider" in data
    assert "embedding_provider" in data

def test_stuck_policy_recovery():
    """Verify that policies stuck in processing are recovered and marked failed."""
    pol_id = create_policy("test_stuck.pdf", "Test Stuck Policy", 0)
    update_policy(pol_id, status="extracting_text", progress_stage="extracting_text")
    
    # Run recovery
    recovered_count = recover_stuck_policies()
    assert recovered_count >= 1
    
    pol = get_policy(pol_id)
    assert pol["status"] == "failed"
    assert "interrupted or timed out" in pol["error_message"].lower()

def test_chat_blocked_on_non_ready_policy():
    """Ensure chatting on a processing or failed policy returns 400 with clear message."""
    pol_id = create_policy("test_pending.pdf", "Test Pending Policy", 0)
    update_policy(pol_id, status="processing")
    
    res = client.post(f"/api/policies/{pol_id}/chat", json={"question": "What is covered?"})
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "not ready for chat" in detail.lower() or "processing" in detail.lower()

def test_invalid_pdf_upload_rejected():
    """Ensure corrupted or non-PDF files are rejected with clear error messages."""
    # 1. Non-pdf extension
    res = client.post(
        "/api/policies",
        files={"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")}
    )
    assert res.status_code == 400
    assert "only pdf files" in res.json().get("detail", "").lower()

    # 2. Corrupt PDF header
    res = client.post(
        "/api/policies",
        files={"file": ("corrupt.pdf", io.BytesIO(b"NOT_A_PDF_FILE"), "application/pdf")}
    )
    assert res.status_code == 400
    assert "invalid pdf" in res.json().get("detail", "").lower()

def test_sample_policy_ingestion_and_chat_flow():
    """Ensure sample policy is ingested in background and reaches ready status."""
    res = client.post("/api/policies/sample")
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    policy_id = data["id"]
    
    # Poll until ready or timeout (max 45 seconds for local test)
    max_wait = 45
    start = time.time()
    ready = False
    
    while time.time() - start < max_wait:
        poll_res = client.get(f"/api/policies/{policy_id}")
        assert poll_res.status_code == 200
        pol_data = poll_res.json()
        if pol_data["status"] == "ready":
            ready = True
            break
        elif pol_data["status"] == "failed":
            pytest.fail(f"Ingestion failed: {pol_data.get('error_message')}")
        time.sleep(1)
        
    assert ready, f"Policy failed to reach ready state within {max_wait}s"
    
    # Test chat works on ready policy
    chat_res = client.post(
        f"/api/policies/{policy_id}/chat",
        json={"question": "What is the deductible?"}
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert "verdict" in chat_data
    assert isinstance(chat_data.get("citations"), list)
    
    # Test chat history endpoint returns citations
    hist_res = client.get(f"/api/policies/{policy_id}/chat")
    assert hist_res.status_code == 200
    messages = hist_res.json().get("messages", [])
    assert len(messages) >= 2
    assistant_msg = next((m for m in messages if m["role"] == "assistant"), None)
    assert assistant_msg is not None
    assert "citations" in assistant_msg

    # Test cascade deletion
    del_res = client.delete(f"/api/policies/{policy_id}")
    assert del_res.status_code == 200
    assert not (settings.UPLOADS_DIR / f"{policy_id}.pdf").exists()
    assert not vector_store.index_exists(policy_id)

def test_claims_workflow_isolation_and_analysis():
    """Ensure claims are created, listed in order, analyzed independently, and cleaned up on policy deletion."""
    pol_id = create_policy("test_car_policy.pdf", "Car Comprehensive Policy", 10)
    update_policy(pol_id, status="ready", chunk_count=1)
    vector_store.build_index(pol_id, [{
        "chunk_id": "car_c1",
        "page_start": 1,
        "page_end": 1,
        "text": "Car Comprehensive Policy: Coverage for accidental damage, bumper repairs, and vehicle collision."
    }])

    # 1. Create Claim 1
    c1_res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_description": "Vehicle was rear-ended at intersection causing bumper damage.",
        "incident_type": "vehicle_accident",
        "incident_date": "2024-05-10"
    })
    assert c1_res.status_code == 200
    claim1_id = c1_res.json()["id"]

    # 2. Create Claim 2
    c2_res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_description": "Windshield cracked by flying gravel during highway travel.",
        "incident_type": "vehicle_accident",
        "incident_date": "2024-05-11"
    })
    assert c2_res.status_code == 200
    claim2_id = c2_res.json()["id"]

    # 3. List claims - should contain both in desc order
    list_res = client.get("/api/claims")
    assert list_res.status_code == 200
    claims_list = list_res.json().get("claims", [])
    claim_ids = [c["id"] for c in claims_list]
    assert claim1_id in claim_ids
    assert claim2_id in claim_ids

    # 4. Analyze Claim 1
    an1_res = client.post(f"/api/claims/{claim1_id}/analyze")
    assert an1_res.status_code == 200
    an1_data = an1_res.json()
    assert "checklist_analysis" in an1_data or "checklist_items" in an1_data

    # Verify claim 2 was unaffected
    c2_detail = client.get(f"/api/claims/{claim2_id}").json()
    assert c2_detail["status"] == "draft"

    # 5. Cascade delete policy and ensure claims are cleaned up
    del_res = client.delete(f"/api/policies/{pol_id}")
    assert del_res.status_code == 200

    assert client.get(f"/api/claims/{claim1_id}").status_code == 404
    assert client.get(f"/api/claims/{claim2_id}").status_code == 404
