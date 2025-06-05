from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Signal, Qt

class LoginWindow(QWidget):
    switch_to_register = Signal()
    login_submitted = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(300, 180)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Login</h2>", alignment=Qt.AlignCenter))

        row = QHBoxLayout()
        row.addWidget(QLabel("Email:"))
        self.email = QLineEdit()
        row.addWidget(self.email)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Password:"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        row.addWidget(self.password)
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.setShortcut("Return")
        login_btn.clicked.connect(self._on_login)
        reg_btn = QPushButton("Registrati")
        reg_btn.clicked.connect(self.switch_to_register.emit)
        btn_row.addWidget(login_btn)
        btn_row.addWidget(reg_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _on_login(self):
        email = self.email.text().strip()
        pwd = self.password.text().strip()
        if not email or not pwd:
            QMessageBox.warning(self, "Errore", "Inserisci email e password.")
            return
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Errore", "Email non valida.")
            return
        self.login_submitted.emit(email, pwd)
