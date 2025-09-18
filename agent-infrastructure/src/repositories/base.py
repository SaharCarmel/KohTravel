"""
Base repository with common CRUD operations

This module provides a generic repository base class that implements
common database operations using SQLAlchemy 2.0+ async patterns.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any, Dict, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.orm import selectinload, joinedload
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
        """
        Get single record by ID

        Args:
            id: Primary key value
            load_relationships: Whether to eagerly load relationships

        Returns:
            Model instance or None if not found
        """
        try:
            query = select(self.model).where(self.model.id == id)

            if load_relationships:
                query = self._add_relationship_loading(query)

            result = await self.session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get record",
                model=self.model.__name__,
                id=id,
                error=str(e)
            )
            raise

    async def get_multi(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        load_relationships: bool = False,
        **filters
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by (prefix with '-' for descending)
            load_relationships: Whether to eagerly load relationships
            **filters: Field-value pairs for filtering

        Returns:
            List of model instances
        """
        try:
            query = select(self.model)

            # Apply filters
            query = self._apply_filters(query, **filters)

            # Apply ordering
            if order_by:
                query = self._apply_ordering(query, order_by)

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Add relationship loading if requested
            if load_relationships:
                query = self._add_relationship_loading(query)

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "Failed to get multiple records",
                model=self.model.__name__,
                filters=filters,
                offset=offset,
                limit=limit,
                error=str(e)
            )
            raise

    async def count(self, **filters) -> int:
        """
        Count records matching filters

        Args:
            **filters: Field-value pairs for filtering

        Returns:
            Number of matching records
        """
        try:
            query = select(func.count()).select_from(self.model)
            query = self._apply_filters(query, **filters)

            result = await self.session.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(
                "Failed to count records",
                model=self.model.__name__,
                filters=filters,
                error=str(e)
            )
            raise

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create new record

        Args:
            obj_in: Data for creating the record

        Returns:
            Created model instance
        """
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

            logger.info(
                "Record created successfully",
                model=self.model.__name__,
                id=getattr(db_obj, 'id', 'unknown')
            )
            return db_obj

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to create record",
                model=self.model.__name__,
                error=str(e)
            )
            raise

    async def update(self, id: Any, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """
        Update existing record

        Args:
            id: Primary key of record to update
            obj_in: Data for updating the record

        Returns:
            Updated model instance or None if not found
        """
        try:
            # Get existing record
            db_obj = await self.get(id)
            if not db_obj:
                logger.warning(
                    "Record not found for update",
                    model=self.model.__name__,
                    id=id
                )
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

            logger.info(
                "Record updated successfully",
                model=self.model.__name__,
                id=id
            )
            return db_obj

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to update record",
                model=self.model.__name__,
                id=id,
                error=str(e)
            )
            raise

    async def delete(self, id: Any) -> bool:
        """
        Delete record by ID

        Args:
            id: Primary key of record to delete

        Returns:
            True if record was deleted, False if not found
        """
        try:
            result = await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await self.session.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(
                    "Record deleted successfully",
                    model=self.model.__name__,
                    id=id
                )
            else:
                logger.warning(
                    "Record not found for deletion",
                    model=self.model.__name__,
                    id=id
                )

            return deleted

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to delete record",
                model=self.model.__name__,
                id=id,
                error=str(e)
            )
            raise

    async def exists(self, id: Any) -> bool:
        """
        Check if record exists by ID

        Args:
            id: Primary key to check

        Returns:
            True if record exists, False otherwise
        """
        try:
            result = await self.session.execute(
                select(self.model.id).where(self.model.id == id)
            )
            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.error(
                "Failed to check record existence",
                model=self.model.__name__,
                id=id,
                error=str(e)
            )
            raise

    def _apply_filters(self, query: Select, **filters) -> Select:
        """Apply filters to query"""
        for field, value in filters.items():
            if not hasattr(self.model, field):
                continue

            model_field = getattr(self.model, field)

            if value is None:
                query = query.where(model_field.is_(None))
            elif isinstance(value, (list, tuple)):
                query = query.where(model_field.in_(value))
            elif isinstance(value, dict):
                # Handle complex filters like {'gt': 5, 'lt': 10}
                if 'gt' in value:
                    query = query.where(model_field > value['gt'])
                if 'gte' in value:
                    query = query.where(model_field >= value['gte'])
                if 'lt' in value:
                    query = query.where(model_field < value['lt'])
                if 'lte' in value:
                    query = query.where(model_field <= value['lte'])
                if 'like' in value:
                    query = query.where(model_field.like(f"%{value['like']}%"))
                if 'ilike' in value:
                    query = query.where(model_field.ilike(f"%{value['ilike']}%"))
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