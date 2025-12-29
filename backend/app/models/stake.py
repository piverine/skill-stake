from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SQLEnum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class StakeStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SETTLED = "SETTLED"

class SettlementType(str, enum.Enum):
    RETURNED = "RETURNED"
    DONATED = "DONATED"

class Stake(Base):
    __tablename__ = "stakes"
    
    stake_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    amount_eth = Column(DECIMAL(18, 8), nullable=False)
    transaction_hash = Column(String(66), nullable=False)
    contract_stake_id = Column(Integer)
    status = Column(SQLEnum(StakeStatus), default=StakeStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    settled_at = Column(DateTime(timezone=True))
    settlement_type = Column(SQLEnum(SettlementType))
    
    # Relationships
    user = relationship("User", back_populates="stakes")
    quiz = relationship("Quiz", back_populates="stake", uselist=False)