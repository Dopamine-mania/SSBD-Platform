"""Customer repository for customer data access."""
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import Customer
from repositories.base_repository import BaseRepository

class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer entity."""

    def __init__(self, session: Session):
        super().__init__(Customer, session)

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        """Get customer by phone number.

        Args:
            phone: Phone number

        Returns:
            Customer or None if not found
        """
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    def search_by_name(self, name: str) -> List[Customer]:
        """Search customers by name (partial match).

        Args:
            name: Name to search for

        Returns:
            List of matching customers
        """
        return self.session.query(Customer).filter(
            Customer.name.like(f'%{name}%')
        ).all()

    def search_by_phone(self, phone: str) -> List[Customer]:
        """Search customers by phone (partial match).

        Args:
            phone: Phone to search for

        Returns:
            List of matching customers
        """
        return self.session.query(Customer).filter(
            Customer.phone.like(f'%{phone}%')
        ).all()
