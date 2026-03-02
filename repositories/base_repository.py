"""Base repository with common CRUD operations."""
from typing import TypeVar, Generic, List, Optional, Type
from sqlalchemy.orm import Session
import logging

from database.models import Base

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations."""

    def __init__(self, model: Type[T], session: Session):
        """Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    def create(self, **kwargs) -> T:
        """Create a new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        self.session.flush()
        logger.info(f"Created {self.model.__name__} with id {entity.id}")
        return entity

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity or None if not found
        """
        return self.session.query(self.model).filter(self.model.id == entity_id).first()

    def get_all(self) -> List[T]:
        """Get all entities.

        Returns:
            List of entities
        """
        return self.session.query(self.model).all()

    def update(self, entity: T, **kwargs) -> T:
        """Update entity attributes.

        Args:
            entity: Entity to update
            **kwargs: Attributes to update

        Returns:
            Updated entity
        """
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self.session.flush()
        logger.info(f"Updated {self.model.__name__} with id {entity.id}")
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity.

        Args:
            entity: Entity to delete
        """
        entity_id = entity.id
        self.session.delete(entity)
        self.session.flush()
        logger.info(f"Deleted {self.model.__name__} with id {entity_id}")

    def count(self) -> int:
        """Count total entities.

        Returns:
            Total count
        """
        return self.session.query(self.model).count()
