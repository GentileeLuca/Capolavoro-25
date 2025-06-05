import pyrebase
from config import FIREBASE_CONFIG

class RealtimeDB:
    def __init__(self, auth_handler):
        fb = pyrebase.initialize_app(FIREBASE_CONFIG)
        self.db   = fb.database()
        self.auth = auth_handler

    def save_user(self, uid, data):
        token = self.auth.get_token()
        self.db.child('users').child(uid).set(data, token)

    def get_user_role(self, uid):
        token = self.auth.get_token()
        node  = self.db.child('users').child(uid).get(token).val()
        return node.get('ruolo') if node else None

    def add_order(self, email_cliente, locker_id, pin, corriere=None):
        token = self.auth.get_token()
        data = {
            'userId'      : self.auth.get_uid(),
            'email_cliente': email_cliente,
            'lockerId'    : locker_id,
            'pin'         : pin,
            'status'      : 'pending',
            'openRequest' : False,
            'corriere'    : corriere or ''
        }
        res = self.db.child('orders').push(data, token)
        return res['name']

    def get_orders_for_user(self) -> list:
        token = self.auth.get_token()
        email = self.auth.user['email']
        print(f"[DEBUG] get_orders_for_user: filtrando per email_cliente = {email}")
        try:
            res = self.db.child('orders') \
                         .order_by_child('email_cliente') \
                         .equal_to(email) \
                         .get(token)
            items = res.each() or []
            print(f"[DEBUG] trovati {len(items)} ordini per email {email}")
            return items
        except Exception as e:
            print(f"[DEBUG] Errore query orders per cliente: {e}")
            return []

    def get_orders_for_courier(self):
        token = self.auth.get_token()
        email = self.auth.user['email']
        res   = self.db.child('orders').order_by_child('corriere').equal_to(email).get(token)
        return res.each() or []

    def request_open(self, order_key) -> bool:
        token = self.auth.get_token()
        path = f"orders/{order_key}/openRequest"
        print(f"[DEBUG] Imposto openRequest=True su /{path}")
        try:
            self.db.child('orders').child(order_key).update({'openRequest': True}, token)
            print("[DEBUG] openRequest impostato correttamente.")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set openRequest: {e}")
            return False


    def verify_pin(self, pin):
        token = self.auth.get_token()
        res   = self.db.child('orders').order_by_child('pin').equal_to(pin).get(token)
        items = res.each() or []
        if not items:
            raise ValueError("PIN non valido.")
        key   = items[0].key()
        data  = items[0].val()
        self.db.child('orders').child(key).update({'openRequest': True}, token)
        return key, data
