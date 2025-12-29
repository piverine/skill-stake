from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import uuid
from enum import Enum

class ProcessingStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PDFUploadBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_size: int = Field(..., gt=0, le=50*1024*1024, description="File size in bytes (max 50MB)")
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v.lower().endswith('.pdf'):
            raise ValueError('File must be a PDF')
        return v

class PDFUploadCreate(PDFUploadBase):
    pass

class PDFUploadUpdate(BaseModel):
    processing_status: Optional[ProcessingStatus] = None
    extracted_text: Optional[str] = None

class PDFUploadResponse(PDFUploadBase):
    upload_id: uuid.UUID
    user_id: uuid.UUID
    processing_status: ProcessingStatus
    extracted_text: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True