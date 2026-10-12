import pytest
import os
import io
import fitz  # PyMuPDF
from fastapi.testclient import TestClient

from main import app
from config import settings
from db import init_db, create_policy, update_policy, create_claim, get_connection
from services import vector_store, report

client = TestClient(app)


def test_report_generation_with_zero_documents():
    """Report generation must succeed when a claim has 0 uploaded documents."""
    pol_id = create_policy("test_zero_docs_policy.pdf", "Zero Docs Policy", 1)
    update_policy(pol_id, status="ready", policy_type="Vehicle")
    vector_store.build_index(pol_id, [{
        "chunk_id": "c1", "page_start": 1, "page_end": 1,
        "text": "Vehicle claim requires notification within 48 hours."
    }])

    claim_id = create_claim(
        pol_id,
        "Car fender scratched while parking at the supermarket.",
        "vehicle_accident",
        "2026-10-01"
    )

    # Generate PDF report
    pdf_path = report.generate_report_pdf(claim_id)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000

    # Verify readable with PyMuPDF
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    assert "Zero Docs Policy" in text
    assert "supermarket" in text
    assert "No external supporting documents uploaded yet" in text


def test_report_generation_with_multiple_documents_regression():
    """
    REGRESSION TEST for: 'dict' object has no attribute 'build'
    When documents are uploaded and exist in claim_documents, report.generate_report_pdf()
    must build the ReportLab PDF without throwing an AttributeError.
    """
    pol_id = create_policy("test_multidoc_policy.pdf", "Multi-Doc Comprehensive Policy", 1)
    update_policy(pol_id, status="ready", policy_type="Vehicle")
    vector_store.build_index(pol_id, [{
        "chunk_id": "c1", "page_start": 1, "page_end": 1,
        "text": "Collision damage requires repair estimate quotation."
    }])

    claim_id = create_claim(
        pol_id,
        "Severe highway collision damage to bumper and radiator.",
        "vehicle_accident",
        "2026-10-02"
    )

    # Insert multiple documents into claim_documents
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO claim_documents (id, claim_id, filename, page_count, extracted_text_preview, doc_type_guess, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("doc-1", claim_id, "Workshop_Repair_Estimate.pdf", 2, "Estimate amount 45000", "estimate", "2026-10-02T10:00:00Z"))
    c.execute("""
        INSERT INTO claim_documents (id, claim_id, filename, page_count, extracted_text_preview, doc_type_guess, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("doc-2", claim_id, "Police_FIR_Report.pdf", 1, "FIR filed for road accident", "fir", "2026-10-02T11:00:00Z"))
    conn.commit()
    conn.close()

    # This MUST succeed and not raise 'dict' object has no attribute 'build'
    pdf_path = report.generate_report_pdf(claim_id)
    assert os.path.exists(pdf_path)

    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    assert "Workshop_Repair_Estimate.pdf" in text
    assert "Police_FIR_Report.pdf" in text
    assert "Multi-Doc Comprehensive Policy" in text


def test_report_download_api_endpoint_with_documents():
    """Verify the API endpoint /api/claims/{id}/report returns valid downloadable PDF."""
    pol_id = create_policy("test_api_rep_policy.pdf", "API Report Policy", 1)
    update_policy(pol_id, status="ready", policy_type="Vehicle")
    vector_store.build_index(pol_id, [{
        "chunk_id": "c1", "page_start": 1, "page_end": 1,
        "text": "General accidental damage coverage terms."
    }])

    res = client.post("/api/claims", json={
        "policy_id": pol_id,
        "incident_type": "vehicle_accident",
        "incident_description": "Rear-end collision at traffic signal with minor dent.",
        "incident_date": "2026-10-03"
    })
    assert res.status_code == 200
    claim_id = res.json()["id"]

    # Upload mock document
    import reportlab.lib.pagesizes as ps
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    canv = canvas.Canvas(buf, pagesize=ps.letter)
    canv.drawString(100, 700, "Official Workshop Estimate Bill")
    canv.save()
    buf.seek(0)

    client.post(
        f"/api/claims/{claim_id}/documents",
        files={"file": ("Official_Estimate.pdf", buf, "application/pdf")}
    )

    # Request report generation
    rep_res = client.post(f"/api/claims/{claim_id}/report")
    assert rep_res.status_code == 200, rep_res.text
    data = rep_res.json()
    assert "report_url" in data

    # Download report
    dl_res = client.get(f"/api/claims/{claim_id}/report/download?format=pdf")
    assert dl_res.status_code == 200
    assert dl_res.headers.get("content-type") == "application/pdf"

    doc = fitz.open(stream=dl_res.content, filetype="pdf")
    pdf_text = "\n".join(page.get_text() for page in doc)
    assert "API Report Policy" in pdf_text
    assert "Official_Estimate.pdf" in pdf_text


def test_markdown_report_generation():
    """Verify Markdown report generation works accurately."""
    pol_id = create_policy("test_md_policy.pdf", "Markdown Test Policy", 1)
    update_policy(pol_id, status="ready", policy_type="Property")
    vector_store.build_index(pol_id, [{
        "chunk_id": "c1", "page_start": 1, "page_end": 1,
        "text": "Property fire coverage terms."
    }])

    claim_id = create_claim(
        pol_id,
        "Electrical fire incident in warehouse facility.",
        "fire_property_damage",
        "2026-10-04"
    )

    md_path = report.generate_report_markdown(claim_id)
    assert os.path.exists(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    assert "Markdown Test Policy" in md_content
    assert "Electrical fire incident" in md_content
    assert "DISCLAIMER" in md_content
