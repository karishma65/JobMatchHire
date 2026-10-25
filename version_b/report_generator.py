import os
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

logger = logging.getLogger("report_generator")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def format_date_ist(date_str: str) -> str:
    if not date_str:
        return "N/A"
    try:
        s = str(date_str).strip()
        if not s.endswith("Z") and "+" not in s:
            s = s.replace(" ", "T") + "Z"
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        ist_dt = dt.astimezone(ZoneInfo("Asia/Kolkata"))
        return ist_dt.strftime("%d %b %Y, %I:%M:%S %p IST")
    except Exception:
        return str(date_str)

def generate_ecce_pdf_report(ecce_data: Dict[str, Any], output_path: str = None) -> str:
    """
    Generates a formal, comprehensive ECCE Candidate Evaluation PDF Report.
    Adheres strictly to the 8 required sections:
    1. Job title and evaluation date
    2. Overall matching score and component scores
    3. Required and preferred skills assessment
    4. Evidence Found, Evidence Not Found and Potential Inconsistency classifications
    5. Supporting resume passages for relevant conclusions
    6. Explanation of the scoring result and job-specific gaps
    7. Counterfactual score simulations (clearly labelled as hypothetical)
    8. Personal learning recommendations and practical next steps
    """
    candidate_id = ecce_data.get("candidate_id", "CAN-000")
    if not output_path:
        filename = f"{candidate_id}_evaluation_report.pdf"
        output_path = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    brand_blue = colors.HexColor("#1e3a8a")
    brand_slate = colors.HexColor("#475569")
    brand_light_bg = colors.HexColor("#f8fafc")
    badge_green = colors.HexColor("#15803d")
    badge_amber = colors.HexColor("#b45309")
    badge_red = colors.HexColor("#b91c1c")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=brand_blue
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=brand_slate
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=brand_blue,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold"
    )

    passage_style = ParagraphStyle(
        "PassageText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    hypothetical_banner = ParagraphStyle(
        "HypoBanner",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=badge_amber
    )

    elements = []

    # ------------------ Header & Brand ------------------
    elements.append(Paragraph("JobMatchHire — ECCE Evaluation Report", title_style))
    elements.append(Paragraph("Explainable Contextual Competency Engine with Automated Counterfactual Gap Remediation", subtitle_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue, spaceBefore=2, spaceAfter=8))

    # ------------------ SECTION 1: Job Title & Evaluation Date ------------------
    elements.append(Paragraph("1. Evaluation Overview & Identification", h1_style))
    
    meta_data = [
        [Paragraph("<b>Job Position:</b>", body_style), Paragraph(str(ecce_data.get("job_title", "N/A")), body_style),
         Paragraph("<b>Evaluation Date (IST):</b>", body_style), Paragraph(format_date_ist(ecce_data.get("evaluation_date", "")), body_style)],
        [Paragraph("<b>Candidate Name:</b>", body_style), Paragraph(str(ecce_data.get("candidate_name", "N/A")), body_style),
         Paragraph("<b>Candidate ID:</b>", body_style), Paragraph(str(ecce_data.get("candidate_id", "N/A")), body_style)],
        [Paragraph("<b>Target Job ID:</b>", body_style), Paragraph(str(ecce_data.get("job_id", "N/A")), body_style),
         Paragraph("<b>Evaluation Status:</b>", body_style), Paragraph(f"<b>{ecce_data.get('evaluation_status', 'Completed')}</b>", body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[105, 160, 105, 160])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), brand_light_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    # ------------------ SECTION 2: Overall Score & Component Breakdown ------------------
    elements.append(Paragraph("2. Overall Match Score & Deterministic Component Breakdown", h1_style))
    bd = ecce_data.get("breakdown", {})
    score_data = [
        [
            Paragraph("<b>Component</b>", body_bold),
            Paragraph("<b>Weight / Max</b>", body_bold),
            Paragraph("<b>Score Achieved</b>", body_bold),
            Paragraph("<b>Metric / Formula</b>", body_bold)
        ],
        [
            Paragraph("Required Skills", body_style),
            Paragraph("50.0 pts", body_style),
            Paragraph(f"<b>{bd.get('required_skills_score', 0.0):.2f} pts</b>", body_style),
            Paragraph("Ratio of verified required skills to total required", body_style)
        ],
        [
            Paragraph("Professional Experience", body_style),
            Paragraph("25.0 pts", body_style),
            Paragraph(f"<b>{bd.get('experience_score', 0.0):.2f} pts</b>", body_style),
            Paragraph("Clamped ratio of verified years vs minimum requirement", body_style)
        ],
        [
            Paragraph("Preferred Skills", body_style),
            Paragraph("15.0 pts", body_style),
            Paragraph(f"<b>{bd.get('preferred_skills_score', 0.0):.2f} pts</b>", body_style),
            Paragraph("Ratio of verified preferred skills to total preferred", body_style)
        ],
        [
            Paragraph("Text Similarity (TF-IDF Cosine)", body_style),
            Paragraph("10.0 pts", body_style),
            Paragraph(f"<b>{bd.get('similarity_score', 0.0):.2f} pts</b>", body_style),
            Paragraph(f"Cosine similarity score: {bd.get('cosine_similarity', 0.0):.3f}", body_style)
        ],
        [
            Paragraph("<b>TOTAL MATCH SCORE</b>", body_bold),
            Paragraph("<b>100.0 pts</b>", body_bold),
            Paragraph(f"<font size=11 color='#1e3a8a'><b>{ecce_data.get('match_score', 0.0):.2f} / 100</b></font>", body_bold),
            Paragraph("<b>Deterministic Bounded Sum [0.0 - 100.0]</b>", body_bold)
        ]
    ]
    score_table = Table(score_data, colWidths=[140, 95, 105, 190])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 10))

    # ------------------ SECTION 3 & 4: Skills Assessment & Evidence Classification ------------------
    elements.append(Paragraph("3 & 4. Competency Assessment & Evidence Classification", h1_style))
    elements.append(Paragraph(
        "<i>ECCE classifies evidence strictly based on extracted resume passages. "
        "<b>Evidence Not Found</b> must not be interpreted as proof that the candidate lacks the skill. "
        "<b>Potential Inconsistency</b> is flagged for human review, not treated as proof of dishonesty.</i>",
        subtitle_style
    ))
    elements.append(Spacer(1, 4))

    all_assessments = ecce_data.get("required_skills_assessment", []) + ecce_data.get("preferred_skills_assessment", [])
    
    table_rows = [
        [
            Paragraph("<b>Skill</b>", body_bold),
            Paragraph("<b>Type</b>", body_bold),
            Paragraph("<b>Classification</b>", body_bold),
            Paragraph("<b>Detected Actions & Project Context</b>", body_bold),
            Paragraph("<b>Assessment Notes</b>", body_bold)
        ]
    ]

    for item in all_assessments:
        cls_val = item.get("classification", "Evidence Not Found")
        if cls_val == "Evidence Found":
            cls_color = "#15803d"
        elif cls_val == "Potential Inconsistency":
            cls_color = "#b45309"
        else:
            cls_color = "#b91c1c"

        actions_str = ", ".join(item.get("actions", [])) or "None identified"
        ctx_str = ", ".join(item.get("project_context", [])) or "General mention"
        act_ctx = f"<b>Actions:</b> {actions_str}<br/><b>Context:</b> {ctx_str}"

        table_rows.append([
            Paragraph(f"<b>{item.get('skill', '')}</b>", body_style),
            Paragraph(item.get("category", "Required"), body_style),
            Paragraph(f"<font color='{cls_color}'><b>{cls_val}</b></font>", body_style),
            Paragraph(act_ctx, body_style),
            Paragraph(item.get("justification", ""), body_style)
        ])

    skills_table = Table(table_rows, colWidths=[90, 65, 110, 135, 130])
    skills_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(skills_table)
    elements.append(Spacer(1, 10))

    # ------------------ SECTION 5: Supporting Resume Passages ------------------
    elements.append(Paragraph("5. Supporting Verbatim Resume Passages", h1_style))
    elements.append(Paragraph(
        "Verbatim excerpts from candidate's submitted resume documenting contextual competency claims without fabrication:",
        subtitle_style
    ))
    elements.append(Spacer(1, 4))

    found_passages = False
    for item in all_assessments:
        passages = item.get("supporting_passages", [])
        if passages:
            found_passages = True
            elements.append(Paragraph(f"<b>Skill: {item.get('skill')}</b> ({item.get('category')})", body_bold))
            for p in passages:
                elements.append(Paragraph(f"&ldquo;{p}&rdquo;", passage_style))
            elements.append(Spacer(1, 3))

    if not found_passages:
        elements.append(Paragraph("<i>No verbatim project passages were detected in the parsed text for the required skills.</i>", body_style))

    elements.append(Spacer(1, 8))

    # ------------------ SECTION 6: Scoring Explanation & Gaps ------------------
    elements.append(Paragraph("6. Scoring Explanation & Role Gap Analysis", h1_style))
    evidence_sum = ecce_data.get("evidence_summary", "Evaluation complete.")
    elements.append(Paragraph(f"<b>Evaluator Summary:</b> {evidence_sum}", body_style))
    elements.append(Spacer(1, 6))

    # ------------------ SECTION 7: Counterfactual Score Simulations ------------------
    elements.append(Paragraph("7. Counterfactual Score Simulations (Hypothetical Analysis)", h1_style))
    elements.append(Paragraph(
        "<b>NOTICE:</b> The following simulations represent hypothetical mathematical sensitivity models under "
        "the deterministic scoring function. They illustrate how specific changes in verified qualifications or "
        "resume parsing clarification would affect the matching score. "
        "<b>These are hypothetical models, not actual results or awarded points. Candidates must never add skills "
        "they do not genuinely possess.</b>",
        hypothetical_banner
    ))
    elements.append(Spacer(1, 6))

    cf_rows = [
        [
            Paragraph("<b>Scenario</b>", body_bold),
            Paragraph("<b>Type</b>", body_bold),
            Paragraph("<b>Baseline</b>", body_bold),
            Paragraph("<b>Hypothetical</b>", body_bold),
            Paragraph("<b>Impact / Explanation</b>", body_bold)
        ]
    ]

    for cf in ecce_data.get("counterfactual_simulations", []):
        cf_rows.append([
            Paragraph(f"<b>{cf.get('scenario_name')}</b>", body_style),
            Paragraph(cf.get("scenario_type", "Skill Acquisition"), body_style),
            Paragraph(f"{cf.get('baseline_score', 0):.2f}%", body_style),
            Paragraph(f"<font color='#15803d'><b>{cf.get('simulated_score', 0):.2f}%</b></font><br/>(+{cf.get('score_delta', 0):.2f}%)", body_style),
            Paragraph(f"{cf.get('description')}<br/><i>{cf.get('hypothetical_label')}</i>", body_style)
        ])

    cf_table = Table(cf_rows, colWidths=[120, 95, 60, 85, 170])
    cf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fcd34d")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(cf_table)
    elements.append(Spacer(1, 10))

    # ------------------ SECTION 8: Private Candidate Skill-Gap Guidance ------------------
    elements.append(Paragraph("8. Candidate Skill-Gap Guidance & Practical Next Steps", h1_style))
    elements.append(Paragraph(
        "<b>[PRIVATE TO CANDIDATE]</b> The following development recommendations are provided exclusively "
        "to assist the candidate in closing identified capability gaps. These recommendations are kept strictly private "
        "and are not disclosed to recruiters.",
        subtitle_style
    ))
    elements.append(Spacer(1, 6))

    guidance_items = ecce_data.get("private_learning_guidance", [])
    if guidance_items:
        g_rows = [
            [
                Paragraph("<b>Skill Gap</b>", body_bold),
                Paragraph("<b>Relevance to Job Role</b>", body_bold),
                Paragraph("<b>Recommended Practical Project</b>", body_bold),
                Paragraph("<b>Authoritative Resource</b>", body_bold)
            ]
        ]
        for g in guidance_items:
            g_rows.append([
                Paragraph(f"<b>{g.get('skill')}</b><br/>({g.get('category')})", body_style),
                Paragraph(g.get("why_it_matters", ""), body_style),
                Paragraph(g.get("recommended_activity", ""), body_style),
                Paragraph(f"<u>{g.get('reliable_resource', '')}</u>", body_style)
            ])

        g_table = Table(g_rows, colWidths=[80, 140, 160, 150])
        g_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(g_table)
    else:
        elements.append(Paragraph("<i>All stated required and preferred competencies have supporting resume evidence. No immediate skill remediation required.</i>", body_style))

    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceBefore=4, spaceAfter=8))
    elements.append(Paragraph(
        "<b>Data Distinction Standard:</b> Verified inputs include job descriptions, candidate submitted files, and deterministic score formulas. "
        "Resume claims reflect candidate-supplied text. Contextual models classify evidence. Counterfactual simulations are strictly hypothetical.",
        subtitle_style
    ))

    # Build PDF document
    doc.build(elements)
    logger.info(f"Generated ECCE PDF report at {output_path}")
    return output_path
