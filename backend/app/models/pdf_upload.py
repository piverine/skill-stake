from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Enum as SQLEnum, Uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class ProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PDFUpload(Base):
    __tablename__ = "pdf_uploads"
    
    upload_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.UPLOADED)
    extracted_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="pdf_uploads")