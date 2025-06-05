#include <Servo.h>
#include <Keypad.h>
#include <LiquidCrystal_I2C.h>

// Servomotori
Servo s1, s2;

// LCD I2C 16×2 (indirizzo 0x27)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Tastierino 4×4
char keys[4][4] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte rowPins[4] = {2, 3, 4, 5};
byte colPins[4] = {6, 7, 8, 9};
Keypad keypad(makeKeymap(keys), rowPins, colPins, 4, 4);

String pinBuf = "";

void setup() {
  Serial.begin(9600);       // per debug e per comunicazione con ESP32
  s1.attach(12);            // Servo 1 su pin 12
  s2.attach(11);            // Servo 2 su pin 11

  // Imposta entrambi i servo a 90° (chiusi)
  s1.write(90);
  s2.write(90);

  lcd.init();
  lcd.backlight();
  lcd.print("Inserisci PIN");
}


void loop() {
  int v = 0;
  if(v >= 1) {
    v++;
    if (v == 3) {
      v = 0;
      lcd.clear();
      lcd.print("PIN Errato");
      delay(1500);
      lcd.clear();
      lcd.print("Verifica PIN");
    }
  }
  // — Gestione tastierino per inserimento PIN —
  char k = keypad.getKey();
  if (k) {
    Serial.println(String("[KEYPAD] Key: ") + k);
    if (k == '#') {
      Serial.println("PIN:" + pinBuf);
      lcd.clear();
      lcd.print("Verifica PIN");
      if (v == 0) {
        v = 1;
      }  
      pinBuf = "";
    }
    else if (k == '*') {
      pinBuf = "";
      lcd.clear();
      lcd.print("Inserisci PIN");
    }
    else {
      pinBuf += k;
      lcd.setCursor(0,1);
      lcd.print(pinBuf);
    }
  }

  // — Gestione comando OPEN_X da ESP32 (via Serial) —
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    Serial.println("[SERIAL] Cmd: " + cmd);

    if (cmd.startsWith("OPEN_")) {
      int id = cmd.substring(5).toInt();
      Servo &sv = (id == 1 ? s1 : s2);

      lcd.clear();
      lcd.print("Apro locker ");
      lcd.print(id);

      // Apertura: servo1 → 180°, servo2 → 0°
      if (id == 1) {
        sv.write(180);
        Serial.println("[LOCKER] Servo1 a 180°");
      } else {
        sv.write(0);
        Serial.println("[LOCKER] Servo2 a 0°");
      }

      // Attende pressione 'D' per chiudere
      lcd.setCursor(0,1);
      lcd.print("Premi D per chiud");
      while (true) {
        char key = keypad.getKey();
        if (key) {
          Serial.println(String("[KEYPAD] Durante open, key: ") + key);
          if (key == 'D') {
            sv.write(90);  // Riporta il servo in posizione 90° (chiuso)
            Serial.println("[LOCKER] Servo" + String(id) + " chiuso a 90°");
            lcd.clear();
            lcd.print("Chiusura OK");
            delay(2000);
            lcd.clear();
            lcd.print("Inserisci PIN");
            break;
          }
        }
      }
    }
  }
}
