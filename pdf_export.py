"""McKinsey-style PDF report export via reportlab."""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from schemas import ConfidenceScore
from tasks import FinancialAnalysis


def _score_color(score: int) -> colors.Color:
    if score >= 75:
        return colors.HexColor("#2ecc71")
    if score >= 50:
        return colors.HexColor("#f39c12")
    return colors.HexColor("#e74c3c")


def _confidence_bar(score: int, width: float = 4 * inch) -> Table:
    fill = min(max(score, 0), 100) / 100.0 * width
    bar = Table(
        [[""]],
        colWidths=[width],
        rowHeights=[14],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecf0f1")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ]),
    )
    overlay = Table(
        [[""]],
        colWidths=[fill or 1],
        rowHeights=[14],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), _score_color(score))]),
    )
    return overlay


def generate_pdf(
    product_name: str,
    executive_summary: str,
    financials: FinancialAnalysis | None,
    confidence: ConfidenceScore | None,
    launch_brief: str = "",
) -> bytes:
    """Build a professional PDF report and return bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontSize=26, spaceAfter=20)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceBefore=16, spaceAfter=8)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)

    story = [
        Paragraph("Market Intelligence Report", title),
        Paragraph(f"<b>{product_name}</b>", h2),
        Paragraph(f"Generated {date.today():%B %d, %Y}", body),
        Spacer(1, 0.3 * inch),
        Paragraph("Executive Summary", h2),
        Paragraph(executive_summary or "No summary available.", body),
    ]

    if financials:
        story += [
            Spacer(1, 0.2 * inch),
            Paragraph("Financial Analysis", h2),
        ]
        fin_data = [
            ["Metric", "Value"],
            ["Estimated COGS", f"${financials.estimated_cogs:,.2f}"],
            ["Suggested Retail", f"${financials.suggested_retail_price:,.2f}"],
            ["Gross Margin", f"{financials.projected_margin_percentage:.1f}%"],
        ]
        for p in financials.key_competitor_prices[:5]:
            fin_data.append(["Competitor", p])
        t = Table(fin_data, colWidths=[2.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        story.append(t)

    if confidence:
        story += [Spacer(1, 0.2 * inch), Paragraph("Confidence Score", h2)]
        story.append(Paragraph(f"<b>Overall: {confidence.overall_score}/100</b>", body))
        for label, val in [
            ("Source Reliability", confidence.source_reliability),
            ("Evidence Coverage", confidence.evidence_coverage),
            ("Consistency", confidence.consistency),
        ]:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"{label}: {val}/100", body))
        if confidence.summary:
            story.append(Spacer(1, 8))
            story.append(Paragraph(confidence.summary, body))

    if launch_brief:
        story += [Spacer(1, 0.2 * inch), Paragraph("Launch Brief", h2)]
        for line in launch_brief.split("\n"):
            if line.startswith("##"):
                story.append(Paragraph(line.replace("#", "").strip(), h2))
            elif line.strip():
                story.append(Paragraph(line, body))

    doc.build(story)
    return buf.getvalue()
