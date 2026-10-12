import os
import time
import json
import uuid
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from config import settings
from db import create_policy, update_policy, get_policy, list_policies, delete_policy_cascade
from services import pdf_service, chunking, vector_store, policy_qa

logger = logging.getLogger("insurewise.policies")
router = APIRouter(prefix="/policies", tags=["policies"])

def parse_policy_row(row: dict) -> dict:
    result = dict(row)
    if "ocr_pages" in result and isinstance(result["ocr_pages"], str):
        try:
            result["ocr_pages"] = json.loads(result["ocr_pages"])
        except Exception:
            result["ocr_pages"] = []
            
    status = result.get("status", "processing")
    progress_stage = result.get("progress_stage")
    if not progress_stage:
        if status == "ready":
            progress_stage = "completed"
        elif status == "failed":
            progress_stage = "failed"
        else:
            progress_stage = "processing"
    result["progress_stage"] = progress_stage
    return result

def process_policy_ingestion(policy_id: str, file_path: str):
    """Background ingestion task that moves policy from processing to ready/failed."""
    start_total = time.time()
    logger.info(f"[{policy_id}] Starting policy ingestion: {file_path}")
    
    try:
        # Stage 1: Text extraction & OCR inspection
        t0 = time.time()
        update_policy(policy_id, status="processing", progress_stage="extracting_text")
        pdf_data = pdf_service.extract_pdf_text(file_path)
        pages = pdf_data["pages"]
        total_pages = pdf_data["total_pages"]
        ocr_pages = pdf_data["ocr_pages"]
        logger.info(f"[{policy_id}] Stage 1 (extracting_text) completed in {time.time() - t0:.2f}s, pages={total_pages}, ocr_pages={len(ocr_pages)}")
        
        # Stage 2: Chunking
        t0 = time.time()
        update_policy(policy_id, status="processing", progress_stage="chunking", page_count=total_pages)
        chunks = chunking.chunk_document(pages)
        if not chunks:
            raise ValueError("No text sections or clauses could be extracted from this document.")
        chunk_count = len(chunks)
        logger.info(f"[{policy_id}] Stage 2 (chunking) completed in {time.time() - t0:.2f}s, chunks={chunk_count}")
        
        # Stage 3: Building Vector Index
        t0 = time.time()
        update_policy(policy_id, status="processing", progress_stage="building_index", chunk_count=chunk_count)
        vector_store.build_index(policy_id, chunks)
        logger.info(f"[{policy_id}] Stage 3 (building_index) completed in {time.time() - t0:.2f}s")
        
        # Stage 4: Analyzing & Summary Generation
        t0 = time.time()
        update_policy(policy_id, status="processing", progress_stage="analyzing")
        policy_type = policy_qa.detect_policy_type(chunks)
        summary = policy_qa.generate_policy_summary(policy_id, chunks)
        logger.info(f"[{policy_id}] Stage 4 (analyzing) completed in {time.time() - t0:.2f}s, type={policy_type}")
        
        # Mark Ready
        update_policy(
            policy_id,
            status="ready",
            progress_stage="completed",
            policy_type=policy_type,
            summary=summary,
            ocr_pages=json.dumps(ocr_pages),
            error_message=""
        )
        logger.info(f"[{policy_id}] Ingestion successfully completed in {time.time() - start_total:.2f}s")
        
    except Exception as e:
        logger.error(f"[{policy_id}] Ingestion failed: {str(e)}", exc_info=True)
        update_policy(
            policy_id, 
            status="failed", 
            progress_stage="failed", 
            error_message=str(e)
        )
        try:
            vector_store.delete_index(policy_id)
        except Exception:
            pass

@router.post("", response_model=dict)
def upload_policy(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    contents = file.file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="The uploaded PDF file is empty (0 bytes).")
        
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Corrupt or invalid PDF file header.")
        
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File size exceeds limit of {settings.MAX_UPLOAD_MB} MB.")

    policy_id = create_policy(file.filename, file.filename, 0)
    
    file_path = str(settings.UPLOADS_DIR / f"{policy_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(contents)
        
    # Launch ingestion asynchronously in background
    background_tasks.add_task(process_policy_ingestion, policy_id, file_path)
    
    policy = get_policy(policy_id)
    return parse_policy_row(policy)

@router.post("/sample", response_model=dict)
def load_sample_policy(background_tasks: BackgroundTasks):
    sample_path = settings.BACKEND_DIR / "sample_data" / "sample_vehicle_policy.pdf"
    if not sample_path.exists():
        # Fallback to relative path if needed
        sample_path = Path("sample_data/sample_vehicle_policy.pdf")
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail="Sample policy PDF not found on server.")
        
    filename = "sample_vehicle_policy.pdf"
    policy_id = create_policy(filename, "Sample Vehicle Comprehensive Policy 2024", 0)
    
    dest_path = str(settings.UPLOADS_DIR / f"{policy_id}.pdf")
    shutil.copyfile(str(sample_path), dest_path)
    
    # Launch ingestion in background
    background_tasks.add_task(process_policy_ingestion, policy_id, dest_path)
    
    policy = get_policy(policy_id)
    return parse_policy_row(policy)

@router.get("", response_model=dict)
def get_policies():
    policies = list_policies()
    return {"policies": [parse_policy_row(p) for p in policies]}

@router.get("/{id}", response_model=dict)
def get_policy_by_id(id: str):
    policy = get_policy(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return parse_policy_row(policy)

@router.delete("/{id}")
def delete_policy_endpoint(id: str):
    policy = get_policy(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    delete_policy_cascade(id)
    return {"status": "success"}

@router.get("/{id}/pdf")
def get_policy_pdf(id: str):
    policy = get_policy(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    file_path = settings.UPLOADS_DIR / f"{id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
    return FileResponse(str(file_path), filename=policy["filename"], media_type="application/pdf")
