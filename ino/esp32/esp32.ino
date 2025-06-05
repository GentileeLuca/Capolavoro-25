#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <ArduinoJson.h>
#include "config.h" 

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, 16, 17); 

  // Wi-Fi
  Serial.print("Connessione WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println(" connesso");

  // Firebase
  config.api_key      = API_KEY;
  config.database_url = DATABASE_URL;
  auth.user.email    = DEVICE_EMAIL;
  auth.user.password = DEVICE_PASSWORD;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  // Stream su /orders
  Serial.println("Avvio stream su /orders...");
  if (!Firebase.RTDB.beginStream(&fbdo, "/orders")) {
    Serial.println("Errore stream: " + fbdo.errorReason());
  } else {
    Serial.println("Stream attivo");
  }
}

void handleOpen(const String &path) {
  int p1 = path.indexOf('/', 1);      // posizione slash dopo "/orders"
  int p2 = path.indexOf('/', p1 + 1); // posizione slash prima di "openRequest"
  String orderId = (p2 > 0)
    ? path.substring(p1 + 1, p2)
    : path.substring(p1 + 1);
  Serial.println("[OPEN] orderId = " + orderId);

  String lockerPath = "/orders/" + orderId + "/lockerId";
  int locker = -1;
  if (Firebase.RTDB.getInt(&fbdo, lockerPath.c_str(), &locker)) {
    Serial.println("[OPEN] lockerId = " + String(locker));
    Serial2.println("OPEN_" + String(locker));
    Serial.println("[OPEN] Inviato OPEN_" + String(locker));
    String delPath = "/orders/" + orderId;
    if (Firebase.RTDB.deleteNode(&fbdo, delPath.c_str())) {
      Serial.println("[OPEN] ordine " + orderId + " eliminato");
    } else {
      Serial.println("[OPEN] deleteNode err: " + fbdo.errorReason());
    }
  } else {
    Serial.println("[OPEN] getInt err: " + fbdo.errorReason());
  }
}


void loop() {
  if (Firebase.RTDB.readStream(&fbdo) && fbdo.streamAvailable()) {
    String path = fbdo.dataPath();  
    Serial.println("[STREAM] Change at: " + path);
    if (path.endsWith("/openRequest")) {
      bool req = fbdo.boolData();
      Serial.println("[STREAM] openRequest flag = " + String(req));
      if (req) {
        handleOpen(path);
      }
    }
    else if (path != "/") {
      String orderId = path.substring(1);
      Serial.println("[STREAM] Node-level change, controllo openRequest su " + orderId);
      bool req = false;
      String reqPath = "/orders/" + orderId + "/openRequest";
      if (Firebase.RTDB.getBool(&fbdo, reqPath.c_str(), &req)) {
        Serial.println("[STREAM] openRequest (via getBool) = " + String(req));
        if (req) {
          handleOpen("/orders/" + orderId + "/openRequest");
        }
      } else {
        Serial.println("[STREAM] getBool err: " + fbdo.errorReason());
      }
    }
  }

  if (Serial2.available()) {
    String msg = Serial2.readStringUntil('\n');
    msg.trim();
    Serial.println("[SERIAL2] Received: '" + msg + "'");
    if (msg.startsWith("PIN:")) {
      String pin = msg.substring(4);
      Serial.println("Verifica PIN: " + pin);
      // scarica solo pins e lockerId
      if (Firebase.RTDB.getJSON(&fbdo, "/orders")) {
        DynamicJsonDocument doc(2048);
        deserializeJson(doc, fbdo.jsonString());
        bool found = false;
        for (JsonPair kv : doc.as<JsonObject>()) {
          JsonObject o = kv.value().as<JsonObject>();
          if (o["pin"] == pin) {
            found = true;
            int locker = o["lockerId"];
            Serial.println("PIN valido, lockerId=" + String(locker));
            Serial2.println("OPEN_" + String(locker));
            
            String key = kv.key().c_str();
            String dp = "/orders/" + key;
            if (Firebase.RTDB.deleteNode(&fbdo, dp.c_str())) {
              Serial.println("Ordine " + key + " eliminato");
            } else {
              Serial.println("Errore deleteNode(pin): " + fbdo.errorReason());
            }
            break;
          }
        }
        if (!found) {
          Serial.println("PIN non trovato");
          Serial2.println("PIN_ERROR");
        }
      } else {
        Serial.println("Errore getJSON orders: " + fbdo.errorReason());
        Serial2.println("PIN_ERROR");
      }
    }
  }

  delay(100);
}
