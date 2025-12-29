from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import re

class QuizQuestion(BaseModel):
    question_id: str = Field(..., description="Unique question identifier")
    question_text: str = Field(..., min_length=10, max_length=500, description="The quiz question")
    options: List[str] = Field(..., min_items=4, max_items=4, description="Four answer options")
    correct_answer: int = Field(..., ge=0, le=3, description="Index of correct answer (0-3)")
    
    @validator('question_id')
    def validate_question_id(cls, v):
        if not re.match(r'^q_\d+$', v):
            raise ValueError('Question ID must follow format "q_N" where N is a number')
        return v
    
    @validator('question_text')
    def validate_question_text(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError('Question text must be at least 10 characters after trimming')
        if not v.endswith('?'):
            raise ValueError('Question text should end with a question mark')
        return v
    
    @validator('options')
    def validate_options(cls, v):
        # Trim whitespace from all options
        v = [option.strip() for option in v]
        
        # Check for empty options
        if any(len(option) < 1 for option in v):
            raise ValueError('All answer options must be non-empty after trimming')
        
        # Check for uniqueness
        if len(set(v)) != len(v):
            raise ValueError('All answer options must be unique')
        
        # Check minimum length for each option
        if any(len(option) < 2 for option in v):
            raise ValueError('Each answer option must be at least 2 characters long')
        
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_correct_answer_exists(cls, values):
        options = values.get('options', [])
        correct_answer = values.get('correct_answer')
        
        if correct_answer is not None and len(options) > correct_answer:
            correct_option = options[correct_answer].strip()
            if len(correct_option) < 2:
                raise ValueError('The correct answer option must be at least 2 characters long')
        
        return values

class QuizBase(BaseModel):
    questions: List[QuizQuestion] = Field(..., min_items=10, max_items=10, description="Exactly 10 quiz questions")
    
    @validator('questions')
    def validate_questions_uniqueness(cls, v):
        # Check for duplicate question texts
        question_texts = [q.question_text.lower().strip() for q in v]
        if len(set(question_texts)) != len(question_texts):
            raise ValueError('All quiz questions must have unique text')
        
        # Check for duplicate question IDs
        question_ids = [q.question_id for q in v]
        if len(set(question_ids)) != len(question_ids):
            raise ValueError('All quiz questions must have unique IDs')
        
        return v

class QuizCreate(QuizBase):
    stake_id: str = Field(..., description="Associated stake ID")

class QuizSubmission(BaseModel):
    quiz_id: str = Field(..., description="Quiz ID being submitted")
    user_answers: List[int] = Field(..., min_items=10, max_items=10, description="User's answers (indices 0-3)")
    
    @validator('user_answers')
    def validate_answers(cls, v):
        for answer in v:
            if answer < 0 or answer > 3:
                raise ValueError('Each answer must be between 0 and 3')
        return v

class GeneratedQuiz(QuizBase):
    source_material: str = Field(..., min_length=1, max_length=255, description="Source PDF filename")
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('source_material')
    def validate_source_material(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Source material filename cannot be empty')
        if not v.lower().endswith('.pdf'):
            raise ValueError('Source material must be a PDF file')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_quiz_completeness(cls, values):
        questions = values.get('questions', [])
        source_material = values.get('source_material', '')
        
        if len(questions) != 10:
            raise ValueError('Generated quiz must contain exactly 10 questions')
        
        # Validate that all questions are properly formed
        for i, question in enumerate(questions):
            if not hasattr(question, 'question_text') or not question.question_text:
                raise ValueError(f'Question {i+1} is missing question text')
            if not hasattr(question, 'options') or len(question.options) != 4:
                raise ValueError(f'Question {i+1} must have exactly 4 options')
            if not hasattr(question, 'correct_answer') or question.correct_answer not in [0, 1, 2, 3]:
                raise ValueError(f'Question {i+1} must have a valid correct answer (0-3)')
        
        return values

class QuizGenerationError(BaseModel):
    error_type: str = Field(..., description="Type of error that occurred")
    error_message: str = Field(..., description="Detailed error message")
    source_material: Optional[str] = Field(None, description="Source material that caused the error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0, description="Number of retry attempts")
    
    class Config:
        schema_extra = {
            "example": {
                "error_type": "AI_PROCESSING_FAILED",
                "error_message": "Gemini API returned invalid JSON response",
                "source_material": "study_guide.pdf",
                "timestamp": "2024-01-01T12:00:00Z",
                "retry_count": 1
            }
        }

class QuizValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether the quiz passed validation")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality score from 0.0 to 1.0")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    
    class Config:
        schema_extra = {
            "example": {
                "is_valid": True,
                "validation_errors": [],
                "quality_score": 0.85,
                "recommendations": ["Consider adding more diverse question types"]
            }
        }

class QuizResponse(QuizBase):
    quiz_id: uuid.UUID
    stake_id: uuid.UUID
    user_answers: Optional[List[int]]
    score: Optional[int]
    completed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True