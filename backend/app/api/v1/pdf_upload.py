from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
import aiofiles
from pathlib import Path

from app.core.database import get_db
from app.crud.pdf_upload import pdf_upload_crud
from app.schemas.pdf_upload import PDFUploadResponse, ProcessingStatus
from app.core.auth import get_current_user
from app.services.pdf_processor import PDFProcessorService

router = APIRouter()

# Configure upload directory
UPLOAD_DIR = Path("uploads/pdfs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# File size limits (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

@router.post("/upload", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a PDF file for processing.
    
    - **file**: PDF file to upload (max 50MB)
    - Returns upload record with processing status
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Read file content to check size
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file_size} bytes exceeds maximum allowed size of {MAX_FILE_SIZE} bytes"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    try:
        # Create upload record in database
        from app.schemas.pdf_upload import PDFUploadCreate
        upload_data = PDFUploadCreate(
            filename=file.filename,
            file_size=file_size
        )
        
        upload_record = pdf_upload_crud.create_upload(
            db=db,
            upload_in=upload_data,
            user_id=current_user["user_id"]
        )
        
        # Save file to disk
        file_path = UPLOAD_DIR / f"{upload_record.upload_id}_{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Update status to processing and start background processing
        pdf_upload_crud.update_processing_status(
            db=db,
            upload_id=str(upload_record.upload_id),
            status=ProcessingStatus.PROCESSING
        )
        
        # Initialize PDF processor service
        processor = PDFProcessorService()
        
        # Process PDF in background (for now, we'll do it synchronously)
        try:
            extracted_text = await processor.extract_text_from_pdf(file_path)
            
            # Update record with extracted text
            upload_record = pdf_upload_crud.update_processing_status(
                db=db,
                upload_id=str(upload_record.upload_id),
                status=ProcessingStatus.COMPLETED,
                extracted_text=extracted_text
            )
            
        except Exception as e:
            # Mark as failed if processing fails
            pdf_upload_crud.update_processing_status(
                db=db,
                upload_id=str(upload_record.upload_id),
                status=ProcessingStatus.FAILED
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF processing failed: {str(e)}"
            )
        
        return upload_record
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/uploads", response_model=List[PDFUploadResponse])
async def get_user_uploads(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all PDF uploads for the current user.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    uploads = pdf_upload_crud.get_by_user_id(
        db=db,
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit
    )
    return uploads

@router.get("/upload/{upload_id}", response_model=PDFUploadResponse)
async def get_upload_status(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of a specific PDF upload.
    
    - **upload_id**: UUID of the upload record
    """
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload ID format"
        )
    
    upload = pdf_upload_crud.get(db=db, id=upload_id)
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    
    # Ensure user can only access their own uploads
    if str(upload.user_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return upload

@router.delete("/upload/{upload_id}")
async def delete_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a PDF upload and its associated file.
    
    - **upload_id**: UUID of the upload record
    """
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload ID format"
        )
    
    upload = pdf_upload_crud.get(db=db, id=upload_id)
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    
    # Ensure user can only delete their own uploads
    if str(upload.user_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Delete file from disk
        file_path = UPLOAD_DIR / f"{upload.upload_id}_{upload.filename}"
        if file_path.exists():
            os.remove(file_path)
        
        # Delete record from database
        pdf_upload_crud.remove(db=db, id=upload_id)
        
        return {"message": "Upload deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete upload: {str(e)}"
        )

@router.get("/upload/{upload_id}/statistics")
async def get_upload_statistics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get upload statistics for the current user.
    """
    stats = pdf_upload_crud.get_upload_statistics_by_user(
        db=db,
        user_id=current_user["user_id"]
    )
    return stats