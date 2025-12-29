"""
Additional unit tests for database operations focusing on edge cases and comprehensive coverage.
Tests CRUD operations, referential integrity, and transaction rollback scenarios.
Requirements: 7.3, 7.4
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import uuid

from app.crud import user_crud, stake_crud, quiz_crud, pdf_upload_crud
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.stake import StakeCreate, StakeUpdate
from app.schemas.quiz import QuizCreate, QuizQuestion, QuizSubmission
from app.schemas.pdf_upload import PDFUploadCreate, PDFUploadUpdate
from app.models import User, Stake, Quiz, PDFUpload, StakeStatus, SettlementType, ProcessingStatus


class TestAdvancedCRUDOperations:
    """Test advanced CRUD operations and edge cases."""
    
    def test_user_crud_with_special_characters(self, db_session):
        """Test user creation with special characters in email."""
        user_data = UserCreate(
            clerk_id="special_chars_test",
            email="test+special.chars@example-domain.com"
        )
        
        user = user_crud.create_user(db_session, user_in=user_data)
        
        assert user.email == "test+special.chars@example-domain.com"
        assert user.clerk_id == "special_chars_test"
        
        # Test retrieval
        retrieved_user = user_crud.get_by_email(db_session, email=user.email)
        assert retrieved_user.user_id == user.user_id

    def test_stake_crud_with_edge_amounts(self, db_session, sample_user):
        """Test stake creation with edge case amounts."""
        # Test very small amount
        small_stake_data = StakeCreate(
            amount_eth=Decimal("0.00000001"),  # 1 wei in ETH
            transaction_hash="0x1111111111111111111111111111111111111111111111111111111111111111"
        )
        
        small_stake = stake_crud.create_stake(
            db_session, stake_in=small_stake_data, user_id=str(sample_user.user_id)
        )
        
        assert small_stake.amount_eth == Decimal("0.00000001")
        
        # Test large amount
        large_stake_data = StakeCreate(
            amount_eth=Decimal("999999.99999999"),  # Large amount
            transaction_hash="0x2222222222222222222222222222222222222222222222222222222222222222"
        )
        
        large_stake = stake_crud.create_stake(
            db_session, stake_in=large_stake_data, user_id=str(sample_user.user_id)
        )
        
        assert large_stake.amount_eth == Decimal("999999.99999999")

    def test_quiz_crud_with_complex_questions(self, db_session, sample_user):
        """Test quiz creation with complex question structures."""
        # Create stake first
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x3333333333333333333333333333333333333333333333333333333333333333"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Create quiz with complex questions
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"complex_q_{i+1}",
                question_text=f"Complex question {i+1}: What is the result of 2^{i+1} + {i*2}? Consider edge cases and mathematical precision.",
                options=[
                    f"Answer A: {2**(i+1) + i*2}",
                    f"Answer B: {2**(i+1) + i*2 + 1}",
                    f"Answer C: {2**(i+1) + i*2 - 1}",
                    f"Answer D: {2**(i+1) * i*2}"
                ],
                correct_answer=0  # First option is correct
            )
            questions.append(question)
        
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        assert len(quiz.questions) == 10
        for i, stored_question in enumerate(quiz.questions):
            assert f"2^{i+1}" in stored_question['question_text']
            assert len(stored_question['options']) == 4

    def test_pdf_upload_crud_with_edge_cases(self, db_session, sample_user):
        """Test PDF upload CRUD with edge cases."""
        # Test minimum valid file size
        min_upload_data = PDFUploadCreate(
            filename="tiny.pdf",
            file_size=1  # 1 byte
        )
        
        min_upload = pdf_upload_crud.create_upload(
            db_session, upload_in=min_upload_data, user_id=str(sample_user.user_id)
        )
        
        assert min_upload.file_size == 1
        
        # Test maximum valid file size (just under 50MB)
        max_upload_data = PDFUploadCreate(
            filename="large.pdf",
            file_size=50 * 1024 * 1024 - 1  # Just under 50MB
        )
        
        max_upload = pdf_upload_crud.create_upload(
            db_session, upload_in=max_upload_data, user_id=str(sample_user.user_id)
        )
        
        assert max_upload.file_size == 50 * 1024 * 1024 - 1

    def test_batch_operations_performance(self, db_session, sample_user):
        """Test batch operations for performance and consistency."""
        # Create multiple stakes in batch
        stakes = []
        for i in range(50):
            stake_data = StakeCreate(
                amount_eth=Decimal(f"{i+1}.{i:02d}"),
                transaction_hash=f"0x{str(i).zfill(64)}"
            )
            stake = stake_crud.create_stake(
                db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
            )
            stakes.append(stake)
        
        # Verify all stakes were created
        user_stakes = stake_crud.get_by_user_id(db_session, user_id=str(sample_user.user_id), limit=100)
        assert len(user_stakes) == 50
        
        # Verify amounts are correct
        amounts = [stake.amount_eth for stake in user_stakes]
        expected_amounts = [Decimal(f"{i+1}.{i:02d}") for i in range(50)]
        
        for expected in expected_amounts:
            assert expected in amounts


class TestReferentialIntegrityAdvanced:
    """Test advanced referential integrity scenarios."""
    
    def test_orphaned_records_prevention(self, db_session, sample_user):
        """Test that orphaned records are properly handled."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x4444444444444444444444444444444444444444444444444444444444444444"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Create quiz for the stake
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"orphan_q_{i+1}",
                question_text=f"Orphan test question {i+1} with sufficient length",
                options=[f"A{i}", f"B{i}", f"C{i}", f"D{i}"],
                correct_answer=0
            )
            questions.append(question)
        
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Try to delete user (should fail due to foreign key constraints)
        with pytest.raises(IntegrityError):
            db_session.delete(sample_user)
            db_session.commit()
        
        # Rollback the failed transaction
        db_session.rollback()
        
        # Verify user still exists
        existing_user = user_crud.get(db_session, str(sample_user.user_id))
        assert existing_user is not None

    def test_cascade_behavior_with_updates(self, db_session, sample_user):
        """Test cascade behavior when updating related records."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("2.0"),
            transaction_hash="0x5555555555555555555555555555555555555555555555555555555555555555"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Update user email
        update_data = UserUpdate(email="updated@example.com")
        updated_user = user_crud.update(db_session, db_obj=sample_user, obj_in=update_data)
        
        # Verify stake still references the correct user
        db_session.refresh(stake)
        assert stake.user_id == updated_user.user_id
        assert stake.user.email == "updated@example.com"

    def test_multiple_foreign_key_constraints(self, db_session, sample_user):
        """Test scenarios with multiple foreign key relationships."""
        # Create PDF upload
        upload_data = PDFUploadCreate(
            filename="multi_fk_test.pdf",
            file_size=1024
        )
        upload = pdf_upload_crud.create_upload(
            db_session, upload_in=upload_data, user_id=str(sample_user.user_id)
        )
        
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x6666666666666666666666666666666666666666666666666666666666666666"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Create quiz
        questions = []
        for i in range(10):
            question = QuizQuestion(
                question_id=f"multi_fk_q_{i+1}",
                question_text=f"Multi FK test question {i+1} with sufficient length",
                options=[f"A{i}", f"B{i}", f"C{i}", f"D{i}"],
                correct_answer=0
            )
            questions.append(question)
        
        quiz_data = QuizCreate(
            stake_id=str(stake.stake_id),
            questions=questions
        )
        quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
        
        # Verify all relationships are intact
        assert upload.user_id == sample_user.user_id
        assert stake.user_id == sample_user.user_id
        assert quiz.stake_id == stake.stake_id
        assert quiz.stake.user_id == sample_user.user_id


class TestTransactionRollbackAdvanced:
    """Test advanced transaction rollback scenarios."""
    
    def test_nested_transaction_rollback(self, db_session, sample_user):
        """Test rollback behavior with nested operations."""
        initial_stake_count = db_session.query(Stake).count()
        initial_quiz_count = db_session.query(Quiz).count()
        
        try:
            # Start a complex transaction
            stake_data = StakeCreate(
                amount_eth=Decimal("3.0"),
                transaction_hash="0x7777777777777777777777777777777777777777777777777777777777777777"
            )
            stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
            
            # Create quiz
            questions = []
            for i in range(10):
                question = QuizQuestion(
                    question_id=f"nested_q_{i+1}",
                    question_text=f"Nested transaction question {i+1} with sufficient length",
                    options=[f"A{i}", f"B{i}", f"C{i}", f"D{i}"],
                    correct_answer=0
                )
                questions.append(question)
            
            quiz_data = QuizCreate(
                stake_id=str(stake.stake_id),
                questions=questions
            )
            quiz = quiz_crud.create_quiz(db_session, quiz_in=quiz_data)
            
            # Force an error by creating a duplicate stake with same transaction hash
            duplicate_stake_data = StakeCreate(
                amount_eth=Decimal("4.0"),
                transaction_hash="0x7777777777777777777777777777777777777777777777777777777777777777"  # Same hash
            )
            
            # This should raise a ValueError due to duplicate transaction hash
            stake_crud.create_stake(db_session, stake_in=duplicate_stake_data, user_id=str(sample_user.user_id))
            
        except ValueError:
            # Expected error - rollback should occur
            db_session.rollback()
        
        # Verify all operations were rolled back
        final_stake_count = db_session.query(Stake).count()
        final_quiz_count = db_session.query(Quiz).count()
        
        assert final_stake_count == initial_stake_count
        assert final_quiz_count == initial_quiz_count

    def test_partial_update_rollback(self, db_session, sample_user):
        """Test rollback during partial update operations."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0x8888888888888888888888888888888888888888888888888888888888888888"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        original_amount = stake.amount_eth
        original_status = stake.status
        
        try:
            # Start update transaction
            stake.amount_eth = Decimal("2.0")
            stake.status = StakeStatus.ACTIVE
            
            # Force an integrity error by trying to create another stake with same hash
            duplicate_stake = Stake(
                user_id=sample_user.user_id,
                amount_eth=Decimal("3.0"),
                transaction_hash="0x8888888888888888888888888888888888888888888888888888888888888888"
            )
            db_session.add(duplicate_stake)
            db_session.commit()  # This should fail
            
        except IntegrityError:
            db_session.rollback()
        
        # Refresh and verify original values are preserved
        db_session.refresh(stake)
        assert stake.amount_eth == original_amount
        assert stake.status == original_status

    def test_concurrent_access_rollback(self, db_session, sample_user):
        """Test rollback behavior under concurrent access scenarios."""
        from sqlalchemy.orm import sessionmaker
        from app.core.database import engine
        
        # Create a second session to simulate concurrent access
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session2 = SessionLocal()
        
        try:
            # Session 1: Create a stake
            stake_data = StakeCreate(
                amount_eth=Decimal("1.0"),
                transaction_hash="0x9999999999999999999999999999999999999999999999999999999999999999"
            )
            stake1 = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
            
            # Session 2: Try to create a stake with the same transaction hash
            try:
                stake_data2 = StakeCreate(
                    amount_eth=Decimal("2.0"),
                    transaction_hash="0x9999999999999999999999999999999999999999999999999999999999999999"
                )
                stake_crud.create_stake(db_session2, stake_in=stake_data2, user_id=str(sample_user.user_id))
                
            except ValueError:
                # Expected error in session 2
                db_session2.rollback()
            
            # Session 1 should still be able to commit successfully
            db_session.commit()
            
            # Verify only one stake exists
            stakes = stake_crud.get_by_transaction_hash(
                db_session, 
                transaction_hash="0x9999999999999999999999999999999999999999999999999999999999999999"
            )
            assert stakes is not None
            assert stakes.amount_eth == Decimal("1.0")  # From session 1
            
        finally:
            db_session2.close()

    def test_settlement_rollback_complex(self, db_session, sample_user):
        """Test complex settlement rollback scenarios."""
        # Create and activate a stake
        stake_data = StakeCreate(
            amount_eth=Decimal("5.0"),
            transaction_hash="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        stake.status = StakeStatus.ACTIVE
        db_session.commit()
        
        original_status = stake.status
        original_settlement_type = stake.settlement_type
        original_settled_at = stake.settled_at
        
        try:
            # Begin settlement process
            settlement_type = SettlementType.RETURNED
            
            # Update stake settlement info
            stake.status = StakeStatus.SETTLED
            stake.settlement_type = settlement_type
            stake.settled_at = datetime.utcnow()
            
            # Simulate an external system failure by forcing a database error
            # Create a raw SQL statement that will fail
            db_session.execute(text("INSERT INTO non_existent_table VALUES (1)"))
            db_session.commit()
            
        except Exception:
            # Any error should trigger rollback
            db_session.rollback()
        
        # Refresh and verify original state is preserved
        db_session.refresh(stake)
        assert stake.status == original_status
        assert stake.settlement_type == original_settlement_type
        assert stake.settled_at == original_settled_at


class TestDataConsistencyAndIntegrity:
    """Test data consistency and integrity constraints."""
    
    def test_timestamp_consistency(self, db_session, sample_user):
        """Test that timestamps are consistent and properly maintained."""
        # Create records and verify timestamp ordering
        start_time = datetime.utcnow()
        
        # Create user record
        user_data = UserCreate(
            clerk_id="timestamp_test",
            email="timestamp@example.com"
        )
        user = user_crud.create_user(db_session, user_in=user_data)
        
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(user.user_id))
        
        end_time = datetime.utcnow()
        
        # Verify timestamps are within expected range
        assert start_time <= user.created_at <= end_time
        assert start_time <= stake.created_at <= end_time
        
        # Verify created_at <= updated_at for user
        assert user.created_at <= user.updated_at

    def test_decimal_precision_consistency(self, db_session, sample_user):
        """Test that decimal precision is maintained consistently."""
        # Test various decimal precisions
        test_amounts = [
            Decimal("0.00000001"),  # 8 decimal places
            Decimal("1.12345678"),  # 8 decimal places
            Decimal("999.87654321"),  # 8 decimal places (should be truncated)
            Decimal("1000000.1"),   # Large number with decimal
        ]
        
        stakes = []
        for i, amount in enumerate(test_amounts):
            stake_data = StakeCreate(
                amount_eth=amount,
                transaction_hash=f"0x{str(i).zfill(64)}"
            )
            stake = stake_crud.create_stake(
                db_session, stake_in=stake_data, user_id=str(sample_user.user_id)
            )
            stakes.append(stake)
        
        # Verify precision is maintained (up to 8 decimal places)
        for i, stake in enumerate(stakes):
            expected = test_amounts[i].quantize(Decimal('0.00000001'))
            assert stake.amount_eth == expected

    def test_string_length_constraints(self, db_session, sample_user):
        """Test string length constraints are properly enforced."""
        # Test maximum length filename (255 characters)
        long_filename = "a" * 251 + ".pdf"  # 255 characters total
        
        upload_data = PDFUploadCreate(
            filename=long_filename,
            file_size=1024
        )
        
        upload = pdf_upload_crud.create_upload(
            db_session, upload_in=upload_data, user_id=str(sample_user.user_id)
        )
        
        assert len(upload.filename) == 255
        assert upload.filename == long_filename

    def test_enum_constraint_consistency(self, db_session, sample_user):
        """Test that enum constraints are properly enforced."""
        # Create stake
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Test all valid stake statuses
        valid_statuses = [StakeStatus.PENDING, StakeStatus.ACTIVE, StakeStatus.SETTLED]
        
        for status in valid_statuses:
            stake.status = status
            db_session.commit()
            db_session.refresh(stake)
            assert stake.status == status
        
        # Test all valid settlement types
        valid_settlement_types = [SettlementType.RETURNED, SettlementType.DONATED]
        
        for settlement_type in valid_settlement_types:
            stake.settlement_type = settlement_type
            db_session.commit()
            db_session.refresh(stake)
            assert stake.settlement_type == settlement_type


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    def test_connection_recovery_simulation(self, db_session, sample_user):
        """Test recovery from simulated connection issues."""
        # Create initial data
        stake_data = StakeCreate(
            amount_eth=Decimal("1.0"),
            transaction_hash="0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
        )
        stake = stake_crud.create_stake(db_session, stake_in=stake_data, user_id=str(sample_user.user_id))
        
        # Simulate connection issue by forcing a rollback
        db_session.rollback()
        
        # Verify we can still perform operations after rollback
        new_stake_data = StakeCreate(
            amount_eth=Decimal("2.0"),
            transaction_hash="0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        )
        new_stake = stake_crud.create_stake(db_session, stake_in=new_stake_data, user_id=str(sample_user.user_id))
        
        assert new_stake.amount_eth == Decimal("2.0")

    def test_data_validation_error_recovery(self, db_session, sample_user):
        """Test recovery from data validation errors."""
        initial_count = db_session.query(Stake).count()
        
        # Try to create invalid stakes and verify recovery
        invalid_operations = [
            # Duplicate transaction hash
            lambda: stake_crud.create_stake(
                db_session,
                stake_in=StakeCreate(
                    amount_eth=Decimal("1.0"),
                    transaction_hash="0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
                ),
                user_id=str(sample_user.user_id)
            ),
            # Same hash again (should fail)
            lambda: stake_crud.create_stake(
                db_session,
                stake_in=StakeCreate(
                    amount_eth=Decimal("2.0"),
                    transaction_hash="0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
                ),
                user_id=str(sample_user.user_id)
            )
        ]
        
        # Execute first operation (should succeed)
        invalid_operations[0]()
        
        # Execute second operation (should fail)
        with pytest.raises(ValueError):
            invalid_operations[1]()
        
        # Verify we can still create valid stakes after error
        valid_stake_data = StakeCreate(
            amount_eth=Decimal("3.0"),
            transaction_hash="0x1010101010101010101010101010101010101010101010101010101010101010"
        )
        valid_stake = stake_crud.create_stake(
            db_session, stake_in=valid_stake_data, user_id=str(sample_user.user_id)
        )
        
        assert valid_stake.amount_eth == Decimal("3.0")
        
        # Verify total count is correct (initial + 2 successful operations)
        final_count = db_session.query(Stake).count()
        assert final_count == initial_count + 2