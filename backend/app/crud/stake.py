from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from decimal import Decimal
from app.crud.base import CRUDBase
from app.models.stake import Stake, StakeStatus, SettlementType
from app.schemas.stake import StakeCreate, StakeUpdate


class CRUDStake(CRUDBase[Stake, StakeCreate, StakeUpdate]):
    def get_by_user_id(self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100) -> List[Stake]:
        """Get all stakes for a specific user."""
        return (
            db.query(Stake)
            .filter(Stake.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_transaction_hash(self, db: Session, *, transaction_hash: str) -> Optional[Stake]:
        """Get stake by transaction hash."""
        return db.query(Stake).filter(Stake.transaction_hash == transaction_hash).first()

    def get_by_status(self, db: Session, *, status: StakeStatus, skip: int = 0, limit: int = 100) -> List[Stake]:
        """Get stakes by status."""
        return (
            db.query(Stake)
            .filter(Stake.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_stakes_by_user(self, db: Session, *, user_id: str) -> List[Stake]:
        """Get all active stakes for a user."""
        return (
            db.query(Stake)
            .filter(and_(Stake.user_id == user_id, Stake.status == StakeStatus.ACTIVE))
            .all()
        )

    def create_stake(self, db: Session, *, stake_in: StakeCreate, user_id: str) -> Stake:
        """Create a new stake with user validation."""
        # Check if transaction hash already exists
        existing_stake = self.get_by_transaction_hash(db, transaction_hash=stake_in.transaction_hash)
        if existing_stake:
            raise ValueError(f"Stake with transaction hash {stake_in.transaction_hash} already exists")
        
        stake_data = stake_in.dict()
        stake_data['user_id'] = user_id
        
        db_stake = Stake(**stake_data)
        db.add(db_stake)
        db.commit()
        db.refresh(db_stake)
        return db_stake

    def settle_stake(
        self, 
        db: Session, 
        *, 
        stake_id: str, 
        settlement_type: SettlementType
    ) -> Optional[Stake]:
        """Settle a stake with proper transaction management."""
        stake = self.get(db, stake_id)
        if not stake:
            return None
        
        if stake.status != StakeStatus.ACTIVE:
            raise ValueError(f"Cannot settle stake with status {stake.status}")
        
        try:
            # Begin transaction
            stake.status = StakeStatus.SETTLED
            stake.settlement_type = settlement_type
            from datetime import datetime
            stake.settled_at = datetime.utcnow()
            
            db.add(stake)
            db.commit()
            db.refresh(stake)
            return stake
        except Exception as e:
            db.rollback()
            raise e

    def get_total_staked_by_user(self, db: Session, *, user_id: str) -> Decimal:
        """Get total amount staked by a user (active stakes only)."""
        result = (
            db.query(Stake.amount_eth)
            .filter(and_(Stake.user_id == user_id, Stake.status == StakeStatus.ACTIVE))
            .all()
        )
        return sum(stake.amount_eth for stake in result) if result else Decimal('0')

    def get(self, db: Session, id: str) -> Optional[Stake]:
        """Override to use stake_id field."""
        return db.query(Stake).filter(Stake.stake_id == id).first()

    def remove(self, db: Session, *, id: str) -> Optional[Stake]:
        """Override to use stake_id field."""
        obj = db.query(Stake).filter(Stake.stake_id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return obj
        return None


stake_crud = CRUDStake(Stake)