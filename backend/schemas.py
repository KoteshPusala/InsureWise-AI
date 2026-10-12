from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Citation(BaseModel):
    page: int
    quote: str

class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, str]] = []

class ChatResponse(BaseModel):
    answer: str
    verdict: str
    supported: bool
    citations: List[Citation] = []
    follow_up_suggestions: List[str] = []

class PolicyResponse(BaseModel):
    id: str
    filename: str
    display_name: str
    uploaded_at: str
    page_count: int
    chunk_count: int
    ocr_pages: List[int]
    status: str
    progress_stage: Optional[str] = None
    error_message: Optional[str] = None
    policy_type: Optional[str] = None
    summary: Optional[str] = None

class PolicyListResponse(BaseModel):
    policies: List[PolicyResponse]

class ClaimCreate(BaseModel):
    policy_id: str
    incident_description: str
    incident_type: str
    incident_date: str
    claim_title: Optional[str] = None
    claim_category: Optional[str] = None
    incident_details: Optional[Dict[str, Any]] = None

class ClaimUpdate(BaseModel):
    claim_title: Optional[str] = None
    incident_type: Optional[str] = None
    incident_date: Optional[str] = None
    incident_description: Optional[str] = None
    incident_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class ChecklistItem(BaseModel):
    item_id: str
    title: str
    why_needed: str
    status: str
    matched_document: Optional[str] = None
    evidence_excerpt: Optional[str] = None
    policy_citations: List[Citation] = []
    confidence: Optional[float] = None
    notes: Optional[str] = None
    source: Optional[str] = "policy_requirement"
    requirement_type: Optional[str] = "policy_requirement"
    verification_criteria: Optional[str] = None
    human_review_status: Optional[str] = None
    document_id: Optional[str] = None
    extracted_summary: Optional[Dict[str, Any]] = None
    issues: Optional[List[Dict[str, Any]]] = None

class ClaimResponse(BaseModel):
    id: str
    policy_id: str
    incident_description: str
    incident_type: str
    incident_date: str
    created_at: str
    status: str
    checklist_items: List[ChecklistItem]
    documents: List[Any] = []
    claim_title: Optional[str] = None
    claim_category: Optional[str] = None
    incident_details: Optional[Dict[str, Any]] = None
    readiness_score: Optional[int] = 0
    report_version: Optional[int] = 1
    report_stale: Optional[bool] = False
    physical_verification_status: Optional[str] = "none"
    physical_verification_id: Optional[str] = ""

class ClaimDocumentResponse(BaseModel):
    id: str
    claim_id: str
    filename: str
    page_count: int
    extracted_text_preview: str
    doc_type_guess: str
    created_at: str
    checklist_item_id: Optional[str] = ""
    file_size: Optional[int] = 0
    version: Optional[int] = 1
    is_current: Optional[int] = 1
    status: Optional[str] = "uploaded"
    classification: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    verification_findings: Optional[Dict[str, Any]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    review_status: Optional[str] = "pending"
    reviewer_name: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[str] = None

class DocumentReviewRequest(BaseModel):
    reviewer_name: str
    review_status: str  # accepted | human_verified | info_required | correction_required | mismatch_confirmed | human_rejected | unable_to_verify
    reviewer_notes: Optional[str] = ""
    reviewer_role: Optional[str] = "reviewer"

class DocumentReassignRequest(BaseModel):
    checklist_item_id: str

class PhysicalVerificationRequest(BaseModel):
    requested_by: str
    instructions: Optional[str] = ""
    reviewer_role: Optional[str] = "reviewer"

class PhysicalVerificationSchedule(BaseModel):
    scheduled_date: str
    scheduled_location: str
    assigned_inspector: Optional[str] = ""
    instructions: Optional[str] = ""
    reviewer_name: Optional[str] = ""
    reviewer_role: Optional[str] = "reviewer"

class PhysicalVerificationOutcome(BaseModel):
    outcome_status: str  # completed | failed
    outcome_notes: str
    inspector_name: Optional[str] = ""
    reviewer_role: Optional[str] = "reviewer"

class PhysicalVerificationResponse(BaseModel):
    id: str
    claim_id: str
    status: str
    requested_by: str
    requested_at: str
    scheduled_date: Optional[str] = ""
    scheduled_location: Optional[str] = ""
    instructions: Optional[str] = ""
    assigned_inspector: Optional[str] = ""
    outcome_status: Optional[str] = ""
    outcome_notes: Optional[str] = ""
    completed_at: Optional[str] = ""
    created_at: str
    updated_at: str

class AuditLogEntry(BaseModel):
    id: str
    claim_id: str
    document_id: Optional[str] = ""
    event_type: str
    actor_name: str
    actor_role: str
    old_status: Optional[str] = ""
    new_status: Optional[str] = ""
    details: Optional[Dict[str, Any]] = None
    created_at: str

class AnalysisResponse(BaseModel):
    checklist_items: List[ChecklistItem] = []
    policy_warnings: List[Dict[str, Any]] = []
    readiness_score: int = 0
    summary: Optional[Dict[str, Any]] = None

class ReportRequest(BaseModel):
    claim_id: str
    format: str = "pdf"

class ReportResponse(BaseModel):
    report_url: str

class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    api_key_configured: bool
    embedding_provider: str
    tesseract_available: bool
    demo_mode: bool

class ErrorResponse(BaseModel):
    error: Dict[str, str]
