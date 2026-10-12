import io
import pytest
from fastapi.testclient import TestClient
import reportlab.lib.pagesizes as ps
from reportlab.pdfgen import canvas

from main import app
from db import create_policy, update_policy, get_claim_audit_logs
from services import vector_store

client = TestClient(app)


def make_test_pdf(title: str, lines: list) -> io.BytesIO:
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
def workflow_policy_and_claim():
    pol_id = create_policy("motor_comprehensive_p1.pdf", "Motor Vehicle Comprehensive Policy", 2)
    update_policy(pol_id, status="ready", policy_type="Motor")
    vector_store.build_index(pol_id, [
        {"chunk_id": "m1", "page_start": 1, "page_end": 1, "text": "Motor claims require repair estimate, driving license, and police FIR if collision occurred."},
        {"chunk_id": "m2", "page_start": 2, "page_end": 2, "text": "Vehicular damage inspection and spot survey apply to severe collision."}
    ])

    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": "Vehicle crashed into a divider at high speed causing front-end and engine damage.",
        "incident_date": "2026-10-05",
        "claim_title": "Highway Collision Frontal Damage",
        "incident_details": {
            "vehicle_number": "KA-01-AB-1234",
            "driver_name": "Alex Mercer",
            "estimated_expenses": 75000
        }
    })
    assert res.status_code == 200, res.text
    claim = res.json()
    return pol_id, claim


