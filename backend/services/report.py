import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from config import settings
import db
from services.claims import analyze_claim


def _get_claim_data(claim_id: str) -> Dict[str, Any]:
    """Get all claim, policy, document, and analysis data needed for the report."""
    conn = db.get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
    claim_row = c.fetchone()
    if not claim_row:
        conn.close()
        raise ValueError(f"Claim not found: {claim_id}")

    claim = dict(claim_row)

    # If checklist items are empty or not analyzed yet, run analysis now
    checklist_raw = claim.get("checklist_items")
    checklist = []
    if checklist_raw:
        try:
            checklist = json.loads(checklist_raw)
        except Exception:
            checklist = []

    if not checklist or claim.get("status") in ("draft", "pending"):
        conn.close()
        analysis_result = analyze_claim(claim_id)
        checklist = analysis_result.get("checklist_items", [])
        policy_warnings = analysis_result.get("policy_warnings", [])
        readiness_score = analysis_result.get("readiness_score", 0)
    else:
        # Re-fetch warnings or calculate score
        from services.claims import calculate_readiness_score
        readiness_score = calculate_readiness_score(checklist)
        policy_warnings = []
        conn.close()

    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM policies WHERE id = ?", (claim["policy_id"],))
    policy_row = c.fetchone()
    policy = dict(policy_row) if policy_row else {}

    c.execute("SELECT * FROM claim_documents WHERE claim_id = ? ORDER BY created_at ASC", (claim_id,))
    documents = [dict(row) for row in c.fetchall()]
    conn.close()

    claim["checklist_items"] = checklist

    return {
        "claim": claim,
        "policy": policy,
        "documents": documents,
        "policy_warnings": policy_warnings,
        "readiness_score": readiness_score,
    }


def _ensure_report_dir(claim_id: str) -> Path:
    path = settings.REPORTS_DIR / claim_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_analysis_fingerprint(data: Dict[str, Any]) -> str:
    claim = data["claim"]
    checklist = claim.get("checklist_items", [])
    raw_str = f"{claim.get('id')}:{claim.get('incident_description')}:{len(checklist)}:{json.dumps(checklist, sort_keys=True)}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:8]


