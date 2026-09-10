from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.api.deps import get_auth_context, AuthContext
from backend.app.auth.rbac import PERM_REPORT_VIEW, PERM_REPORT_DOWNLOAD
from backend.app.models.report import Report
from backend.app.models.research import ResearchJob
from backend.app.services.storage import storage_service

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

@router.get("/{report_id}")
def get_report_metadata(
    report_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_REPORT_VIEW)

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report.org_id != auth.organization.id and not auth.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    download_url = storage_service.generate_signed_url(report.object_key, expires_in=3600)

    return {
        "report_id": report.id,
        "job_id": report.job_id,
        "mime_type": report.mime_type,
        "size_bytes": report.size,
        "checksum_sha256": report.checksum,
        "created_at": report.created_at,
        "download_url": download_url
    }

@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    auth.require_permission(PERM_REPORT_DOWNLOAD)

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report.org_id != auth.organization.id and not auth.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    signed_url = storage_service.generate_signed_url(report.object_key, expires_in=300)
    return RedirectResponse(url=signed_url)
