from datetime import datetime, UTC
from typing import Dict, Any
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class TimestampMixin:
    """Mixin for adding timestamp fields"""

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    @declared_attr
    def deleted_at(cls):
        return Column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)

    def restore(self):
        """Restore soft deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class UUIDMixin:
    """Mixin for UUID primary key"""

    @declared_attr
    def id(cls):
        return Column(
            String(36),
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )


class MetadataMixin:
    """Mixin for metadata storage"""

    @declared_attr
    def metadata(cls):
        return Column(JSON, default={}, nullable=True)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        if self.metadata:
            return self.metadata.get(key, default)
        return default

    def set_metadata(self, key: str, value: Any):
        """Set metadata value"""
        if not self.metadata:
            self.metadata = {}
        self.metadata[key] = value

    def update_metadata(self, data: Dict[str, Any]):
        """Update multiple metadata values"""
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(data)


class AuditMixin:
    """Mixin for audit fields"""

    @declared_attr
    def created_by(cls):
        return Column(Integer, nullable=True)

    @declared_attr
    def updated_by(cls):
        return Column(Integer, nullable=True)

    @declared_attr
    def ip_address(cls):
        return Column(String(45), nullable=True)  # Supports IPv6

    @declared_attr
    def user_agent(cls):
        return Column(Text, nullable=True)


class StatusMixin:
    """Mixin for status field"""

    @declared_attr
    def status(cls):
        return Column(String(50), nullable=False, default="active")

    @declared_attr
    def status_changed_at(cls):
        return Column(DateTime(timezone=True), nullable=True)

    def change_status(self, new_status: str):
        """Change status and update timestamp"""
        self.status = new_status
        self.status_changed_at = datetime.now(UTC)


class BaseModel(Base, TimestampMixin):
    """Base model with common fields"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update_from_dict(self, data: Dict[str, Any]):
        """Update model from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


class ExtendedBaseModel(BaseModel, SoftDeleteMixin, MetadataMixin, AuditMixin):
    """Extended base model with all mixins"""
    __abstract__ = True


