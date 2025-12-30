from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Uuid, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class Quiz(Base):
    __tablename__ = "quizzes"
    
    quiz_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stake_id = Column(Uuid(as_uuid=True), ForeignKey("stakes.stake_id"), nullable=False)
    questions = Column(JSON, nullable=False)
    user_answers = Column(JSON)
    score = Column(Integer)
    attempts_count = Column(Integer, default=0)
    is_passed = Column(Boolean, default=False)
    signature = Column(String, nullable=True) # Hex string of signature
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stake = relationship("Stake", back_populates="quiz")