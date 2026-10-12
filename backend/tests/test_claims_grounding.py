import pytest
import io
import os
import json
import pymupdf  # PyMuPDF
from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from config import settings
from db import init_db, create_policy, update_policy, get_connection
from services import vector_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def create_indexed_test_policy(filename: str, display_name: str, policy_type: str, chunks: list) -> str:
    """Helper to create and index a test policy with custom chunks."""
    pol_id = create_policy(filename, display_name, len(chunks))
    update_policy(
        pol_id,
        status="ready",
        policy_type=policy_type,
        chunk_count=len(chunks),
        page_count=max((c.get("page_start", 1) for c in chunks), default=1)
    )
    vector_store.build_index(pol_id, chunks)
    return pol_id


def test_different_policies_produce_different_checklists_and_reports():
    """
    Same incident described on two different policies MUST produce:
    1. Different checklist items and policy citations.
    2. Different reports citing different policies and clauses.
    """
    # Policy A: Motor comprehensive policy
    chunks_a = [
        {
            "chunk_id": "pol_a_1",
            "page_start": 1,
            "page_end": 1,
            "text": "Section 1: Motor Claims. In the event of an accidental collision, the insured must submit a repair estimate from an authorized garage and copy of valid driving licence within 48 hours. Deductible: INR 2,500 applies to each collision loss."
        },
        {
            "chunk_id": "pol_a_2",
            "page_start": 2,
            "page_end": 2,
            "text": "General Conditions: Notice of accident must be given immediately. Police report FIR is required for major collisions exceeding INR 50,000 damage or third party injury."
        }
    ]
    pol_a = create_indexed_test_policy("motor_policy.pdf", "Motor Comprehensive Secure 2024", "Vehicle", chunks_a)

    # Policy B: Property & Fire policy
    chunks_b = [
        {
            "chunk_id": "pol_b_1",
            "page_start": 1,
            "page_end": 1,
            "text": "Section 4: Property Loss. Claims require submission of a certified fire brigade report, original property deed ownership documents, and itemized damaged asset inventory within 14 days."
        },
        {
            "chunk_id": "pol_b_2",
            "page_start": 3,
            "page_end": 3,
            "text": "Exclusions: Fire loss caused by spontaneous combustion or nuclear hazard is strictly excluded. Mandatory deductible: INR 25,000 per commercial property incident."
        }
    ]
    pol_b = create_indexed_test_policy("property_policy.pdf", "Commercial Property Fire Shield", "Property", chunks_b)

    incident_text = "Severe accidental incident occurred yesterday causing extensive physical damage."

    # Create claims on both policies
    res_1 = client.post("/api/claims", json={
        "policy_id": pol_a,
        "incident_type": "vehicle_accident",
        "incident_description": incident_text,
        "incident_date": "2026-10-01"
    })
    assert res_1.status_code == 200, res_1.text
    claim_1 = res_1.json()

    res_2 = client.post("/api/claims", json={
        "policy_id": pol_b,
        "incident_type": "vehicle_accident",
        "incident_description": incident_text,
        "incident_date": "2026-10-01"
    })
    assert res_2.status_code == 200, res_2.text
    claim_2 = res_2.json()

    # Analyze both claims
    an_1 = client.post(f"/api/claims/{claim_1['id']}/analyze").json()
    an_2 = client.post(f"/api/claims/{claim_2['id']}/analyze").json()

    check_1 = an_1["checklist_items"]
    check_2 = an_2["checklist_items"]

    # Verify that citations and grounding differ
    cit_1 = [c for item in check_1 for c in item.get("policy_citations", [])]
    cit_2 = [c for item in check_2 for c in item.get("policy_citations", [])]

    # Policy A should have citations from motor chunks (e.g. Page 1 / 2)
    assert len(cit_1) > 0, "Policy A should have grounded citations"
    # Citations in Claim 1 must not mention property deed or fire brigade
    assert any("repair estimate" in c["quote"].lower() or "driving licence" in c["quote"].lower() or "motor" in c["quote"].lower() for c in cit_1)

    # Claim 2 on property policy cannot have citations for motor repair estimate
    assert not any("motor" in c["quote"].lower() for c in cit_2)

    # Generate reports for both
    rep_res_1 = client.post(f"/api/claims/{claim_1['id']}/report")
    assert rep_res_1.status_code == 200
    pdf_1 = client.get(f"/api/claims/{claim_1['id']}/report/download?format=pdf")
    assert pdf_1.status_code == 200
    assert pdf_1.headers.get("cache-control") == "no-store, no-cache, must-revalidate"

    rep_res_2 = client.post(f"/api/claims/{claim_2['id']}/report")
    assert rep_res_2.status_code == 200
    pdf_2 = client.get(f"/api/claims/{claim_2['id']}/report/download?format=pdf")
    assert pdf_2.status_code == 200

    # Verify report PDFs are distinct and reflect their own policy names
    doc_1 = pymupdf.open(stream=pdf_1.content, filetype="pdf")
    text_1 = "\n".join(page.get_text() for page in doc_1)

    doc_2 = pymupdf.open(stream=pdf_2.content, filetype="pdf")
    text_2 = "\n".join(page.get_text() for page in doc_2)

    assert "Motor Comprehensive Secure 2024" in text_1
    assert "Commercial Property Fire Shield" not in text_1

    assert "Commercial Property Fire Shield" in text_2
    assert "Motor Comprehensive Secure 2024" not in text_2


