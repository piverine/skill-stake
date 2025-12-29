"""
Property-based tests for data integrity and consistency.

Feature: skill-stake-learning, Property 7: Data Integrity and Consistency
"""

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from datetime import datetime, timezone
import uuid

from app.models import User, Stake, Quiz, PDFUpload, StakeStatus, SettlementType, ProcessingStatus
from app.schemas.user import UserCreate
from app.schemas.stake import StakeCreate
from app.schemas.quiz import QuizCreate, QuizQuestion
from app.schemas.pdf_upload import PDFUploadCreate


# Hypothesis strategies for generating test data
@st.composite
def user_data(draw):
    """Generate valid user data."""
    clerk_id = draw(st.text(min_size=1, max_size=255, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))))
    email = draw(st.emails())
    return {
        'clerk_id': clerk_id,
        'email': email
    }

@st.composite
def stake_data(draw):
    """Generate valid stake data."""
    amount_eth = draw(st.decimals(min_value=Decimal('0.001'), max_value=Decimal('100'), places=8))
    tx_hash = '0x' + draw(st.text(min_size=64, max_size=64, alphabet='0123456789abcdef'))
    return {
        'amount_eth': amount_eth,
        'transaction_hash': tx_hash
    }

@st.composite
def quiz_question_data(draw):
    """Generate valid quiz question data."""
    question_text = draw(st.text(min_size=10, max_size=500))
    options = draw(st.lists(st.text(min_size=1, max_size=100), min_size=4, max_size=4, unique=True))
    correct_answer = draw(st.integers(min_value=0, max_value=3))
    return QuizQuestion(
        question_id=str(uuid.uuid4()),
        question_text=question_text,
        options=options,
        correct_answer=correct_answer
    )

@st.composite
def pdf_upload_data(draw):
    """Generate valid PDF upload data."""
    filename = draw(st.text(min_size=1, max_size=250)) + '.pdf'
    file_size = draw(st.integers(min_value=1, max_value=50*1024*1024))
    return {
        'filename': filename,
        'file_size': file_size
    }


