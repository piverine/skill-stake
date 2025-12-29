import google.generativeai as genai
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import ValidationError
import time
import random

from app.core.config import settings
from app.schemas.quiz import QuizQuestion, GeneratedQuiz, QuizGenerationError

logger = logging.getLogger(__name__)

class AIProcessingError(Exception):
    """Custom exception for AI processing failures."""
    def __init__(self, message: str, error_type: str = "AI_PROCESSING_FAILED", retry_count: int = 0):
        super().__init__(message)
        self.error_type = error_type
        self.retry_count = retry_count

class QuizGeneratorService:
    """Service for generating quizzes from PDF content using Gemini 3 Flash API."""
    
    def __init__(self):
        """Initialize the quiz generator with Gemini API configuration."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for quiz generation")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff
    
    async def generate_quiz_from_text(self, extracted_text: str, source_filename: str) -> GeneratedQuiz:
        """
        Generate a 10-question quiz from extracted PDF text using Gemini API with robust error handling.
        
        Args:
            extracted_text: Text content extracted from PDF
            source_filename: Original PDF filename for reference
            
        Returns:
            GeneratedQuiz object with 10 questions
            
        Raises:
            AIProcessingError: If quiz generation fails after all retries
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # Validate input
                if not extracted_text or not isinstance(extracted_text, str):
                    raise AIProcessingError(
                        "Invalid text content provided",
                        error_type="INVALID_INPUT"
                    )
                
                cleaned_text = extracted_text.strip()
                if len(cleaned_text) < 100:
                    raise AIProcessingError(
                        f"Text content is too short for quiz generation (minimum 100 characters, got {len(cleaned_text)})",
                        error_type="INSUFFICIENT_CONTENT"
                    )
                
                if not source_filename or not isinstance(source_filename, str):
                    raise AIProcessingError(
                        "Invalid source filename provided",
                        error_type="INVALID_INPUT"
                    )
                
                # Create the prompt for quiz generation
                prompt = self._create_quiz_generation_prompt(cleaned_text)
                
                # Generate quiz using Gemini API with timeout
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(self.model.generate_content, prompt),
                        timeout=60.0  # 60 second timeout
                    )
                except asyncio.TimeoutError:
                    raise AIProcessingError(
                        "Gemini API request timed out",
                        error_type="API_TIMEOUT",
                        retry_count=retry_count
                    )
                
                if not response or not hasattr(response, 'text') or not response.text:
                    raise AIProcessingError(
                        "No response received from Gemini API",
                        error_type="EMPTY_RESPONSE",
                        retry_count=retry_count
                    )
                
                # Parse the JSON response
                quiz_data = self._parse_quiz_response(response.text)
                
                # Validate and create quiz questions
                questions = self._validate_and_create_questions(quiz_data)
                
                # Create the generated quiz object with validation
                try:
                    generated_quiz = GeneratedQuiz(
                        questions=questions,
                        source_material=source_filename
                    )
                except ValidationError as e:
                    raise AIProcessingError(
                        f"Generated quiz failed Pydantic validation: {str(e)}",
                        error_type="VALIDATION_FAILED",
                        retry_count=retry_count
                    )
                
                # Final quality validation
                quality_metrics = self.validate_quiz_quality(generated_quiz)
                if not quality_metrics['is_valid']:
                    if retry_count < self.max_retries:
                        logger.warning(f"Generated quiz quality issues (attempt {retry_count + 1}): {quality_metrics['issues']}")
                        retry_count += 1
                        await self._wait_with_backoff(retry_count)
                        continue
                    else:
                        raise AIProcessingError(
                            f"Generated quiz quality issues after {self.max_retries} attempts: {quality_metrics['issues']}",
                            error_type="QUALITY_VALIDATION_FAILED",
                            retry_count=retry_count
                        )
                
                logger.info(f"Successfully generated quiz with {len(questions)} questions from {source_filename}")
                return generated_quiz
                
            except AIProcessingError:
                # Re-raise AIProcessingError as-is
                raise
            except Exception as e:
                last_error = e
                error_msg = f"Unexpected error during quiz generation (attempt {retry_count + 1}): {str(e)}"
                logger.error(error_msg)
                
                if retry_count >= self.max_retries:
                    raise AIProcessingError(
                        f"Quiz generation failed after {self.max_retries + 1} attempts. Last error: {str(e)}",
                        error_type="MAX_RETRIES_EXCEEDED",
                        retry_count=retry_count
                    )
                
                retry_count += 1
                await self._wait_with_backoff(retry_count)
        
        # This should never be reached, but just in case
        raise AIProcessingError(
            f"Quiz generation failed after all retries. Last error: {str(last_error)}",
            error_type="GENERATION_FAILED",
            retry_count=retry_count
        )
    
    async def _wait_with_backoff(self, attempt: int):
        """Wait with exponential backoff between retries."""
        delay = self.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
        logger.info(f"Waiting {delay:.2f} seconds before retry attempt {attempt}")
        await asyncio.sleep(delay)
    
    def _create_quiz_generation_prompt(self, text_content: str) -> str:
        """Create a detailed prompt for quiz generation."""
        return f"""
        Based on the following text content, generate exactly 10 multiple-choice questions that test comprehension and understanding of the material.

        TEXT CONTENT:
        {text_content}

        REQUIREMENTS:
        1. Generate exactly 10 questions
        2. Each question should have exactly 4 answer options (A, B, C, D)
        3. Only one option should be correct
        4. Questions should test understanding, not just memorization
        5. Cover different parts of the content
        6. Make questions clear and unambiguous
        7. Ensure incorrect options are plausible but clearly wrong

        RESPONSE FORMAT:
        Return your response as a valid JSON object with this exact structure:
        {{
            "questions": [
                {{
                    "question_text": "Your question here?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": 0
                }},
                ... (repeat for all 10 questions)
            ]
        }}

        IMPORTANT:
        - The "correct_answer" field should be the index (0, 1, 2, or 3) of the correct option
        - Return ONLY the JSON object, no additional text or formatting
        - Ensure the JSON is valid and properly formatted
        """
    
    def _parse_quiz_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the JSON response from Gemini API with comprehensive error handling."""
        try:
            if not response_text or not isinstance(response_text, str):
                raise AIProcessingError(
                    "Empty or invalid response text from API",
                    error_type="EMPTY_RESPONSE"
                )
            
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Remove any markdown formatting if present
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            if not cleaned_text:
                raise AIProcessingError(
                    "Response text is empty after cleaning",
                    error_type="EMPTY_RESPONSE"
                )
            
            # Parse JSON
            try:
                quiz_data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response if it's embedded in text
                import re
                json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                if json_match:
                    try:
                        quiz_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        raise AIProcessingError(
                            f"Invalid JSON response from API: {str(e)}. Response: {cleaned_text[:200]}...",
                            error_type="INVALID_JSON"
                        )
                else:
                    raise AIProcessingError(
                        f"No valid JSON found in response: {str(e)}. Response: {cleaned_text[:200]}...",
                        error_type="INVALID_JSON"
                    )
            
            # Validate response structure
            if not isinstance(quiz_data, dict):
                raise AIProcessingError(
                    f"Response is not a JSON object, got {type(quiz_data)}",
                    error_type="INVALID_RESPONSE_FORMAT"
                )
            
            if 'questions' not in quiz_data:
                raise AIProcessingError(
                    "Response does not contain required 'questions' field",
                    error_type="MISSING_QUESTIONS_FIELD"
                )
            
            if not isinstance(quiz_data['questions'], list):
                raise AIProcessingError(
                    f"'questions' field must be a list, got {type(quiz_data['questions'])}",
                    error_type="INVALID_QUESTIONS_FORMAT"
                )
            
            if len(quiz_data['questions']) != 10:
                raise AIProcessingError(
                    f"Expected exactly 10 questions, got {len(quiz_data['questions'])}",
                    error_type="INCORRECT_QUESTION_COUNT"
                )
            
            return quiz_data
            
        except AIProcessingError:
            # Re-raise AIProcessingError as-is
            raise
        except Exception as e:
            raise AIProcessingError(
                f"Unexpected error parsing quiz response: {str(e)}",
                error_type="PARSING_ERROR"
            )
    
    def _validate_and_create_questions(self, quiz_data: Dict[str, Any]) -> List[QuizQuestion]:
        """Validate quiz data and create QuizQuestion objects with comprehensive error handling."""
        questions = []
        validation_errors = []
        
        try:
            for i, question_data in enumerate(quiz_data['questions']):
                try:
                    # Ensure question_data is a dictionary
                    if not isinstance(question_data, dict):
                        validation_errors.append(f"Question {i+1}: Must be a dictionary, got {type(question_data)}")
                        continue
                    
                    # Add question ID if missing
                    if 'question_id' not in question_data:
                        question_data['question_id'] = f"q_{i+1}"
                    
                    # Validate required fields
                    required_fields = ['question_text', 'options', 'correct_answer']
                    missing_fields = [field for field in required_fields if field not in question_data]
                    if missing_fields:
                        validation_errors.append(f"Question {i+1}: Missing required fields: {missing_fields}")
                        continue
                    
                    # Validate and clean question text
                    question_text = question_data.get('question_text', '')
                    if not isinstance(question_text, str):
                        validation_errors.append(f"Question {i+1}: question_text must be a string")
                        continue
                    
                    question_text = question_text.strip()
                    if len(question_text) < 10:
                        validation_errors.append(f"Question {i+1}: question_text must be at least 10 characters")
                        continue
                    
                    question_data['question_text'] = question_text
                    
                    # Validate options
                    options = question_data.get('options', [])
                    if not isinstance(options, list):
                        validation_errors.append(f"Question {i+1}: options must be a list")
                        continue
                    
                    if len(options) != 4:
                        validation_errors.append(f"Question {i+1}: Must have exactly 4 options, got {len(options)}")
                        continue
                    
                    # Clean and validate each option
                    cleaned_options = []
                    for j, option in enumerate(options):
                        if not isinstance(option, str):
                            validation_errors.append(f"Question {i+1}, Option {j+1}: Must be a string")
                            break
                        
                        cleaned_option = str(option).strip()
                        if len(cleaned_option) < 1:
                            validation_errors.append(f"Question {i+1}, Option {j+1}: Cannot be empty")
                            break
                        
                        cleaned_options.append(cleaned_option)
                    
                    if len(cleaned_options) != 4:
                        continue  # Skip this question due to option validation errors
                    
                    # Check for duplicate options
                    if len(set(cleaned_options)) != len(cleaned_options):
                        validation_errors.append(f"Question {i+1}: Options must be unique")
                        continue
                    
                    question_data['options'] = cleaned_options
                    
                    # Validate correct answer
                    correct_answer = question_data.get('correct_answer')
                    if not isinstance(correct_answer, int):
                        # Try to convert to int if it's a string number
                        try:
                            correct_answer = int(correct_answer)
                            question_data['correct_answer'] = correct_answer
                        except (ValueError, TypeError):
                            validation_errors.append(f"Question {i+1}: correct_answer must be an integer")
                            continue
                    
                    if correct_answer < 0 or correct_answer > 3:
                        validation_errors.append(f"Question {i+1}: correct_answer must be 0, 1, 2, or 3, got {correct_answer}")
                        continue
                    
                    # Create and validate QuizQuestion using Pydantic
                    try:
                        question = QuizQuestion(**question_data)
                        questions.append(question)
                    except ValidationError as e:
                        validation_errors.append(f"Question {i+1} Pydantic validation failed: {str(e)}")
                        continue
                    
                except Exception as e:
                    validation_errors.append(f"Question {i+1} processing failed: {str(e)}")
                    continue
            
            # Check if we have the required number of valid questions
            if len(questions) != 10:
                error_summary = f"Expected 10 valid questions, got {len(questions)}. Errors: {'; '.join(validation_errors)}"
                raise AIProcessingError(
                    error_summary,
                    error_type="QUESTION_VALIDATION_FAILED"
                )
            
            # Additional quality checks
            question_texts = [q.question_text.lower() for q in questions]
            if len(set(question_texts)) != len(question_texts):
                raise AIProcessingError(
                    "Duplicate questions detected in generated quiz",
                    error_type="DUPLICATE_QUESTIONS"
                )
            
            return questions
            
        except AIProcessingError:
            # Re-raise AIProcessingError as-is
            raise
        except Exception as e:
            raise AIProcessingError(
                f"Unexpected error validating questions: {str(e)}",
                error_type="VALIDATION_ERROR"
            )
    
    async def regenerate_quiz(self, extracted_text: str, source_filename: str, attempt: int = 1) -> GeneratedQuiz:
        """
        Regenerate quiz with different questions (for retry scenarios).
        
        Args:
            extracted_text: Text content extracted from PDF
            source_filename: Original PDF filename
            attempt: Attempt number for variation in generation
            
        Returns:
            GeneratedQuiz object with different questions
        """
        try:
            # Modify prompt slightly for variation
            variation_prompt = f"""
            Based on the following text content, generate exactly 10 NEW multiple-choice questions (attempt #{attempt}) 
            that test comprehension and understanding of the material. Focus on different aspects than a basic reading.

            TEXT CONTENT:
            {extracted_text}

            REQUIREMENTS:
            1. Generate exactly 10 questions that are DIFFERENT from basic comprehension
            2. Each question should have exactly 4 answer options
            3. Only one option should be correct
            4. Focus on analysis, inference, and deeper understanding
            5. Cover different sections of the content
            6. Make questions challenging but fair
            7. Ensure incorrect options are plausible distractors

            RESPONSE FORMAT:
            Return your response as a valid JSON object with this exact structure:
            {{
                "questions": [
                    {{
                        "question_text": "Your analytical question here?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0
                    }},
                    ... (repeat for all 10 questions)
                ]
            }}

            IMPORTANT:
            - The "correct_answer" field should be the index (0, 1, 2, or 3) of the correct option
            - Return ONLY the JSON object, no additional text or formatting
            - Ensure the JSON is valid and properly formatted
            """
            
            # Generate quiz using modified prompt
            response = await asyncio.to_thread(
                self.model.generate_content,
                variation_prompt
            )
            
            if not response.text:
                raise Exception("No response received from Gemini API")
            
            # Parse and validate
            quiz_data = self._parse_quiz_response(response.text)
            questions = self._validate_and_create_questions(quiz_data)
            
            generated_quiz = GeneratedQuiz(
                questions=questions,
                source_material=source_filename
            )
            
            logger.info(f"Successfully regenerated quiz (attempt {attempt}) with {len(questions)} questions")
            return generated_quiz
            
        except Exception as e:
            logger.error(f"Failed to regenerate quiz (attempt {attempt}): {str(e)}")
            raise Exception(f"Quiz regeneration failed: {str(e)}")
    
    def create_error_record(self, error: AIProcessingError, source_material: Optional[str] = None) -> QuizGenerationError:
        """Create a structured error record for AI processing failures."""
        return QuizGenerationError(
            error_type=error.error_type,
            error_message=str(error),
            source_material=source_material,
            retry_count=error.retry_count
        )
    
    async def generate_quiz_with_error_handling(self, extracted_text: str, source_filename: str) -> tuple[Optional[GeneratedQuiz], Optional[QuizGenerationError]]:
        """
        Generate quiz with comprehensive error handling and error record creation.
        
        Returns:
            Tuple of (GeneratedQuiz, None) on success or (None, QuizGenerationError) on failure
        """
        try:
            quiz = await self.generate_quiz_from_text(extracted_text, source_filename)
            return quiz, None
        except AIProcessingError as e:
            error_record = self.create_error_record(e, source_filename)
            logger.error(f"AI processing failed for {source_filename}: {error_record.dict()}")
            return None, error_record
        except Exception as e:
            # Convert unexpected errors to AIProcessingError
            ai_error = AIProcessingError(
                f"Unexpected error: {str(e)}",
                error_type="UNEXPECTED_ERROR"
            )
            error_record = self.create_error_record(ai_error, source_filename)
            logger.error(f"Unexpected error for {source_filename}: {error_record.dict()}")
            return None, error_record

    def validate_quiz_quality(self, quiz: GeneratedQuiz) -> Dict[str, Any]:
        """
        Validate the quality of generated quiz questions.
        
        Args:
            quiz: Generated quiz to validate
            
        Returns:
            Dictionary with quality metrics and validation results
        """
        quality_metrics = {
            'total_questions': len(quiz.questions),
            'valid_questions': 0,
            'unique_questions': 0,
            'option_diversity': 0,
            'issues': []
        }
        
        question_texts = set()
        
        for i, question in enumerate(quiz.questions):
            # Check for unique questions
            if question.question_text not in question_texts:
                question_texts.add(question.question_text)
                quality_metrics['unique_questions'] += 1
            else:
                quality_metrics['issues'].append(f"Question {i+1}: Duplicate question text")
            
            # Check option diversity
            unique_options = len(set(question.options))
            if unique_options == 4:
                quality_metrics['valid_questions'] += 1
            else:
                quality_metrics['issues'].append(f"Question {i+1}: Only {unique_options} unique options")
            
            # Check question length
            if len(question.question_text) < 10:
                quality_metrics['issues'].append(f"Question {i+1}: Question too short")
            
            # Check option lengths
            for j, option in enumerate(question.options):
                if len(option.strip()) < 2:
                    quality_metrics['issues'].append(f"Question {i+1}, Option {j+1}: Option too short")
        
        quality_metrics['option_diversity'] = quality_metrics['valid_questions'] / len(quiz.questions) if quiz.questions else 0
        quality_metrics['is_valid'] = len(quality_metrics['issues']) == 0
        
        return quality_metrics