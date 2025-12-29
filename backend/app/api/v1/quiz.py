from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from app.core.database import get_db
from app.crud.quiz import quiz_crud
from app.crud.pdf_upload import pdf_upload_crud
from app.schemas.quiz import QuizResponse, QuizCreate, QuizSubmission, GeneratedQuiz, QuizValidationResult
from app.schemas.pdf_upload import ProcessingStatus
from app.core.auth import get_current_user
from app.services.quiz_generator import QuizGeneratorService, AIProcessingError

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    quiz_request: QuizCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a quiz from a processed PDF upload with comprehensive error handling.
    
    - **stake_id**: ID of the stake associated with this quiz
    - Returns generated quiz with 10 questions
    """
    try:
        # Validate stake_id format
        try:
            stake_uuid = uuid.UUID(quiz_request.stake_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid stake ID format"
            )
        
        # TODO: Validate that stake belongs to current user and is active
        # For now, we'll skip stake validation and focus on PDF processing
        
        # Find a completed PDF upload for this user to generate quiz from
        try:
            completed_uploads = pdf_upload_crud.get_completed_uploads_by_user(
                db=db,
                user_id=current_user["user_id"]
            )
        except Exception as e:
            logger.error(f"Error retrieving PDF uploads for user {current_user['user_id']}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve PDF uploads"
            )
        
        if not completed_uploads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No completed PDF uploads found. Please upload and process a PDF first."
            )
        
        # Use the most recent completed upload
        pdf_upload = completed_uploads[-1]
        
        if not pdf_upload.extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF text extraction not completed"
            )
        
        # Initialize quiz generator
        try:
            generator = QuizGeneratorService()
        except Exception as e:
            logger.error(f"Failed to initialize quiz generator: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Quiz generation service unavailable"
            )
        
        # Generate quiz from extracted text with error handling
        try:
            generated_quiz, error_record = await generator.generate_quiz_with_error_handling(
                extracted_text=pdf_upload.extracted_text,
                source_filename=pdf_upload.filename
            )
            
            if error_record:
                # Log the error and return appropriate HTTP error
                logger.error(f"Quiz generation failed: {error_record.dict()}")
                
                if error_record.error_type == "INSUFFICIENT_CONTENT":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"PDF content is insufficient for quiz generation: {error_record.error_message}"
                    )
                elif error_record.error_type == "API_TIMEOUT":
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="AI service timeout. Please try again."
                    )
                elif error_record.error_type in ["INVALID_JSON", "EMPTY_RESPONSE"]:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="AI service returned invalid response. Please try again."
                    )
                elif error_record.error_type == "MAX_RETRIES_EXCEEDED":
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Quiz generation failed after multiple attempts. Please try again later."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Quiz generation failed: {error_record.error_message}"
                    )
            
            if not generated_quiz:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Quiz generation returned no result"
                )
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except AIProcessingError as e:
            logger.error(f"AI processing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI processing failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during quiz generation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error during quiz generation"
            )
        
        # Store quiz in database with validation
        try:
            quiz_record = quiz_crud.create_quiz(
                db=db,
                quiz_data=generated_quiz,
                stake_id=quiz_request.stake_id
            )
            
            logger.info(f"Successfully created quiz {quiz_record.quiz_id} for stake {quiz_request.stake_id}")
            return quiz_record
            
        except ValueError as e:
            logger.error(f"Quiz validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quiz validation failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Database error creating quiz: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store quiz in database"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_quiz endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific quiz by ID.
    
    - **quiz_id**: UUID of the quiz
    """
    try:
        quiz_uuid = uuid.UUID(quiz_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quiz ID format"
        )
    
    quiz = quiz_crud.get(db=db, id=quiz_id)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # TODO: Validate that quiz belongs to current user through stake relationship
    # For now, we'll return the quiz
    
    return quiz

