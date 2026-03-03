"""Pytest configuration and fixtures."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, User, UserRole, Resource, ResourceType, ResourceStatus, Customer
from repositories.user_repository import UserRepository
from repositories.booking_repository import BookingRepository
from services.auth_service import AuthService
from services.booking_service import BookingService
from services.billing_service import BillingService
from utils.security import hash_password

@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def user_repo(test_session):
    """Create user repository."""
    return UserRepository(test_session)

@pytest.fixture
def booking_repo(test_session):
    """Create booking repository."""
    return BookingRepository(test_session)

@pytest.fixture
def auth_service(user_repo):
    """Create auth service."""
    return AuthService(user_repo)

@pytest.fixture
def booking_service(booking_repo):
    """Create booking service."""
    return BookingService(booking_repo)

@pytest.fixture
def billing_service():
    """Create billing service."""
    return BillingService()

@pytest.fixture
def sample_admin(test_session):
    """Create sample admin user."""
    user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN,
        full_name="管理员",
        is_active=True
    )
    test_session.add(user)
    test_session.commit()
    return user

@pytest.fixture
def sample_engineer(test_session):
    """Create sample engineer user."""
    user = User(
        username="engineer1",
        password_hash=hash_password("eng123"),
        role=UserRole.ENGINEER,
        full_name="工程师张三",
        is_active=True
    )
    test_session.add(user)
    test_session.commit()
    return user

@pytest.fixture
def sample_room(test_session):
    """Create sample recording room."""
    room = Resource(
        name="录音间A",
        resource_type=ResourceType.RECORDING_ROOM,
        status=ResourceStatus.AVAILABLE_RENTAL,
        hourly_rate=200.0
    )
    test_session.add(room)
    test_session.commit()
    return room

@pytest.fixture
def sample_equipment(test_session):
    """Create sample equipment."""
    mic = Resource(
        name="话筒 Neumann U87",
        resource_type=ResourceType.MICROPHONE,
        status=ResourceStatus.AVAILABLE_RENTAL,
        hourly_rate=50.0
    )
    test_session.add(mic)
    test_session.commit()
    return mic

@pytest.fixture
def sample_customer(test_session):
    """Create sample customer."""
    customer = Customer(
        name="客户李四",
        phone="13800138000",
        email="lisi@example.com"
    )
    test_session.add(customer)
    test_session.commit()
    return customer
