from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from typing import Optional
import uuid
from enum import Enum

class StakeStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SETTLED = "SETTLED"

class SettlementType(str, Enum):
    RETURNED = "RETURNED"
    DONATED = "DONATED"

class StakeBase(BaseModel):
    amount_eth: Decimal = Field(..., gt=0, decimal_places=8, description="Stake amount in ETH")

class StakeCreate(StakeBase):
    transaction_hash: str = Field(..., min_length=66, max_length=66, description="Ethereum transaction hash")
    upload_id: Optional[str] = Field(None, description="Associated PDF upload ID")
    
    @validator('transaction_hash')
    def validate_transaction_hash(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Transaction hash must start with 0x')
        if len(v) != 66:
            raise ValueError('Transaction hash must be 66 characters long')
        return v.lower()

class StakeUpdate(BaseModel):
    contract_stake_id: Optional[int] = None
    status: Optional[StakeStatus] = None
    settled_at: Optional[datetime] = None
    settlement_type: Optional[SettlementType] = None

class StakeSettlementRequest(BaseModel):
    stake_id: str = Field(..., description="Stake ID to settle")
    quiz_score: int = Field(..., ge=0, le=100, description="Quiz score percentage")
    quiz_id: str = Field(..., description="Quiz ID for verification")

class StakeResponse(StakeBase):
    stake_id: uuid.UUID
    user_id: uuid.UUID
    transaction_hash: str
    contract_stake_id: Optional[int]
    status: StakeStatus
    created_at: datetime
    settled_at: Optional[datetime]
    settlement_type: Optional[SettlementType]
    
    class Config:
        from_attributes = True