def test_stage1_and_stage2_upload_validations_and_independence(workflow_policy_and_claim):
    _, claim = workflow_policy_and_claim
    claim_id = claim["id"]

    # 1. Reject 0-byte file
    empty_stream = io.BytesIO(b"")
    res_empty = client.post(
        f"/api/claims/{claim_id}/checklist/repair_estimate/documents",
        files={"file": ("empty.pdf", empty_stream, "application/pdf")}
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # 2. Reject non-PDF file extension
    txt_stream = io.BytesIO(b"Some text content")
    res_txt = client.post(
        f"/api/claims/{claim_id}/checklist/repair_estimate/documents",
        files={"file": ("notes.txt", txt_stream, "text/plain")}
    )
    assert res_txt.status_code == 400
    assert "only pdf" in res_txt.json()["detail"].lower()

    # 3. Reject corrupted / non-PDF header despite .pdf name
    fake_stream = io.BytesIO(b"GIF89a this is not a pdf file")
    res_fake = client.post(
        f"/api/claims/{claim_id}/checklist/repair_estimate/documents",
        files={"file": ("fake.pdf", fake_stream, "application/pdf")}
    )
    assert res_fake.status_code == 400
    fake_detail = res_fake.json()["detail"].lower()
    assert "invalid" in fake_detail and "pdf" in fake_detail

    # 4. Successful independent upload for repair_estimate
    repair_pdf = make_test_pdf(
        "AutoCare Workshop - Collision Repair Estimate",
        [
            "Vehicle: KA-01-AB-1234",
            "Bumper Replacement: INR 25000",
            "Radiator & Engine Support: INR 35000",
            "Labor Charges: INR 15000",
            "Total Amount: INR 75000"
        ]
    )
    res_upload = client.post(
        f"/api/claims/{claim_id}/checklist/repair_estimate/documents",
        files={"file": ("AutoCare_Estimate_Final.pdf", repair_pdf, "application/pdf")}
    )
    assert res_upload.status_code == 200
    doc_data = res_upload.json()
    doc_id = doc_data["id"]
    assert doc_data["filename"] == "AutoCare_Estimate_Final.pdf"
    assert doc_data["status"] == "ready_for_review"

    # 5. Verify Document PDF inline preview endpoint
    res_preview = client.get(f"/api/claims/{claim_id}/documents/{doc_id}/file")
    assert res_preview.status_code == 200
    assert res_preview.headers["content-type"] == "application/pdf"
    assert "inline" in res_preview.headers.get("content-disposition", "")
    assert len(res_preview.content) > 100

    # 6. Re-upload / Replacement archives the previous document
    repair_pdf_v2 = make_test_pdf(
        "AutoCare Workshop - Collision Repair Estimate V2",
        [
            "Vehicle: KA-01-AB-1234",
            "Bumper Replacement: INR 25000",
            "Radiator & Engine Support: INR 35000",
            "Labor Charges: INR 15000",
            "Total Amount: INR 75000"
        ]
    )
    res_replace = client.post(
        f"/api/claims/{claim_id}/checklist/repair_estimate/documents",
        files={"file": ("AutoCare_Estimate_V2.pdf", repair_pdf_v2, "application/pdf")}
    )
    assert res_replace.status_code == 200
    doc_v2_data = res_replace.json()
    assert doc_v2_data["filename"] == "AutoCare_Estimate_V2.pdf"
    assert doc_v2_data["id"] != doc_id

    # Verify claim state has new current document
    claim_state = client.get(f"/api/claims/{claim_id}").json()
    current_docs = claim_state.get("documents", [])
    matching_docs = [d for d in current_docs if d["checklist_item_id"] == "repair_estimate"]
    assert len(matching_docs) == 1
    assert matching_docs[0]["id"] == doc_v2_data["id"]


def test_human_review_authorization_and_validation(workflow_policy_and_claim):
    _, claim = workflow_policy_and_claim
    claim_id = claim["id"]

    # Upload driving license
    dl_pdf = make_test_pdf(
        "Transport Department - Driving Licence",
        [
            "Name: Alex Mercer",
            "Licence No: DL-KA-2018-00991",
            "Valid Till: 2038-05-10",
            "Vehicle Class: LMV"
        ]
    )
    res_upload = client.post(
        f"/api/claims/{claim_id}/checklist/driving_license/documents",
        files={"file": ("Driving_Licence_Alex.pdf", dl_pdf, "application/pdf")}
    )
    assert res_upload.status_code == 200
    doc_id = res_upload.json()["id"]

    # 1. Enforce reviewer authorization: Claimant attempting review should receive 403
    res_claimant_attempt = client.post(
        f"/api/claims/{claim_id}/documents/{doc_id}/review",
        json={
            "reviewer_name": "Claimant Alex",
            "reviewer_role": "claimant",
            "review_status": "accepted",
            "reviewer_notes": "Trying to approve my own document"
        }
    )
    assert res_claimant_attempt.status_code == 403
    assert "claimants" in res_claimant_attempt.json()["detail"].lower()
    assert "not authorized" in res_claimant_attempt.json()["detail"].lower()

    # 2. Reject missing notes when requesting correction or rejecting
    res_missing_notes = client.post(
        f"/api/claims/{claim_id}/documents/{doc_id}/review",
        json={
            "reviewer_name": "Officer Smith",
            "reviewer_role": "reviewer",
            "review_status": "info_required",
            "reviewer_notes": "   "  # whitespace only
        }
    )
    assert res_missing_notes.status_code == 400
    assert "mandatory" in res_missing_notes.json()["detail"].lower()

    # 3. Successful review with notes
    res_valid_review = client.post(
        f"/api/claims/{claim_id}/documents/{doc_id}/review",
        json={
            "reviewer_name": "Officer Smith (Claims Auditor)",
            "reviewer_role": "reviewer",
            "review_status": "accepted",
            "reviewer_notes": "Driver license valid and matches driver details in claim statement."
        }
    )
    assert res_valid_review.status_code == 200
    review_data = res_valid_review.json()
    assert review_data["review_status"] == "accepted"
    assert review_data["status"] == "reviewed"


def test_physical_verification_workflow_end_to_end(workflow_policy_and_claim):
    _, claim = workflow_policy_and_claim
    claim_id = claim["id"]

    # 1. Check physical verification eligibility before mandatory docs are reviewed
    res_elig_before = client.get(f"/api/claims/{claim_id}/physical-verification/eligibility")
    assert res_elig_before.status_code == 200
    data_elig_before = res_elig_before.json()
    assert data_elig_before["is_eligible"] is False
    assert len(data_elig_before["pending_mandatory_items"]) > 0

    # 2. Attempting to request physical verification must be rejected with 400
    res_bad_req = client.post(
        f"/api/claims/{claim_id}/physical-verification/request",
        json={
            "requested_by": "Officer Smith",
            "reviewer_role": "reviewer",
            "instructions": "Attempting early request"
        }
    )
    assert res_bad_req.status_code == 400
    assert "physical verification blocked" in res_bad_req.json()["detail"].lower()

    # 3. Fulfill and verify all mandatory checklist items
    claim_info = client.get(f"/api/claims/{claim_id}").json()
    mandatory_items = [
        i for i in claim_info["checklist_items"]
        if i.get("is_mandatory") is True or i.get("source") == "policy_requirement" or i.get("policy_citations")
    ]
    if not mandatory_items:
        mandatory_items = [i for i in claim_info["checklist_items"] if i.get("status") not in ("not_stated", "not_applicable")]

    for item in mandatory_items:
        item_id = item["item_id"]
        pdf_bytes = make_test_pdf(
            f"Official Document: {item['title']}",
            [
                f"Claim Ref: {claim_id}",
                f"Document Item: {item_id}",
                "Verified by Authority",
                "Total Amount: INR 75000",
                "Patient or Driver: Alex Mercer"
            ]
        )
        up_res = client.post(
            f"/api/claims/{claim_id}/checklist/{item_id}/documents",
            files={"file": (f"{item_id}_verified.pdf", pdf_bytes, "application/pdf")}
        )
        assert up_res.status_code == 200, up_res.text
        doc = up_res.json()

        # Review and accept
        rev_res = client.post(
            f"/api/claims/{claim_id}/documents/{doc['id']}/review",
            json={
                "reviewer_name": "Officer Smith",
                "reviewer_role": "reviewer",
                "review_status": "accepted",
                "reviewer_notes": f"Mandatory document {item['title']} fully verified online."
            }
        )
        assert rev_res.status_code == 200

    # 4. Check eligibility now - should be eligible!
    res_elig_after = client.get(f"/api/claims/{claim_id}/physical-verification/eligibility")
    assert res_elig_after.status_code == 200
    data_elig_after = res_elig_after.json()
    assert data_elig_after["is_eligible"] is True, f"Physical verification eligibility details: {data_elig_after}"
    assert len(data_elig_after["pending_mandatory_items"]) == 0

    # 5. Claimant attempting to request physical verification -> 403
    res_claimant_pv = client.post(
        f"/api/claims/{claim_id}/physical-verification/request",
        json={
            "requested_by": "Claimant Alex",
            "reviewer_role": "claimant",
            "instructions": "Claimant trying to request"
        }
    )
    assert res_claimant_pv.status_code == 403
    assert "claimants are not authorized" in res_claimant_pv.json()["detail"].lower()

    # 6. Authorized reviewer requests physical verification
    res_req_pv = client.post(
        f"/api/claims/{claim_id}/physical-verification/request",
        json={
            "requested_by": "Officer Smith",
            "reviewer_role": "reviewer",
            "instructions": "All documents verified online. On-site vehicle chassis inspection required."
        }
    )
    assert res_req_pv.status_code == 200
    pv_req_data = res_req_pv.json()
    assert pv_req_data["status"] == "pending"

    # Verify claim status updated to physical_verification_pending
    claim_after_pv = client.get(f"/api/claims/{claim_id}").json()
    assert claim_after_pv["status"] == "physical_verification_pending"
    assert claim_after_pv["physical_verification_status"] == "pending"

    # 7. Schedule appointment
    res_schedule = client.post(
        f"/api/claims/{claim_id}/physical-verification/schedule",
        json={
            "scheduled_date": "2026-10-18T10:00:00Z",
            "scheduled_location": "AutoCare Authorized Workshop, Bay 4, Bangalore",
            "assigned_inspector": "Eng. Rajesh Kumar (Senior Auto Surveyor)",
            "reviewer_name": "Officer Smith",
            "reviewer_role": "reviewer",
            "instructions": "Inspect vehicle frame, engine block alignment, and odometer reading."
        }
    )
    assert res_schedule.status_code == 200
    sched_data = res_schedule.json()
    assert sched_data["status"] == "scheduled"
    assert sched_data["assigned_inspector"] == "Eng. Rajesh Kumar (Senior Auto Surveyor)"

    claim_scheduled = client.get(f"/api/claims/{claim_id}").json()
    assert claim_scheduled["status"] == "physical_verification_scheduled"

    # 8. Complete physical verification outcome
    res_outcome = client.post(
        f"/api/claims/{claim_id}/physical-verification/outcome",
        json={
            "outcome_status": "completed",
            "outcome_notes": "Physical inspection successfully completed. Chassis damage confirmed consistent with claim.",
            "inspector_name": "Eng. Rajesh Kumar",
            "reviewer_role": "reviewer"
        }
    )
    assert res_outcome.status_code == 200
    outcome_data = res_outcome.json()
    assert outcome_data["status"] == "completed"

    claim_completed = client.get(f"/api/claims/{claim_id}").json()
    assert claim_completed["status"] == "physical_verification_completed"
    assert claim_completed["physical_verification_status"] == "completed"

    # 9. Audit trail verification
    res_audit = client.get(f"/api/claims/{claim_id}/audit-history")
    assert res_audit.status_code == 200
    audit_history = res_audit.json().get("audit_history", [])
    assert len(audit_history) >= 5

    event_types = [a["event_type"] for a in audit_history]
    assert "claim_created" in event_types
    assert "document_uploaded" in event_types
    assert "document_reviewed" in event_types
    assert "physical_verification_requested" in event_types
    assert "physical_verification_scheduled" in event_types
    assert "physical_verification_outcome_recorded" in event_types
