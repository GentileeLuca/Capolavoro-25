# UI/ui_main.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton,
    QListWidget, QLineEdit, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Signal, QTimer

class ClientWindow(QWidget):
    logout_clicked = Signal()
    def __init__(self, auth, db):
        super().__init__()
        self.auth = auth
        self.db   = db
        self.setWindowTitle("Area Cliente")
        self.setFixedSize(400,350)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Benvenuto: {auth.user['email']}"))
        self.listwidget = QListWidget()
        layout.addWidget(self.listwidget)

        btn_refresh = QPushButton("Aggiorna Ordini")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        btn_open_list = QPushButton("Apri da lista")
        btn_open_list.clicked.connect(self.open_from_list)
        layout.addWidget(btn_open_list)

        row = QHBoxLayout()
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Inserisci PIN")
        btn_open_pin = QPushButton("Apri via PIN")
        btn_open_pin.clicked.connect(self.open_by_pin)
        row.addWidget(self.pin_input)
        row.addWidget(btn_open_pin)
        layout.addLayout(row)

        btn_logout = QPushButton("Logout")
        btn_logout.clicked.connect(self.logout_clicked.emit)
        layout.addWidget(btn_logout)

        self.refresh()

    def refresh(self):
        self.listwidget.clear()
        orders = self.db.get_orders_for_user()
        if not orders:
            self.listwidget.addItem("Nessun ordine trovato.")
            return

        for item in orders:
            o = item.val()
            self.listwidget.addItem(
                f"{item.key()} | Locker {o['lockerId']} | PIN: {o['pin']} | Stato: {o['status']}"
            )


    def open_from_list(self):
        it = self.listwidget.currentItem()
        if not it: return
        pin = it.text().split("PIN: ")[1].split(" ")[0]
        try:
            key, _ = self.db.verify_pin(pin)
            QMessageBox.information(self, "OK", f"Richiesta apertura inoltrata (order {key}).")
        except ValueError as e:
            QMessageBox.warning(self, "Errore", str(e))
        self.refresh()

    def open_by_pin(self):
        pin = self.pin_input.text().strip()
        if not pin:
            QMessageBox.warning(self, "Errore", "Inserisci PIN.")
            return
        try:
            key, _ = self.db.verify_pin(pin)
            QMessageBox.information(self, "OK", f"Richiesta apertura inoltrata (order {key}).")
        except ValueError as e:
            QMessageBox.warning(self, "Errore", str(e))
        self.refresh()

class CourierWindow(QWidget):
    logout_clicked = Signal()
    def __init__(self, auth, db):
        super().__init__()
        self.auth = auth
        self.db   = db
        self.setWindowTitle("Area Corriere")
        self.setFixedSize(400,300)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Corriere: {auth.user['email']}"))
        self.listwidget = QListWidget()
        layout.addWidget(self.listwidget)

        btn_refresh = QPushButton("Aggiorna Consegne")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        btn_add = QPushButton("Nuova Consegna")
        btn_add.clicked.connect(self.add_order)
        layout.addWidget(btn_add)

        btn_request = QPushButton("Richiedi apertura")
        btn_request.clicked.connect(self.request_open)
        layout.addWidget(btn_request)

        btn_logout = QPushButton("Logout")
        btn_logout.clicked.connect(self.logout_clicked.emit)
        layout.addWidget(btn_logout)

        self.refresh()

    def refresh(self):
        self.listwidget.clear()
        for item in self.db.get_orders_for_courier():
            o = item.val()
            self.listwidget.addItem(
                f"{item.key()} | {o['email_cliente']} → Locker {o['lockerId']} | Stato: {o['status']}"
            )

    def add_order(self):
        from PySide6.QtWidgets import QInputDialog
        email, ok1 = QInputDialog.getText(self, "Email Cliente", "Email destinatario:")
        if not ok1 or not email: return
        locker, ok2 = QInputDialog.getInt(self, "Locker", "Numero locker (1-2):",1,1,2)
        if not ok2: return
        import random
        pin = f"{random.randint(1000,9999)}"
        self.db.add_order(email, locker, pin, self.auth.user['email'])
        QMessageBox.information(self, "Ordine", f"Ordine creato con PIN {pin}")
        self.refresh()

    def request_open(self):
        it = self.listwidget.currentItem()
        if not it:
            return
        order_key = it.text().split(" | ")[0]
        success = self.db.request_open(order_key)
        if success:
            QMessageBox.information(self, "OK", f"Richiesta apertura per {order_key} inviata.")
            QTimer.singleShot(1000, self.refresh)
        else:
            QMessageBox.critical(self, "Errore", "Impossibile inviare la richiesta di apertura.")
