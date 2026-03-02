"""Resource repository for resource data access."""
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import Resource, ResourceType, ResourceStatus
from repositories.base_repository import BaseRepository

class ResourceRepository(BaseRepository[Resource]):
    """Repository for Resource entity."""

    def __init__(self, session: Session):
        super().__init__(Resource, session)

    def get_by_type(self, resource_type: ResourceType) -> List[Resource]:
        """Get resources by type.

        Args:
            resource_type: Resource type

        Returns:
            List of resources
        """
        return self.session.query(Resource).filter(Resource.resource_type == resource_type).all()

    def get_by_status(self, status: ResourceStatus) -> List[Resource]:
        """Get resources by status.

        Args:
            status: Resource status

        Returns:
            List of resources
        """
        return self.session.query(Resource).filter(Resource.status == status).all()

    def get_available_resources(self) -> List[Resource]:
        """Get all available resources (not in maintenance).

        Returns:
            List of available resources
        """
        return self.session.query(Resource).filter(
            Resource.status.in_([ResourceStatus.AVAILABLE_RENTAL, ResourceStatus.INTERNAL_ONLY])
        ).all()

    def get_rooms(self) -> List[Resource]:
        """Get all room resources.

        Returns:
            List of rooms
        """
        return self.session.query(Resource).filter(
            Resource.resource_type.in_([ResourceType.RECORDING_ROOM, ResourceType.CONTROL_ROOM])
        ).all()

    def get_equipment(self) -> List[Resource]:
        """Get all equipment resources.

        Returns:
            List of equipment
        """
        return self.session.query(Resource).filter(
            Resource.resource_type.in_([
                ResourceType.MICROPHONE,
                ResourceType.SOUND_CARD,
                ResourceType.OTHER_EQUIPMENT
            ])
        ).all()
