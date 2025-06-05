import pyrebase
from config import FIREBASE_CONFIG

class AuthHandler:
    def __init__(self):
        fb = pyrebase.initialize_app(FIREBASE_CONFIG)
        self.auth = fb.auth()
        self.user = None

    def sign_in(self, email, password):
        try:
            self.user = self.auth.sign_in_with_email_and_password(email, password)
        except Exception:
            raise ValueError("Login fallito: credenziali errate.")
        return self.user

    def register(self, email, password):
        try:
            self.user = self.auth.create_user_with_email_and_password(email, password)
        except Exception:
            raise ValueError("Registrazione fallita.")
        return self.user

    def get_token(self):
        if not self.user:
            raise ValueError("Utente non autenticato.")
        return self.user['idToken']

    def get_uid(self):
        if not self.user:
            raise ValueError("Utente non autenticato.")
        return self.user['localId']
