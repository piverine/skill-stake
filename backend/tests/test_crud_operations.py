"""
Unit tests for CRUD operations and database functionality.
Tests CRUD operations, referential integrity, and transaction rollback scenarios.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import uuid

from app.crud import user_crud, stake_crud, quiz_crud, pdf_upload_crud
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.stake import StakeCreate, StakeUpdate
from app.schemas.quiz import QuizCreate, QuizQuestion, QuizSubmission
from app.schemas.pdf_upload import PDFUploadCreate, PDFUploadUpdate
from app.models import User, Stake, Quiz, PDFUpload, StakeStatus, SettlementType, ProcessingStatus


class TestUserCRUD:
    """Test user CRUD operations."""
    
    def test_create_user(self, db_session):
        """Test creating a new user."""
        user_data = UserCreate(
            clerk_id="test_clerk_123",
            email="test@example.com"
        )
        
        user = user_crud.create_user(db_session, user_in=user_data)
        
        assert user.clerk_id == "test_clerk_123"
        assert user.email == "test@example.com"
        assert user.user_id is not None
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_get_user_by_clerk_id(self, db_session):
        """Test retrieving user by Clerk ID."""
        user_data = UserCreate(
            clerk_id="test_clerk_456",
            email="test2@example.com"
        )
        created_user = user_crud.create_user(db_session, user_in=user_data)
        
        retrieved_user = user_crud.get_by_clerk_id(db_session, clerk_id="test_clerk_456")
        
        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id
        assert retrieved_user.email == "test2@example.com"

    def test_get_user_by_email(self, db_session):
        """Test retrieving user by email."""
        user_data = UserCreate(
            clerk_id="test_clerk_789",
            email="unique@example.com"
        )
        created_user = user_crud.create_user(db_session, user_in=user_data)
        
        retrieved_user = user_crud.get_by_email(db_session, email="unique@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id

    def test_duplicate_clerk_id_raises_error(self, db_session):
        """Test that duplicate clerk_id raises an error."""
        user_data1 = UserCreate(
            clerk_id="duplicate_clerk",
            email="first@example.com"
        )
        user_data2 = UserCreate(
            clerk_id="duplicate_clerk",
            email="second@example.com"
        )
        
        user_crud.create_user(db_session, user_in=user_data1)
        
        with pytest.raises(ValueError, match="already exists"):
            user_crud.create_user(db_session, user_in=user_data2)

    def test_update_user(self, db_session):
        """Test updating user information."""
        user_data = UserCreate(
            clerk_id="update_test",
            email="original@example.com"
        )
        user = user_crud.create_user(db_session, user_in=user_data)
        
        update_data = UserUpdate(email="updated@example.com")
        updated_user = user_crud.update(db_session, db_obj=user, obj_in=update_data)
        
        assert updated_user.email == "updated@example.com"
        assert updated_user.clerk_id == "update_test"  # Should remain unchanged


class TestStakeCRUD:
    """Test stake CRUD operations."""
    
    def test_create_stake(self, db_session, sample_user):
        """Test creating a new stake."""
        stake_data = StakeCreate(
            amount_eth=Decimal("1.5"),
            transaction_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        assert stake.amount_eth == Decimal("1.5")
        assert stake.user_id == sample_user.user_id
        assert stake.status == StakeStatus.PENDING
        assert stake.transaction_hash == stake_data.transaction_hash.lower()

    def test_get_stakes_by_user(self, db_session, sample_user):
        """Test retrieving stakes by user ID."""
        stake_data1 = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x1111111111111111111111111111111111111111111111111111111111111111"
        )
        stake_data2 = StakeCreate(
            amount_eth=Decimal("2.0"),
            transaction_hash="0x2222222222222222222222222222222222222222222222222222222222222222"
        )
        
        stake_crud.create_stake(db_session, stake_in=stake_data1, user_id=str(sample_user.user_id))
        stake_crud.create_stake(db_session, stake_in=stake_data2, user_id=str(sample_user.user_id))
        
        stakes = stake_crud.get_by_user_id(db_session, user_id=str(sample_user.user_id))
        
        assert len(stakes) == 2
        amounts = [stake.amount_eth for stake in stakes]
        assert Decimal("1.0") in amounts
        assert Decimal("2.0") in amounts

    def test_settle_stake(self, db_session, sample_user):
        """Test settling a stake."""
        stake_data = StakeCreate(
            amount_eth=Decimal("0.5"),
            transaction_hash="0x3333333333333333333333333333333333333333333333333333333333333333"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Update to ACTIVE status first
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        settled_stake = stake_crud.settle_stake(
            db_session, 
            stake_id=str(stake.stake_id),
            settlement_type=SettlementType.RETURNED
        )
        
        assert settled_stake.status == StakeStatus.SETTLED
        assert settled_stake.settlement_type == SettlementType.RETURNED
        assert settled_stake.settled_at is not None

    def test_duplicate_transaction_hash_raises_error(self, db_session, sample_user):
        """Test that duplicate transaction hash raises an error."""
        tx_hash = "0x4444444444444444444444444444444444444444444444444444444444444444"
        stake_data1 = StakeCreate(amount_eth=Decimal("1.0"), transaction_hash=tx_hash)
        stake_data2 = StakeCreate(amount_eth=Decimal("2.0"), transaction_hash=tx_hash)
        
        stake_crud.create_stake(db_session, stake_in=stake_data1, user_id=str(sample_user.user_id))
        
        with pytest.raises(ValueError, match="already exists"):
            stake_crud.create_stake(db_session, stake_in=stake_data2, user_id=str(sample_user.user_id))

    def test_get_total_staked_by_user(self, db_session, sample_user):
        """Test calculating total staked amount for a user."""
        # Create stakes with different statuses
        stake1_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x5555555555555555555555555555555555555555555555555555555555555555"
        )
        stake2_data = StakeCreate(
            amount_eth=Decimal("2.0"),
            transaction_hash="0x6666666666666666666666666666666666666666666666666666666666666666"
        )
        
        stake1 = stake_crud.create_stake(db_session, stake_in=stake1_data, user_id=str(sample_user.user_id))
        stake2 = stake_crud.create_stake(db_session, stake_in=stake2_data, user_id=str(sample_user.user_id))
        
        # Set one to ACTIVE (should be counted)
        stake1.status = StakeStatus.ACTIVE
        # Leave stake2 as PENDING (should not be counted)
        db_session.commit()
        
        total = stake_crud.get_total_staked_by_user(db_session, user_id=str(sample_user.user_id))
        
        assert total == Decimal("1.0")  # Only ACTIVE stakes counted


class TestQuizCRUD:
    """Test quiz CRUD operations."""
    
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

    def test_create_quiz(self, db_session, sample_user):
        """Test creating a new quiz."""
        # Create a stake first
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x7777777777777777777777777777777777777777777777777777777777777777"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        assert quiz.stake_id == stake.stake_id
        assert len(quiz.questions) == 10
        assert quiz.score is None
        assert quiz.completed_at is None

    def test_submit_quiz_answers(self, db_session, sample_user):
        """Test submitting quiz answers and score calculation."""
        # Create stake and quiz
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x8888888888888888888888888888888888888888888888888888888888888888"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        questions = self.create_sample_questions()
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Submit answers (all correct for first 7 questions, wrong for last 3)
        user_answers = []
        for i in range(10):
            if i < 7:
                user_answers.append(i % 4)  # Correct answer
            else:
                user_answers.append((i % 4 + 1) % 4)  # Wrong answer
        
        submission = QuizSubmission(
            quiz_id=str(quiz.quiz_id),
            user_answers=user_answers
        )
        
        completed_quiz = quiz_crud.submit_answers(db_session, quiz_id=str(quiz.quiz_id), submission=submission)
        
        assert completed_quiz.score == 70  # 7 out of 10 correct = 70%
        assert completed_quiz.user_answers == user_answers
        assert completed_quiz.completed_at is not None

    def test_quiz_statistics(self, db_session, sample_user):
        """Test quiz statistics calculation."""
        # Create multiple quizzes with different scores
        for i, score in enumerate([80, 60, 90, 50]):
            stake_data = StakeCreate(
                amount_eth=Decimal("1.0"),
                transaction_hash=f"0x{str(i).zfill(64)}"
            )
            stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
            
            questions = self.create_sample_questions()
            quiz_data = QuizCreate(
                stake_id=str(stake.stake_id),
                questions=questions
            )
            quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
            
            # Manually set score and completion
            quiz.score = score
            quiz.completed_at = datetime.utcnow()
            db_session.commit()
        
        stats = quiz_crud.get_quiz_statistics_by_user(db_session, user_id=str(sample_user.user_id))
        
        assert stats['total_quizzes'] == 4
        assert stats['average_score'] == 70.0  # (80+60+90+50)/4
        assert stats['passed_quizzes'] == 2  # 80 and 90 >= 70
        assert stats['failed_quizzes'] == 2  # 60 and 50 < 70
        assert stats['pass_rate'] == 50.0  # 2/4 * 100


class TestPDFUploadCRUD:
    """Test PDF upload CRUD operations."""
    
    def test_create_pdf_upload(self, db_session, sample_user):
        """Test creating a new PDF upload."""
        upload_data = PDFUploadCreate(
            filename="test_document.pdf",
            file_size=1024000  # 1MB
        )
        
        upload = pdf_upload_crud.create_upload(db_session, upload_in=upload_data, user_id=str(sample_user.user_id))
        
        assert upload.filename == "test_document.pdf"
        assert upload.file_size == 1024000
        assert upload.user_id == sample_user.user_id
        assert upload.processing_status == ProcessingStatus.UPLOADED

    def test_file_size_validation(self, db_session, sample_user):
        """Test file size validation."""
        upload_data = PDFUploadCreate(
            filename="large_file.pdf",
            file_size=60 * 1024 * 1024  # 60MB - exceeds 50MB limit
        )
        
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            pdf_upload_crud.create_upload(db_session, upload_in=upload_data, user_id=str(sample_user.user_id))

    def test_file_extension_validation(self, db_session, sample_user):
        """Test file extension validation."""
        upload_data = PDFUploadCreate(
            filename="document.txt",  # Wrong extension
            file_size=1024
        )
        
        with pytest.raises(ValueError, match="Only PDF files are allowed"):
            pdf_upload_crud.create_upload(db_session, upload_in=upload_data, user_id=str(sample_user.user_id))

    def test_update_processing_status(self, db_session, sample_user):
        """Test updating processing status."""
        upload_data = PDFUploadCreate(
            filename="process_test.pdf",
            file_size=2048
        )
        upload = pdf_upload_crud.create_upload(db_session, upload_in=upload_data, user_id=str(sample_user.user_id))
        
        updated_upload = pdf_upload_crud.update_processing_status(
            db_session,
            upload_id=str(upload.upload_id),
            status=ProcessingStatus.COMPLETED,
            extracted_text="Sample extracted text content"
        )
        
        assert updated_upload.processing_status == ProcessingStatus.COMPLETED
        assert updated_upload.extracted_text == "Sample extracted text content"


class TestReferentialIntegrity:
    """Test referential integrity constraints."""
    
    def test_cascade_relationships(self, db_session, sample_user):
        """Test that relationships are properly maintained."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x9999999999999999999999999999999999999999999999999999999999999999"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Create quiz for the stake
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"q_{i+1}",
                question_text=f"Test question {i+1} with sufficient length",
                options=[f"A{i}", f"B{i}", f"C{i}", f"D{i}"],
                correct_answer=0
            )
            questions.append(question)
        
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Verify relationships
        assert stake.quiz == quiz
        assert quiz.stake == stake
        assert stake in sample_user.stakes

    def test_foreign_key_constraint_violation(self, db_session):
        """Test that foreign key constraints are enforced."""
        # Try to create stake with non-existent user
        fake_user_id = str(uuid.uuid4())
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        
        with pytest.raises(IntegrityError):
            stake_crud.create_stake(db_session, stake_in=stake_data, user_id=fake_user_id)


