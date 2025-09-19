"""
Base repository with common CRUD operations

This module provides a generic repository base class that implements
common database operations using SQLAlchemy 2.0+ async patterns.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select
import structlog

logger = structlog.get_logger(__name__)

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Base repository with common CRUD operations

    This abstract base class provides a foundation for repository implementations
    with standardized CRUD operations, error handling, and logging.

    Features:
    - Generic type support for models and schemas
    - Async SQLAlchemy 2.0+ operations
    - Comprehensive error handling and logging
    - Flexible filtering and pagination
    - Transaction management
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @property
    @abstractmethod
    def model(self) -> type[ModelType]:
        """Return the SQLAlchemy model class"""
        pass

    async def get(self, id: Any, load_relationships: bool = False) -> Optional[ModelType]:
        """Get single record by ID"""
        query = select(self.model).where(self.model.id == id)

        if load_relationships:
            query = self._add_relationship_loading(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        load_relationships: bool = False,
        **filters
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering"""
        query = select(self.model)
        query = self._apply_filters(query, **filters)

        if order_by:
            query = self._apply_ordering(query, order_by)

        query = query.offset(offset).limit(limit)

        if load_relationships:
            query = self._add_relationship_loading(query)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, **filters) -> int:
        """Count records matching filters"""
        query = select(func.count()).select_from(self.model)
        query = self._apply_filters(query, **filters)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create new record"""
        try:
            # Convert input to dict if it's a Pydantic model
            if hasattr(obj_in, 'model_dump'):
                create_data = obj_in.model_dump()
            elif hasattr(obj_in, 'dict'):
                create_data = obj_in.dict()
            else:
                create_data = obj_in

            db_obj = self.model(**create_data)
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj

        except Exception:
            await self.session.rollback()
            raise

    async def update(self, id: Any, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """Update existing record"""
        try:
            db_obj = await self.get(id)
            if not db_obj:
                return None

            # Convert update data to dict
            if hasattr(obj_in, 'model_dump'):
                update_data = obj_in.model_dump(exclude_unset=True)
            elif hasattr(obj_in, 'dict'):
                update_data = obj_in.dict(exclude_unset=True)
            else:
                update_data = obj_in

            # Update fields
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj

        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, id: Any) -> bool:
        """Delete record by ID, returns True if deleted, False if not found"""
        try:
            result = await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await self.session.commit()
            return result.rowcount > 0

        except Exception:
            await self.session.rollback()
            raise

    async def exists(self, id: Any) -> bool:
        """Check if record exists by ID"""
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None

    def _apply_filters(self, query: Select, **filters) -> Select:
        """Apply simple filters to query"""
        for field, value in filters.items():
            if hasattr(self.model, field):
                model_field = getattr(self.model, field)
                if value is None:
                    query = query.where(model_field.is_(None))
                elif isinstance(value, (list, tuple)):
                    query = query.where(model_field.in_(value))
                else:
                    query = query.where(model_field == value)
        return query

    def _apply_ordering(self, query: Select, order_by: str) -> Select:
        """Apply ordering to query"""
        if order_by.startswith('-'):
            field_name = order_by[1:]
            desc = True
        else:
            field_name = order_by
            desc = False

        if hasattr(self.model, field_name):
            field = getattr(self.model, field_name)
            if desc:
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field)

        return query

    def _add_relationship_loading(self, query: Select) -> Select:
        """
        Add relationship loading to query

        Override in subclasses to specify which relationships to load
        """
        return query