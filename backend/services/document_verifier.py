import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from config import settings
from services.pdf_service import extract_pdf_text
from services.vector_store import search as vector_search, get_policy_chunks, index_exists
from services.llm import generate_json, LLMError

logger = logging.getLogger(__name__)

# Known Document Categories
DOC_CATEGORIES = {
    "hospital_bills": "Hospital Bill",
    "discharge_summary": "Discharge Summary",
    "doctor_prescription": "Doctor Prescription",
    "diagnostic_reports": "Diagnostic Report",
    "pharmacy_bills": "Pharmacy Bill",
    "payment_receipt": "Payment Receipt",
    "repair_estimate": "Repair Estimate / Quotation",
    "final_invoice": "Final Repair Invoice",
    "police_report": "Police Report / FIR",
    "driving_licence": "Driving Licence",
    "vehicle_registration": "Vehicle Registration Certificate",
    "photos_damage": "Damage Photographs",
    "property_documents": "Property Ownership Document",
    "fire_brigade_report": "Fire Brigade Report",
    "identity_proof": "Identity Proof",
    "claim_form": "Claim Form",
    "theft_declaration": "Theft Declaration",
}


def _safe_float(val: Any) -> float:
    """Safely convert any numeric, string, or mixed currency value to float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.]", "", val)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def _extract_amounts(text: str) -> List[float]:
    """Find currency amounts in text."""
    matches = re.findall(r"(?:INR|Rs\.?|₹|\$)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    amounts = []
    for m in matches:
        clean = m.replace(",", "").strip()
        try:
            val = float(clean)
            if 0 < val < 100000000:
                amounts.append(val)
        except ValueError:
            pass
    return amounts


def _extract_dates(text: str) -> List[str]:
    """Extract standard dates (DD-MM-YYYY, YYYY-MM-DD, DD/MM/YYYY)."""
    patterns = [
        r"\b(\d{1,2}[-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/]\d{2,4})\b",
        r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
        r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
    ]
    dates = []
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE):
            if m not in dates:
                dates.append(m)
    return dates


# ---------------------------------------------------------------------------
# Stage A: File Validation
# ---------------------------------------------------------------------------
def validate_file(file_path: str) -> Dict[str, Any]:
    """Inspect and extract text from uploaded PDF."""
    if not os.path.exists(file_path):
        return {"valid": False, "error": "File not found on disk"}

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return {"valid": False, "error": "Uploaded file is empty (0 bytes)"}

    try:
        pdf_data = extract_pdf_text(file_path)
    except Exception as e:
        return {"valid": False, "error": f"Failed to parse PDF document: {str(e)}"}

    pages = pdf_data.get("pages", [])
    total_pages = pdf_data.get("page_count", len(pages))
    if total_pages == 0:
        return {"valid": False, "error": "PDF has 0 pages or is corrupted"}

    full_text = "\n".join(p.get("text", "") for p in pages)
    ocr_pages = pdf_data.get("ocr_pages", [])

    return {
        "valid": True,
        "page_count": total_pages,
        "file_size": file_size,
        "full_text": full_text,
        "pages": pages,
        "ocr_pages": ocr_pages,
    }


# ---------------------------------------------------------------------------
# Stage B: Document Classification
# ---------------------------------------------------------------------------
def classify_document(text: str, filename: str, expected_item_id: str) -> Dict[str, Any]:
    """
    Classify the uploaded document into one of the known insurance document categories.
    Determines whether there is a mismatch with the target checklist requirement.
    """
    text_lower = text.lower()
    fn_lower = filename.lower()

    # Rule-based score per category
    scores: Dict[str, int] = {k: 0 for k in DOC_CATEGORIES.keys()}

    # Keywords scoring
    rules = [
        ("hospital_bills", ["hospital bill", "inpatient bill", "tax invoice", "bill no", "room charges", "nursing charges", "investigation charges", "pharmacy charges", "total amount", "amount payable", "bed charges", "ipd bill", "hospital invoice"]),
        ("discharge_summary", ["discharge summary", "discharge card", "date of admission", "date of discharge", "clinical summary", "course in hospital", "treatment given", "condition on discharge", "provisional diagnosis", "final diagnosis"]),
        ("doctor_prescription", ["doctor prescription", "rx", "dr.", "consultant", "medicines prescribed", "dosage", "tablet", "capsule", "syrup"]),
        ("diagnostic_reports", ["diagnostic report", "investigation report", "lab report", "pathology", "blood test", "ultrasound", "x-ray", "ct scan", "mri", "reference range", "sample collected"]),
        ("pharmacy_bills", ["pharmacy bill", "medical store", "chemist", "batch no", "expiry date", "mrp", "hsn code", "tablets", "pharma"]),
        ("payment_receipt", ["payment receipt", "money receipt", "received with thanks", "receipt no", "transaction id", "mode of payment", "cash/cheque", "paid sum of"]),
        ("repair_estimate", ["repair estimate", "quotation", "workshop", "authorized service", "body shop", "labor charges", "part description", "bumper replacement", "dent repair", "painting charges", "estimated repair cost"]),
        ("final_invoice", ["final repair invoice", "tax invoice", "final bill", "delivery order", "repairs completed"]),
        ("police_report", ["first information report", "fir", "police station", "station house officer", "sho", "sub-inspector", "bailable", "ipc section", "incident report", "police report"]),
        ("driving_licence", ["driving licence", "driving license", "union of india", "transport department", "licensing authority", "dl no", "valid till", "date of birth", "blood group"]),
        ("vehicle_registration", ["registration certificate", "rc book", "chassis number", "engine number", "owner name", "unladen weight", "fuel type"]),
        ("photos_damage", ["photograph", "damage photo", "visual evidence", "vehicle inspection"]),
        ("property_documents", ["property deed", "sale deed", "property tax receipt", "title deed", "ownership deed", "khata certificate"]),
        ("fire_brigade_report", ["fire brigade", "fire station", "fire occurrence report", "incident of fire", "fire call"]),
        ("identity_proof", ["aadhaar", "pan card", "income tax department", "passport", "voter id", "election commission"]),
        ("claim_form", ["claim form", "claim application", "claimant signature", "policyholder signature", "details of loss"]),
    ]

    for cat, keywords in rules:
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 3
            if kw in fn_lower:
                scores[cat] += 4

    # Determine highest scoring category
    detected_type = max(scores, key=scores.get)
    highest_score = scores[detected_type]

    if highest_score < 3:
        # Fallback heuristic: check if expected matches hints
        detected_type = expected_item_id if expected_item_id in DOC_CATEGORIES else "unknown"
        confidence = 0.5
    else:
        confidence = min(0.95, 0.5 + highest_score * 0.05)

    # Check for mismatch
    # Allow loose matching (e.g. final_invoice vs repair_estimate, or medical synonyms)
    allowed_synonyms = {
        "repair_estimate": ["repair_estimate", "final_invoice"],
        "final_invoice": ["repair_estimate", "final_invoice"],
        "hospital_bills": ["hospital_bills", "pharmacy_bills", "payment_receipt"],
        "payment_receipt": ["hospital_bills", "payment_receipt", "pharmacy_bills"],
    }
    allowed = allowed_synonyms.get(expected_item_id, [expected_item_id])

    is_mismatch = (detected_type != "unknown") and (detected_type not in allowed) and (highest_score >= 6)

    mismatch_message = ""
    suggested_item = ""
    if is_mismatch:
        detected_label = DOC_CATEGORIES.get(detected_type, detected_type.replace("_", " ").title())
        expected_label = DOC_CATEGORIES.get(expected_item_id, expected_item_id.replace("_", " ").title())
        mismatch_message = (
            f"The uploaded file appears to be a '{detected_label}', but this checklist item requires '{expected_label}'. "
            f"Please verify or reassign this document."
        )
        suggested_item = detected_type

    return {
        "detected_type": detected_type,
        "detected_label": DOC_CATEGORIES.get(detected_type, detected_type.replace("_", " ").title()),
        "confidence": confidence,
        "score": highest_score,
        "is_mismatch": is_mismatch,
        "mismatch_message": mismatch_message,
        "suggested_item_id": suggested_item,
    }


# ---------------------------------------------------------------------------
# Stage C: Structured Information Extraction
# ---------------------------------------------------------------------------
def extract_document_information(
    text: str,
    doc_type: str,
    filename: str
) -> Dict[str, Any]:
    """
    Extract key fields based on document category (Patient, Hospital, Line Items, Amounts, Dates).
    Uses deterministic parsing first, with LLM structured fallback if configured.
    """
    extracted: Dict[str, Any] = {
        "doc_type": doc_type,
        "filename": filename,
        "dates_found": _extract_dates(text)[:5],
        "amounts_found": _extract_amounts(text)[:10],
    }

    # Deterministic regex extraction
    # 1. Patient / Insured Name
    name_match = re.search(r"(?:Patient Name|Patient|Insured Name|Customer Name|Name of Insured|Name)\s*[:\-]\s*([A-Za-z\.\t ]{2,40})", text, re.IGNORECASE)
    if name_match:
        extracted["patient_name"] = name_match.group(1).strip()

    # 2. Hospital / Workshop / Facility Name
    hosp_match = re.search(r"([A-Z][A-Za-z\s]+(?:Hospital|Healthcare|Clinic|Medical Centre|Nursing Home|Workshop|Garage|Motors|AutoCare))", text)
    if hosp_match:
        extracted["facility_name"] = hosp_match.group(1).strip()

    # 3. Bill / Invoice / Reference Number
    inv_match = re.search(r"(?:Invoice No|Bill No|Estimate No|FIR No|Ref No|Receipt No|Reg No)\s*[:\-]?\s*([A-Za-z0-9\/\-_]{3,25})", text, re.IGNORECASE)
    if inv_match:
        extracted["reference_number"] = inv_match.group(1).strip()

    # 4. Total Amount
    total_match = re.search(r"(?:Total Amount|Total|Grand Total|Net Amount|Gross Amount)\s*[:\-]?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if total_match:
        try:
            extracted["total_amount"] = float(total_match.group(1).replace(",", "").strip())
        except ValueError:
            pass
    elif extracted["amounts_found"]:
        # Largest detected amount is often total
        extracted["total_amount"] = max(extracted["amounts_found"])

    # 5. Amount Paid & Outstanding Balance
    paid_match = re.search(r"(?:Amount Paid|Paid Amount|Advance Paid|Total Paid)\s*[:\-]?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if paid_match:
        try:
            extracted["amount_paid"] = float(paid_match.group(1).replace(",", "").strip())
        except ValueError:
            pass

    balance_match = re.search(r"(?:Balance|Balance Due|Amount Due|Outstanding|Payable)\s*[:\-]?\s*(?:INR|Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if balance_match:
        try:
            extracted["outstanding_balance"] = float(balance_match.group(1).replace(",", "").strip())
        except ValueError:
            pass

    # 6. Diagnosis / Clinical Findings (Discharge summary)
    diag_match = re.search(r"(?:Diagnosis|Final Diagnosis|Provisional Diagnosis)\s*[:\-]\s*([^\n\r]+)", text, re.IGNORECASE)
    if diag_match:
        extracted["diagnosis"] = diag_match.group(1).strip()

    # 7. Itemized lines extraction for bills / estimates
    line_items = []
    # Lines with item and cost at the end: e.g. "Front bumper replacement 12,500" or "Room rent 5000"
    for line in text.split("\n"):
        line_clean = line.strip()
        m = re.search(r"^([\d\.\-\s]*[A-Za-z\s\(\)\/\-_]{4,50})\s+(?:INR|Rs\.?|₹)?\s*([\d,]{2,10}(?:\.\d{2})?)$", line_clean)
        if m:
            desc = m.group(1).strip()
            # Ignore header/footer lines
            if any(h in desc.lower() for h in ["total", "amount", "s.no", "description", "page", "date"]):
                continue
            try:
                amt = float(m.group(2).replace(",", ""))
                if 10 <= amt <= 10000000:
                    line_items.append({"description": desc, "amount": amt})
            except ValueError:
                pass

    if line_items:
        extracted["itemized_charges"] = line_items
        extracted["itemized_sum"] = sum(item["amount"] for item in line_items)

    # 8. Try LLM structured extraction if API key configured for deep nuances
    if getattr(settings, "api_key_configured", False) and not getattr(settings, "DEMO_MODE", False):
        try:
            system_prompt = (
                "You are an insurance claims document data extractor.\n"
                "Extract structured facts from this document excerpt into JSON without inventing any data.\n"
                "Fields: patient_name, hospital_or_facility_name, reference_number, admission_date, discharge_date, diagnosis, "
                "itemized_charges (list of {description, amount}), total_amount, amount_paid, payment_status ('paid'|'unpaid'|'partial'|'unknown')."
            )
            user_prompt = f"Document Type: {doc_type}\nFilename: {filename}\nText Excerpt:\n{text[:3500]}"
            llm_facts = generate_json(system_prompt, user_prompt)
            for k, v in llm_facts.items():
                if v and (k not in extracted or not extracted[k]):
                    extracted[k] = v
        except Exception as e:
            logger.debug("LLM extraction skipped or failed: %s", e)

    # Sanitize numeric fields to float to avoid runtime TypeErrors
    if "total_amount" in extracted and extracted["total_amount"] is not None:
        extracted["total_amount"] = _safe_float(extracted["total_amount"])
    if "amount_paid" in extracted and extracted["amount_paid"] is not None:
        extracted["amount_paid"] = _safe_float(extracted["amount_paid"])
    if "outstanding_balance" in extracted and extracted["outstanding_balance"] is not None:
        extracted["outstanding_balance"] = _safe_float(extracted["outstanding_balance"])
    if isinstance(extracted.get("itemized_charges"), list):
        sanitized_lines = []
        for itm in extracted["itemized_charges"]:
            if isinstance(itm, dict):
                itm_copy = dict(itm)
                itm_copy["amount"] = _safe_float(itm.get("amount", 0))
                sanitized_lines.append(itm_copy)
        extracted["itemized_charges"] = sanitized_lines
        if sanitized_lines and ("itemized_sum" not in extracted or not extracted["itemized_sum"]):
            extracted["itemized_sum"] = round(sum(itm["amount"] for itm in sanitized_lines), 2)

    return extracted


# ---------------------------------------------------------------------------
# Stage D: Requirement-Specific & Cross-Document Verification
# ---------------------------------------------------------------------------
def verify_document_content(
    extracted_data: Dict[str, Any],
    claim: Dict[str, Any],
    checklist_item: Dict[str, Any],
    other_documents: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Perform deterministic arithmetic checks and cross-document verification.
    Returns: (verification_findings, issues_list)
    """
    findings: Dict[str, Any] = {}
    issues: List[Dict[str, Any]] = []

    # 1. Deterministic Arithmetic Validation
    itemized_charges = extracted_data.get("itemized_charges", [])
    raw_total = extracted_data.get("total_amount")
    if itemized_charges and raw_total is not None:
        calc_sum = round(sum(_safe_float(item.get("amount", 0)) for item in itemized_charges if isinstance(item, dict)), 2)
        total_amount = _safe_float(raw_total)
        findings["calculated_itemized_sum"] = calc_sum
        findings["declared_total"] = total_amount
        diff = round(abs(calc_sum - total_amount), 2)
        if diff > 1.0:
            issue_msg = (
                f"Arithmetic discrepancy: Sum of itemized lines (₹{calc_sum:,.2f}) does not match declared total (₹{total_amount:,.2f}). "
                f"Difference: ₹{diff:,.2f}."
            )
            issues.append({
                "type": "arithmetic_mismatch",
                "severity": "warning",
                "message": issue_msg,
                "calc_sum": calc_sum,
                "declared_total": total_amount,
            })
            findings["arithmetic_check"] = "discrepancy_detected"
        else:
            findings["arithmetic_check"] = "consistent"

    # 2. Payment Status Verification
    total_amount = _safe_float(raw_total) if raw_total is not None else 0.0
    amount_paid = _safe_float(extracted_data.get("amount_paid")) if extracted_data.get("amount_paid") is not None else None
    outstanding = _safe_float(extracted_data.get("outstanding_balance")) if extracted_data.get("outstanding_balance") is not None else None
    payment_status = str(extracted_data.get("payment_status", "")).lower()

    if total_amount > 0 and outstanding is not None and outstanding >= total_amount:
        payment_status = "unpaid"
    elif total_amount > 0 and amount_paid is not None and amount_paid >= total_amount:
        payment_status = "paid"

    if payment_status == "unpaid":
        issues.append({
            "type": "unpaid_balance",
            "severity": "info",
            "message": "Document indicates this bill is unpaid or has an outstanding balance. Proof of payment/receipt may be requested.",
        })
        findings["payment_status"] = "unpaid"
    elif payment_status == "paid":
        findings["payment_status"] = "paid"

    # 3. Patient Name Alignment with Incident Statement
    patient_name = extracted_data.get("patient_name")
    incident_desc = claim.get("incident_description", "").lower()
    if patient_name:
        findings["extracted_patient_name"] = patient_name
        # Check against other documents
        for od in other_documents:
            od_ext = od.get("extracted_data") or {}
            od_name = od_ext.get("patient_name")
            if od_name and patient_name.lower() != od_name.lower():
                # Check token overlap
                p_tokens = set(re.findall(r"\w+", patient_name.lower()))
                od_tokens = set(re.findall(r"\w+", od_name.lower()))
                if not (p_tokens & od_tokens):
                    issues.append({
                        "type": "name_discrepancy",
                        "severity": "warning",
                        "message": f"Patient name '{patient_name}' differs from '{od_name}' in {od.get('filename')}.",
                    })

    # 4. Date Alignment
    incident_date_str = claim.get("incident_date")
    if incident_date_str and extracted_data.get("dates_found"):
        findings["incident_date"] = incident_date_str

    findings["verified_at"] = datetime.now(timezone.utc).isoformat()
    return findings, issues


