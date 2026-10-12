import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def draw_watermark(canvas, doc, text):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 45)
    canvas.setFillGray(0.8)
    canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, text)
    canvas.restoreState()

def watermark_policy(canvas, doc):
    draw_watermark(canvas, doc, 'SYNTHETIC SAMPLE: NOT A REAL POLICY')

def watermark_doc(canvas, doc):
    draw_watermark(canvas, doc, 'SYNTHETIC DOCUMENT')

def watermark_mismatch(canvas, doc):
    draw_watermark(canvas, doc, 'SYNTHETIC DOCUMENT - INTENTIONAL MISMATCH')

def generate_samples():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = TA_CENTER
    h2_style = styles['Heading2']
    h3_style = styles['Heading3']
    normal_style = styles['Normal']
    justify_style = ParagraphStyle('Justify', parent=styles['Normal'], alignment=TA_JUSTIFY, spaceAfter=10)
    
    # 1. sample_vehicle_policy.pdf
    policy_path = os.path.join(output_dir, 'sample_vehicle_policy.pdf')
    doc_policy = SimpleDocTemplate(policy_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    
    elements = []
    # Page 1 - Policy Schedule
    elements.append(Paragraph("INSUREWISE AI INSURANCE POLICY SCHEDULE", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    data = [
        ["Policy Number:", "INSW/VEH/2024/001234"],
        ["Insured Name:", "Rajesh Kumar"],
        ["Vehicle:", "2022 Honda City (Reg: MH-01-AB-1234)"],
        ["Policy Period:", "01-Jan-2024 to 31-Dec-2024"],
        ["Sum Insured (IDV):", "INR 8,50,000"],
        ["Deductible/Excess:", "INR 2,500"],
        ["Premium:", "INR 15,750"],
        ["No Claim Bonus (NCB):", "20%"],
        ["Coverage Type:", "Comprehensive"]
    ]
    
    t = Table(data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(PageBreak())
    
    # Page 2 - Definitions
    elements.append(Paragraph("Part II: Definitions", title_style))
    definitions = [
        ("Accident", "A sudden, unforeseen, and unexpected physical event caused by external, visible, and violent means."),
        ("Insured Vehicle", "The vehicle described in the Policy Schedule for which premium has been paid."),
        ("Third Party", "Any person or entity other than the Insured and the Insurer."),
        ("Constructive Total Loss (CTL)", "When the aggregate cost of retrieval and/or repair of the vehicle exceeds 75% of the Insured Declared Value (IDV)."),
        ("Market Value", "The value of the vehicle at the time of the loss after factoring in depreciation.")
    ]
    for term, definition in definitions:
        elements.append(Paragraph(f"<b>{term}:</b> {definition}", justify_style))
    elements.append(PageBreak())
    
    # Page 3 - Coverage Section
    elements.append(Paragraph("Part III: Coverage Section", title_style))
    elements.append(Paragraph("<b>Section A: Own Damage</b>", h2_style))
    elements.append(Paragraph("The Company will indemnify the Insured against loss or damage to the vehicle and/or its accessories whilst thereon by: accidental damage, fire, explosion, self-ignition or lightning; burglary, housebreaking or theft; riot and strike; earthquake (fire and shock damage); flood, typhoon, hurricane, storm, tempest, inundation, cyclone, hailstorm, frost; accidental external means; malicious act; terrorist activity; whilst in transit by road, rail, inland waterway, lift, elevator or air.", justify_style))
    
    elements.append(Paragraph("<b>Section B: Third Party Liability</b>", h2_style))
    elements.append(Paragraph("The Company will indemnify the Insured in the event of an accident caused by or arising out of the use of the vehicle against all sums which the Insured shall become legally liable to pay in respect of: death of or bodily injury to any person; damage to property other than property belonging to the Insured.", justify_style))
    
    elements.append(Paragraph("<b>Section C: Personal Accident Cover</b>", h2_style))
    elements.append(Paragraph("The Company undertakes to pay compensation for bodily injury/death sustained by the Owner-Driver. Coverage limit: INR 15,00,000.", justify_style))
    elements.append(PageBreak())
    
    # Page 4 - Exclusions
    elements.append(Paragraph("Part IV: Exclusions", title_style))
    exclusions = [
        "Driving under influence of alcohol or drugs.",
        "Unlicensed driver or driver without a valid driving license.",
        "Normal wear and tear, and depreciation.",
        "Mechanical or electrical breakdown, failures or breakages.",
        "Consequential loss of any nature.",
        "Racing, pacemaking, reliability trial or speed testing.",
        "War, invasion, act of foreign enemy, hostilities, civil war, mutiny, rebellion or nuclear risks.",
        "Using the vehicle for purposes other than those stated in the limitations as to use.",
        "Modifications or accessories not declared to the insurer.",
        "Pre-existing damage prior to the inception of this policy."
    ]
    for ex in exclusions:
        elements.append(Paragraph(f"• {ex}", justify_style))
    elements.append(PageBreak())
    
    # Page 5 - Claim Procedure
    elements.append(Paragraph("Part V: Claim Procedure", title_style))
    elements.append(Paragraph("<b>Notification</b>", h2_style))
    elements.append(Paragraph("Notice of any claim must be given to the Company within 48 hours of occurrence of the event, except for theft claims which must be reported within 24 hours.", justify_style))
    
    elements.append(Paragraph("<b>Required Documents</b>", h2_style))
    docs = [
        "Completed and signed claim form.",
        "FIR/Police report for theft or third-party claims.",
        "Copy of valid driving licence.",
        "Copy of Registration Certificate (RC).",
        "Repair estimate from authorized workshop.",
        "Photographs of damage.",
        "Identity proof of the insured."
    ]
    for d in docs:
        elements.append(Paragraph(f"- {d}", justify_style))
        
    elements.append(Paragraph("<b>Survey and Payment</b>", h2_style))
    elements.append(Paragraph("Survey and assessment will be conducted by an IRDAI licensed surveyor. Payment will be made within 30 days from final document submission. Salvage handling will be at the discretion of the Insurer.", justify_style))
    elements.append(PageBreak())
    
    # Page 6 - General Conditions
    elements.append(Paragraph("Part VI: General Conditions", title_style))
    conditions = [
        "<b>Premium payment terms:</b> Coverage is valid only if the full premium is realized by the Insurer.",
        "<b>Transfer of interest:</b> The policy may be transferred to a new owner upon intimation within 14 days and payment of applicable fees.",
        "<b>Cancellation policy:</b> Policy may be cancelled with 7 days notice. Pro-rata refund applies if no claims have been made.",
        "<b>Fraud clause:</b> If any claim is fraudulent or supported by fraudulent means, all benefits under this policy shall be forfeited.",
        "<b>Dispute resolution:</b> Any disputes shall be subject to arbitration under the Arbitration and Conciliation Act, 1996.",
        "<b>Governing law:</b> The policy is subject to Indian Law and jurisdiction of Indian Courts.",
        "<b>Renewal terms:</b> The Company is not bound to accept any renewal premium or give notice that renewal is due.",
        "<b>No Claim Bonus:</b> Entitlement to NCB follows the standard tariff rules as applicable in India."
    ]
    for c in conditions:
        elements.append(Paragraph(f"• {c}", justify_style))
        
    doc_policy.build(elements, onFirstPage=watermark_policy, onLaterPages=watermark_policy)
    
    # 2. sample_repair_estimate.pdf
    est_path = os.path.join(output_dir, 'sample_repair_estimate.pdf')
    doc_est = SimpleDocTemplate(est_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    elements.append(Paragraph("AutoCare Workshop - Repair Estimate", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("<b>Date:</b> 15-Mar-2024", normal_style))
    elements.append(Paragraph("<b>Customer:</b> Rajesh Kumar", normal_style))
    elements.append(Paragraph("<b>Policy Reference:</b> INSW/VEH/2024/001234", normal_style))
    elements.append(Paragraph("<b>Vehicle:</b> 2022 Honda City (MH-01-AB-1234)", normal_style))
    elements.append(Paragraph("<b>Incident:</b> Front collision damage", normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    est_data = [
        ["S.No", "Description", "Amount (INR)"],
        ["1", "Front bumper replacement", "12,500"],
        ["2", "Headlight assembly (left)", "8,200"],
        ["3", "Hood repair and painting", "15,000"],
        ["4", "Radiator grille", "3,500"],
        ["5", "Labor charges", "6,000"],
        ["6", "Painting/refinishing", "8,000"],
        ["", "TOTAL", "53,200"]
    ]
    t2 = Table(est_data, colWidths=[0.5*inch, 4*inch, 1.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph("Authorized Signatory & Workshop Stamp", normal_style))
    
    doc_est.build(elements, onFirstPage=watermark_doc, onLaterPages=watermark_doc)
    
    # 3. sample_incident_report.pdf
    inc_path = os.path.join(output_dir, 'sample_incident_report.pdf')
    doc_inc = SimpleDocTemplate(inc_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    elements.append(Paragraph("Incident/Accident Report", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    inc_details = [
        "<b>Date of Incident:</b> 14-Mar-2024",
        "<b>Location:</b> Junction of MG Road and Station Road, Mumbai",
        "<b>Description:</b> Front collision with another vehicle at traffic signal. Other vehicle ran red light.",
        "<b>Policy Number:</b> INSW/VEH/2024/001234",
        "<b>Driver:</b> Rajesh Kumar (Licence: MH-0120200012345)",
        "<b>Third party involved:</b> Yes (vehicle reg: MH-02-CD-5678)",
        "<b>Injuries:</b> None",
        "<b>Police report filed:</b> Yes (FIR No: 234/2024, Bandra PS)"
    ]
    for detail in inc_details:
        elements.append(Paragraph(detail, justify_style))
        
    doc_inc.build(elements, onFirstPage=watermark_doc, onLaterPages=watermark_doc)
    
    # 4. sample_mismatched_doc.pdf
    mis_path = os.path.join(output_dir, 'sample_mismatched_doc.pdf')
    doc_mis = SimpleDocTemplate(mis_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    elements.append(Paragraph("Vehicle Inspection Report", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    mis_details = [
        "<b>Date:</b> 10-Jan-2023",
        "<b>Policy Number:</b> INSW/VEH/2023/005678",
        "<b>Vehicle:</b> 2020 Maruti Swift",
        "<b>Customer:</b> Rajesh Kumar",
        "<b>Inspection Status:</b> Completed.",
        "<b>Remarks:</b> Minor scratches on rear bumper."
    ]
    for detail in mis_details:
        elements.append(Paragraph(detail, justify_style))
        
    doc_mis.build(elements, onFirstPage=watermark_mismatch, onLaterPages=watermark_mismatch)
    
    print("Sample files generated in backend/sample_data/")
    print("Use sample_vehicle_policy.pdf to upload as a policy")
    print("Use sample_repair_estimate.pdf and sample_incident_report.pdf as claim documents")
    print("Note: sample_mismatched_doc.pdf has intentional mismatches for demo purposes")
    print("Note: No driving licence or final invoice is provided - these will show as Missing items")

if __name__ == "__main__":
    generate_samples()
