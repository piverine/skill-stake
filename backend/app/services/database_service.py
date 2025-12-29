from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from contextlib import contextmanager
from app.core.database import SessionLocal
from app.crud import user_crud, stake_crud, quiz_crud, pdf_upload_crud
from app.models import StakeStatus, SettlementType
from app.schemas.stake import StakeSettlementRequest
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service layer for database operations with transaction management.
    Provides high-level operations that may involve multiple CRUD operations.
    """
    
    def __init__(self):
        self.user_crud = user_crud
        self.stake_crud = stake_crud
        self.quiz_crud = quiz_crud
        self.pdf_upload_crud = pdf_upload_crud

    @contextmanager
    def get_db_session(self):
        """Context manager for database sessions with automatic cleanup."""
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            db.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            db.close()

    def create_user_with_validation(self, db: Session, user_data: dict) -> dict:
        """Create a user with comprehensive validation."""
        try:
            user = self.user_crud.create_user(db, user_in=user_data)
            return {
                'success': True,
                'user': user,
                'message': 'User created successfully'
            }
        except ValueError as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'User validation failed'
            }
        except IntegrityError as e:
            db.rollback()
            return {
                'success': False,
                'error': 'Database constraint violation',
                'message': 'User creation failed due to data integrity constraints'
            }

    def process_stake_settlement(self, db: Session, settlement_request: StakeSettlementRequest) -> dict:
        """
        Process stake settlement with full transaction management.
        This is a critical financial operation that requires ACID compliance.
        """
        try:
            # Begin transaction (implicit with session)
            
            # 1. Validate quiz exists and belongs to the stake
            quiz = self.quiz_crud.get(db, settlement_request.quiz_id)
            if not quiz:
                return {
                    'success': False,
                    'error': 'Quiz not found',
                    'message': f'Quiz {settlement_request.quiz_id} does not exist'
                }
            
            if str(quiz.stake_id) != settlement_request.stake_id:
                return {
                    'success': False,
                    'error': 'Quiz-Stake mismatch',
                    'message': 'Quiz does not belong to the specified stake'
                }
            
            # 2. Validate stake exists and is in correct state
            stake = self.stake_crud.get(db, settlement_request.stake_id)
            if not stake:
                return {
                    'success': False,
                    'error': 'Stake not found',
                    'message': f'Stake {settlement_request.stake_id} does not exist'
                }
            
            if stake.status != StakeStatus.ACTIVE:
                return {
                    'success': False,
                    'error': 'Invalid stake status',
                    'message': f'Stake status is {stake.status}, expected ACTIVE'
                }
            
            # 3. Validate quiz is completed
            if not quiz.completed_at or quiz.score is None:
                return {
                    'success': False,
                    'error': 'Quiz not completed',
                    'message': 'Cannot settle stake for incomplete quiz'
                }
            
            # 4. Determine settlement type based on score
            settlement_type = SettlementType.RETURNED if quiz.score >= 70 else SettlementType.DONATED
            
            # 5. Validate provided score matches calculated score
            if settlement_request.quiz_score != quiz.score:
                return {
                    'success': False,
                    'error': 'Score mismatch',
                    'message': f'Provided score {settlement_request.quiz_score} does not match quiz score {quiz.score}'
                }
            
            # 6. Perform settlement (this updates the stake)
            settled_stake = self.stake_crud.settle_stake(
                db, 
                stake_id=settlement_request.stake_id,
                settlement_type=settlement_type
            )
            
            if not settled_stake:
                return {
                    'success': False,
                    'error': 'Settlement failed',
                    'message': 'Failed to update stake settlement'
                }
            
            # Transaction is committed automatically when session closes successfully
            return {
                'success': True,
                'stake': settled_stake,
                'settlement_type': settlement_type,
                'quiz_score': quiz.score,
                'message': f'Stake settled successfully - {settlement_type.value}'
            }
            
        except SQLAlchemyError as e:
            # Database error - transaction will be rolled back
            db.rollback()
            logger.error(f"Database error during stake settlement: {e}")
            return {
                'success': False,
                'error': 'Database error',
                'message': 'Settlement failed due to database error'
            }
        except Exception as e:
            # Unexpected error - transaction will be rolled back
            db.rollback()
            logger.error(f"Unexpected error during stake settlement: {e}")
            return {
                'success': False,
                'error': 'Unexpected error',
                'message': 'Settlement failed due to unexpected error'
            }

    def get_user_dashboard_data(self, db: Session, user_id: str) -> dict:
        """
        Get comprehensive dashboard data for a user.
        Aggregates data from multiple tables in a single transaction.
        """
        try:
            # Get user info
            user = self.user_crud.get(db, user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': f'User {user_id} does not exist'
                }
            
            # Get user stakes
            stakes = self.stake_crud.get_by_user_id(db, user_id=user_id, limit=1000)
            
            # Get user quizzes
            quizzes = self.quiz_crud.get_by_user_id(db, user_id=user_id, limit=1000)
            
            # Get user uploads
            uploads = self.pdf_upload_crud.get_by_user_id(db, user_id=user_id, limit=1000)
            
            # Calculate statistics
            total_staked = self.stake_crud.get_total_staked_by_user(db, user_id=user_id)
            quiz_stats = self.quiz_crud.get_quiz_statistics_by_user(db, user_id=user_id)
            upload_stats = self.pdf_upload_crud.get_upload_statistics_by_user(db, user_id=user_id)
            
            return {
                'success': True,
                'user': user,
                'stakes': stakes,
                'quizzes': quizzes,
                'uploads': uploads,
                'statistics': {
                    'total_staked_eth': float(total_staked),
                    'quiz_statistics': quiz_stats,
                    'upload_statistics': upload_stats
                },
                'message': 'Dashboard data retrieved successfully'
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving dashboard data: {e}")
            return {
                'success': False,
                'error': 'Database error',
                'message': 'Failed to retrieve dashboard data'
            }

    def cleanup_failed_operations(self, db: Session) -> dict:
        """
        Cleanup operations for failed or stuck transactions.
        This is an administrative function for data maintenance.
        """
        try:
            # Find stakes that are stuck in PENDING status for too long
            from datetime import datetime, timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            stuck_stakes = (
                db.query(self.stake_crud.model)
                .filter(self.stake_crud.model.status == StakeStatus.PENDING)
                .filter(self.stake_crud.model.created_at < cutoff_time)
                .all()
            )
            
            # Find failed uploads that can be retried
            failed_uploads = self.pdf_upload_crud.get_failed_uploads(db, limit=100)
            
            return {
                'success': True,
                'stuck_stakes': len(stuck_stakes),
                'failed_uploads': len(failed_uploads),
                'message': f'Found {len(stuck_stakes)} stuck stakes and {len(failed_uploads)} failed uploads'
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during cleanup: {e}")
            return {
                'success': False,
                'error': 'Database error',
                'message': 'Cleanup operation failed'
            }


# Global instance
database_service = DatabaseService()