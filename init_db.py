"""Database initialization script - creates default admin user."""
import logging
from database.connection import db
from database.models import User, UserRole
from utils.security import hash_password

logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with default data."""
    logger.info("Initializing database...")

    with db.get_session() as session:
        # Check if admin user exists
        existing_admin = session.query(User).filter(User.username == "admin").first()

        if not existing_admin:
            # Create default admin user
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                role=UserRole.ADMIN,
                full_name="系统管理员",
                is_active=True
            )
            session.add(admin)
            logger.info("Created default admin user: admin / admin123")

            # Create sample front desk user
            front_desk = User(
                username="frontdesk",
                password_hash=hash_password("front123"),
                role=UserRole.FRONT_DESK,
                full_name="前台小王",
                is_active=True
            )
            session.add(front_desk)
            logger.info("Created sample front desk user: frontdesk / front123")

            # Create sample engineer user
            engineer = User(
                username="engineer",
                password_hash=hash_password("eng123"),
                role=UserRole.ENGINEER,
                full_name="工程师张三",
                is_active=True
            )
            session.add(engineer)
            logger.info("Created sample engineer user: engineer / eng123")

            session.commit()
            logger.info("Database initialization completed")
        else:
            logger.info("Admin user already exists, skipping initialization")

if __name__ == "__main__":
    from config.logging_config import setup_logging

    setup_logging()
    db.initialize()
    init_database()
    db.close()
