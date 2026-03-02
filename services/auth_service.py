"""Authentication service for user login and authorization."""
from datetime import datetime, timedelta
from typing import Optional
import logging

from database.models import User, UserRole
from repositories.user_repository import UserRepository
from utils.security import verify_password, hash_password
from config.settings import LOGIN_LOCKOUT_ATTEMPTS, LOGIN_LOCKOUT_DURATION_MINUTES

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Authentication error exception."""
    pass

class AccountLockedError(AuthenticationError):
    """Account locked error exception."""
    pass

class AuthService:
    """Authentication and authorization service."""

    def __init__(self, user_repo: UserRepository, audit_service=None):
        """Initialize auth service.

        Args:
            user_repo: User repository
            audit_service: Optional audit service for logging
        """
        self.user_repo = user_repo
        self.audit_service = audit_service

    def login(self, username: str, password: str) -> User:
        """Authenticate user and return user object.

        Args:
            username: Username
            password: Password

        Returns:
            Authenticated user

        Raises:
            AuthenticationError: If authentication fails
            AccountLockedError: If account is locked
        """
        user = self.user_repo.get_by_username(username)

        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            raise AuthenticationError("用户名或密码错误")

        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {username}")
            raise AuthenticationError("账号已被禁用")

        # Check if account is locked
        if self.is_locked(user):
            remaining_minutes = self._get_lockout_remaining_minutes(user)
            logger.warning(f"Login attempt for locked account: {username}")
            raise AccountLockedError(f"账号已锁定，请在 {remaining_minutes} 分钟后重试")

        # Verify password
        if not verify_password(password, user.password_hash):
            self._record_failed_login(user)
            logger.warning(f"Failed login attempt for user: {username}")

            if self.is_locked(user):
                raise AccountLockedError(
                    f"密码错误次数过多，账号已锁定 {LOGIN_LOCKOUT_DURATION_MINUTES} 分钟"
                )
            else:
                remaining_attempts = LOGIN_LOCKOUT_ATTEMPTS - user.failed_login_attempts
                raise AuthenticationError(f"用户名或密码错误，还有 {remaining_attempts} 次尝试机会")

        # Successful login - reset failed attempts
        self._reset_failed_attempts(user)
        logger.info(f"User logged in successfully: {username}")

        # Log successful login
        if self.audit_service:
            self.audit_service.log_login(user.id, username, success=True)

        return user

    def is_locked(self, user: User) -> bool:
        """Check if user account is locked.

        Args:
            user: User to check

        Returns:
            True if locked, False otherwise
        """
        if user.locked_until is None:
            return False

        if datetime.utcnow() < user.locked_until:
            return True

        # Lock period expired, clear it
        self.user_repo.update(user, locked_until=None, failed_login_attempts=0)
        return False

    def _record_failed_login(self, user: User) -> None:
        """Record failed login attempt.

        Args:
            user: User who failed login
        """
        failed_attempts = user.failed_login_attempts + 1

        if failed_attempts >= LOGIN_LOCKOUT_ATTEMPTS:
            # Lock account
            locked_until = datetime.utcnow() + timedelta(minutes=LOGIN_LOCKOUT_DURATION_MINUTES)
            self.user_repo.update(
                user,
                failed_login_attempts=failed_attempts,
                locked_until=locked_until
            )
            logger.warning(f"Account locked due to failed attempts: {user.username}")
        else:
            self.user_repo.update(user, failed_login_attempts=failed_attempts)

    def _reset_failed_attempts(self, user: User) -> None:
        """Reset failed login attempts.

        Args:
            user: User to reset
        """
        if user.failed_login_attempts > 0 or user.locked_until is not None:
            self.user_repo.update(user, failed_login_attempts=0, locked_until=None)

    def _get_lockout_remaining_minutes(self, user: User) -> int:
        """Get remaining lockout minutes.

        Args:
            user: User to check

        Returns:
            Remaining minutes
        """
        if user.locked_until is None:
            return 0

        remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
        return max(0, int(remaining) + 1)

    def has_permission(self, user: User, action: str) -> bool:
        """Check if user has permission for action.

        Args:
            user: User to check
            action: Action to check permission for

        Returns:
            True if user has permission, False otherwise
        """
        # Admin has all permissions
        if user.role == UserRole.ADMIN:
            return True

        # Define role-based permissions
        permissions = {
            UserRole.FRONT_DESK: [
                'view_bookings',
                'create_booking',
                'edit_booking',
                'view_customers',
                'create_customer',
                'edit_customer',
                'view_resources',
                'create_order',
                'process_payment'
            ],
            UserRole.ENGINEER: [
                'view_bookings',
                'view_own_bookings',
                'start_session',
                'pause_session',
                'end_session'
            ]
        }

        user_permissions = permissions.get(user.role, [])
        return action in user_permissions

    def create_user(self, username: str, password: str, role: UserRole, full_name: str, **kwargs) -> User:
        """Create a new user.

        Args:
            username: Username
            password: Plain text password
            role: User role
            full_name: Full name
            **kwargs: Additional user attributes

        Returns:
            Created user
        """
        password_hash = hash_password(password)

        user = self.user_repo.create(
            username=username,
            password_hash=password_hash,
            role=role,
            full_name=full_name,
            **kwargs
        )

        logger.info(f"User created: {username} with role {role.value}")
        return user

    def change_password(self, user: User, old_password: str, new_password: str) -> None:
        """Change user password.

        Args:
            user: User to change password for
            old_password: Current password
            new_password: New password

        Raises:
            AuthenticationError: If old password is incorrect
        """
        if not verify_password(old_password, user.password_hash):
            raise AuthenticationError("当前密码错误")

        new_password_hash = hash_password(new_password)
        self.user_repo.update(user, password_hash=new_password_hash)
        logger.info(f"Password changed for user: {user.username}")