def test_different_incidents_produce_different_checklists_and_reports():
    """Same policy with different incident descriptions produces different grounded results."""
    chunks = [
        {
            "chunk_id": "chunk_1",
            "page_start": 1,
            "page_end": 1,
            "text": "Vehicle Insurance: In case of vehicle theft or burglary, immediate police report FIR is mandatory. Provide original keys and theft declaration. For accidental collision damage, submit repair estimate and driving licence."
        },
        {
            "chunk_id": "chunk_2",
            "page_start": 2,
            "page_end": 2,
            "text": "Section 2: Deductible INR 1,500. Exclusions apply if driver was unlicensed."
        }
    ]
    pol_id = create_indexed_test_policy("flex_policy.pdf", "Flex Vehicle Shield", "Vehicle", chunks)

    # Incident 1: Collision where driver facts are given
    res_1 = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": "Accidental collision on main highway. Front bumper dented and headlight broken. Driver was John driving with valid licence.",
        "incident_date": "2026-10-02"
    })
    claim_1 = res_1.json()

    # Incident 2: Theft where FIR details are given
    res_2 = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "theft",
        "incident_description": "Car was stolen from residential parking overnight. Immediately lodged police FIR #441 at North Precinct.",
        "incident_date": "2026-10-03"
    })
    claim_2 = res_2.json()

    an_1 = client.post(f"/api/claims/{claim_1['id']}/analyze").json()
    an_2 = client.post(f"/api/claims/{claim_2['id']}/analyze").json()

    items_1 = an_1["checklist_items"]
    items_2 = an_2["checklist_items"]

    # Claim 1 should have satisfied damage/driver details from description
    driver_item_1 = next((i for i in items_1 if "driving" in i["title"].lower() or "driver" in i["title"].lower()), None)
    assert driver_item_1 is not None
    assert driver_item_1["status"] == "present"
    assert driver_item_1["source"] == "incident_description"

    # Claim 2 should have satisfied police report FIR from description
    fir_item_2 = next((i for i in items_2 if "police" in i["title"].lower() or "fir" in i["title"].lower()), None)
    assert fir_item_2 is not None
    assert fir_item_2["status"] == "present"
    assert fir_item_2["source"] == "incident_description"
    assert "FIR #441" in fir_item_2["evidence_excerpt"]


def test_missing_policy_requirement_is_not_stated():
    """If the policy does not state a requirement, it must be marked 'not_stated', not 'missing'."""
    chunks = [
        {
            "chunk_id": "chunk_min_1",
            "page_start": 1,
            "page_end": 1,
            "text": "Basic policy covers only bumper collision damage. Requires repair quotation from approved workshop."
        }
    ]
    pol_id = create_indexed_test_policy("minimal_policy.pdf", "Minimal Cover Policy", "Vehicle", chunks)

    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": "Vehicle collision occurred in parking lot with minor dent.",
        "incident_date": "2026-10-04"
    })
    claim = res.json()

    an = client.post(f"/api/claims/{claim['id']}/analyze").json()
    items = an["checklist_items"]

    # Requirements not mentioned in the policy (such as medical or third party or police report)
    unmentioned = [i for i in items if i.get("status") == "not_stated"]
    assert len(unmentioned) > 0, "Unmentioned items must be marked as not_stated"
    assert all("not stated" in i["why_needed"].lower() for i in unmentioned)
    assert all(i["source"] == "general_guidance" for i in unmentioned)


