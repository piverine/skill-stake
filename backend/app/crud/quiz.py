from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import logging
from app.crud.base import CRUDBase
from app.models.quiz import Quiz
from app.schemas.quiz import QuizCreate, QuizSubmission, GeneratedQuiz, QuizQuestion, QuizValidationResult

logger = logging.getLogger(__name__)


class CRUDQuiz(CRUDBase[Quiz, QuizCreate, dict]):
    def get_by_stake_id(self, db: Session, *, stake_id: str) -> Optional[Quiz]:
        """Get quiz by stake ID."""
        return db.query(Quiz).filter(Quiz.stake_id == stake_id).first()

    def get_by_user_id(self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100) -> List[Quiz]:
        """Get all quizzes for a specific user through stakes."""
        from app.models.stake import Stake
        return (
            db.query(Quiz)
            .join(Stake, Quiz.stake_id == Stake.stake_id)
            .filter(Stake.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_quiz(self, db: Session, *, quiz_data: GeneratedQuiz, stake_id: str) -> Quiz:
        """Create a new quiz from generated quiz data with comprehensive validation."""
        try:
            # Validate stake_id format
            import uuid
            try:
                stake_uuid = uuid.UUID(stake_id)
            except ValueError:
                raise ValueError(f"Invalid stake ID format: {stake_id}")
            
            # Check if quiz already exists for this stake
            existing_quiz = self.get_by_stake_id(db, stake_id=stake_id)
            if existing_quiz:
                raise ValueError(f"Quiz already exists for stake {stake_id}")
            
            # Validate quiz data using Pydantic validation
            try:
                # This will trigger all Pydantic validators
                validated_quiz = GeneratedQuiz(**quiz_data.dict())
            except Exception as e:
                raise ValueError(f"Quiz data validation failed: {str(e)}")
            
            # Additional business logic validation
            validation_result = self._validate_quiz_business_rules(validated_quiz)
            if not validation_result.is_valid:
                error_msg = "; ".join(validation_result.validation_errors)
                raise ValueError(f"Quiz business validation failed: {error_msg}")
            
            # Convert questions to dict format for JSONB storage
            questions_data = []
            for question in validated_quiz.questions:
                question_dict = question.dict()
                # Ensure all required fields are present
                required_fields = ['question_id', 'question_text', 'options', 'correct_answer']
                for field in required_fields:
                    if field not in question_dict:
                        raise ValueError(f"Missing required field '{field}' in question {question.question_id}")
                questions_data.append(question_dict)
            
            # Create database record
            db_quiz = Quiz(
                stake_id=stake_id,
                questions=questions_data
            )
            
            db.add(db_quiz)
            db.commit()
            db.refresh(db_quiz)
            
            logger.info(f"Successfully created quiz {db_quiz.quiz_id} for stake {stake_id}")
            return db_quiz
            
        except ValueError as e:
            # Re-raise validation errors as-is
            logger.error(f"Quiz validation error for stake {stake_id}: {str(e)}")
            raise e
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error creating quiz for stake {stake_id}: {str(e)}")
            raise ValueError(f"Database constraint violation: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating quiz for stake {stake_id}: {str(e)}")
            raise ValueError(f"Database operation failed: {str(e)}")
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error creating quiz for stake {stake_id}: {str(e)}")
            raise ValueError(f"Quiz creation failed: {str(e)}")
    
    def _validate_quiz_business_rules(self, quiz: GeneratedQuiz) -> QuizValidationResult:
        """Validate quiz against business rules and quality standards."""
        errors = []
        recommendations = []
        quality_score = 1.0
        
        # Check question distribution and quality
        question_lengths = [len(q.question_text) for q in quiz.questions]
        avg_question_length = sum(question_lengths) / len(question_lengths)
        
        if avg_question_length < 20:
            errors.append("Average question length is too short (minimum 20 characters)")
            quality_score -= 0.2
        
        # Check for question variety (different question starters)
        question_starters = [q.question_text.split()[0].lower() for q in quiz.questions if q.question_text]
        unique_starters = len(set(question_starters))
        
        if unique_starters < 5:
            recommendations.append("Consider using more varied question starters for better diversity")
            quality_score -= 0.1
        
        # Check option lengths for balance
        for i, question in enumerate(quiz.questions):
            option_lengths = [len(opt) for opt in question.options]
            if max(option_lengths) - min(option_lengths) > 50:
                recommendations.append(f"Question {i+1}: Large variation in option lengths may indicate quality issues")
                quality_score -= 0.05
        
        # Check for potential duplicate content
        all_text = " ".join([q.question_text for q in quiz.questions])
        words = all_text.lower().split()
        unique_words = len(set(words))
        total_words = len(words)
        
        if unique_words / total_words < 0.7:
            recommendations.append("High word repetition detected - consider more diverse vocabulary")
            quality_score -= 0.1
        
        # Ensure quality score doesn't go below 0
        quality_score = max(0.0, quality_score)
        
        return QuizValidationResult(
            is_valid=len(errors) == 0,
            validation_errors=errors,
            quality_score=quality_score,
            recommendations=recommendations
        )

    def submit_answers(self, db: Session, *, quiz_id: str, user_answers: List[int], score: int) -> Quiz:
        """Submit quiz answers and score with comprehensive validation."""
        try:
            # Validate quiz_id format
            import uuid
            try:
                quiz_uuid = uuid.UUID(quiz_id)
            except ValueError:
                raise ValueError(f"Invalid quiz ID format: {quiz_id}")
            
            quiz = self.get(db, quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")
            
            if quiz.completed_at:
                raise ValueError("Quiz has already been completed")
            
            if len(user_answers) != 10:
                raise ValueError("Must provide exactly 10 answers")
            
            # Validate answer format
            for i, answer in enumerate(user_answers):
                if not isinstance(answer, int) or answer < 0 or answer > 3:
                    raise ValueError(f"Answer {i+1} must be an integer between 0 and 3")
            
            # Validate score
            if not isinstance(score, int) or score < 0 or score > 100:
                raise ValueError("Score must be an integer between 0 and 100")
            
            # Verify score calculation
            calculated_score = self.calculate_score(quiz, user_answers)
            if calculated_score != score:
                logger.warning(f"Score mismatch for quiz {quiz_id}: provided {score}, calculated {calculated_score}")
                # Use calculated score for consistency
                score = calculated_score
            
            # Update quiz with answers and score
            quiz.user_answers = user_answers
            quiz.score = score
            quiz.completed_at = datetime.utcnow()
            
            db.add(quiz)
            db.commit()
            db.refresh(quiz)
            
            logger.info(f"Successfully submitted answers for quiz {quiz_id} with score {score}")
            return quiz
            
        except ValueError as e:
            # Re-raise validation errors as-is
            logger.error(f"Quiz submission validation error for quiz {quiz_id}: {str(e)}")
            raise e
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error submitting quiz {quiz_id}: {str(e)}")
            raise ValueError(f"Database operation failed: {str(e)}")
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error submitting quiz {quiz_id}: {str(e)}")
            raise ValueError(f"Quiz submission failed: {str(e)}")

    def calculate_score(self, quiz: Quiz, user_answers: List[int]) -> int:
        """Calculate quiz score based on user answers with validation."""
        try:
            if len(user_answers) != 10:
                raise ValueError("Must provide exactly 10 answers")
            
            if not quiz.questions or len(quiz.questions) != 10:
                raise ValueError("Quiz must have exactly 10 questions")
            
            # Validate user answers format
            for i, answer in enumerate(user_answers):
                if not isinstance(answer, int) or answer < 0 or answer > 3:
                    raise ValueError(f"Answer {i+1} must be an integer between 0 and 3")
            
            correct_answers = 0
            for i, user_answer in enumerate(user_answers):
                if i < len(quiz.questions):
                    question = quiz.questions[i]
                    
                    # Validate question structure
                    if not isinstance(question, dict) or 'correct_answer' not in question:
                        raise ValueError(f"Question {i+1} has invalid structure")
                    
                    correct_answer = question['correct_answer']
                    
                    # Validate correct answer format
                    if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer > 3:
                        raise ValueError(f"Question {i+1} has invalid correct answer: {correct_answer}")
                    
                    if user_answer == correct_answer:
                        correct_answers += 1
            
            score = int((correct_answers / 10) * 100)
            logger.debug(f"Calculated score: {correct_answers}/10 correct = {score}%")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating quiz score: {str(e)}")
            raise ValueError(f"Score calculation failed: {str(e)}")

    def update_questions(self, db: Session, *, quiz_id: str, new_questions: List[QuizQuestion]) -> Quiz:
        """Update quiz questions (for regeneration)."""
        quiz = self.get(db, quiz_id)
        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")
        
        if quiz.completed_at:
            raise ValueError("Cannot update questions for completed quiz")
        
        if len(new_questions) != 10:
            raise ValueError("Must provide exactly 10 questions")
        
        # Convert questions to dict format
        questions_data = [q.dict() for q in new_questions]
        quiz.questions = questions_data
        
        # Reset any existing answers
        quiz.user_answers = None
        quiz.score = None
        
        try:
            db.add(quiz)
            db.commit()
            db.refresh(quiz)
            return quiz
        except Exception as e:
            db.rollback()
            raise e

    def get_completed_quizzes_by_user(self, db: Session, *, user_id: str) -> List[Quiz]:
        """Get all completed quizzes for a user."""
        from app.models.stake import Stake
        return (
            db.query(Quiz)
            .join(Stake, Quiz.stake_id == Stake.stake_id)
            .filter(Stake.user_id == user_id)
            .filter(Quiz.completed_at.isnot(None))
            .all()
        )

    def get_quiz_statistics_by_user(self, db: Session, *, user_id: str) -> dict:
        """Get quiz statistics for a user."""
        completed_quizzes = self.get_completed_quizzes_by_user(db, user_id=user_id)
        
        if not completed_quizzes:
            return {
                'total_quizzes': 0,
                'average_score': 0,
                'passed_quizzes': 0,
                'failed_quizzes': 0,
                'pass_rate': 0
            }
        
        total_score = sum(quiz.score for quiz in completed_quizzes if quiz.score is not None)
        passed_quizzes = len([quiz for quiz in completed_quizzes if quiz.score and quiz.score >= 70])
        
        return {
            'total_quizzes': len(completed_quizzes),
            'average_score': total_score / len(completed_quizzes),
            'passed_quizzes': passed_quizzes,
            'failed_quizzes': len(completed_quizzes) - passed_quizzes,
            'pass_rate': (passed_quizzes / len(completed_quizzes)) * 100
        }

    def validate_quiz_data_integrity(self, db: Session, quiz_id: str) -> QuizValidationResult:
        """Validate the integrity of stored quiz data."""
        try:
            quiz = self.get(db, quiz_id)
            if not quiz:
                return QuizValidationResult(
                    is_valid=False,
                    validation_errors=[f"Quiz {quiz_id} not found"],
                    quality_score=0.0
                )
            
            errors = []
            recommendations = []
            quality_score = 1.0
            
            # Validate questions structure
            if not quiz.questions:
                errors.append("Quiz has no questions")
                return QuizValidationResult(
                    is_valid=False,
                    validation_errors=errors,
                    quality_score=0.0
                )
            
            if len(quiz.questions) != 10:
                errors.append(f"Quiz must have exactly 10 questions, found {len(quiz.questions)}")
                quality_score -= 0.5
            
            # Validate each question
            for i, question in enumerate(quiz.questions):
                if not isinstance(question, dict):
                    errors.append(f"Question {i+1} is not a valid dictionary")
                    continue
                
                # Check required fields
                required_fields = ['question_id', 'question_text', 'options', 'correct_answer']
                for field in required_fields:
                    if field not in question:
                        errors.append(f"Question {i+1} missing required field: {field}")
                
                # Validate question text
                if 'question_text' in question:
                    text = question['question_text']
                    if not isinstance(text, str) or len(text.strip()) < 10:
                        errors.append(f"Question {i+1} text is too short or invalid")
                
                # Validate options
                if 'options' in question:
                    options = question['options']
                    if not isinstance(options, list) or len(options) != 4:
                        errors.append(f"Question {i+1} must have exactly 4 options")
                    else:
                        # Check for empty or duplicate options
                        clean_options = [str(opt).strip() for opt in options]
                        if any(len(opt) < 1 for opt in clean_options):
                            errors.append(f"Question {i+1} has empty options")
                        if len(set(clean_options)) != len(clean_options):
                            errors.append(f"Question {i+1} has duplicate options")
                
                # Validate correct answer
                if 'correct_answer' in question:
                    correct_answer = question['correct_answer']
                    if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer > 3:
                        errors.append(f"Question {i+1} has invalid correct answer: {correct_answer}")
            
            # Check for duplicate questions
            if len(quiz.questions) > 1:
                question_texts = []
                for question in quiz.questions:
                    if isinstance(question, dict) and 'question_text' in question:
                        question_texts.append(question['question_text'].lower().strip())
                
                if len(set(question_texts)) != len(question_texts):
                    errors.append("Quiz contains duplicate questions")
                    quality_score -= 0.2
            
            # Validate user answers if present
            if quiz.user_answers:
                if len(quiz.user_answers) != 10:
                    errors.append(f"User answers must contain exactly 10 responses, found {len(quiz.user_answers)}")
                
                for i, answer in enumerate(quiz.user_answers):
                    if not isinstance(answer, int) or answer < 0 or answer > 3:
                        errors.append(f"User answer {i+1} is invalid: {answer}")
            
            # Validate score if present
            if quiz.score is not None:
                if not isinstance(quiz.score, int) or quiz.score < 0 or quiz.score > 100:
                    errors.append(f"Quiz score is invalid: {quiz.score}")
                
                # Verify score calculation if answers are present
                if quiz.user_answers and len(quiz.user_answers) == 10:
                    try:
                        calculated_score = self.calculate_score(quiz, quiz.user_answers)
                        if calculated_score != quiz.score:
                            errors.append(f"Score mismatch: stored {quiz.score}, calculated {calculated_score}")
                    except Exception as e:
                        errors.append(f"Cannot verify score calculation: {str(e)}")
            
            # Adjust quality score based on errors
            if errors:
                quality_score = max(0.0, quality_score - (len(errors) * 0.1))
            
            return QuizValidationResult(
                is_valid=len(errors) == 0,
                validation_errors=errors,
                quality_score=quality_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error validating quiz data integrity for {quiz_id}: {str(e)}")
            return QuizValidationResult(
                is_valid=False,
                validation_errors=[f"Validation failed: {str(e)}"],
                quality_score=0.0
            )

    def get(self, db: Session, id: str) -> Optional[Quiz]:
        """Override to use quiz_id field."""
        return db.query(Quiz).filter(Quiz.quiz_id == id).first()

    def remove(self, db: Session, *, id: str) -> Optional[Quiz]:
        """Override to use quiz_id field."""
        obj = db.query(Quiz).filter(Quiz.quiz_id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return obj
        return None


quiz_crud = CRUDQuiz(Quiz)