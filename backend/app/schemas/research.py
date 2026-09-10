from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ResearchCreateRequest(BaseModel):
    product_idea: str = Field(..., min_length=3, max_length=2000, description="Product idea or concept to research")
    mode: str = Field("deep", pattern="^(quick|deep|batch)$")
    idempotency_key: Optional[str] = Field(None, max_length=255)
    org_id: Optional[str] = Field(None, description="Optional org ID if user belongs to multiple")

class ResearchResponse(BaseModel):
    task_id: str
    status: str
    mode: str
    created_at: datetime

class ResearchEventResponse(BaseModel):
    stage: str
    progress: int
    message: str
    level: str
    created_at: datetime

class ResearchDetailResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    mode: str
    product_idea: str
    result: Optional[Dict[str, Any]] = None
    pdf_ready: bool = False
    pdf_download_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