def generate_report_pdf(claim_id: str) -> str:
    """Generate a high quality, fully grounded PDF report using ReportLab."""
    data = _get_claim_data(claim_id)
    claim = data["claim"]
    policy = data["policy"]
    documents = data["documents"]
    checklist = claim.get("checklist_items", [])
    policy_warnings = data.get("policy_warnings", [])
    readiness_score = data.get("readiness_score", 0)

    report_dir = _ensure_report_dir(claim_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_path = str(report_dir / f"claim_{claim_id}_{timestamp}.pdf")
    latest_symlink = str(report_dir / "report.pdf")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    )

    pdf_doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#312e81'),
        alignment=0,
        spaceAfter=4
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e1b4b'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#334155'))
    bold_body = ParagraphStyle('DocBold', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#0f172a'))
    disclaimer_style = ParagraphStyle(
        'DocDisclaimer',
        parent=styles['Normal'],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#991b1b'),
        backColor=colors.HexColor('#fef2f2'),
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=8
    )
    footer_style = ParagraphStyle(
        'DocFooter',
        parent=styles['Normal'],
        fontSize=7.5,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )

    elements = []

    # 1. Header
    gen_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    elements.append(Paragraph("InsureWise AI — Claim Preparation Audit Report", title_style))
    elements.append(Paragraph(f"<b>Generated:</b> {gen_time} &nbsp;|&nbsp; <b>Claim ID:</b> <font name='Courier'>{claim_id}</font>", body_style))
    elements.append(Spacer(1, 6))

    # 2. Disclaimer
    disclaimer_html = (
        "<b>LEGAL & COMPLIANCE NOTICE:</b> This audit is prepared solely for pre-submission claim documentation and readiness assessment. "
        "InsureWise AI is not an insurance company, insurance broker, or claims loss adjuster. "
        "The insurer's policy terms, clauses, and underwriting decision remain final. Please confirm all details with your insurance provider."
    )
    elements.append(Paragraph(disclaimer_html, disclaimer_style))

    # 3. Policy & Incident Metadata Grid
    elements.append(Paragraph("Policy & Incident Overview", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=6))

    overview_table_data = [
        [
            Paragraph("<b>Policy Name:</b>", body_style),
            Paragraph(policy.get("display_name", "N/A"), bold_body),
            Paragraph("<b>Incident Type:</b>", body_style),
            Paragraph(claim.get("incident_type", "").replace("_", " ").title(), bold_body),
        ],
        [
            Paragraph("<b>Policy Type:</b>", body_style),
            Paragraph(str(policy.get("policy_type", "Standard")), body_style),
            Paragraph("<b>Incident Date:</b>", body_style),
            Paragraph(str(claim.get("incident_date", "Not specified")), body_style),
        ],
        [
            Paragraph("<b>Total Pages:</b>", body_style),
            Paragraph(str(policy.get("page_count", "N/A")), body_style),
            Paragraph("<b>Readiness Score:</b>", body_style),
            Paragraph(f"<b><font color='{'#15803d' if readiness_score>=80 else '#b45309' if readiness_score>=50 else '#b91c1c'}'>{readiness_score}%</font></b>", bold_body),
        ]
    ]
    t_overview = Table(overview_table_data, colWidths=[1.1*inch, 2.5*inch, 1.2*inch, 2.7*inch])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_overview)
    elements.append(Spacer(1, 6))

    # Incident Description
    elements.append(Paragraph("<b>Reported Incident Description:</b>", body_style))
    elements.append(Paragraph(claim.get("incident_description", "No description provided."), ParagraphStyle('DescBlock', parent=body_style, backColor=colors.HexColor('#f8fafc'), borderPadding=5)))
    elements.append(Spacer(1, 8))

    # 4. Document Checklist Table
    elements.append(Paragraph("Document & Evidence Checklist Audit", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=4))

    present_count = sum(1 for i in checklist if i.get("status") == "present")
    unclear_count = sum(1 for i in checklist if i.get("status") == "unclear")
    missing_count = sum(1 for i in checklist if i.get("status") == "missing")
    not_stated_count = sum(1 for i in checklist if i.get("status") in ("not_stated", "not_applicable"))

    summary_text = (
        f"<b>Audit Breakdown:</b> <font color='#16a34a'>{present_count} Present</font> &nbsp;|&nbsp; "
        f"<font color='#d97706'>{unclear_count} Needs Review</font> &nbsp;|&nbsp; "
        f"<font color='#dc2626'>{missing_count} Missing</font> &nbsp;|&nbsp; "
        f"<font color='#64748b'>{not_stated_count} Not Stated in Policy</font>"
    )
    elements.append(Paragraph(summary_text, body_style))
    elements.append(Spacer(1, 5))

    if checklist:
        headers = ["Requirement", "Status", "Source / Matched Evidence", "Policy Citation"]
        table_rows = [[Paragraph(f"<b>{h}</b>", ParagraphStyle('Th', parent=body_style, textColor=colors.white)) for h in headers]]

        for item in checklist:
            status = item.get("status", "missing").lower()
            status_label = {
                "present": "PRESENT",
                "unclear": "NEEDS REVIEW",
                "missing": "MISSING",
                "not_stated": "NOT STATED",
                "not_applicable": "N/A"
            }.get(status, status.upper())

            status_color = {
                "present": "#15803d",
                "unclear": "#b45309",
                "missing": "#b91c1c",
                "not_stated": "#64748b",
            }.get(status, "#64748b")

            # Evidence / matched
            evidence_parts = []
            if item.get("matched_document"):
                evidence_parts.append(f"<b>Doc:</b> {item['matched_document']}")
            if item.get("evidence_excerpt"):
                evidence_parts.append(f"“{item['evidence_excerpt'][:90]}”")
            if not evidence_parts:
                evidence_parts.append(item.get("notes", "No evidence submitted yet"))
            evidence_cell = "<br/>".join(evidence_parts)

            # Citations
            citations = item.get("policy_citations", [])
            cit_parts = []
            for cit in citations[:2]:
                cit_parts.append(f"<b>p. {cit.get('page', '?')}:</b> “{cit.get('quote', '')[:70]}…”")
            if not cit_parts:
                cit_parts.append("<font color='#94a3b8'>Not explicitly stated</font>")
            cit_cell = "<br/>".join(cit_parts)

            title_cell = f"<b>{item.get('title', 'Item')}</b><br/><font color='#64748b'>{item.get('why_needed', '')[:90]}</font>"
            status_cell = f"<b><font color='{status_color}'>{status_label}</font></b>"

            table_rows.append([
                Paragraph(title_cell, body_style),
                Paragraph(status_cell, body_style),
                Paragraph(evidence_cell, body_style),
                Paragraph(cit_cell, body_style),
            ])

        t_checklist = Table(table_rows, colWidths=[2.2*inch, 1.0*inch, 2.3*inch, 2.0*inch])
        t_checklist.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#312e81')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_checklist)
    else:
        elements.append(Paragraph("No checklist items generated.", body_style))

    elements.append(Spacer(1, 8))

    # 5. Policy Conditions, Exclusions & Warnings
    if policy_warnings:
        elements.append(KeepTogether([
            Paragraph("Policy Conditions, Exclusions & Deadlines", heading_style),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=4)
        ]))
        for w in policy_warnings[:5]:
            w_text = w.get("warning", "")
            w_page = w.get("page")
            w_type = w.get("type", "condition").upper()
            page_str = f" (Page {w_page})" if w_page else ""
            w_p = f"• <b>[{w_type}{page_str}]</b>: {w_text}"
            elements.append(Paragraph(w_p, body_style))
        elements.append(Spacer(1, 8))

    # 6. Uploaded Supporting Evidence & Recommended Next Steps
    missing_items = [i for i in checklist if i.get("status") in ("missing", "unclear")]
    if missing_items:
        elements.append(KeepTogether([
            Paragraph("Action Items Before Insurer Submission", heading_style),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=4)
        ]))
        for item in missing_items:
            req_title = item.get("title", "")
            act = item.get("notes") or f"Please obtain and upload {req_title} to satisfy policy requirements."
            elements.append(Paragraph(f"• <b>{req_title}</b>: {act}", body_style))
        elements.append(Spacer(1, 8))

    # 7. Uploaded Documents List
    elements.append(KeepTogether([
        Paragraph("Uploaded Documents & Proof of Loss", heading_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=4)
    ]))
    if documents:
        for doc_item in documents:
            d_name = doc_item.get("filename", "document.pdf")
            d_time = str(doc_item.get("created_at", ""))[:10]
            d_status = doc_item.get("status", "uploaded").replace("_", " ").title()
            d_review = doc_item.get("review_status", "")
            review_str = f" &bull; Review: <b>{d_review.replace('_', ' ').title()}</b>" if d_review else ""
            elements.append(Paragraph(f"• <b>{d_name}</b> (Uploaded: {d_time} &bull; Status: <b>{d_status}</b>{review_str})", body_style))
    else:
        elements.append(Paragraph("• No external supporting documents uploaded yet. Claim evaluated against incident statement and policy clauses.", body_style))

    elements.append(Spacer(1, 12))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceAfter=4))
    elements.append(Paragraph("Generated by InsureWise AI Policy Intelligence Platform &bull; Guidance Only &bull; All rights reserved", footer_style))

    pdf_doc.build(elements)

    # Overwrite report.pdf as latest symlink/copy for compatibility
    try:
        import shutil
        shutil.copyfile(file_path, latest_symlink)
    except Exception:
        pass

    return file_path


