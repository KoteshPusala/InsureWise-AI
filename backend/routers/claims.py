import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from config import settings
import db
from schemas import (
    ClaimCreate,
    ClaimUpdate,
    ClaimResponse,
    ClaimDocumentResponse,
    DocumentReviewRequest,
    DocumentReassignRequest,
    PhysicalVerificationRequest,
    PhysicalVerificationSchedule,
    PhysicalVerificationOutcome,
    PhysicalVerificationResponse,
    AuditLogEntry,
)
from services import pdf_service, claims, report, vector_store, document_verifier

router = APIRouter(prefix="/claims", tags=["claims"])


def parse_claim_row(row: dict) -> dict:
    result = dict(row)
    for field in ["checklist_items", "documents", "incident_details"]:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except Exception:
                result[field] = [] if field in ("checklist_items", "documents") else {}
    if "report_stale" in result:
        result["report_stale"] = bool(result["report_stale"])
    if ("documents" not in result or not result["documents"]) and "id" in result:
        try:
            result["documents"] = [parse_doc_row(d) for d in db.get_claim_documents(result["id"], is_current_only=True)]
        except Exception:
            result["documents"] = []
    return result


def parse_doc_row(row: dict) -> dict:
    doc = dict(row)
    for json_field in ["classification", "extracted_data", "verification_findings", "issues"]:
        if json_field in doc and isinstance(doc[json_field], str):
            try:
                doc[json_field] = json.loads(doc[json_field])
            except Exception:
                doc[json_field] = [] if json_field == "issues" else {}
    return doc


