import io
import hashlib
import uuid
import datetime
from celery.utils.log import get_task_logger
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.models.research import ResearchJob, ResearchRun, ResearchEvent
from backend.app.models.report import Report
from backend.app.services.storage import storage_service

logger = get_task_logger(__name__)

import html

def safe_html(text: str) -> str:
    """Escapes HTML entities to prevent ReportLab markup injection."""
    if not isinstance(text, str):
        return str(text)
    return html.escape(text).replace("\n", "<br/>")

def build_pdf_document(product_idea: str, result: dict) -> bytes:
    """
    Renders an executive-grade PDF report using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#111827'),
        spaceAfter=14
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151')
    )

    story = []

    # Title
    story.append(Paragraph("MarketAI Executive Intelligence Brief", title_style))
    story.append(Paragraph(f"<b>Target Subject:</b> {safe_html(product_idea)}", body_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.datetime.utcnow().strftime('%B %d, %Y - %H:%M UTC')}", body_style))
    story.append(Spacer(1, 16))

    # Executive Summary
    story.append(Paragraph("Executive Summary", h2_style))
    exec_sum = result.get("executive_summary", "No executive summary available.")
    story.append(Paragraph(safe_html(exec_sum), body_style))
    story.append(Spacer(1, 14))

    # Financials Table
    story.append(Paragraph("Deterministic Unit Economics", h2_style))
    fin = result.get("financials", {})
    fin_data = [
        ["Metric", "Value"],
        ["Suggested Retail Price", f"${fin.get('suggested_retail_price', 0):.2f}"],
        ["Estimated COGS", f"${fin.get('estimated_cogs', 0):.2f}"],
        ["Gross Margin", f"{fin.get('projected_margin_percentage', 0)}%"],
        ["Markup", f"{fin.get('markup_percentage', 0)}%"],
        ["Break-Even Monthly Units", str(fin.get('break_even_units', 0))],
        ["Assumption Type", safe_html(fin.get('assumption_type', 'N/A'))]
    ]
    t = Table(fin_data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#111827')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # Competitors
    story.append(Paragraph("Competitor Intelligence", h2_style))
    competitors = result.get("competitors", [])
    if competitors:
        comp_data = [["Competitor", "Positioning", "Pricing"]]
        for c in competitors[:5]:
            comp_data.append([
                safe_html(c.get("name", "N/A")),
                safe_html(c.get("positioning", "N/A")),
                safe_html(str(c.get("pricing", "N/A")))
            ])
        ct = Table(comp_data, colWidths=[150, 150, 150])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        story.append(ct)
    story.append(Spacer(1, 14))

    # Recommendations
    recs = result.get("strategic_recommendations", [])
    if recs:
        story.append(Paragraph("Strategic Recommendations", h2_style))
        for r in recs:
            story.append(Paragraph(f"• {safe_html(r)}", body_style))
        story.append(Spacer(1, 14))

    # Confidence Metric
    conf = result.get("confidence", {})
    story.append(Paragraph(f"<b>Overall Research Confidence:</b> {conf.get('overall_score', 'N/A')}/100", body_style))
    reasons = conf.get("reasoning", [])
    for r in reasons:
        story.append(Paragraph(f"- {safe_html(r)}", body_style))

    doc.build(story)
    return buffer.getvalue()

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def generate_pdf_report_task(self, job_id: str):
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job or job.status == "CANCELLED":
        db.close()
        return

    run_record = ResearchRun(
        job_id=job_id,
        stage="report",
        status="RUNNING",
        worker_id=str(self.request.id)
    )
    db.add(run_record)

    try:
        job.status = "GENERATING_REPORT"
        db.commit()

        # Build real PDF
        pdf_bytes = build_pdf_document(job.product_idea, job.result or {})
        pdf_size = len(pdf_bytes)
        checksum = hashlib.sha256(pdf_bytes).hexdigest()

        # Tenant-namespaced object key: organizations/{org_id}/reports/{report_id}.pdf
        report_id = str(uuid.uuid4())
        object_key = f"organizations/{job.org_id}/reports/{report_id}.pdf"

        # Upload to real S3/MinIO
        storage_service.upload_bytes(
            key=object_key,
            data=pdf_bytes,
            content_type="application/pdf"
        )

        # Record in reports table (Phase 9)
        report_record = Report(
            id=report_id,
            job_id=job.id,
            org_id=job.org_id,
            object_key=object_key,
            mime_type="application/pdf",
            size=pdf_size,
            checksum=checksum
        )
        db.add(report_record)

        # Finalize job status
        job.pdf_object_key = object_key
        job.status = "COMPLETED"
        job.progress = 100
        job.completed_at = datetime.datetime.utcnow()

        event = ResearchEvent(
            job_id=job.id,
            stage="completed",
            progress=100,
            message="Executive PDF report compiled and persisted in object storage",
            level="INFO"
        )
        db.add(event)

        run_record.status = "COMPLETED"
        run_record.completed_at = datetime.datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.exception(f"Error in PDF worker for job {job_id}: {e}")
        job.status = "FAILED"
        job.error_code = "PDF_GENERATION_ERROR"
        job.error_message = str(e)
        run_record.status = "FAILED"
        run_record.error_message = str(e)
        db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()
