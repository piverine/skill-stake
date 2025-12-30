from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.pdf_upload import PDFUpload, ProcessingStatus
from app.schemas.pdf_upload import PDFUploadCreate, PDFUploadUpdate


class CRUDPDFUpload(CRUDBase[PDFUpload, PDFUploadCreate, PDFUploadUpdate]):
    def get_by_user_id(self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100) -> List[PDFUpload]:
        """Get all PDF uploads for a specific user."""
        # Ensure user_id is UUID
        import uuid
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return []
                
        return (
            db.query(PDFUpload)
            .filter(PDFUpload.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(self, db: Session, *, status: ProcessingStatus, skip: int = 0, limit: int = 100) -> List[PDFUpload]:
        """Get PDF uploads by processing status."""
        return (
            db.query(PDFUpload)
            .filter(PDFUpload.processing_status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_filename(self, db: Session, *, user_id: str, filename: str) -> Optional[PDFUpload]:
        """Get PDF upload by user and filename."""
        return (
            db.query(PDFUpload)
            .filter(PDFUpload.user_id == user_id)
            .filter(PDFUpload.filename == filename)
            .first()
        )

    def create_upload(self, db: Session, *, upload_in: PDFUploadCreate, user_id: str) -> PDFUpload:
        """Create a new PDF upload with validation."""
        # Check file size limits (50MB max)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if upload_in.file_size > max_size:
            raise ValueError(f"File size {upload_in.file_size} exceeds maximum allowed size of {max_size} bytes")
        
        # Validate file extension
        if not upload_in.filename.lower().endswith('.pdf'):
            raise ValueError("Only PDF files are allowed")
        
        upload_data = upload_in.dict()
        
        # Ensure user_id is UUID
        import uuid
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                pass # Let it fail later or handle as needed, but try conversion first
        
        upload_data['user_id'] = user_id
        
        db_upload = PDFUpload(**upload_data)
        db.add(db_upload)
        db.commit()
        db.refresh(db_upload)
        return db_upload

    def update_processing_status(
        self, 
        db: Session, 
        *, 
        upload_id: str, 
        status: ProcessingStatus,
        extracted_text: Optional[str] = None
    ) -> Optional[PDFUpload]:
        """Update processing status and extracted text."""
        # Convert string ID to UUID for query
        import uuid
        if isinstance(upload_id, str):
            try:
                upload_id = uuid.UUID(upload_id)
            except ValueError:
                return None
                
        upload = self.get(db, upload_id)
        if not upload:
            return None
        
        try:
            upload.processing_status = status
            if extracted_text is not None:
                upload.extracted_text = extracted_text
            
            db.add(upload)
            db.commit()
            db.refresh(upload)
            return upload
        except Exception as e:
            db.rollback()
            raise e

    def get_completed_uploads_by_user(self, db: Session, *, user_id: str) -> List[PDFUpload]:
        """Get all completed PDF uploads for a user."""
        # Ensure user_id is UUID
        import uuid
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return []

        return (
            db.query(PDFUpload)
            .filter(PDFUpload.user_id == user_id)
            .filter(PDFUpload.processing_status == ProcessingStatus.COMPLETED)
            .all()
        )

    def get_failed_uploads(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[PDFUpload]:
        """Get all failed PDF uploads for retry processing."""
        return (
            db.query(PDFUpload)
            .filter(PDFUpload.processing_status == ProcessingStatus.FAILED)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_upload_statistics_by_user(self, db: Session, *, user_id: str) -> dict:
        """Get upload statistics for a user."""
        uploads = self.get_by_user_id(db, user_id=user_id, limit=1000)  # Get all uploads
        
        if not uploads:
            return {
                'total_uploads': 0,
                'completed_uploads': 0,
                'failed_uploads': 0,
                'processing_uploads': 0,
                'total_size_bytes': 0
            }
        
        completed = len([u for u in uploads if u.processing_status == ProcessingStatus.COMPLETED])
        failed = len([u for u in uploads if u.processing_status == ProcessingStatus.FAILED])
        processing = len([u for u in uploads if u.processing_status == ProcessingStatus.PROCESSING])
        total_size = sum(u.file_size for u in uploads)
        
        return {
            'total_uploads': len(uploads),
            'completed_uploads': completed,
            'failed_uploads': failed,
            'processing_uploads': processing,
            'total_size_bytes': total_size
        }

    def get(self, db: Session, id: str) -> Optional[PDFUpload]:
        """Override to use upload_id field."""
        # Convert string ID to UUID for query
        import uuid
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                return None
                
        return db.query(PDFUpload).filter(PDFUpload.upload_id == id).first()

    def remove(self, db: Session, *, id: str) -> Optional[PDFUpload]:
        """Override to use upload_id field."""
        # Convert string ID to UUID for query
        import uuid
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                return None

        obj = db.query(PDFUpload).filter(PDFUpload.upload_id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return obj
        return None


pdf_upload_crud = CRUDPDFUpload(PDFUpload)