@router.get("/{quiz_id}/validate", response_model=QuizValidationResult)
async def validate_quiz_integrity(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Validate the integrity of stored quiz data.
    
    - **quiz_id**: UUID of the quiz to validate
    """
    try:
        quiz_uuid = uuid.UUID(quiz_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quiz ID format"
        )
    
    try:
        validation_result = quiz_crud.validate_quiz_data_integrity(db=db, quiz_id=quiz_id)
        return validation_result
    except Exception as e:
        logger.error(f"Error validating quiz {quiz_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate quiz data"
        )

@router.post("/{quiz_id}/submit", response_model=QuizResponse)
async def submit_quiz(
    quiz_id: str,
    submission: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit answers for a quiz and calculate score with comprehensive validation.
    
    - **quiz_id**: UUID of the quiz
    - **submission**: User's answers to the quiz questions
    """
    try:
        # Validate quiz_id format
        try:
            quiz_uuid = uuid.UUID(quiz_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid quiz ID format"
            )
        
        if submission.quiz_id != quiz_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz ID in submission does not match URL parameter"
            )
        
        # Get quiz with error handling
        try:
            quiz = quiz_crud.get(db=db, id=quiz_id)
        except Exception as e:
            logger.error(f"Error retrieving quiz {quiz_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve quiz"
            )
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Check if quiz is already completed
        if quiz.completed_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz has already been completed"
            )
        
        # Validate quiz data integrity before processing submission
        try:
            validation_result = quiz_crud.validate_quiz_data_integrity(db=db, quiz_id=quiz_id)
            if not validation_result.is_valid:
                logger.error(f"Quiz {quiz_id} failed integrity validation: {validation_result.validation_errors}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Quiz data integrity validation failed"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating quiz integrity for {quiz_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to validate quiz integrity"
            )
        
        # Calculate and submit score
        try:
            # Calculate score
            score = quiz_crud.calculate_score(quiz, submission.user_answers)
            
            # Update quiz with answers and score
            updated_quiz = quiz_crud.submit_answers(
                db=db,
                quiz_id=quiz_id,
                user_answers=submission.user_answers,
                score=score
            )
            
            logger.info(f"Successfully submitted quiz {quiz_id} with score {score}")
            return updated_quiz
            
        except ValueError as e:
            logger.error(f"Quiz submission validation error for {quiz_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error submitting quiz {quiz_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit quiz"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_quiz endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/user/quizzes", response_model=List[QuizResponse])
async def get_user_quizzes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all quizzes for the current user.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    # TODO: Implement get_by_user_id in quiz_crud
    # For now, return empty list
    return []

@router.post("/{quiz_id}/regenerate", response_model=QuizResponse)
async def regenerate_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate a quiz with different questions from the same source material.
    
    - **quiz_id**: UUID of the existing quiz to regenerate
    """
    try:
        quiz_uuid = uuid.UUID(quiz_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quiz ID format"
        )
    
    quiz = quiz_crud.get(db=db, id=quiz_id)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Check if quiz is already completed
    if quiz.completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot regenerate a completed quiz"
        )
    
    try:
        # Find the associated PDF upload to get source text
        # TODO: Add relationship between quiz and pdf_upload
        # For now, find the most recent completed upload for the user
        completed_uploads = pdf_upload_crud.get_completed_uploads_by_user(
            db=db,
            user_id=current_user["user_id"]
        )
        
        if not completed_uploads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No source PDF found for regeneration"
            )
        
        pdf_upload = completed_uploads[-1]
        
        # Initialize quiz generator
        generator = QuizGeneratorService()
        
        # Regenerate quiz with variation
        generated_quiz = await generator.regenerate_quiz(
            extracted_text=pdf_upload.extracted_text,
            source_filename=pdf_upload.filename,
            attempt=2
        )
        
        # Update existing quiz with new questions
        updated_quiz = quiz_crud.update_questions(
            db=db,
            quiz_id=quiz_id,
            new_questions=generated_quiz.questions
        )
        
        return updated_quiz
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz regeneration failed: {str(e)}"
        )