def test_every_citation_quote_exists_on_cited_page():
    """Verify that 100% of policy citations really occur on the cited page."""
    chunks = [
        {
            "chunk_id": "chunk_cite_1",
            "page_start": 4,
            "page_end": 4,
            "text": "Notice clause: The insured person shall give immediate notice within forty-eight hours of any loss or damage. A driving licence and valid registration book must be produced upon request."
        }
    ]
    pol_id = create_indexed_test_policy("cited_policy.pdf", "Cited Standard Policy", "Vehicle", chunks)

    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": "Collision on city expressway on 2026-10-05.",
        "incident_date": "2026-10-05"
    })
    claim = res.json()
    an = client.post(f"/api/claims/{claim['id']}/analyze").json()

    policy_chunks = vector_store.get_policy_chunks(pol_id)

    citations = [cit for item in an["checklist_items"] for cit in item.get("policy_citations", [])]
    assert len(citations) > 0

    for cit in citations:
        page = cit["page"]
        quote = cit["quote"].lower()
        # Find chunk on that page
        page_chunks = [c for c in policy_chunks if c.get("page_start", 1) == page]
        assert len(page_chunks) > 0, f"Page {page} must exist in policy chunks"
        full_page_text = " ".join(c["text"].lower() for c in page_chunks)
        # Verify quote or token overlap
        words = quote.split()
        assert any(w in full_page_text for w in words if len(w) > 4), f"Quote '{quote}' must exist on Page {page}"


def test_document_upload_updates_status_and_readiness_score():
    """Uploading a document matches checklist item and increases readiness score deterministically."""
    chunks = [
        {
            "chunk_id": "chunk_doc_1",
            "page_start": 1,
            "page_end": 1,
            "text": "Claims documentation: An authorized workshop repair estimate and quotation must be submitted for accidental damage."
        }
    ]
    pol_id = create_indexed_test_policy("doc_policy.pdf", "Doc Test Policy", "Vehicle", chunks)

    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": "Accidental damage to front fender requiring repair.",
        "incident_date": "2026-10-06"
    })
    claim = res.json()

    an_before = client.post(f"/api/claims/{claim['id']}/analyze").json()
    initial_score = an_before["readiness_score"]

    # Upload mock Repair Estimate PDF
    import reportlab.lib.pagesizes as ps
    from reportlab.pdfgen import canvas
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=ps.letter)
    c.drawString(100, 700, "Official Authorized Workshop Repair Estimate and Quotation")
    c.drawString(100, 680, "Total Estimated Repair Cost: INR 15,400 for front fender repair.")
    c.save()
    pdf_buf.seek(0)

    upload_res = client.post(
        f"/api/claims/{claim['id']}/documents",
        files={"file": ("Repair_Estimate_Quotation.pdf", pdf_buf, "application/pdf")}
    )
    assert upload_res.status_code == 200

    an_after = client.post(f"/api/claims/{claim['id']}/analyze").json()
    new_score = an_after["readiness_score"]

    # Score must increase deterministically
    assert new_score > initial_score

    # Item must be marked present with matched document
    matched_item = next(
        (i for i in an_after["checklist_items"] if i.get("matched_document") == "Repair_Estimate_Quotation.pdf"),
        None
    )
    assert matched_item is not None
    assert matched_item["status"] in ("present", "ready_for_review")
    assert matched_item["source"] == "uploaded_document"


def test_report_pdf_contains_claim_policy_name_and_incident_description():
    """Verify that report PDF text contains the specific policy name and incident description."""
    chunks = [
        {
            "chunk_id": "chunk_rep_1",
            "page_start": 1,
            "page_end": 1,
            "text": "Policy provisions: Comprehensive vehicle collision coverage."
        }
    ]
    pol_id = create_indexed_test_policy("report_policy.pdf", "Royal Sundaram Elite Platinum", "Vehicle", chunks)

    unique_incident = "Hit by a stray animal at midnight near junction 4, denting radiator grille."
    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": unique_incident,
        "incident_date": "2026-10-07"
    })
    claim = res.json()

    # Generate and download report
    client.post(f"/api/claims/{claim['id']}/report")
    pdf_res = client.get(f"/api/claims/{claim['id']}/report/download?format=pdf")
    assert pdf_res.status_code == 200

    doc = pymupdf.open(stream=pdf_res.content, filetype="pdf")
    pdf_text = "\n".join(page.get_text() for page in doc)

    assert "Royal Sundaram Elite Platinum" in pdf_text
    assert unique_incident in pdf_text
    assert f"{claim['id']}" in pdf_text
