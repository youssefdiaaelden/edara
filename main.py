import sys

from PySide6.QtWidgets import QApplication

from database.migrations import run_migrations
from api.auth import init_users
from windows.login_window import LoginWindow
from windows.cashier_window import CashierWindow


def main():

    # إنشاء أو تحديث الجداول
    run_migrations()

    # إنشاء المستخدمين الافتراضيين
    init_users()

    app = QApplication(sys.argv)

    login = LoginWindow()

    if login.exec():

        window = CashierWindow(
            login.role,
            login.username_value
        )

        window.show()

        sys.exit(app.exec())


if __name__ == "__main__":
    main()