@router.post("", response_model=dict)
def create_new_claim(claim: ClaimCreate):
    # 1. Validate policy
    policy = db.get_policy(claim.policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy["status"] != "ready" or not vector_store.index_exists(claim.policy_id):
        raise HTTPException(status_code=400, detail="Selected policy is not ready or has not been indexed yet")

    # 2. Validate incident description
    desc_clean = claim.incident_description.strip()
    if len(desc_clean) < 20:
        raise HTTPException(status_code=400, detail="Incident description must be at least 20 characters")
    if len(desc_clean) > 5000:
        raise HTTPException(status_code=400, detail="Incident description cannot exceed 5000 characters")

    # 3. Validate incident date (cannot be in the future)
    if claim.incident_date:
        try:
            inc_date = datetime.strptime(claim.incident_date[:10], "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            if inc_date > today:
                raise HTTPException(status_code=400, detail="Incident date cannot be in the future")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid incident date format. Please use YYYY-MM-DD")

    claim_id = db.create_claim(
        policy_id=claim.policy_id,
        incident_description=desc_clean,
        incident_type=claim.incident_type,
        incident_date=claim.incident_date,
        claim_title=claim.claim_title or f"{claim.incident_type.replace('_', ' ').title()} Claim",
        claim_category=claim.claim_category or claim.incident_type,
        incident_details=claim.incident_details or {}
    )

    # Pre-generate personalized checklist items while keeping claim status as draft
    chk = claims.generate_checklist(claim_id, claim.policy_id, claim.incident_type, desc_clean)
    items = chk.get("checklist_items", [])
    if items:
        items = claims.extract_facts_from_incident(desc_clean, items)
        initial_score = claims.calculate_readiness_score(items)
        db.update_claim(claim_id, checklist_items=json.dumps(items), readiness_score=initial_score)

    new_claim = db.get_claim(claim_id)
    return parse_claim_row(new_claim)


@router.get("", response_model=dict)
def list_all_claims(policy_id: Optional[str] = None):
    conn = db.get_connection()
    c = conn.cursor()
    if policy_id:
        c.execute("SELECT * FROM claims WHERE policy_id = ? ORDER BY created_at DESC", (policy_id,))
    else:
        c.execute("SELECT * FROM claims ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    return {"claims": [parse_claim_row(dict(row)) for row in rows]}


@router.get("/{id}", response_model=dict)
def get_claim(id: str):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    return parse_claim_row(claim)


@router.patch("/{id}", response_model=dict)
def update_claim_details(id: str, update: ClaimUpdate):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    update_fields = {}
    if update.claim_title is not None:
        update_fields["claim_title"] = update.claim_title
    if update.incident_type is not None:
        update_fields["incident_type"] = update.incident_type
    if update.incident_date is not None:
        update_fields["incident_date"] = update.incident_date
    if update.incident_description is not None:
        update_fields["incident_description"] = update.incident_description.strip()
    if update.incident_details is not None:
        update_fields["incident_details"] = json.dumps(update.incident_details)
    if update.status is not None:
        update_fields["status"] = update.status

    if update_fields:
        db.update_claim(id, **update_fields)
        if any(k in update_fields for k in ["incident_description", "incident_type", "incident_date"]):
            claims.analyze_claim(id)

    updated_claim = db.get_claim(id)
    return parse_claim_row(updated_claim)


@router.post("/{id}/checklist/generate", response_model=dict)
def force_generate_checklist(id: str):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    res = claims.generate_checklist(
        id,
        claim["policy_id"],
        claim["incident_type"],
        claim["incident_description"]
    )
    items = res.get("checklist_items", [])
    db.update_claim(id, checklist_items=json.dumps(items))
    analysis = claims.analyze_claim(id)
    return analysis


# ---------------------------------------------------------------------------
# Per-Checklist-Item Document Upload & Management
# ---------------------------------------------------------------------------
@router.post("/{id}/checklist/{item_id}/documents", response_model=dict)
def upload_document_for_checklist_item(
    id: str,
    item_id: str,
    file: UploadFile = File(...)
):
    """Dedicated upload control for an individual checklist requirement."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported")

    # Sanitize filename against directory traversal
    sanitized_filename = os.path.basename(file.filename)
    if not sanitized_filename:
        sanitized_filename = f"document_{item_id}.pdf"

    # Read and validate contents
    contents = file.file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes)")

    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid or corrupt PDF file header")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size limit of {settings.MAX_UPLOAD_MB}MB")

    # Create document record (archives previous version of this item automatically)
    doc_id = db.create_claim_document(
        claim_id=id,
        filename=sanitized_filename,
        checklist_item_id=item_id,
        file_size=len(contents),
        status="processing"
    )

    # Save to disk
    file_path = os.path.join(str(settings.UPLOADS_DIR), f"{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(contents)

    # Find checklist item specification
    checklist_raw = claim.get("checklist_items")
    checklist = []
    if checklist_raw:
        try:
            checklist = json.loads(checklist_raw) if isinstance(checklist_raw, str) else checklist_raw
        except Exception:
            pass
    target_item = next((i for i in checklist if i.get("item_id") == item_id), {"item_id": item_id, "title": item_id.replace("_", " ").title()})

    other_docs = db.get_claim_documents(id)
    other_docs_parsed = [parse_doc_row(d) for d in other_docs if d["id"] != doc_id]

    # Run 5-stage verification pipeline
    verification_result = document_verifier.verify_claim_document_pipeline(
        doc_id=doc_id,
        file_path=file_path,
        claim=claim,
        checklist_item=target_item,
        other_documents=other_docs_parsed
    )

    # Update document in database
    db.update_claim_document(
        doc_id,
        page_count=verification_result.get("page_count", 1),
        extracted_text_preview=verification_result.get("extracted_text_preview", ""),
        doc_type_guess=verification_result.get("classification", {}).get("detected_type", "unknown"),
        status=verification_result.get("status", "ready_for_review"),
        classification=json.dumps(verification_result.get("classification", {})),
        extracted_data=json.dumps(verification_result.get("extracted_data", {})),
        verification_findings=json.dumps(verification_result.get("verification_findings", {})),
        issues=json.dumps(verification_result.get("issues", [])),
    )

    # Synchronize checklist item states and readiness
    claims.analyze_claim(id)

    updated_doc = db.get_claim_document(doc_id)
    return parse_doc_row(updated_doc)


@router.post("/{id}/documents", response_model=dict)
def upload_claim_document_general(id: str, file: UploadFile = File(...)):
    """Legacy/general upload: automatically classifies and attaches to best checklist item."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    sanitized_filename = os.path.basename(file.filename)
    if not sanitized_filename:
        sanitized_filename = "document.pdf"

    contents = file.file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes)")

    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid or corrupt PDF file header")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds limit of {settings.MAX_UPLOAD_MB}MB")

    doc_id = db.create_claim_document(
        claim_id=id,
        filename=sanitized_filename,
        checklist_item_id="",
        file_size=len(contents),
        status="processing"
    )

    file_path = os.path.join(str(settings.UPLOADS_DIR), f"{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(contents)

    # Run validation and classification
    val = document_verifier.validate_file(file_path)
    classified = document_verifier.classify_document(val.get("full_text", ""), sanitized_filename, "")
    guessed_type = classified.get("detected_type", "unknown")

    # Map to checklist item if available
    checklist = []
    if claim.get("checklist_items"):
        try:
            checklist = json.loads(claim["checklist_items"]) if isinstance(claim["checklist_items"], str) else claim["checklist_items"]
        except Exception:
            pass

    target_item = next((i for i in checklist if i.get("item_id") == guessed_type), None)
    if not target_item:
        target_item = {"item_id": guessed_type, "title": guessed_type.replace("_", " ").title()}

    other_docs = [parse_doc_row(d) for d in db.get_claim_documents(id) if d["id"] != doc_id]
    verification_result = document_verifier.verify_claim_document_pipeline(
        doc_id=doc_id,
        file_path=file_path,
        claim=claim,
        checklist_item=target_item,
        other_documents=other_docs
    )

    db.update_claim_document(
        doc_id,
        checklist_item_id=target_item.get("item_id", ""),
        page_count=verification_result.get("page_count", 1),
        extracted_text_preview=verification_result.get("extracted_text_preview", ""),
        doc_type_guess=guessed_type,
        status=verification_result.get("status", "ready_for_review"),
        classification=json.dumps(verification_result.get("classification", {})),
        extracted_data=json.dumps(verification_result.get("extracted_data", {})),
        verification_findings=json.dumps(verification_result.get("verification_findings", {})),
        issues=json.dumps(verification_result.get("issues", [])),
    )

    claims.analyze_claim(id)
    updated_doc = db.get_claim_document(doc_id)
    return parse_doc_row(updated_doc)


@router.get("/{id}/documents/{doc_id}/file")
def get_claim_document_file(id: str, doc_id: str):
    """Secure preview and download endpoint for an uploaded claim document."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    doc = db.get_claim_document(doc_id)
    if not doc or doc["claim_id"] != id:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = settings.UPLOADS_DIR / f"{doc_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    return FileResponse(
        str(file_path),
        filename=doc["filename"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'}
    )


@router.get("/{id}/documents", response_model=dict)
def list_claim_documents(id: str):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    docs = db.get_claim_documents(id, is_current_only=True)
    return {"documents": [parse_doc_row(d) for d in docs]}


@router.get("/{id}/documents/{doc_id}", response_model=dict)
def get_claim_document_detail(id: str, doc_id: str):
    doc = db.get_claim_document(doc_id)
    if not doc or doc["claim_id"] != id:
        raise HTTPException(status_code=404, detail="Document not found")

    return parse_doc_row(doc)


@router.post("/{id}/documents/{doc_id}/reassign", response_model=dict)
def reassign_document_endpoint(id: str, doc_id: str, req: DocumentReassignRequest):
    """Reassign document to another checklist item (e.g. if uploaded to wrong category)."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    doc = db.get_claim_document(doc_id)
    if not doc or doc["claim_id"] != id:
        raise HTTPException(status_code=404, detail="Document not found")

    new_item_id = req.checklist_item_id
    db.reassign_claim_document(doc_id, new_item_id)

    # Re-run verification under the new requirement
    file_path = os.path.join(str(settings.UPLOADS_DIR), f"{doc_id}.pdf")
    checklist = []
    if claim.get("checklist_items"):
        try:
            checklist = json.loads(claim["checklist_items"]) if isinstance(claim["checklist_items"], str) else claim["checklist_items"]
        except Exception:
            pass
    target_item = next((i for i in checklist if i.get("item_id") == new_item_id), {"item_id": new_item_id, "title": new_item_id.replace("_", " ").title()})

    other_docs = [parse_doc_row(d) for d in db.get_claim_documents(id) if d["id"] != doc_id]
    verification_result = document_verifier.verify_claim_document_pipeline(
        doc_id=doc_id,
        file_path=file_path,
        claim=claim,
        checklist_item=target_item,
        other_documents=other_docs
    )

    db.update_claim_document(
        doc_id,
        status=verification_result.get("status", "ready_for_review"),
        classification=json.dumps(verification_result.get("classification", {})),
        extracted_data=json.dumps(verification_result.get("extracted_data", {})),
        verification_findings=json.dumps(verification_result.get("verification_findings", {})),
        issues=json.dumps(verification_result.get("issues", [])),
    )

    claims.analyze_claim(id)
    updated_doc = db.get_claim_document(doc_id)
    return parse_doc_row(updated_doc)


@router.post("/{id}/documents/{doc_id}/replace", response_model=dict)
def replace_claim_document(
    id: str,
    doc_id: str,
    file: UploadFile = File(...)
):
    """Replace an existing uploaded document, archiving previous version."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    old_doc = db.get_claim_document(doc_id)
    if not old_doc or old_doc["claim_id"] != id:
        raise HTTPException(status_code=404, detail="Document not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    sanitized_filename = os.path.basename(file.filename)
    if not sanitized_filename:
        sanitized_filename = "replacement.pdf"

    contents = file.file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded replacement file is empty (0 bytes)")

    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid or corrupt PDF file header")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds limit of {settings.MAX_UPLOAD_MB}MB")

    # Mark old doc not current
    db.update_claim_document(doc_id, is_current=0)

    # Create new version
    item_id = old_doc.get("checklist_item_id", "")
    new_doc_id = db.create_claim_document(
        claim_id=id,
        filename=sanitized_filename,
        checklist_item_id=item_id,
        file_size=len(contents),
        status="processing"
    )

    new_file_path = os.path.join(str(settings.UPLOADS_DIR), f"{new_doc_id}.pdf")
    with open(new_file_path, "wb") as f:
        f.write(contents)

    checklist = []
    if claim.get("checklist_items"):
        try:
            checklist = json.loads(claim["checklist_items"]) if isinstance(claim["checklist_items"], str) else claim["checklist_items"]
        except Exception:
            pass
    target_item = next((i for i in checklist if i.get("item_id") == item_id), {"item_id": item_id, "title": item_id.replace("_", " ").title()})

    other_docs = [parse_doc_row(d) for d in db.get_claim_documents(id) if d["id"] != new_doc_id and d.get("is_current")]
    verification_result = document_verifier.verify_claim_document_pipeline(
        doc_id=new_doc_id,
        file_path=new_file_path,
        claim=claim,
        checklist_item=target_item,
        other_documents=other_docs
    )

    db.update_claim_document(
        new_doc_id,
        page_count=verification_result.get("page_count", 1),
        extracted_text_preview=verification_result.get("extracted_text_preview", ""),
        doc_type_guess=verification_result.get("classification", {}).get("detected_type", "unknown"),
        status=verification_result.get("status", "ready_for_review"),
        classification=json.dumps(verification_result.get("classification", {})),
        extracted_data=json.dumps(verification_result.get("extracted_data", {})),
        verification_findings=json.dumps(verification_result.get("verification_findings", {})),
        issues=json.dumps(verification_result.get("issues", [])),
    )

    db.log_audit_event(
        claim_id=id,
        document_id=new_doc_id,
        event_type="document_replaced",
        actor_name="Claimant",
        actor_role="claimant",
        details={"previous_doc_id": doc_id, "filename": sanitized_filename, "checklist_item_id": item_id}
    )

    claims.analyze_claim(id)
    updated_doc = db.get_claim_document(new_doc_id)
    return parse_doc_row(updated_doc)


@router.delete("/{id}/documents/{doc_id}")
def delete_claim_document_endpoint(id: str, doc_id: str):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    doc = db.get_claim_document(doc_id)
    if not doc or doc["claim_id"] != id:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete_claim_document(doc_id)
    claims.analyze_claim(id)
    return {"status": "success"}


# ---------------------------------------------------------------------------
# Human Review Workflow & Review Queue
# ---------------------------------------------------------------------------
@router.get("/{id}/review-queue", response_model=dict)
def get_human_review_queue(id: str):
    """Retrieve documents in review queue for this claim."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    docs = db.get_claim_documents(id, is_current_only=True)
    # Review queue items: documents that are ready_for_review, needs_attention, or already reviewed
    queue_docs = [
        parse_doc_row(d) for d in docs
        if d.get("status") in ("ready_for_review", "needs_attention", "review_in_progress", "reviewed")
    ]
    return {"queue": queue_docs}


@router.post("/{id}/documents/{doc_id}/review", response_model=dict)
def record_human_review(id: str, doc_id: str, review_req: DocumentReviewRequest):
    """Record an authorized human reviewer outcome and notes."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    doc = db.get_claim_document(doc_id)
    if not doc or doc["claim_id"] != id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Enforce reviewer role authorization: claimant cannot perform reviews
    req_role = (review_req.reviewer_role or "reviewer").strip().lower()
    if req_role == "claimant":
        raise HTTPException(
            status_code=403,
            detail="Claimants are not authorized to perform reviewer verification."
        )

    valid_outcomes = (
        "accepted", "human_verified",
        "info_required", "correction_required",
        "mismatch_confirmed", "human_rejected",
        "unable_to_verify"
    )
    if review_req.review_status not in valid_outcomes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid review outcome. Must be one of: {', '.join(valid_outcomes)}"
        )

    # Rejection or correction requires mandatory notes/reasons
    if review_req.review_status in ("info_required", "correction_required", "mismatch_confirmed", "human_rejected", "unable_to_verify"):
        if not review_req.reviewer_notes or not review_req.reviewer_notes.strip():
            raise HTTPException(
                status_code=400,
                detail="Reviewer notes and justification are mandatory when rejecting or requesting corrections for a document."
            )

    db.record_document_review(
        doc_id=doc_id,
        reviewer_name=review_req.reviewer_name.strip() or "Senior Claims Analyst",
        review_status=review_req.review_status,
        reviewer_notes=review_req.reviewer_notes or ""
    )

    claims.analyze_claim(id)
    updated_doc = db.get_claim_document(doc_id)
    return parse_doc_row(updated_doc)


# ---------------------------------------------------------------------------
# Physical Verification Workflow
# ---------------------------------------------------------------------------
@router.get("/{id}/physical-verification/eligibility", response_model=dict)
def check_physical_verification_eligibility(id: str):
    """Check whether all mandatory documents have completed online verification to allow physical verification."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    eligible, reason, summary = claims.can_request_physical_verification(id)
    pv = db.get_physical_verification(id)
    pending_items = summary.get("missing", []) + summary.get("unverified", []) + summary.get("corrections", [])
    return {
        "claim_id": id,
        "eligible": eligible,
        "is_eligible": eligible,
        "reason": reason,
        "summary": summary,
        "pending_mandatory_items": pending_items,
        "current_status": pv.get("status") if pv else "none"
    }


@router.get("/{id}/physical-verification", response_model=dict)
def get_physical_verification_endpoint(id: str):
    """Retrieve physical verification record for this claim."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    pv = db.get_physical_verification(id)
    if not pv:
        return {"status": "none"}
    return pv


@router.post("/{id}/physical-verification/request", response_model=dict)
def request_physical_verification_endpoint(id: str, req: PhysicalVerificationRequest):
    """Initiate physical verification request once all mandatory online verifications are complete."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Enforce reviewer role authorization
    role = (req.reviewer_role or "reviewer").strip().lower()
    if role == "claimant":
        raise HTTPException(
            status_code=403,
            detail="Claimants are not authorized to request physical verification. Only authorized reviewers may initiate physical verification."
        )

    eligible, reason, summary = claims.can_request_physical_verification(id)
    if not eligible:
        raise HTTPException(status_code=400, detail=reason)

    existing_pv = db.get_physical_verification(id)
    if existing_pv and existing_pv.get("status") in ("pending", "scheduled", "completed"):
        raise HTTPException(status_code=400, detail=f"Physical verification has already been requested (status: {existing_pv.get('status')}).")

    pv_id = db.create_physical_verification_request(id, req.requested_by.strip() or "Reviewer", req.instructions or "")
    claims.analyze_claim(id)
    return db.get_physical_verification(id)


@router.post("/{id}/physical-verification/schedule", response_model=dict)
def schedule_physical_verification_endpoint(id: str, sched: PhysicalVerificationSchedule):
    """Schedule physical verification inspection appointment."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    role = (sched.reviewer_role or "reviewer").strip().lower()
    if role == "claimant":
        raise HTTPException(
            status_code=403,
            detail="Claimants are not authorized to schedule physical verification inspections."
        )

    pv = db.get_physical_verification(id)
    if not pv or pv.get("status") not in ("pending", "scheduled"):
        raise HTTPException(status_code=400, detail="Physical verification must be requested before scheduling an appointment.")

    if not sched.scheduled_date or not sched.scheduled_location:
        raise HTTPException(status_code=400, detail="Scheduled date and inspection location are required.")

    db.update_physical_verification(
        id,
        status="scheduled",
        scheduled_date=sched.scheduled_date,
        scheduled_location=sched.scheduled_location,
        assigned_inspector=sched.assigned_inspector or "",
        instructions=sched.instructions or pv.get("instructions", "")
    )
    db.update_claim(id, status="physical_verification_scheduled", physical_verification_status="scheduled")
    db.log_audit_event(
        claim_id=id,
        event_type="physical_verification_scheduled",
        actor_name=sched.reviewer_name or "Authorized Assessor",
        actor_role="reviewer",
        new_status="physical_verification_scheduled",
        details={
            "scheduled_date": sched.scheduled_date,
            "scheduled_location": sched.scheduled_location,
            "assigned_inspector": sched.assigned_inspector
        }
    )
    claims.analyze_claim(id)
    return db.get_physical_verification(id)


@router.post("/{id}/physical-verification/outcome", response_model=dict)
def record_physical_verification_outcome_endpoint(id: str, outcome: PhysicalVerificationOutcome):
    """Record completed or failed outcome of physical inspection."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    role = (outcome.reviewer_role or "reviewer").strip().lower()
    if role == "claimant":
        raise HTTPException(
            status_code=403,
            detail="Claimants are not authorized to record inspection outcomes."
        )

    pv = db.get_physical_verification(id)
    if not pv or pv.get("status") not in ("scheduled", "pending"):
        raise HTTPException(status_code=400, detail="Cannot record outcome: physical verification is not in a pending or scheduled state.")

    if outcome.outcome_status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Outcome status must be 'completed' or 'failed'.")

    if not outcome.outcome_notes or not outcome.outcome_notes.strip():
        raise HTTPException(status_code=400, detail="Outcome notes and inspection findings are mandatory.")

    now_str = datetime.now(timezone.utc).isoformat()
    db.update_physical_verification(
        id,
        status=outcome.outcome_status,
        outcome_status=outcome.outcome_status,
        outcome_notes=outcome.outcome_notes.strip(),
        completed_at=now_str
    )
    new_status = f"physical_verification_{outcome.outcome_status}"
    db.update_claim(id, status=new_status, physical_verification_status=outcome.outcome_status)
    db.log_audit_event(
        claim_id=id,
        event_type="physical_verification_outcome_recorded",
        actor_name=outcome.inspector_name or "Inspector",
        actor_role="reviewer",
        new_status=new_status,
        details={"outcome_notes": outcome.outcome_notes}
    )
    claims.analyze_claim(id)
    return db.get_physical_verification(id)


# ---------------------------------------------------------------------------
# Audit History
# ---------------------------------------------------------------------------
@router.get("/{id}/audit-history", response_model=dict)
def get_claim_audit_history_endpoint(id: str):
    """Retrieve full audit history trail for the claim."""
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    logs = db.get_claim_audit_logs(id)
    return {
        "audit_logs": logs,
        "audit_history": logs
    }


# ---------------------------------------------------------------------------
# Analysis & Audit
# ---------------------------------------------------------------------------
@router.post("/{id}/analyze")
@router.post("/{id}/audit")
def analyze_claim_endpoint(id: str):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    try:
        result = claims.analyze_claim(id)
        return {
            "checklist_items": result["checklist_items"],
            "checklist_analysis": result["checklist_items"],
            "policy_warnings": result["policy_warnings"],
            "warnings": result["policy_warnings"],
            "readiness_score": result["readiness_score"],
            "summary": result.get("summary", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claim analysis failed: {str(e)}")


# ---------------------------------------------------------------------------
# Reports & Download
# ---------------------------------------------------------------------------
@router.post("/{id}/report")
def generate_claim_report(id: str, format_type: str = "pdf"):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    try:
        if format_type.lower() == "pdf":
            report.generate_report_pdf(id)
        else:
            report.generate_report_markdown(id)

        # Mark report as up to date
        cur_version = claim.get("report_version", 1) or 1
        db.update_claim(id, report_stale=0, report_version=cur_version + 1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    return {
        "report_url": f"/claims/{id}/report/download?format={format_type}",
        "version": claim.get("report_version", 1),
        "status": "ready"
    }


@router.get("/{id}/report")
def get_claim_report_info(id: str):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    report_dir = settings.REPORTS_DIR / id
    pdf_path = report_dir / "report.pdf"
    has_pdf = pdf_path.exists()
    
    return {
        "claim_id": id,
        "has_report": has_pdf,
        "version": claim.get("report_version", 1),
        "is_stale": bool(claim.get("report_stale", 0)),
        "download_url": f"/claims/{id}/report/download?format=pdf" if has_pdf else None
    }


@router.get("/{id}/report/download")
def download_claim_report(id: str, format: str = "pdf"):
    claim = db.get_claim(id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    report_dir = settings.REPORTS_DIR / id
    if format.lower() == "pdf":
        file_path = report_dir / "report.pdf"
        media_type = "application/pdf"
        filename = f"InsureWise_Claim_Audit_{id}.pdf"
        if not file_path.exists():
            report.generate_report_pdf(id)
    else:
        file_path = report_dir / "report.md"
        media_type = "text/markdown"
        filename = f"InsureWise_Claim_Audit_{id}.md"
        if not file_path.exists():
            report.generate_report_markdown(id)

    if not os.path.exists(str(file_path)):
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        str(file_path),
        filename=filename,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
    )