class TestTransactionRollback:
    """Test transaction rollback scenarios."""
    
    def test_rollback_on_constraint_violation(self, db_session, sample_user):
        """Test that transactions are properly rolled back on constraint violations."""
        initial_stake_count = db_session.query(Stake).count()
        
        # Create a valid stake first
        stake_data1 = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        )
        stake_crud.create_stake(db_session, stake_in=stake_data1, user_id=str(sample_user.user_id))
        
        # Try to create another stake with the same transaction hash (should fail)
        stake_data2 = StakeCreate(
            amount_eth=Decimal("2.0"),
            transaction_hash="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"  # Duplicate
        )
        
        try:
            stake_crud.create_stake(db_session, stake_in=stake_data2, user_id=str(sample_user.user_id))
        except ValueError:
            pass  # Expected error
        
        # Verify only one stake was created
        final_stake_count = db_session.query(Stake).count()
        assert final_stake_count == initial_stake_count + 1

    def test_rollback_preserves_data_integrity(self, db_session, sample_user):
        """Test that rollback preserves data integrity."""
        # Get initial counts
        initial_user_count = db_session.query(User).count()
        initial_stake_count = db_session.query(Stake).count()
        
        try:
            # Start a transaction that will fail
            stake_data = StakeCreate(
                amount_eth=Decimal("1.0"),
                transaction_hash="0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
            )
            stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
            
            # Force a constraint violation by trying to create duplicate
            duplicate_stake = Stake(
                user_id=sample_user.user_id,
                amount_eth=Decimal("2.0"),
                transaction_hash="0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
            )
            db_session.add(duplicate_stake)
            db_session.commit()  # This should fail
            
        except IntegrityError:
            db_session.rollback()
        
        # Verify counts are preserved
        final_user_count = db_session.query(User).count()
        final_stake_count = db_session.query(Stake).count()
        
        assert final_user_count == initial_user_count
        # The first stake should have been created successfully before the rollback
        assert final_stake_count == initial_stake_count + 1

    def test_concurrent_transaction_isolation(self, db_session, sample_user):
        """Test transaction isolation with concurrent operations."""
        from sqlalchemy.orm import sessionmaker
        from app.core.database import engine
        
        # Create a second session to simulate concurrent access
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session2 = SessionLocal()
        
        try:
            # Session 1: Create a stake
            stake_data1 = StakeCreate(
                amount_eth=Decimal("1.0"),
                transaction_hash="0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
            )
            stake1 = stake_crud.create_stake(db_session, stake_in=stake_data1, user_id=str(sample_user.user_id))
            
            # Session 2: Try to read the stake before session 1 commits (should not see it)
            stake_from_session2 = stake_crud.get(db_session2, str(stake1.stake_id))
            
            # The stake should not be visible in session 2 until session 1 commits
            assert stake_from_session2 is None
            
            # Now commit session 1
            db_session.commit()
            
            # Session 2 should now see the stake after refresh
            db_session2.refresh(db_session2.query(Stake).first())
            stake_from_session2 = stake_crud.get(db_session2, str(stake1.stake_id))
            assert stake_from_session2 is not None
            
        finally:
            db_session2.close()

    def test_rollback_on_quiz_creation_failure(self, db_session, sample_user):
        """Test rollback when quiz creation fails after stake creation."""
        initial_stake_count = db_session.query(Stake).count()
        initial_quiz_count = db_session.query(Quiz).count()
        
        # Create a stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        try:
            # Try to create an invalid quiz (wrong number of questions)
            invalid_questions = [
                QuizQuestion(
                    question_id="q1",
                    question_text="Invalid quiz with only one question",
                    options=["A", "B", "C", "D"],
                    correct_answer=0
                )
            ]
            
            quiz_data = QuizCreate(
                stake_id=str(stake.stake_id),
                questions=invalid_questions  # Only 1 question instead of 10
            )
            
            quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
            
        except ValueError:
            # Expected error - quiz creation should fail
            db_session.rollback()
        
        # Verify that both stake and quiz counts are back to initial values
        final_stake_count = db_session.query(Stake).count()
        final_quiz_count = db_session.query(Quiz).count()
        
        # After rollback, counts should be back to initial
        assert final_stake_count == initial_stake_count
        assert final_quiz_count == initial_quiz_count

    def test_settlement_rollback_on_failure(self, db_session, sample_user):
        """Test that settlement operations are properly rolled back on failure."""
        # Create and activate a stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        original_status = stake.status
        original_settlement_type = stake.settlement_type
        original_settled_at = stake.settled_at
        
        # Simulate a settlement failure by corrupting the database state
        try:
            # Start settlement
            stake.status = StakeStatus.SETTLED
            stake.settlement_type = SettlementType.RETURNED
            from datetime import datetime
            stake.settled_at = datetime.utcnow()
            
            # Force an error by violating a constraint
            # Create another stake with the same transaction hash to trigger integrity error
            duplicate_stake = Stake(
                user_id=sample_user.user_id,
                amount_eth=Decimal("2.0"),
                transaction_hash="0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
            )
            db_session.add(duplicate_stake)
            db_session.commit()  # This should fail
            
        except IntegrityError:
            db_session.rollback()
        
        # Refresh the stake to get current state
        db_session.refresh(stake)
        
        # Verify that the stake is back to its original state
        assert stake.status == original_status
        assert stake.settlement_type == original_settlement_type
        assert stake.settled_at == original_settled_at


