from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import Base
import uuid

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Get a single record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise e

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record."""
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise e

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Delete a record by ID."""
        obj = db.query(self.model).get(id)
        if obj:
            try:
                db.delete(obj)
                db.commit()
                return obj
            except IntegrityError as e:
                db.rollback()
                raise e
        return None

    def get_by_field(self, db: Session, field_name: str, field_value: Any) -> Optional[ModelType]:
        """Get a record by a specific field."""
        return db.query(self.model).filter(getattr(self.model, field_name) == field_value).first()

    def get_multi_by_field(
        self, db: Session, field_name: str, field_value: Any, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records by a specific field."""
        return (
            db.query(self.model)
            .filter(getattr(self.model, field_name) == field_value)
            .offset(skip)
            .limit(limit)
            .all()
        )