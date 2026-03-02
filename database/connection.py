from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging
from pathlib import Path

from database.models import Base

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection manager using SQLAlchemy."""

    def __init__(self, db_path: str = "studio.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = None
        self.session_factory = None
        self.Session = None

    def initialize(self):
        """Initialize database engine and create tables."""
        db_file = Path(self.db_path)
        db_exists = db_file.exists()

        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True
        )

        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

        if not db_exists:
            logger.info("Creating database tables...")
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        else:
            logger.info(f"Connected to existing database: {self.db_path}")

    @contextmanager
    def get_session(self):
        """Get a database session with automatic commit/rollback.

        Yields:
            Session: SQLAlchemy session
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def close(self):
        """Close database connection."""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

# Global database instance
db = DatabaseConnection()