class TestDatabaseConstraints:
    """Test database constraints and data integrity."""
    
    def test_user_email_uniqueness_not_enforced(self, db_session):
        """Test that email uniqueness is not enforced at database level."""
        # Create two users with the same email (should be allowed)
        user1_data = UserCreate(
            clerk_id="user1_unique",
            email="shared@example.com"
        )
        user2_data = UserCreate(
            clerk_id="user2_unique", 
            email="shared@example.com"  # Same email
        )
        
        user1 = user_crud.create_user(db_session, user_in=user1_data)
        user2 = user_crud.create_user(db_session, user_in=user2_data)
        
        # Both should be created successfully (email uniqueness not enforced)
        assert user1.email == user2.email
        assert user1.clerk_id != user2.clerk_id

    def test_stake_amount_precision(self, db_session, sample_user):
        """Test that stake amounts maintain proper decimal precision."""
        # Test with high precision decimal
        precise_amount = Decimal("1.12345678")  # 8 decimal places
        
        stake_data = StakeCreate(
            amount_eth=precise_amount,
            transaction_hash="0x1111111111111111111111111111111111111111111111111111111111111111"
        )
        
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Verify precision is maintained
        assert stake.amount_eth == precise_amount
        assert str(stake.amount_eth) == "1.12345678"

    def test_transaction_hash_case_sensitivity(self, db_session, sample_user):
        """Test transaction hash handling with different cases."""
        # Create stake with uppercase hash
        upper_hash = "0xABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890"
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash=upper_hash
        )
        
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Verify hash is stored as provided (case preserved)
        assert stake.transaction_hash == upper_hash.lower()  # Should be normalized to lowercase

    def test_quiz_questions_json_structure(self, db_session, sample_user):
        """Test that quiz questions maintain proper JSON structure."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x2222222222222222222222222222222222222222222222222222222222222222"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Create quiz with complex question structure
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"complex_q_{i+1}",
                question_text=f"Complex question {i+1} with special characters: àáâãäå & symbols!@#$%",
                options=[
                    f"Option A{i} with unicode: ñ",
                    f"Option B{i} with symbols: &*()[]",
                    f"Option C{i} with numbers: 123.456",
                    f"Option D{i} with quotes: \"test\""
                ],
                correct_answer=i % 4
            )
            questions.append(question)
        
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Verify JSON structure is preserved
        assert len(quiz.questions) == 10
        for i, stored_question in enumerate(quiz.questions):
            assert stored_question['question_id'] == f"complex_q_{i+1}"
            assert "special characters" in stored_question['question_text']
            assert len(stored_question['options']) == 4

    def test_pdf_upload_filename_validation(self, db_session, sample_user):
        """Test PDF upload filename edge cases."""
        # Test with very long filename
        long_filename = "a" * 250 + ".pdf"  # 254 characters total
        
        upload_data = PDFUploadCreate(
            filename=long_filename,
            file_size=1024
        )
        
        upload = pdf_upload_crud.create_upload(db_session, upload_in=upload_data, user_id=str(sample_user.user_id))
        assert upload.filename == long_filename

    def test_cascade_delete_behavior(self, db_session, sample_user):
        """Test cascade delete behavior for related records."""
        # Create stake with quiz
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x3333333333333333333333333333333333333333333333333333333333333333"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"cascade_q_{i+1}",
                question_text=f"Cascade test question {i+1} with sufficient length",
                options=[f"A{i}", f"B{i}", f"C{i}", f"D{i}"],
                correct_answer=0
            )
            questions.append(question)
        
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Delete the stake
        stake_crud.remove(db_session, id=str(stake.stake_id))
        
        # Verify quiz still exists (no cascade delete configured)
        remaining_quiz = quiz_crud.get(db_session, str(quiz.quiz_id))
        assert remaining_quiz is not None  # Quiz should still exist