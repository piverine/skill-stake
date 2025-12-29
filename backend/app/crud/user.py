from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_clerk_id(self, db: Session, *, clerk_id: str) -> Optional[User]:
        """Get user by Clerk ID."""
        return db.query(User).filter(User.clerk_id == clerk_id).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    def create_user(self, db: Session, *, user_in: UserCreate) -> User:
        """Create a new user with validation."""
        # Check if user with clerk_id already exists
        existing_user = self.get_by_clerk_id(db, clerk_id=user_in.clerk_id)
        if existing_user:
            raise ValueError(f"User with clerk_id {user_in.clerk_id} already exists")
        
        return self.create(db, obj_in=user_in)

    def get(self, db: Session, id: str) -> Optional[User]:
        """Override to use user_id field."""
        return db.query(User).filter(User.user_id == id).first()

    def remove(self, db: Session, *, id: str) -> Optional[User]:
        """Override to use user_id field."""
        obj = db.query(User).filter(User.user_id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return obj
        return None


user_crud = CRUDUser(User)