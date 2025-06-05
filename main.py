import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from auth_handler import AuthHandler
from realtime_db import RealtimeDB
from UI.ui_login import LoginWindow
from UI.ui_register import RegisterWindow
from UI.ui_main import ClientWindow, CourierWindow

class MainApp:
    def __init__(self):
        self.app  = QApplication(sys.argv)
        self.auth = AuthHandler()
        self.db   = RealtimeDB(self.auth)

        self.login    = LoginWindow()
        self.register = RegisterWindow()

        self.login.login_submitted.connect(self.on_login)
        self.login.switch_to_register.connect(self.show_register)
        self.register.register_submitted.connect(self.on_register)
        self.register.switch_to_login.connect(self.show_login)

        self.login.show()
        sys.exit(self.app.exec())

    def show_register(self):
        self.login.close()
        self.register.show()

    def show_login(self):
        self.register.close()
        self.login.show()

    def on_login(self, email, pwd):
        try:
            self.auth.sign_in(email, pwd)
        except ValueError as e:
            QMessageBox.critical(None, "Errore Login", str(e))
            return

        role = self.db.get_user_role(self.auth.get_uid())
        if role == 'cliente':
            self.win = ClientWindow(self.auth, self.db)
        elif role == 'corriere':
            self.win = CourierWindow(self.auth, self.db)
        else:
            QMessageBox.critical(None, "Errore", "Ruolo utente non valido.")
            return

        self.login.close()
        self.win.logout_clicked.connect(self.on_logout)
        self.win.show()

    def on_register(self, email, pwd, role):
        try:
            user = self.auth.register(email, pwd)
        except ValueError as e:
            QMessageBox.critical(None, "Errore Registrazione", str(e))
            return

        self.db.save_user(user['localId'], {'email':email, 'ruolo':role})
        QMessageBox.information(None, "OK", "Registrazione completata.")
        self.show_login()

    def on_logout(self):
        self.win.close()
        self.login.show()

if __name__ == '__main__':
    MainApp()
