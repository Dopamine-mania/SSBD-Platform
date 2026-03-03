#!/usr/bin/env python3
"""Test script for resource widget."""
import sys
from PySide6.QtWidgets import QApplication
from database.connection import db
from database.models import User, UserRole
from ui.widgets.resource_widget import ResourceWidget

def main():
    """Test resource widget."""
    app = QApplication(sys.argv)

    # Create test user
    with db.get_session() as session:
        test_user = session.query(User).filter_by(username="admin").first()
        if not test_user:
            print("Error: Admin user not found")
            return 1

    # Create and show widget
    widget = ResourceWidget(test_user)
    widget.setWindowTitle("资源管理测试")
    widget.resize(1200, 700)
    widget.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
