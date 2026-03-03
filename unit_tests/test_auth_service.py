"""Tests for authentication service."""
import pytest
from datetime import datetime, timedelta

from database.models import UserRole
from services.auth_service import AuthService, AuthenticationError, AccountLockedError

class TestAuthService:
    """Test authentication service."""

    def test_login_success(self, auth_service, sample_admin):
        """Test successful login."""
        user = auth_service.login("admin", "admin123")

        assert user.id == sample_admin.id
        assert user.username == "admin"
        assert user.failed_login_attempts == 0

    def test_login_wrong_password(self, auth_service, sample_admin):
        """Test login with wrong password."""
        with pytest.raises(AuthenticationError, match="用户名或密码错误"):
            auth_service.login("admin", "wrongpassword")

        # Check failed attempts incremented
        assert sample_admin.failed_login_attempts == 1

    def test_login_nonexistent_user(self, auth_service):
        """Test login with non-existent username."""
        with pytest.raises(AuthenticationError, match="用户名或密码错误"):
            auth_service.login("nonexistent", "password")

    def test_login_lockout_after_3_failures(self, auth_service, sample_admin):
        """Test account lockout after 3 failed login attempts."""
        # First failure
        with pytest.raises(AuthenticationError):
            auth_service.login("admin", "wrong1")

        # Second failure
        with pytest.raises(AuthenticationError):
            auth_service.login("admin", "wrong2")

        # Third failure - should lock account
        with pytest.raises(AccountLockedError, match="账号已锁定"):
            auth_service.login("admin", "wrong3")

        assert sample_admin.failed_login_attempts == 3
        assert sample_admin.locked_until is not None

    def test_login_locked_account(self, auth_service, sample_admin, user_repo):
        """Test login attempt on locked account."""
        # Lock the account
        locked_until = datetime.utcnow() + timedelta(minutes=15)
        user_repo.update(sample_admin, locked_until=locked_until, failed_login_attempts=3)

        # Try to login
        with pytest.raises(AccountLockedError, match="账号已锁定"):
            auth_service.login("admin", "admin123")

    def test_login_lockout_expires(self, auth_service, sample_admin, user_repo):
        """Test that lockout expires after duration."""
        # Lock the account with expired time
        locked_until = datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
        user_repo.update(sample_admin, locked_until=locked_until, failed_login_attempts=3)

        # Should be able to login now
        user = auth_service.login("admin", "admin123")

        assert user.id == sample_admin.id
        assert user.locked_until is None
        assert user.failed_login_attempts == 0

    def test_failed_attempts_reset_on_success(self, auth_service, sample_admin, user_repo):
        """Test that failed attempts reset on successful login."""
        # Set some failed attempts
        user_repo.update(sample_admin, failed_login_attempts=2)

        # Successful login should reset
        user = auth_service.login("admin", "admin123")

        assert user.failed_login_attempts == 0

    def test_inactive_user_cannot_login(self, auth_service, sample_admin, user_repo):
        """Test that inactive users cannot login."""
        user_repo.update(sample_admin, is_active=False)

        with pytest.raises(AuthenticationError, match="账号已被禁用"):
            auth_service.login("admin", "admin123")

    def test_admin_has_all_permissions(self, auth_service, sample_admin):
        """Test that admin has all permissions."""
        assert auth_service.has_permission(sample_admin, 'view_bookings')
        assert auth_service.has_permission(sample_admin, 'create_booking')
        assert auth_service.has_permission(sample_admin, 'delete_user')
        assert auth_service.has_permission(sample_admin, 'any_action')

    def test_engineer_has_limited_permissions(self, auth_service, sample_engineer):
        """Test that engineer has limited permissions."""
        assert auth_service.has_permission(sample_engineer, 'view_bookings')
        assert auth_service.has_permission(sample_engineer, 'start_session')
        assert not auth_service.has_permission(sample_engineer, 'create_booking')
        assert not auth_service.has_permission(sample_engineer, 'delete_user')

    def test_create_user(self, auth_service):
        """Test creating a new user."""
        user = auth_service.create_user(
            username="newuser",
            password="password123",
            role=UserRole.FRONT_DESK,
            full_name="新用户"
        )

        assert user.id is not None
        assert user.username == "newuser"
        assert user.role == UserRole.FRONT_DESK
        assert user.password_hash != "password123"  # Should be hashed

    def test_change_password(self, auth_service, sample_admin):
        """Test changing user password."""
        auth_service.change_password(sample_admin, "admin123", "newpassword123")

        # Should be able to login with new password
        user = auth_service.login("admin", "newpassword123")
        assert user.id == sample_admin.id

        # Old password should not work
        with pytest.raises(AuthenticationError):
            auth_service.login("admin", "admin123")

    def test_change_password_wrong_old_password(self, auth_service, sample_admin):
        """Test changing password with wrong old password."""
        with pytest.raises(AuthenticationError, match="当前密码错误"):
            auth_service.change_password(sample_admin, "wrongold", "newpassword123")
