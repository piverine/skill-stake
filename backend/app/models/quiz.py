from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class Quiz(Base):
    __tablename__ = "quizzes"
    
    quiz_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stake_id = Column(UUID(as_uuid=True), ForeignKey("stakes.stake_id"), nullable=False)
    questions = Column(JSONB, nullable=False)
    user_answers = Column(JSONB)
    score = Column(Integer)
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stake = relationship("Stake", back_populates="quiz")