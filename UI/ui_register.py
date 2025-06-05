from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Signal, Qt

class RegisterWindow(QWidget):
    switch_to_login = Signal()
    register_submitted = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registrazione")
        self.setFixedSize(300, 220)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Registrazione</h2>", alignment=Qt.AlignCenter))

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

        row = QHBoxLayout()
        row.addWidget(QLabel("Ruolo:"))
        self.role = QComboBox()
        self.role.addItems(["cliente", "corriere"])
        row.addWidget(self.role)
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        reg_btn = QPushButton("Registrati")
        reg_btn.setShortcut("Return")
        reg_btn.clicked.connect(self._on_register)
        back_btn = QPushButton("Indietro")
        back_btn.clicked.connect(self.switch_to_login.emit)
        btn_row.addWidget(reg_btn)
        btn_row.addWidget(back_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _on_register(self):
        email = self.email.text().strip()
        pwd = self.password.text().strip()
        role = self.role.currentText().strip()
        if not email or not pwd or role not in ("cliente", "corriere"):
            QMessageBox.warning(self, "Errore", "Compila tutti i campi.")
            return
        if len(pwd) < 6:
            QMessageBox.warning(self, "Errore", "Password troppo corta.")
            return
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Errore", "Email non valida.")
            return
        self.register_submitted.emit(email, pwd, role)