# ---------------------------------------------------------------------------
# Stage E: Policy-Grounded RAG Clause Retrieval
# ---------------------------------------------------------------------------
def retrieve_policy_grounding(
    policy_id: str,
    item_id: str,
    item_title: str
) -> List[Dict[str, Any]]:
    """Retrieve grounded clauses from policy FAISS index for this requirement."""
    if not index_exists(policy_id):
        return []

    policy_chunks = get_policy_chunks(policy_id)
    search_query = f"{item_title} requirements documentation submit"
    matching = vector_search(policy_id, search_query, top_k=2, threshold=0.28)

    citations = []
    for chunk in matching:
        page_no = chunk.get("page_start", chunk.get("page", 1))
        c_text = chunk.get("text", "")
        # Find sentence containing keywords
        sentences = re.split(r"(?<=[.!?\n])\s+", c_text)
        quote = c_text[:140]
        for s in sentences:
            if any(w.lower() in s.lower() for w in item_title.split() if len(w) > 3):
                quote = s.strip()
                break
        citations.append({
            "page": int(page_no),
            "quote": quote
        })
        if len(citations) >= 2:
            break

    return citations


# ---------------------------------------------------------------------------
# Master Verification Pipeline Entrypoint
# ---------------------------------------------------------------------------
def verify_claim_document_pipeline(
    doc_id: str,
    file_path: str,
    claim: Dict[str, Any],
    checklist_item: Dict[str, Any],
    other_documents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Executes all 5 stages of the AI document verification pipeline.
    Returns complete verification results, classification, extracted facts, issues, and lifecycle status.
    """
    filename = os.path.basename(file_path)
    expected_item_id = checklist_item.get("item_id", "")

    # Stage A: File Validation
    val_res = validate_file(file_path)
    if not val_res["valid"]:
        return {
            "status": "processing_failed",
            "classification": {"detected_type": "unknown", "is_mismatch": False},
            "extracted_data": {},
            "verification_findings": {},
            "issues": [{"type": "file_error", "severity": "error", "message": val_res.get("error", "Invalid file")}],
            "policy_citations": [],
            "error": val_res.get("error"),
        }

    full_text = val_res["full_text"]
    page_count = val_res["page_count"]
    file_size = val_res["file_size"]

    # Stage B: Classification
    class_res = classify_document(full_text, filename, expected_item_id)

    # Stage C: Information Extraction
    extracted_data = extract_document_information(full_text, class_res["detected_type"], filename)
    extracted_data["page_count"] = page_count
    extracted_data["file_size"] = file_size

    # Stage D: Verification & Arithmetic Checks
    findings, issues = verify_document_content(extracted_data, claim, checklist_item, other_documents)

    # If mismatch detected in Stage B, add issue
    if class_res.get("is_mismatch"):
        issues.insert(0, {
            "type": "document_mismatch",
            "severity": "warning",
            "message": class_res["mismatch_message"],
            "detected_type": class_res["detected_type"],
            "suggested_item_id": class_res["suggested_item_id"],
        })

    # Stage E: Policy Grounding
    policy_id = claim.get("policy_id", "")
    citations = retrieve_policy_grounding(policy_id, expected_item_id, checklist_item.get("title", ""))

    # Determine final lifecycle status
    has_blocking_issue = any(iss.get("severity") in ("warning", "error") for iss in issues)
    if class_res.get("is_mismatch"):
        lifecycle_status = "needs_attention"
    elif has_blocking_issue:
        lifecycle_status = "needs_attention"
    else:
        lifecycle_status = "ready_for_review"

    return {
        "status": lifecycle_status,
        "page_count": page_count,
        "file_size": file_size,
        "classification": class_res,
        "extracted_data": extracted_data,
        "verification_findings": findings,
        "issues": issues,
        "policy_citations": citations,
        "extracted_text_preview": full_text[:400] if full_text else "",
    }