def generate_report_markdown(claim_id: str) -> str:
    """Generate Markdown report with actual claim and policy data."""
    data = _get_claim_data(claim_id)
    claim = data["claim"]
    policy = data["policy"]
    documents = data["documents"]
    checklist = claim.get("checklist_items", [])
    policy_warnings = data.get("policy_warnings", [])
    readiness_score = data.get("readiness_score", 0)

    report_dir = _ensure_report_dir(claim_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_path = str(report_dir / f"claim_{claim_id}_{timestamp}.md")
    latest_symlink = str(report_dir / "report.md")

    present_count = sum(1 for i in checklist if i.get("status") == "present")
    unclear_count = sum(1 for i in checklist if i.get("status") == "unclear")
    missing_count = sum(1 for i in checklist if i.get("status") == "missing")
    not_stated_count = sum(1 for i in checklist if i.get("status") in ("not_stated", "not_applicable"))

    lines = [
        f"# InsureWise AI — Claim Preparation Report",
        "",
        f"**Claim Reference:** `{claim_id}`",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "> **DISCLAIMER:** This report is advisory guidance generated by InsureWise AI for claim preparation. "
        "InsureWise AI does not process or settle claims. The insurance provider's policy terms and decisions are final.",
        "",
        "---",
        "",
        "## Policy & Incident Details",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Policy Name | **{policy.get('display_name', 'N/A')}** |",
        f"| Policy Type | {policy.get('policy_type', 'Standard')} |",
        f"| Policy Pages | {policy.get('page_count', 'N/A')} |",
        f"| Incident Type | {claim.get('incident_type', '').replace('_', ' ').title()} |",
        f"| Incident Date | {claim.get('incident_date', 'Not specified')} |",
        f"| Readiness Score | **{readiness_score}%** |",
        "",
        "### Incident Description",
        f"> {claim.get('incident_description', '')}",
        "",
        "---",
        "",
        "## Document Checklist & Policy Grounding",
        "",
        f"**Summary:** {present_count} Present | {unclear_count} Needs Review | {missing_count} Missing | {not_stated_count} Not Stated in Policy",
        "",
        "| Requirement | Status | Source / Evidence | Policy Citations |",
        "|-------------|--------|-------------------|------------------|",
    ]

    for item in checklist:
        status_emoji = {"present": "✅ PRESENT", "unclear": "⚠️ REVIEW", "missing": "❌ MISSING", "not_stated": "ℹ️ NOT STATED"}.get(item.get("status"), item.get("status", "").upper())
        ev = item.get("matched_document") or item.get("evidence_excerpt") or "-"
        ev_clean = str(ev).replace("\n", " ")[:60]
        cits = item.get("policy_citations", [])
        cit_str = "; ".join([f"Page {c.get('page')}: \"{c.get('quote','')[:40]}\"" for c in cits]) if cits else "Not explicitly stated"
        lines.append(f"| {item.get('title')} | {status_emoji} | {ev_clean} | {cit_str} |")

    if policy_warnings:
        lines.extend(["", "## Policy Conditions & Deadlines", ""])
        for w in policy_warnings:
            lines.append(f"- **[{w.get('type','').upper()}]**: {w.get('warning')} (Page {w.get('page', '?')})")

    lines.extend(["", "## Uploaded Documents", ""])
    if documents:
        for doc in documents:
            lines.append(f"- `{doc.get('filename')}` (uploaded: {str(doc.get('created_at'))[:10]})")
    else:
        lines.append("- *No documents uploaded yet.*")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    try:
        import shutil
        shutil.copyfile(file_path, latest_symlink)
    except Exception:
        pass

    return file_path