class TestDataIntegrityProperty:
    """Property-based tests for data integrity and consistency."""

    @given(user_data())
    @settings(max_examples=100)
    def test_user_creation_maintains_integrity(self, db_session, user_data_dict):
        """
        Property 7: Data Integrity and Consistency
        For any valid user data, creating a user should maintain database integrity.
        Validates: Requirements 7.1, 7.3, 7.4
        """
        # Create user
        user = User(**user_data_dict)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Verify integrity constraints
        assert user.user_id is not None
        assert user.clerk_id == user_data_dict['clerk_id']
        assert user.email == user_data_dict['email']
        assert user.created_at is not None
        assert user.updated_at is not None
        
        # Verify uniqueness constraint
        duplicate_user = User(**user_data_dict)
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    @given(user_data(), stake_data())
    @settings(max_examples=100)
    def test_stake_referential_integrity(self, db_session, user_data_dict, stake_data_dict):
        """
        Property 7: Data Integrity and Consistency
        For any valid user and stake data, creating stakes should maintain referential integrity.
        Validates: Requirements 7.1, 7.3, 7.4
        """
        # Create user first
        user = User(**user_data_dict)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create stake with valid foreign key
        stake = Stake(
            user_id=user.user_id,
            **stake_data_dict
        )
        db_session.add(stake)
        db_session.commit()
        db_session.refresh(stake)
        
        # Verify referential integrity
        assert stake.user_id == user.user_id
        assert stake.user == user
        assert stake in user.stakes
        
        # Verify foreign key constraint
        invalid_stake = Stake(
            user_id=uuid.uuid4(),  # Non-existent user
            **stake_data_dict
        )
        db_session.add(invalid_stake)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    @given(user_data(), stake_data(), st.lists(quiz_question_data(), min_size=10, max_size=10))
    @settings(max_examples=50)
    def test_quiz_data_consistency(self, db_session, user_data_dict, stake_data_dict, questions):
        """
        Property 7: Data Integrity and Consistency
        For any valid quiz data, creating quizzes should maintain data consistency.
        Validates: Requirements 7.1, 7.3, 7.4
        """
        # Create user and stake
        user = User(**user_data_dict)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        stake = Stake(user_id=user.user_id, **stake_data_dict)
        db_session.add(stake)
        db_session.commit()
        db_session.refresh(stake)
        
        # Create quiz with valid data
        questions_dict = [q.dict() for q in questions]
        quiz = Quiz(
            stake_id=stake.stake_id,
            questions=questions_dict
        )
        db_session.add(quiz)
        db_session.commit()
        db_session.refresh(quiz)
        
        # Verify data consistency
        assert quiz.stake_id == stake.stake_id
        assert quiz.stake == stake
        assert stake.quiz == quiz
        assert len(quiz.questions) == 10
        
        # Verify JSON structure integrity
        for i, question in enumerate(quiz.questions):
            assert 'question_id' in question
            assert 'question_text' in question
            assert 'options' in question
            assert 'correct_answer' in question
            assert len(question['options']) == 4
            assert 0 <= question['correct_answer'] <= 3

    @given(user_data(), pdf_upload_data())
    @settings(max_examples=100)
    def test_pdf_upload_constraints(self, db_session, user_data_dict, pdf_data_dict):
        """
        Property 7: Data Integrity and Consistency
        For any valid PDF upload data, creating uploads should maintain constraints.
        Validates: Requirements 7.1, 7.3, 7.4
        """
        # Create user first
        user = User(**user_data_dict)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create PDF upload
        pdf_upload = PDFUpload(
            user_id=user.user_id,
            **pdf_data_dict
        )
        db_session.add(pdf_upload)
        db_session.commit()
        db_session.refresh(pdf_upload)
        
        # Verify constraints
        assert pdf_upload.user_id == user.user_id
        assert pdf_upload.user == user
        assert pdf_upload in user.pdf_uploads
        assert pdf_upload.processing_status == ProcessingStatus.UPLOADED
        assert pdf_upload.created_at is not None

    @given(user_data(), stake_data())
    @settings(max_examples=50)
    def test_transaction_rollback_integrity(self, db_session, user_data_dict, stake_data_dict):
        """
        Property 7: Data Integrity and Consistency
        For any transaction that fails, database should maintain integrity through rollback.
        Validates: Requirements 7.1, 7.3, 7.4
        """
        # Create user
        user = User(**user_data_dict)
        db_session.add(user)
        db_session.commit()
        initial_user_count = db_session.query(User).count()
        initial_stake_count = db_session.query(Stake).count()
        
        try:
            # Start transaction that will fail
            stake1 = Stake(user_id=user.user_id, **stake_data_dict)
            db_session.add(stake1)
            
            # Add invalid stake that will cause constraint violation
            invalid_stake = Stake(
                user_id=uuid.uuid4(),  # Non-existent user
                **stake_data_dict
            )
            db_session.add(invalid_stake)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
        
        # Verify rollback maintained integrity
        final_user_count = db_session.query(User).count()
        final_stake_count = db_session.query(Stake).count()
        
        assert final_user_count == initial_user_count
        assert final_stake_count == initial_stake_count

    @given(user_data(), stake_data())
    @settings(max_examples=50)
    def test_cascade_delete_integrity(self, db_session, user_data_dict, stake_data_dict):
        """
        Property 7: Data Integrity and Consistency
        For any user deletion, related data should maintain referential integrity.
        Validates: Requirements 7.1, 7.3, 7.4
        """
        # Create user with related data
        user = User(**user_data_dict)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        stake = Stake(user_id=user.user_id, **stake_data_dict)
        db_session.add(stake)
        db_session.commit()
        
        # Verify relationships exist
        assert len(user.stakes) == 1
        assert stake.user == user
        
        # Note: In a real system, we might have cascade delete rules
        # For now, we verify that foreign key constraints prevent orphaned records
        db_session.delete(user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()