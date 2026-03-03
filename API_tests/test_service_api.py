"""
API 测试 - 服务层接口测试

注意：本项目为桌面应用，此处测试的是服务层的公共接口（API），
而非 HTTP REST API。
"""
import pytest
from datetime import datetime, timedelta
from database.connection import db
from database.models import User, UserRole, Customer, Resource, ResourceType, ResourceStatus
from repositories.user_repository import UserRepository
from repositories.customer_repository import CustomerRepository
from repositories.resource_repository import ResourceRepository
from repositories.booking_repository import BookingRepository
from services.auth_service import AuthService
from services.booking_service import BookingService, BookingConflictError
from services.billing_service import BillingService
from utils.security import hash_password


@pytest.fixture
def session():
    """Create test database session."""
    db.initialize()
    with db.get_session() as sess:
        yield sess
        sess.rollback()


@pytest.fixture
def test_user(session):
    """Create test user."""
    user = User(
        username="testuser",
        password_hash=hash_password("test123"),
        role=UserRole.ADMIN,
        full_name="Test User",
        is_active=True
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def test_customer(session):
    """Create test customer."""
    customer = Customer(
        name="测试客户",
        phone="13800138000",
        email="test@example.com"
    )
    session.add(customer)
    session.flush()
    return customer


@pytest.fixture
def test_resource(session):
    """Create test resource."""
    resource = Resource(
        name="测试录音棚",
        type=ResourceType.RECORDING_ROOM,
        status=ResourceStatus.AVAILABLE_RENTAL,
        hourly_rate=300.0
    )
    session.add(resource)
    session.flush()
    return resource


class TestAuthServiceAPI:
    """测试认证服务接口"""

    def test_login_success(self, session, test_user):
        """测试登录成功"""
        auth_service = AuthService(UserRepository(session))
        user = auth_service.login("testuser", "test123")
        assert user is not None
        assert user.username == "testuser"

    def test_login_wrong_password(self, session, test_user):
        """测试错误密码"""
        auth_service = AuthService(UserRepository(session))
        user = auth_service.login("testuser", "wrongpass")
        assert user is None

    def test_login_nonexistent_user(self, session):
        """测试不存在的用户"""
        auth_service = AuthService(UserRepository(session))
        user = auth_service.login("nonexistent", "test123")
        assert user is None


class TestBookingServiceAPI:
    """测试预约服务接口"""

    def test_create_booking_success(self, session, test_user, test_customer, test_resource):
        """测试创建预约成功"""
        booking_service = BookingService(BookingRepository(session))
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        booking = booking_service.create_booking(
            customer_id=test_customer.id,
            created_by=test_user.id,
            start_time=start_time,
            end_time=end_time,
            resource_ids=[test_resource.id]
        )

        assert booking is not None
        assert booking.customer_id == test_customer.id

    def test_create_booking_conflict(self, session, test_user, test_customer, test_resource):
        """测试预约冲突检测"""
        booking_service = BookingService(BookingRepository(session))
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # 创建第一个预约
        booking_service.create_booking(
            customer_id=test_customer.id,
            created_by=test_user.id,
            start_time=start_time,
            end_time=end_time,
            resource_ids=[test_resource.id]
        )

        # 尝试创建冲突预约
        with pytest.raises(BookingConflictError):
            booking_service.create_booking(
                customer_id=test_customer.id,
                created_by=test_user.id,
                start_time=start_time + timedelta(minutes=30),
                end_time=end_time + timedelta(minutes=30),
                resource_ids=[test_resource.id]
            )

    def test_create_booking_invalid_duration(self, session, test_user, test_customer, test_resource):
        """测试无效时长"""
        booking_service = BookingService(BookingRepository(session))
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=15)  # 少于30分钟

        with pytest.raises(ValueError, match="预约时长不能少于"):
            booking_service.create_booking(
                customer_id=test_customer.id,
                created_by=test_user.id,
                start_time=start_time,
                end_time=end_time,
                resource_ids=[test_resource.id]
            )


class TestBillingServiceAPI:
    """测试计费服务接口"""

    def test_calculate_billing_basic(self, session, test_resource):
        """测试基本计费计算"""
        billing_service = BillingService()
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)

        # 创建模拟预约
        from database.models import Booking, BookingResource
        booking = Booking(
            customer_id=1,
            start_time=start_time,
            end_time=end_time,
            pause_duration_minutes=0
        )
        booking.booking_resources = [
            BookingResource(resource_id=test_resource.id, resource=test_resource)
        ]

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 2.0
        assert result['room_charges'] == 600.0  # 300 * 2
        assert result['total'] == 600.0

    def test_calculate_billing_with_rounding(self, session, test_resource):
        """测试15分钟进位"""
        billing_service = BillingService()
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 10, 13)  # 13分钟

        from database.models import Booking, BookingResource
        booking = Booking(
            customer_id=1,
            start_time=start_time,
            end_time=end_time,
            pause_duration_minutes=0
        )
        booking.booking_resources = [
            BookingResource(resource_id=test_resource.id, resource=test_resource)
        ]

        result = billing_service.calculate_billing(booking)

        assert result['rounded_minutes'] == 15  # 13分钟进位到15分钟
        assert result['hours'] == 0.25  # 15分钟 = 0.25小时


class TestCustomerRepositoryAPI:
    """测试客户仓储接口"""

    def test_create_customer(self, session):
        """测试创建客户"""
        repo = CustomerRepository(session)
        customer = Customer(
            name="新客户",
            phone="13900139000",
            email="new@example.com"
        )
        created = repo.create(customer)
        assert created.id is not None
        assert created.name == "新客户"

    def test_get_by_phone(self, session, test_customer):
        """测试按电话查询"""
        repo = CustomerRepository(session)
        customer = repo.get_by_phone("13800138000")
        assert customer is not None
        assert customer.name == "测试客户"

    def test_search_customers(self, session, test_customer):
        """测试搜索客户"""
        repo = CustomerRepository(session)
        results = repo.search("测试")
        assert len(results) > 0
        assert any(c.name == "测试客户" for c in results)


class TestResourceRepositoryAPI:
    """测试资源仓储接口"""

    def test_get_available_resources(self, session, test_resource):
        """测试获取可用资源"""
        repo = ResourceRepository(session)
        resources = repo.get_available()
        assert len(resources) > 0
        assert all(r.status == ResourceStatus.AVAILABLE_RENTAL for r in resources)

    def test_get_by_type(self, session, test_resource):
        """测试按类型查询"""
        repo = ResourceRepository(session)
        resources = repo.get_by_type(ResourceType.RECORDING_ROOM)
        assert len(resources) > 0
        assert all(r.type == ResourceType.RECORDING_ROOM for r in resources)
