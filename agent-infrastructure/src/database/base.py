"""
SQLAlchemy Base Model with async support and naming conventions
"""
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import MetaData, DateTime, func
from datetime import datetime
from typing import Optional


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base model with async support and naming conventions

    Features:
    - Async attribute support for lazy loading
    - Consistent naming conventions for constraints
    - Common timestamp fields
    - Proper timezone handling
    """

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    # Common timestamp fields for all models
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp"
    )

    def __repr__(self) -> str:
        """String representation of the model"""
        class_name = self.__class__.__name__
        primary_key = getattr(self, 'id', 'unknown')
        return f"<{class_name}(id={primary_key})>"