"""User repository for user data access."""
from typing import Optional
from sqlalchemy.orm import Session

from database.models import User, UserRole
from repositories.base_repository import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository for User entity."""

    def __init__(self, session: Session):
        super().__init__(User, session)

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User or None if not found
        """
        return self.session.query(User).filter(User.username == username).first()

    def get_by_role(self, role: UserRole) -> list[User]:
        """Get all users with specific role.

        Args:
            role: User role

        Returns:
            List of users
        """
        return self.session.query(User).filter(User.role == role).all()

    def get_active_users(self) -> list[User]:
        """Get all active users.

        Returns:
            List of active users
        """
        return self.session.query(User).filter(User.is_active == True).all()

    def get_engineers(self) -> list[User]:
        """Get all engineer users.

        Returns:
            List of engineers
        """
        return self.get_by_role(UserRole.ENGINEER)
