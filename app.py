"""Main application entry point."""
import sys
import logging
from PySide6.QtWidgets import QApplication

from config.logging_config import setup_logging
from config.settings import DATABASE_PATH
from database.connection import db
from ui.dialogs.login_dialog import LoginDialog
from ui.main_window import MainWindow

logger = logging.getLogger(__name__)

def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger.info("Application starting...")

    # Initialize database
    try:
        db.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("声匠录音棚排班与计费系统")

    # Show login dialog
    login_dialog = LoginDialog()
    if login_dialog.exec():
        # Login successful, show main window
        current_user = login_dialog.current_user
        logger.info(f"User logged in: {current_user.username}")

        main_window = MainWindow(current_user)
        main_window.show()

        # Run application
        exit_code = app.exec()

        # Cleanup
        db.close()
        logger.info("Application closed")

        sys.exit(exit_code)
    else:
        # Login cancelled
        db.close()
        logger.info("Login cancelled, application closed")
        sys.exit(0)

if __name__ == "__main__":
    main()
