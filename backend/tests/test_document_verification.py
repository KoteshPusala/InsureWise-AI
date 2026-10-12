import pytest
import io
import pymupdf
from fastapi.testclient import TestClient
import reportlab.lib.pagesizes as ps
from reportlab.pdfgen import canvas

from main import app
from db import create_policy, update_policy
from services import vector_store

client = TestClient(app)


def make_pdf_bytes(title: str, lines: list) -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=ps.letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, title)
    c.setFont("Helvetica", 10)
    y = 690
    for line in lines:
        c.drawString(72, y, line)
        y -= 20
    c.save()
    buf.seek(0)
    return buf


@pytest.fixture
def sample_health_claim():
    pol_id = create_policy("test_health_policy.pdf", "Care Shield Health Comprehensive", 1)
    update_policy(pol_id, status="ready", policy_type="Health")
    vector_store.build_index(pol_id, [
        {"chunk_id": "c1", "page_start": 1, "page_end": 1, "text": "Hospitalization requires itemized hospital bills and discharge summary."},
        {"chunk_id": "c2", "page_start": 2, "page_end": 2, "text": "Claim form must be submitted within 30 days of discharge."}
    ])

    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "medical_health",
        "incident_description": "Hospitalized for acute appendicitis surgery for 3 days.",
        "incident_date": "2026-10-01",
        "claim_title": "Appendicitis Hospitalization Claim",
        "incident_details": {
            "hospital_name": "City Care Hospital",
            "admission_date": "2026-10-01",
            "discharge_date": "2026-10-04",
            "estimated_expenses": 45000
        }
    })
    assert res.status_code == 200, res.text
    return res.json()


def test_scenario_a_correct_item_upload_and_extraction(sample_health_claim):
    """Scenario A: User uploads hospital bill under hospital_bills item."""
    claim_id = sample_health_claim["id"]

    pdf_stream = make_pdf_bytes(
        "City Care Hospital - Inpatient Hospital Bill",
        [
            "Invoice No: CCH-2026-8812",
            "Date of Admission: 01-Oct-2026",
            "Date of Discharge: 04-Oct-2026",
            "Patient Name: John Doe",
            "Room Rent Charges 12000",
            "Surgery Operation Charges 25000",
            "Medicine Pharmacy Charges 8000",
            "Total Amount: INR 45000",
            "Amount Paid: INR 45000"
        ]
    )

    upload_res = client.post(
        f"/api/claims/{claim_id}/checklist/hospital_bills/documents",
        files={"file": ("Hospital_Bill_Final.pdf", pdf_stream, "application/pdf")}
    )
    assert upload_res.status_code == 200, upload_res.text
    doc_data = upload_res.json()

    # Stage B: Classification check
    assert doc_data["classification"]["detected_type"] == "hospital_bills"
    assert doc_data["classification"]["is_mismatch"] is False

    # Stage C: Structured field extraction
    extracted = doc_data["extracted_data"]
    assert extracted.get("patient_name") == "John Doe"
    assert extracted.get("total_amount") == 45000.0

    # Stage D & E: Lifecycle status
    assert doc_data["status"] == "ready_for_review"

    # Verify claim checklist updated
    claim_res = client.get(f"/api/claims/{claim_id}").json()
    bill_item = next((i for i in claim_res["checklist_items"] if i["item_id"] == "hospital_bills"), None)
    assert bill_item is not None
    assert bill_item["status"] == "ready_for_review"
    assert bill_item["matched_document"] == "Hospital_Bill_Final.pdf"


def test_scenario_b_document_mismatch_and_reassign(sample_health_claim):
    """Scenario B: User uploads hospital bill under discharge_summary item."""
    claim_id = sample_health_claim["id"]

    # Hospital bill uploaded under discharge summary
    pdf_stream = make_pdf_bytes(
        "City Care Hospital Tax Invoice and Bill",
        [
            "Bill No: INV-4491",
            "Patient: John Doe",
            "Bed Charges 15000",
            "Total Amount: INR 15000"
        ]
    )

    upload_res = client.post(
        f"/api/claims/{claim_id}/checklist/discharge_summary/documents",
        files={"file": ("Bill_Misplaced.pdf", pdf_stream, "application/pdf")}
    )
    assert upload_res.status_code == 200
    doc_data = upload_res.json()

    # Must detect mismatch!
    assert doc_data["classification"]["is_mismatch"] is True
    assert doc_data["status"] == "needs_attention"
    assert doc_data["classification"]["suggested_item_id"] == "hospital_bills"

    # Now test reassign endpoint
    reassign_res = client.post(
        f"/api/claims/{claim_id}/documents/{doc_data['id']}/reassign",
        json={"checklist_item_id": "hospital_bills"}
    )
    assert reassign_res.status_code == 200
    reassigned_data = reassign_res.json()
    assert reassigned_data["checklist_item_id"] == "hospital_bills"
    assert reassigned_data["classification"]["is_mismatch"] is False


