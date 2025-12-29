"""
Unit tests for database service layer.
Tests high-level database operations and transaction management.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from app.services.database_service import DatabaseService
from app.schemas.user import UserCreate
from app.schemas.stake import StakeCreate, StakeSettlementRequest
from app.schemas.quiz import QuizCreate, QuizQuestion, QuizSubmission
from app.models import StakeStatus, SettlementType


class TestDatabaseService:
    """Test database service operations."""
    
    def setup_method(self):
        """Set up test instance."""
        self.db_service = DatabaseService()

    def create_sample_questions(self):
        """Helper to create sample quiz questions."""
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"q_{i+1}",
                question_text=f"Sample question {i+1} with sufficient length for validation",
                options=[f"Option A{i}", f"Option B{i}", f"Option C{i}", f"Option D{i}"],
                correct_answer=i % 4
            )
            questions.append(question)
        return questions

    def test_create_user_with_validation_success(self, db_session):
        """Test successful user creation with validation."""
        user_data = UserCreate(
            clerk_id="service_test_123",
            email="service@example.com"
        )
        
        result = self.db_service.create_user_with_validation(db_session, user_data)
        
        assert result['success'] is True
        assert result['user'].clerk_id == "service_test_123"
        assert result['user'].email == "service@example.com"
        assert 'User created successfully' in result['message']

    def test_create_user_with_validation_duplicate(self, db_session):
        """Test user creation with duplicate clerk_id."""
        user_data = UserCreate(
            clerk_id="duplicate_service",
            email="first@example.com"
        )
        
        # Create first user
        self.db_service.create_user_with_validation(db_session, user_data)
        
        # Try to create duplicate
        duplicate_data = UserCreate(
            clerk_id="duplicate_service",
            email="second@example.com"
        )
        result = self.db_service.create_user_with_validation(db_session, duplicate_data)
        
        assert result['success'] is False
        assert 'already exists' in result['error']
        assert 'validation failed' in result['message']

    def test_process_stake_settlement_success_pass(self, db_session, sample_user):
        """Test successful stake settlement for passing quiz."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x1111111111111111111111111111111111111111111111111111111111111111"
        )
        stake = self.db_service.stake_crud.create_stake(
            db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
        )
        
        # Set stake to ACTIVE
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        # Create and complete quiz with passing score
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = self.db_service.quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Submit passing answers (8 correct out of 10)
        user_answers = [0] * 8 + [1, 1]  # First 8 correct, last 2 wrong
        submission = QuizSubmission(
            quiz_id=str(quiz.quiz_id),
            user_answers=user_answers
        )
        completed_quiz = self.db_service.quiz_crud.submit_answers(
            db_session, quiz_id=str(quiz.quiz_id), submission=submission
        )
        
        # Process settlement
        settlement_request = StakeSettlementRequest(
            stake_id=str(stake.stake_id),
            quiz_score=completed_quiz.score,
            quiz_id=str(quiz.quiz_id)
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is True
        assert result['settlement_type'] == SettlementType.RETURNED
        assert result['quiz_score'] == 80  # 8/10 = 80%
        assert result['stake'].status == StakeStatus.SETTLED
        assert 'RETURNED' in result['message']

    def test_process_stake_settlement_success_fail(self, db_session, sample_user):
        """Test successful stake settlement for failing quiz."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("2.0"),
            transaction_hash="0x2222222222222222222222222222222222222222222222222222222222222222"
        )
        stake = self.db_service.stake_crud.create_stake(
            db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
        )
        
        # Set stake to ACTIVE
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        # Create and complete quiz with failing score
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = self.db_service.quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Submit failing answers (5 correct out of 10)
        user_answers = [0] * 5 + [1] * 5  # First 5 correct, last 5 wrong
        submission = QuizSubmission(
            quiz_id=str(quiz.quiz_id),
            user_answers=user_answers
        )
        completed_quiz = self.db_service.quiz_crud.submit_answers(
            db_session, quiz_id=str(quiz.quiz_id), submission=submission
        )
        
        # Process settlement
        settlement_request = StakeSettlementRequest(
            stake_id=str(stake.stake_id),
            quiz_score=completed_quiz.score,
            quiz_id=str(quiz.quiz_id)
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is True
        assert result['settlement_type'] == SettlementType.DONATED
        assert result['quiz_score'] == 50  # 5/10 = 50%
        assert result['stake'].status == StakeStatus.SETTLED
        assert 'DONATED' in result['message']

    def test_process_stake_settlement_quiz_not_found(self, db_session):
        """Test settlement with non-existent quiz."""
        settlement_request = StakeSettlementRequest(
            stake_id="fake-stake-id",
            quiz_score=80,
            quiz_id="fake-quiz-id"
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is False
        assert 'Quiz not found' in result['error']

    def test_process_stake_settlement_stake_not_found(self, db_session, sample_user):
        """Test settlement with non-existent stake."""
        # Create quiz without stake (this would normally not happen)
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id="fake-stake-id",
            questions=questions
        )
        
        settlement_request = StakeSettlementRequest(
            stake_id="fake-stake-id",
            quiz_score=80,
            quiz_id="fake-quiz-id"
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is False
        assert 'Quiz not found' in result['error']

    def test_process_stake_settlement_wrong_status(self, db_session, sample_user):
        """Test settlement with stake in wrong status."""
        # Create stake in PENDING status
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x3333333333333333333333333333333333333333333333333333333333333333"
        )
        stake = self.db_service.stake_crud.create_stake(
            db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
        )
        # Don't change status to ACTIVE
        
        # Create quiz
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = self.db_service.quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Complete quiz
        quiz.score = 80
        quiz.completed_at = datetime.utcnow()
        db_session.commit()
        
        # Try to settle
        settlement_request = StakeSettlementRequest(
            stake_id=str(stake.stake_id),
            quiz_score=80,
            quiz_id=str(quiz.quiz_id)
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is False
        assert 'Invalid stake status' in result['error']
        assert 'expected ACTIVE' in result['message']

    def test_process_stake_settlement_quiz_not_completed(self, db_session, sample_user):
        """Test settlement with incomplete quiz."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x4444444444444444444444444444444444444444444444444444444444444444"
        )
        stake = self.db_service.stake_crud.create_stake(
            db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
        )
        
        # Set stake to ACTIVE
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        # Create quiz but don't complete it
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = self.db_service.quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Try to settle incomplete quiz
        settlement_request = StakeSettlementRequest(
            stake_id=str(stake.stake_id),
            quiz_score=80,
            quiz_id=str(quiz.quiz_id)
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is False
        assert 'Quiz not completed' in result['error']

    def test_process_stake_settlement_score_mismatch(self, db_session, sample_user):
        """Test settlement with mismatched scores."""
        # Create and complete quiz
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x5555555555555555555555555555555555555555555555555555555555555555"
        )
        stake = self.db_service.stake_crud.create_stake(
            db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
        )
        
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = self.db_service.quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Complete quiz with score 70
        user_answers = [0] * 7 + [1] * 3  # 7 correct = 70%
        submission = QuizSubmission(
            quiz_id=str(quiz.quiz_id),
            user_answers=user_answers
        )
        completed_quiz = self.db_service.quiz_crud.submit_answers(
            db_session, quiz_id=str(quiz.quiz_id), submission=submission
        )
        
        # Try to settle with wrong score
        settlement_request = StakeSettlementRequest(
            stake_id=str(stake.stake_id),
            quiz_score=80,  # Wrong score
            quiz_id=str(quiz.quiz_id)
        )
        
        result = self.db_service.process_stake_settlement(db_session, settlement_request)
        
        assert result['success'] is False
        assert 'Score mismatch' in result['error']
        assert '80' in result['message'] and '70' in result['message']

    def test_get_user_dashboard_data(self, db_session, sample_user):
        """Test retrieving comprehensive user dashboard data."""
        # Create some test data
        stake_data = StakeCreate(
            amount_eth=Decimal("1.5"),
            transaction_hash="0x6666666666666666666666666666666666666666666666666666666666666666"
        )
        stake = self.db_service.stake_crud.create_stake(
            db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
        )
        
        result = self.db_service.get_user_dashboard_data(db_session, str(sample_user.user_id))
        
        assert result['success'] is True
        assert result['user'].user_id == sample_user.user_id
        assert len(result['stakes']) >= 1
        assert 'statistics' in result
        assert 'total_staked_eth' in result['statistics']
        assert 'quiz_statistics' in result['statistics']
        assert 'upload_statistics' in result['statistics']

    def test_get_user_dashboard_data_user_not_found(self, db_session):
        """Test dashboard data for non-existent user."""
        fake_user_id = "fake-user-id"
        
        result = self.db_service.get_user_dashboard_data(db_session, fake_user_id)
        
        assert result['success'] is False
        assert 'User not found' in result['error']

    def test_cleanup_failed_operations(self, db_session):
        """Test cleanup operations for failed transactions."""
        result = self.db_service.cleanup_failed_operations(db_session)
        
        assert result['success'] is True
        assert 'stuck_stakes' in result
        assert 'failed_uploads' in result
        assert isinstance(result['stuck_stakes'], int)
        assert isinstance(result['failed_uploads'], int)