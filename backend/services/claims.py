import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from config import settings
from services.vector_store import search as vector_search, get_policy_chunks, index_exists
from services.llm import generate_json, LLMError
from services.pdf_service import extract_pdf_text
import db


def _load_base_checklist(incident_type: str) -> List[Dict[str, Any]]:
    """Load base checklist items from configurable JSON file."""
    checklist_path = str(settings.CHECKLIST_PATH)
    if not os.path.exists(checklist_path):
        return []
    with open(checklist_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    type_map = {
        "vehicle_accident": "vehicle_accident",
        "theft": "theft",
        "fire_property_damage": "fire_property_damage",
        "natural_disaster": "fire_property_damage",
        "medical_health": "medical_health",
        "accident": "vehicle_accident",
        "fire": "fire_property_damage",
        "medical": "medical_health",
        "other": "vehicle_accident",
    }
    key = type_map.get(incident_type.lower(), "vehicle_accident")
    checklist_data = data.get(key, {})
    items = []
    for item_id, item_data in checklist_data.items():
        item = {"id": item_id, **item_data}
        items.append(item)
    return items


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _token_overlap_ratio(quote: str, chunk_text: str) -> float:
    quote_words = set(re.findall(r"\w{3,}", quote.lower()))
    if not quote_words:
        return 0.0
    chunk_words = set(re.findall(r"\w{3,}", chunk_text.lower()))
    intersection = quote_words.intersection(chunk_words)
    return len(intersection) / len(quote_words)


def _verify_citation(citation: Dict[str, Any], policy_chunks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Verify that a cited quote actually appears on the claimed page of the policy."""
    if not citation or not isinstance(citation, dict):
        return None
    page = citation.get("page")
    quote = citation.get("quote", "").strip()
    if not quote or page is None:
        return None

    norm_quote = _normalize_text(quote)
    if len(norm_quote) < 8:
        return None

    # First check chunks on the cited page
    for chunk in policy_chunks:
        chunk_page = chunk.get("page_start", chunk.get("page", 0))
        if chunk_page == page:
            norm_chunk = _normalize_text(chunk.get("text", ""))
            if norm_quote in norm_chunk or _token_overlap_ratio(norm_quote, norm_chunk) >= 0.65:
                return {"page": int(page), "quote": quote}

    # If page was slightly offset (+/- 1 page) due to headers or pagination
    for chunk in policy_chunks:
        chunk_page = chunk.get("page_start", chunk.get("page", 0))
        if abs(chunk_page - page) <= 1:
            norm_chunk = _normalize_text(chunk.get("text", ""))
            if norm_quote in norm_chunk or _token_overlap_ratio(norm_quote, norm_chunk) >= 0.75:
                return {"page": int(chunk_page), "quote": quote}

    return None


def _extract_document_texts(claim_id: str) -> List[Dict[str, Any]]:
    """Extract full text from all uploaded claim documents."""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM claim_documents WHERE claim_id = ? ORDER BY created_at ASC", (claim_id,))
    rows = c.fetchall()
    conn.close()

    docs = []
    for row in rows:
        doc = dict(row)
        file_path = str(settings.UPLOADS_DIR / f"{doc['id']}.pdf")
        full_text = doc.get("extracted_text_preview", "")
        pages_data = []
        if os.path.exists(file_path):
            try:
                result = extract_pdf_text(file_path)
                pages_data = result.get("pages", [])
                full_text = "\n".join([p["text"] for p in pages_data])
            except Exception:
                pass
        docs.append({
            "id": doc["id"],
            "filename": doc["filename"],
            "text": full_text,
            "pages": pages_data,
            "doc_type_guess": doc.get("doc_type_guess", "unknown"),
        })
    return docs


def extract_facts_from_incident(incident_description: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract facts directly from the user's incident description to satisfy
    checklist items where the description already answers them.
    """
    if not incident_description or not incident_description.strip():
        return items

    desc_lower = incident_description.lower()
    sentences = re.split(r"(?<=[.!?\n])\s+", incident_description.strip())

    def find_matching_sentence(keywords: List[str]) -> Optional[str]:
        for sentence in sentences:
            s_lower = sentence.lower()
            if any(kw in s_lower for kw in keywords):
                return sentence.strip()
        return None

    # Physical files, photos, official IDs, vehicle documents, bills, and reports
    # MUST NEVER be satisfied by text description alone; they require an actual document upload.
    PHYSICAL_DOCUMENT_KEYWORDS = [
        "photo", "photos", "picture", "image", "damage", "bill", "bills", "invoice",
        "receipt", "estimate", "quotation", "policy_copy", "copy", "licence",
        "license", "registration", "rc", "prescription", "summary", "report",
        "fir", "police", "form", "proof", "pre_auth"
    ]

    for item in items:
        # Don't overwrite if document already uploaded for this requirement
        if item.get("source") == "uploaded_document" or item.get("document_id"):
            continue

        item_id = item.get("item_id", "").lower()
        title = item.get("title", "").lower()

        # Physical documents and damage photos MUST remain awaiting upload
        if any(pk in item_id or pk in title for pk in PHYSICAL_DOCUMENT_KEYWORDS):
            continue

        matched_phrase = None

        # Declarative items only (e.g. third party statement, theft declaration)
        if any(k in item_id or k in title for k in ["third_party", "third party", "other vehicle"]):
            tp_keywords = ["third party", "other car", "other vehicle", "auto", "pedestrian", "truck", "cab", "other driver", "opposite vehicle"]
            matched_phrase = find_matching_sentence(tp_keywords)

        elif any(k in item_id or k in title for k in ["theft_declaration", "declaration"]):
            theft_keywords = ["stolen", "theft", "burgled", "parked and missing", "break-in"]
            matched_phrase = find_matching_sentence(theft_keywords)

        if matched_phrase:
            item["status"] = "present"
            item["matched_document"] = "Incident Description"
            item["evidence_excerpt"] = matched_phrase[:220]
            item["source"] = "incident_description"
            item["confidence"] = 0.85
            item["notes"] = "Fact provided in incident description"

    return items


def match_documents(checklist_items: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Match uploaded PDF documents against checklist items using text and doc type.
    Enforces strict 1-to-1 matching so a single document is never duplicated
    across multiple checklist items.
    """
    if not documents or not checklist_items:
        return checklist_items

    # 1. First, bind documents that have an explicit checklist_item_id
    used_doc_ids = set()
    assigned_item_ids = set()

    for item in checklist_items:
        iid = item.get("item_id")
        for doc in documents:
            if doc.get("checklist_item_id") and doc.get("checklist_item_id") == iid:
                used_doc_ids.add(doc.get("id"))
                assigned_item_ids.add(iid)
                item["status"] = "present"
                item["matched_document"] = doc.get("filename")
                item["document_id"] = doc.get("id")
                item["source"] = "uploaded_document"
                item["confidence"] = 0.95
                item["notes"] = f"Document attached: {doc.get('filename')}"
                break

    # 2. Score unassigned pairs
    candidates = []
    for idx, item in enumerate(checklist_items):
        iid = item.get("item_id")
        if iid in assigned_item_ids:
            continue

        title = item.get("title", "")
        title_lower = title.lower()
        title_words = [w for w in re.findall(r"\w{3,}", title_lower) if w not in ["the", "and", "for", "with", "copy"]]

        for doc in documents:
            doc_id = doc.get("id")
            if doc_id in used_doc_ids:
                continue

            doc_text = doc.get("text", "")
            doc_text_lower = doc_text.lower()
            doc_name_lower = doc.get("filename", "").lower()
            doc_type = doc.get("doc_type_guess", "").lower()

            score = 0

            # Title words in filename
            for tw in title_words:
                if tw in doc_name_lower:
                    score += 4

            # Doc type match
            if doc_type != "unknown" and any(k in doc_type for k in title_words):
                score += 3

            # Exact keyword matches in text
            matched_words = sum(1 for tw in title_words if tw in doc_text_lower)
            if title_words and matched_words >= 2:
                score += matched_words * 2

            if score >= 4:
                # Find excerpt
                excerpt = doc_text[:200]
                for tw in title_words:
                    pos = doc_text_lower.find(tw)
                    if pos != -1:
                        start = max(0, pos - 30)
                        end = min(len(doc_text), pos + 150)
                        excerpt = doc_text[start:end].strip()
                        break
                candidates.append((score, idx, doc, excerpt))

    # 3. Sort candidates by score descending and greedily match 1-to-1
    candidates.sort(key=lambda x: x[0], reverse=True)
    for score, idx, doc, excerpt in candidates:
        item = checklist_items[idx]
        iid = item.get("item_id")
        doc_id = doc.get("id")

        if iid in assigned_item_ids or doc_id in used_doc_ids:
            continue

        assigned_item_ids.add(iid)
        used_doc_ids.add(doc_id)

        if score >= 5:
            item["status"] = "present"
            item["matched_document"] = doc["filename"]
            item["document_id"] = doc_id
            item["evidence_excerpt"] = excerpt if excerpt else "Document content verified"
            item["source"] = "uploaded_document"
            item["confidence"] = min(0.95, 0.6 + score * 0.05)
            item["notes"] = f"Verified from uploaded document: {doc['filename']}"
        else:
            item["status"] = "unclear"
            item["matched_document"] = doc["filename"]
            item["document_id"] = doc_id
            item["evidence_excerpt"] = excerpt[:200]
            item["source"] = "uploaded_document"
            item["confidence"] = 0.5
            item["notes"] = f"Partial match found in {doc['filename']}. Please verify."

    return checklist_items


def calculate_readiness_score(checklist_items: List[Dict[str, Any]]) -> int:
    """
    Deterministic Readiness Score Formula:
    Evaluates completion credit across applicable items (policy requirements & general guidance).
    Excludes 'not_stated' and 'not_applicable' items from denominator.
    
    Status credits:
      - 'reviewed': 1.0 (100% - human reviewer accepted)
      - 'ready_for_review': 0.9 (90% - AI verified without issues)
      - 'present': 0.85 (85% - verified from document content or explicit incident details)
      - 'unclear': 0.4 (40% - partial match needing review)
      - 'needs_attention': 0.3 (30% - arithmetic discrepancy or mismatch flagged)
      - 'processing' / 'uploaded': 0.15 (15% - currently in flight)
      - 'awaiting_upload' / 'missing' / 'processing_failed': 0.0 (0%)
      
    Weights:
      - Policy requirements: 1.0
      - General guidance: 0.6
    """
    applicable_items = [
        i for i in checklist_items
        if i.get("status") not in ("not_stated", "not_applicable")
    ]
    if not applicable_items:
        return 100

    credits = {
        "reviewed": 1.0,
        "human_verified": 1.0,
        "ready_for_review": 0.9,
        "present": 0.85,
        "unclear": 0.4,
        "needs_attention": 0.3,
        "correction_required": 0.2,
        "info_required": 0.2,
        "human_rejected": 0.0,
        "processing": 0.15,
        "uploaded": 0.15,
        "awaiting_upload": 0.0,
        "missing": 0.0,
        "processing_failed": 0.0,
    }

    total_weight = 0.0
    earned_points = 0.0

    for item in applicable_items:
        status = str(item.get("status", "missing")).lower()
        item_credit = credits.get(status, 0.0)
        source = str(item.get("source", "policy_requirement")).lower()
        is_policy = "policy" in source or item.get("is_mandatory") is True or bool(item.get("policy_citations"))
        weight = 1.0 if is_policy else 0.6

        earned_points += item_credit * weight
        total_weight += weight

    if total_weight == 0:
        return 100

    score = int(round((earned_points / total_weight) * 100))
    return max(0, min(100, score))


def _check_policy_deadlines(policy_warnings: List[Dict[str, Any]], incident_date_str: str) -> List[Dict[str, Any]]:
    """Compare notification deadlines extracted from policy against the elapsed incident days."""
    if not incident_date_str:
        return policy_warnings

    try:
        incident_date = datetime.strptime(incident_date_str[:10], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        days_elapsed = (today - incident_date).days
    except Exception:
        return policy_warnings

    enhanced_warnings = []
    for w in policy_warnings:
        warning_text = w.get("warning", "")
        text_lower = warning_text.lower()
        enhanced = dict(w)

        # Detect hours or days
        deadline_days = None
        match_hours = re.search(r"within\s+(\d+)\s+hours", text_lower)
        if match_hours:
            deadline_days = max(1, int(match_hours.group(1)) // 24)
        else:
            match_days = re.search(r"within\s+(\d+)\s+days", text_lower)
            if match_days:
                deadline_days = int(match_days.group(1))

        if deadline_days is not None:
            if days_elapsed > deadline_days:
                enhanced["deadline_alert"] = f"CRITICAL: Policy states notification within {deadline_days} days. {days_elapsed} days have elapsed since incident date ({incident_date_str})."
                enhanced["warning"] = f"[EXPIRED DEADLINE] {warning_text} - Warning: {days_elapsed} days elapsed since incident."
            else:
                remaining = deadline_days - days_elapsed
                enhanced["deadline_alert"] = f"Time sensitive: {remaining} day(s) remaining to notify insurer under policy terms."

        enhanced_warnings.append(enhanced)

    return enhanced_warnings


def generate_checklist(claim_id: str, policy_id: str, incident_type: str, incident_description: str) -> Dict[str, Any]:
    """
    Generate a policy-grounded checklist by querying THAT policy's FAISS index.
    Every citation is verified against real page chunks.
    Items missing from policy are explicitly marked 'not_stated'.
    """
    base_items = _load_base_checklist(incident_type)
    policy_chunks = get_policy_chunks(policy_id)

    # 1. Targeted vector queries against the selected policy index
    targeted_queries = [
        "claim procedure documentation requirements proof of loss",
        "documents required for claim filing",
        "notification deadline time limit notice of claim",
        f"exclusions conditions {incident_type}",
        "deductible excess mandatory deductible",
        f"{incident_description[:120]}",
    ]
    # Add queries for base items
    for item in base_items:
        pq = item.get("policy_query")
        if pq and pq not in targeted_queries:
            targeted_queries.append(pq)

    retrieved_chunks: List[Dict[str, Any]] = []
    seen_chunk_ids = set()
    for q in targeted_queries:
        chunks = vector_search(policy_id, q, top_k=3, threshold=0.25)
        for c in chunks:
            cid = c.get("chunk_id", f"{c.get('page_start')}_{c.get('text')[:30]}")
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                retrieved_chunks.append(c)

    # 2. Check if LLM is configured
    llm_active = getattr(settings, "api_key_configured", False) and not getattr(settings, "DEMO_MODE", False)

    if llm_active and retrieved_chunks:
        context_parts = []
        for i, c in enumerate(retrieved_chunks[:12]):
            page_num = c.get("page_start", c.get("page", 1))
            context_parts.append(f"--- Clause {i+1} [Page {page_num}] ---\n{c.get('text', '')}")
        context = "\n\n".join(context_parts)

        base_summary = [
            {"id": item["id"], "title": item["title"], "description": item.get("description", "")}
            for item in base_items
        ]

        system_prompt = (
            "You are an insurance claim analyst. Analyze the provided policy clauses for this claim.\n"
            "Rules:\n"
            "1. For each item in the base checklist, inspect the clauses to see if the policy requires it.\n"
            "2. If the policy specifies/requires the item, cite the exact page and quote from the clauses. Set status to 'missing' (to be satisfied by user) and source to 'policy_requirement'.\n"
            "3. If the policy clauses DO NOT state or require this item, set status to 'not_stated', why_needed to 'Not stated in this policy', policy_citations to [], and source to 'general_guidance'.\n"
            "4. Add any policy-specific requirements mentioned in the clauses (e.g. deadline notices, spot inspection, FIR requirement within X hours).\n"
            "5. Extract policy warnings: deadlines, exclusions, deductibles, or conditions precedent, with citations.\n"
            "6. Every citation MUST have page (integer) and quote (exact substring from the excerpt). NEVER invent quotes or page numbers.\n"
            "Output JSON format:\n"
            "{\n"
            '  "checklist_items": [\n'
            '    {"item_id": "...", "title": "...", "why_needed": "...", "status": "missing|not_stated", "policy_citations": [{"page": N, "quote": "..."}], "source": "policy_requirement|general_guidance"}\n'
            "  ],\n"
            '  "policy_warnings": [\n'
            '    {"warning": "...", "page": N, "quote": "...", "type": "deadline|exclusion|deductible|condition"}\n'
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Incident Type: {incident_type}\n"
            f"Incident Description: {incident_description}\n\n"
            f"Policy Excerpts:\n{context}\n\n"
            f"Base Guidance Items:\n{json.dumps(base_summary, indent=2)}"
        )

        try:
            llm_result = generate_json(system_prompt, user_prompt)
            raw_items = llm_result.get("checklist_items", [])
            raw_warnings = llm_result.get("policy_warnings", [])

            verified_items = []
            for item in raw_items:
                # Verify citations against actual policy chunks
                valid_citations = []
                for cit in item.get("policy_citations", []):
                    checked = _verify_citation(cit, policy_chunks)
                    if checked:
                        valid_citations.append(checked)

                if not valid_citations:
                    status = "not_stated"
                    source = "general_guidance"
                    why = "Not stated in this policy document"
                else:
                    status = "missing"
                    source = "policy_requirement"
                    why = item.get("why_needed", "Required for claim processing")

                verified_items.append({
                    "item_id": item.get("item_id", str(uuid.uuid4())),
                    "title": item.get("title", "Document Requirement"),
                    "why_needed": why,
                    "status": status,
                    "matched_document": None,
                    "evidence_excerpt": None,
                    "policy_citations": valid_citations,
                    "confidence": 0.85 if valid_citations else 0.4,
                    "notes": "Verified from policy clauses" if valid_citations else "Standard guidance (not explicitly found in policy)",
                    "source": source,
                })

            verified_warnings = []
            for w in raw_warnings:
                cit = {"page": w.get("page"), "quote": w.get("quote", w.get("warning", ""))}
                checked = _verify_citation(cit, policy_chunks)
                verified_warnings.append({
                    "warning": w.get("warning", ""),
                    "page": checked["page"] if checked else w.get("page"),
                    "type": w.get("type", "condition"),
                })

            if verified_items:
                return {
                    "checklist_items": verified_items,
                    "policy_warnings": verified_warnings[:8],
                }
        except Exception as e:
            # Fall back to semantic chunk analysis below if LLM fails
            pass

    # 3. Fallback: Semantic retrieval & clause matching without LLM
    checklist_items = []
    for item in base_items:
        pq = item.get("policy_query", item["title"])
        matching_chunks = vector_search(policy_id, pq, top_k=2, threshold=0.32)

        citations = []
        for c in matching_chunks:
            # Extract sentence with keyword
            c_text = c.get("text", "")
            page_no = c.get("page_start", c.get("page", 1))
            sentences = re.split(r"(?<=[.!?\n])\s+", c_text)
            matched_s = None
            for s in sentences:
                if any(kw.lower() in s.lower() for kw in item.get("keywords", [item["title"]])):
                    matched_s = s.strip()
            if matched_s:
                checked = _verify_citation({"page": page_no, "quote": matched_s}, policy_chunks)
                if checked:
                    citations.append(checked)
                    break

        if citations:
            checklist_items.append({
                "item_id": item["id"],
                "title": item["title"],
                "why_needed": item.get("description", "Specified in policy claim requirements"),
                "status": "missing",
                "matched_document": None,
                "evidence_excerpt": None,
                "policy_citations": citations,
                "confidence": 0.75,
                "notes": f"Policy requirement confirmed on Page {citations[0]['page']}",
                "source": "policy_requirement",
                "is_mandatory": True,
            })
        else:
            checklist_items.append({
                "item_id": item["id"],
                "title": item["title"],
                "why_needed": "Not stated in this policy",
                "status": "not_stated",
                "matched_document": None,
                "evidence_excerpt": None,
                "policy_citations": [],
                "confidence": 0.35,
                "notes": "General guidance (not explicitly found in policy wording)",
                "source": "general_guidance",
                "is_mandatory": False,
            })

    # Extract policy warnings from retrieved chunks
    warnings = []
    for chunk in retrieved_chunks:
        text_lower = chunk.get("text", "").lower()
        page = chunk.get("page_start", 1)
        if any(w in text_lower for w in ["within", "hours", "days", "deadline", "immediate", "notice"]):
            sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", chunk["text"]) if any(w in s.lower() for w in ["within", "hours", "days", "deadline"])]
            if sentences:
                warnings.append({"warning": sentences[0][:200], "page": page, "type": "deadline"})
        if any(w in text_lower for w in ["exclude", "exclusion", "not covered", "does not cover"]):
            sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", chunk["text"]) if any(w in s.lower() for w in ["exclude", "not covered"])]
            if sentences:
                warnings.append({"warning": sentences[0][:200], "page": page, "type": "exclusion"})
        if any(w in text_lower for w in ["deductible", "excess"]):
            sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", chunk["text"]) if any(w in s.lower() for w in ["deductible", "excess"])]
            if sentences:
                warnings.append({"warning": sentences[0][:200], "page": page, "type": "deductible"})

    return {
        "checklist_items": checklist_items,
        "policy_warnings": warnings[:8],
    }


def can_request_physical_verification(claim_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Evaluates whether all mandatory policy checklist items have successfully completed
    online human verification.
    Returns: (is_eligible, reason_message, summary_stats)
    """
    claim = db.get_claim(claim_id)
    if not claim:
        return False, "Claim not found.", {}

    checklist_raw = claim.get("checklist_items") or "[]"
    try:
        items = json.loads(checklist_raw) if isinstance(checklist_raw, str) else checklist_raw
    except Exception:
        items = []

    if not items:
        return False, "No checklist items exist for this claim.", {}

    def _is_item_mandatory(itm: Dict[str, Any]) -> bool:
        if itm.get("is_mandatory") is True:
            return True
        if itm.get("is_mandatory") is False:
            return False
        if itm.get("policy_citations") and len(itm["policy_citations"]) > 0:
            return True
        if itm.get("source") == "policy_requirement":
            return True
        return False

    mandatory_items = [i for i in items if _is_item_mandatory(i)]
    if not mandatory_items:
        mandatory_items = [i for i in items if i.get("status") not in ("not_stated", "not_applicable")]

    if not mandatory_items:
        return False, "No mandatory requirements found for this claim.", {}

    claim_docs = db.get_claim_documents(claim_id, is_current_only=True)
    doc_by_item = {d.get("checklist_item_id"): d for d in claim_docs if d.get("checklist_item_id")}

    unverified_items = []
    correction_items = []
    missing_items = []

    for item in mandatory_items:
        iid = item.get("item_id")
        title = item.get("title", iid)
        doc = doc_by_item.get(iid)
        if not doc:
            missing_items.append(title)
        else:
            rev_status = str(doc.get("review_status", "pending")).lower()
            if rev_status in ("info_required", "correction_required"):
                correction_items.append(f"{title} (correction requested)")
            elif rev_status in ("mismatch_confirmed", "human_rejected", "rejected"):
                correction_items.append(f"{title} (document rejected)")
            elif rev_status not in ("accepted", "human_verified"):
                unverified_items.append(f"{title} (pending online human review)")

    summary = {
        "mandatory_count": len(mandatory_items),
        "missing": missing_items,
        "unverified": unverified_items,
        "corrections": correction_items,
    }

    if missing_items:
        return False, f"Physical verification blocked: Missing mandatory document(s): {', '.join(missing_items)}.", summary
    if correction_items:
        return False, f"Physical verification blocked: Document(s) require replacement or correction: {', '.join(correction_items)}.", summary
    if unverified_items:
        return False, f"Physical verification blocked: Mandatory document(s) awaiting online human verification: {', '.join(unverified_items)}.", summary

    return True, "All mandatory documents have successfully completed online human verification.", summary


def analyze_claim(claim_id: str) -> Dict[str, Any]:
    """
    Full end-to-end claim analysis pipeline:
    1. Reads claim, policy, and uploaded documents from database.
    2. Builds policy-grounded checklist by querying THAT policy's vector index (persisted once created).
    3. Merges per-item uploaded documents and verification results.
    4. Extracts facts from the incident description to satisfy remaining checklist items.
    5. Checks policy deadlines against elapsed incident date.
    6. Computes deterministic readiness score.
    7. Evaluates overall claim lifecycle stage and updates claim record in database.
    """
    claim = db.get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim not found: {claim_id}")

    policy_id = claim["policy_id"]
    incident_type = claim["incident_type"]
    incident_description = claim["incident_description"]
    incident_date = claim.get("incident_date", "")

    # Step 1: Check if checklist is already persisted
    persisted_checklist = []
    checklist_raw = claim.get("checklist_items")
    if checklist_raw:
        try:
            persisted_checklist = json.loads(checklist_raw) if isinstance(checklist_raw, str) else checklist_raw
        except Exception:
            persisted_checklist = []

    if not persisted_checklist:
        checklist_data = generate_checklist(claim_id, policy_id, incident_type, incident_description)
        checklist_items = checklist_data.get("checklist_items", [])
        policy_warnings = checklist_data.get("policy_warnings", [])
    else:
        checklist_items = persisted_checklist
        policy_warnings = []

    # Step 2: Fetch current claim documents from DB
    claim_docs = db.get_claim_documents(claim_id, is_current_only=True)

    # Index current documents by checklist_item_id
    doc_by_item: Dict[str, Dict[str, Any]] = {}
    unassigned_docs = []
    for doc in claim_docs:
        cid = doc.get("checklist_item_id", "")
        if cid:
            doc_by_item[cid] = doc
        else:
            unassigned_docs.append(doc)

    # For legacy or unassigned documents, run text heuristic matcher
    legacy_matched = {}
    if unassigned_docs:
        docs_with_text = _extract_document_texts(claim_id)
        unclaimed_items = [i for i in checklist_items if i.get("item_id") not in doc_by_item]
        matched_items = match_documents(unclaimed_items, docs_with_text)
        for mi in matched_items:
            legacy_matched[mi["item_id"]] = mi

    # Update checklist items with document statuses
    for item in checklist_items:
        iid = item.get("item_id", "")
        if iid in doc_by_item:
            d = doc_by_item[iid]
            d_status = d.get("status", "uploaded")
            d_review = d.get("review_status", "pending")

            if d_review in ("accepted", "human_verified"):
                item["status"] = "reviewed"
            elif d_review in ("info_required", "correction_required", "mismatch_confirmed", "human_rejected"):
                item["status"] = "needs_attention"
            elif d_status in ("ready_for_review", "needs_attention", "processing", "processing_failed"):
                item["status"] = d_status
            else:
                item["status"] = "ready_for_review"

            item["matched_document"] = d.get("filename")
            item["document_id"] = d.get("id")
            item["source"] = "uploaded_document"
            item["fulfillment_type"] = "uploaded_document"
            item["human_review_status"] = d_review
            try:
                item["extracted_summary"] = json.loads(d.get("extracted_data", "{}")) if isinstance(d.get("extracted_data"), str) else d.get("extracted_data", {})
                item["issues"] = json.loads(d.get("issues", "[]")) if isinstance(d.get("issues"), str) else d.get("issues", [])
            except Exception:
                pass
            item["notes"] = f"Document attached: {d.get('filename')}"
        elif iid in legacy_matched:
            lm = legacy_matched[iid]
            item["status"] = lm.get("status", item.get("status"))
            item["matched_document"] = lm.get("matched_document")
            item["evidence_excerpt"] = lm.get("evidence_excerpt")
            item["source"] = lm.get("source", item.get("source"))

    # Step 3: Extract facts from incident description for remaining missing items
    checklist_items = extract_facts_from_incident(incident_description, checklist_items)

    # Sanitize any physical documents / photos that were previously marked present from incident description
    for item in checklist_items:
        iid = (item.get("item_id") or "").lower()
        title = (item.get("title") or "").lower()
        if item.get("source") == "incident_description" and any(k in iid or k in title for k in [
            "photo", "photos", "damage", "licence", "license", "registration", "rc",
            "police", "fir", "bill", "bills", "invoice", "prescription", "copy"
        ]):
            item["status"] = "missing"
            item["matched_document"] = None
            item["evidence_excerpt"] = None
            item["source"] = "policy_requirement" if _is_item_mandatory(item) else "general_guidance"
            item["confidence"] = 0.0
            item["notes"] = f"Awaiting upload: {item.get('title')}"

    # Step 4: Check deadlines
    policy_warnings = _check_policy_deadlines(policy_warnings, incident_date)

    # Step 5: Compute deterministic readiness score
    readiness_score = calculate_readiness_score(checklist_items)

    total = len(checklist_items)
    present = sum(1 for i in checklist_items if i.get("status") in ("present", "ready_for_review", "reviewed"))
    unclear = sum(1 for i in checklist_items if i.get("status") in ("unclear", "needs_attention"))
    missing = sum(1 for i in checklist_items if i.get("status") in ("missing", "awaiting_upload", "processing_failed"))
    not_stated = sum(1 for i in checklist_items if i.get("status") in ("not_stated", "not_applicable"))

    # Determine overall claim status transition
    cur_status = claim.get("status", "draft")
    pv = db.get_physical_verification(claim_id)

    if pv and pv.get("status") in ("pending", "scheduled", "completed", "failed"):
        new_claim_status = f"physical_verification_{pv['status']}"
    elif any(d.get("status") in ("processing", "uploading") for d in claim_docs):
        new_claim_status = "documents_processing"
    else:
        # Check whether mandatory documents are fully reviewed online
        eligible, _, _ = can_request_physical_verification(claim_id)
        if eligible:
            new_claim_status = "online_review_completed"
        elif any(d.get("review_status") == "pending" for d in claim_docs):
            new_claim_status = "online_human_review"
        elif claim_docs:
            new_claim_status = "documents_pending"
        elif checklist_items:
            new_claim_status = "checklist_ready"
        else:
            new_claim_status = cur_status or "draft"

    # Step 6: Save back to DB
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE claims SET status = ?, checklist_items = ?, readiness_score = ? WHERE id = ?",
        (new_claim_status, json.dumps(checklist_items), readiness_score, claim_id)
    )
    conn.commit()
    conn.close()

    return {
        "checklist_items": checklist_items,
        "policy_warnings": policy_warnings,
        "readiness_score": readiness_score,
        "claim_status": new_claim_status,
        "summary": {
            "total": total,
            "present": present,
            "unclear": unclear,
            "missing": missing,
            "not_stated": not_stated,
        },
    }