def test_scenario_c_arithmetic_discrepancy_detection(sample_health_claim):
    """Scenario C: Arithmetic check flags discrepancy when itemized sum != declared total."""
    claim_id = sample_health_claim["id"]

    pdf_stream = make_pdf_bytes(
        "Hospital Inpatient Bill",
        [
            "Room rent 10000",
            "Nursing charges 5000",
            # Sum is 15000, but declared total is 25000 (diff 10000)
            "Total Amount: INR 25000"
        ]
    )

    upload_res = client.post(
        f"/api/claims/{claim_id}/checklist/hospital_bills/documents",
        files={"file": ("Bill_Math_Error.pdf", pdf_stream, "application/pdf")}
    )
    assert upload_res.status_code == 200
    doc_data = upload_res.json()

    # Discrepancy detected
    issues = doc_data["issues"]
    math_issue = next((i for i in issues if i["type"] == "arithmetic_mismatch"), None)
    assert math_issue is not None
    assert doc_data["status"] == "needs_attention"


def test_scenario_d_independent_uploads_and_readiness_score(sample_health_claim):
    """Scenario D: Independent uploads update only their card and increase readiness deterministically."""
    claim_id = sample_health_claim["id"]

    claim_before = client.get(f"/api/claims/{claim_id}").json()
    score_before = claim_before["readiness_score"]

    # Upload document for pharmacy_bills
    pdf_stream = make_pdf_bytes(
        "Apollo Pharmacy Medical Store Bill",
        [
            "Patient Name: John Doe",
            "Medicine items: Paracetamol, Antibiotics",
            "Total Amount: INR 3500",
            "Amount Paid: INR 3500"
        ]
    )

    client.post(
        f"/api/claims/{claim_id}/checklist/pharmacy_bills/documents",
        files={"file": ("Pharmacy_Bill.pdf", pdf_stream, "application/pdf")}
    )

    claim_after = client.get(f"/api/claims/{claim_id}").json()
    score_after = claim_after["readiness_score"]

    # Readiness score must increase
    assert score_after > score_before

    # pharmacy_bills card updated
    pharm_item = next(i for i in claim_after["checklist_items"] if i["item_id"] == "pharmacy_bills")
    assert pharm_item["status"] == "ready_for_review"

    # discharge_summary remains unfulfilled (missing/awaiting_upload)
    disch_item = next(i for i in claim_after["checklist_items"] if i["item_id"] == "discharge_summary")
    assert disch_item["status"] in ("missing", "awaiting_upload")


def test_scenario_e_human_review_workflow(sample_health_claim):
    """Scenario E: Document enters review queue; reviewer accepts it; audit trail records outcome."""
    claim_id = sample_health_claim["id"]

    pdf_stream = make_pdf_bytes(
        "City Care Hospital - Discharge Summary",
        [
            "Patient: John Doe",
            "Admission: 01-Oct-2026",
            "Discharge: 04-Oct-2026",
            "Diagnosis: Acute appendicitis with localized peritonitis",
            "Treatment: Laparoscopic appendectomy performed under general anesthesia."
        ]
    )

    upload_res = client.post(
        f"/api/claims/{claim_id}/checklist/discharge_summary/documents",
        files={"file": ("Discharge_Summary_Signed.pdf", pdf_stream, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # 1. Inspect Review Queue
    queue_res = client.get(f"/api/claims/{claim_id}/review-queue").json()
    assert any(d["id"] == doc_id for d in queue_res["queue"])

    # 2. Record Reviewer Decision
    review_res = client.post(
        f"/api/claims/{claim_id}/documents/{doc_id}/review",
        json={
            "reviewer_name": "Dr. Sarah Jenkins (Senior Medical Reviewer)",
            "review_status": "accepted",
            "reviewer_notes": "All clinical dates and surgical diagnosis verified against incident statement."
        }
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()
    assert rev_data["review_status"] == "accepted"
    assert rev_data["status"] == "reviewed"
    assert "Dr. Sarah Jenkins" in rev_data["reviewer_name"]

    # 3. Verify Claim Checklist reflects human review
    claim_res = client.get(f"/api/claims/{claim_id}").json()
    item = next(i for i in claim_res["checklist_items"] if i["item_id"] == "discharge_summary")
    assert item["status"] == "reviewed"
    assert item["human_review_status"] == "accepted"
