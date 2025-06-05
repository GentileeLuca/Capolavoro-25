# SmartLocker – Relazione Tecnica e Documentazione

## 1. Panoramica del Progetto

SmartLocker è una soluzione integrata per la gestione automatizzata di due locker (scomparti pacchi). Il sistema si articola in tre componenti principali:

* un’applicazione desktop in Python (PySide6 + Pyrebase)
* un modulo ESP32 con connessione Wi-Fi
* un Arduino dotato di servomotori, tastierino 4×4 e display LCD

L’obiettivo è consentire ai corrieri di creare ordini e generare automaticamente un PIN per ciascun locker, in modo che il cliente possa ritirare il proprio pacco sia da remoto, tramite l’applicazione desktop, sia localmente inserendo il PIN sul tastierino. Il flusso di apertura e chiusura dei servomotori è gestito da Arduino, mentre l’ESP32 si occupa di sincronizzare in tempo reale lo stato degli ordini con il database Firebase.

---

## 2. Componenti Hardware

* **ESP32 Dev Board**

  * Modulo Wi-Fi che si connette a Firebase Realtime Database.
  * Utilizza la libreria Firebase\_ESP\_Client per ricevere eventi in streaming.
  * GPIO16 (RX2) e GPIO17 (TX2) collegati in seriale a Arduino.

* **Arduino UNO/Nano**

  * Controlla fisicamente i servomotori SG90.
  * Gestisce un tastierino 4×4 per l’inserimento del PIN e il tasto “D” per la chiusura manuale.
  * Guida un display LCD I2C 16×2 (indirizzo 0x27) per mostrare messaggi di stato.
  * Pin dedicati:

    * Servomotori → 11 e 12
    * Tastierino righe → 2, 3, 4, 5; colonne → 6, 7, 8, 9
    * LCD I2C SDA → A4; SCL → A5

* **Servomotori SG90**

  * Alimentazione a 5 V (non direttamente dai 9 V).
  * Montati in direzioni opposte:

    * Locker 1 → apertura a 180° (verso destra), chiusura a 90°
    * Locker 2 → apertura a 0° (verso sinistra), chiusura a 90°

* **Keypad 4×4**

  * Tasti numerici 0–9, lettere A–D, “\*” e “#”.
  * “#” invia il PIN, “\*” cancella l’input, “D” chiude il locker dopo l’apertura.

* **LCD I2C 16×2**

  * Mostra messaggi come “Inserisci PIN”, “Verifica PIN”, “Apro locker X”, “Premi D per chiud”, “Chiusura OK”.
  * Collegato a SDA (A4) e SCL (A5) di Arduino.

---

## 3. Architettura Software

### 3.1 Applicazione Desktop (PySide6 + Pyrebase)

1. **Autenticazione**

   * Tramite Firebase Authentication (Email/Password).
   * L’utente può registrarsi come “cliente” o “corriere” e fare login con la propria email.

2. **Ruoli e funzionalità**

   * **Corriere**:

     * Accede all’area corriere dopo il login.
     * Può aggiungere nuove consegne, specificando l’email del cliente e il numero del locker (1 o 2).
     * Viene generato automaticamente un PIN a quattro cifre.
     * L’ordine viene salvato in `/orders` con i campi:

       * `email_cliente`
       * `lockerId`
       * `pin`
       * `status: pending`
       * `openRequest: false`
       * `corriere`
     * Visualizza la lista delle consegne che gli sono state assegnate (filtrate per `corriere`).

   * **Cliente**:

     * Accede all’area cliente dopo il login.
     * Visualizza la lista dei propri ordini (filtrata per `email_cliente`).
     * Può aprire un ordine in modalità remota oppure inserendo il PIN.

3. **Database Realtime**

   * Struttura di un nodo `/orders/{orderId}`:

     * `email_cliente: string`
     * `lockerId: int`
     * `pin: string`
     * `status: string` (pending, aperto, chiuso)
     * `openRequest: boolean`
     * `corriere: string`

   * **Query principali**:

     * *get\_orders\_for\_user()*: `.order_by_child("email_cliente").equal_to(email_cliente)`
     * *get\_orders\_for\_courier()*: `.order_by_child("corriere").equal_to(email_corriere)`
     * *add\_order(...)*: `push({ ... })`, restituisce il `orderId`.
     * *request\_open(orderId)*: `update({'openRequest': true})`.
     * *verify\_pin(pin)*: `.order_by_child("pin").equal_to(pin)`, imposta poi `openRequest: true` per quell’ordine.

4. **Interfaccia Utente (UI)**

   * `LoginWindow`: inserimento email e password, pulsante “Login” e “Registrati”.
   * `RegisterWindow`: inserimento email, password, selezione ruolo (cliente/corriere).
   * `ClientWindow`:

     * Visualizza lista ordini del cliente con `QListWidget`.
     * Campo per inserimento PIN e pulsante “Apri via PIN”.
     * Pulsante “Aggiorna Ordini” e “Logout”.
   * `CourierWindow`:

     * Visualizza lista consegne assegnate.
     * Pulsanti: “Aggiorna Consegne”, “Nuova Consegna”, “Richiedi Apertura”, “Logout”.
     * “Nuova Consegna” apre un dialogo di input per email cliente e selezione locker.
     * “Richiedi Apertura” imposta `openRequest = true` per l’ordine selezionato e aggiorna la lista con un breve ritardo (QTimer).

### 3.2 ESP32 (Firmware C++)

1. **Configurazione Wi-Fi e Firebase**

   * `WiFi.begin(WIFI_SSID, WIFI_PASSWORD)` → attende `WL_CONNECTED`.
   * `config.api_key = API_KEY`
   * `config.database_url = DATABASE_URL`
   * `auth.user.email = DEVICE_EMAIL`
   * `auth.user.password = DEVICE_PASSWORD`
   * `Firebase.begin(&config, &auth)` e `Firebase.reconnectWiFi(true)`.

2. **Stream in tempo reale su `/orders`**

   * `Firebase.RTDB.beginStream(&fbdo, "/orders")` → attiva il listener.
   * *Nota*: il primo evento ricevuto è il nodo root (`path="/"`), va ignorato.

3. **Logica nello `loop()`**

   * **Evento su `/orders/{orderId}/openRequest`**

     * `fbdo.dataPath()` restituisce qualcosa come `"/orders/-XYZ/openRequest"`.
     * `fbdo.boolData()` legge il valore booleano di `openRequest`.
     * Se è `true`, chiama `handleOpen(path)` per estrarre `orderId`, leggere `lockerId` via `getInt()`, inviare `OPEN_<lockerId>` ad Arduino, quindi cancellare `/orders/{orderId}` da Firebase.

   * **Evento sul nodo intero `/orders/{orderId}`**

     * Se `dataPath()` è ad esempio `"/orders/-XYZ"`, significa che un parametro interno è stato modificato.
     * In questo caso si esegue:

       1. `String orderId = path.substring(1)` (rimuove lo slash iniziale)
       2. `getBool("/orders/" + orderId + "/openRequest")`
       3. Se `true`, chiama `handleOpen("/orders/" + orderId + "/openRequest")`.

   * **Verifica PIN da tastierino**

     * Arduino invia via `Serial2` il messaggio `"PIN:<valore>"` quando l’utente preme `#`.
     * ESP32 controlla `/orders` con `getJSON()`, deserializza in un oggetto JSON e scorre i nodi:

       * Se trova un nodo con `pin == valore`, legge `lockerId`, invia `OPEN_<lockerId>` ad Arduino, cancella l’ordine.
       * Altrimenti invia `"PIN_ERROR"` ad Arduino.

4. **Funzione `handleOpen(const String &path)`**

   * Estrae `orderId` da `"/orders/{orderId}/openRequest"` usando due `indexOf('/')`.
   * Legge `lockerId` con `FB.RTDB.getInt("/orders/" + orderId + "/lockerId", &locker)`.
   * Invia ad Arduino `Serial2.println("OPEN_" + locker)`.
   * Cancella `/orders/{orderId}` con `FB.RTDB.deleteNode()`.

### 3.3 Arduino (Controllo Locker)

1. **Setup**

   * `Serial2.begin(9600)` per collegamento con ESP32.
   * `s1.attach(12)`, `s2.attach(11)` per i due servo.
   * Servo1 e servo2 inizializzati a 90° (chiusi).
   * `lcd.init()` e `lcd.backlight()`, mostra “Inserisci PIN”.

2. **Loop Principale**

   * **Gestione tastierino**

     * `keypad.getKey()` preleva un tasto.
     * Costruisce la stringa `pinBuf` finché non preme `#`.
     * Alla pressione di `#`, invia `Serial.println("PIN:" + pinBuf)` a ESP32, mostra “Verifica PIN” e resetta `pinBuf`.
     * Alla pressione di `*`, resettare `pinBuf` e ripristinare “Inserisci PIN”.

   * **Gestione comando da ESP32**

     * `Serial2.readStringUntil('\n')` legge un comando come “OPEN\_1” o “OPEN\_2”.
     * Estrae `id = cmd.substring(5).toInt()`.
     * Se `id == 1`, `s1.write(180)` (apertura verso destra); altrimenti `s2.write(0)` (apertura verso sinistra).
     * `lcd.clear()` → mostra “Apro locker X”.
     * `lcd.setCursor(0,1)` → mostra “Premi D per chiud”.
     * Entra in un loop che attende il tasto `D`:

       * Alla pressione di `D`, esegue `sv.write(90)` (chiude il servo), mostra “Chiusura OK” e torna a “Inserisci PIN”.

---

## 4. Flusso Operativo Dettagliato

1. **Il corriere crea un ordine**

   * Accede all’area corriere → “Nuova Consegna” → inserisce `email_cliente` e `lockerId`.
   * Il software genera un PIN casuale a 4 cifre (es. “4721”) e chiama `add_order(...)`.
   * Firebase memorizza:

     ```
     /orders/-MxAbCdEf12345:
       {
         "email_cliente": "cliente@example.com",
         "lockerId": 1,
         "pin": "4721",
         "status": "pending",
         "openRequest": false,
         "corriere": "corriere@example.com"
       }
     ```
   * L’ordine compare nella lista dell’area corriere e nella lista dell’area cliente (filtrata per `email_cliente`).

2. **Cliente richiede apertura da desktop**

   * Il cliente seleziona l’ordine e clicca “Apri”.
   * Viene chiamato `request_open(orderId)`, che aggiorna:

     ```
     /orders/-MxAbCdEf12345/openRequest = true
     ```
   * L’app Python stampa in console:

     ```
     [DEBUG] Imposto openRequest=True su /orders/-MxAbCdEf12345/openRequest
     [DEBUG] openRequest impostato correttamente.
     ```

3. **ESP32 riceve lo stream**

   * `readStream(&fbdo)` rileva un cambiamento su `/orders/-MxAbCdEf12345/openRequest`.
   * `fbdo.dataPath() = "/orders/-MxAbCdEf12345/openRequest"`.
   * `fbdo.boolData() = true`.
   * Chiama `handleOpen("/orders/-MxAbCdEf12345/openRequest")`.

4. **`handleOpen()` su ESP32**

   * Estrae `orderId = "-MxAbCdEf12345"`.
   * Legge `lockerId = 1` con `getInt("/orders/-MxAbCdEf12345/lockerId", &locker)`.
   * Invia ad Arduino: `Serial2.println("OPEN_1")`.
   * Cancella `/orders/-MxAbCdEf12345` con `deleteNode()`, impedendo riutilizzo del PIN.

5. **Arduino apre il locker**

   * Riceve `cmd = "OPEN_1"`.
   * Esegue `s1.write(180)`, spostando la leva verso destra (apertura).
   * LCD mostra “Apro locker 1” e poi “Premi D per chiud”.
   * Attende il tasto `D`:

     * Alla pressione di `D`, esegue `s1.write(90)` (chiusura), mostra “Chiusura OK” e poi torna a “Inserisci PIN”.

6. **Cliente può inserire PIN al tastierino (alternativa remota)**

   * Digita il PIN (es. “4721”) e preme `#`.
   * Arduino invia `Serial.println("PIN:4721")` a ESP32.
   * ESP32 esegue `getJSON("/orders")` e scorre i nodi: trova `/orders/-NxYzAbCd6789` con `pin == "4721"`.
   * Legge `lockerId`, invia `OPEN_<lockerId>` ad Arduino e cancella `/orders/-NxYzAbCd6789`.
   * Se il PIN non corrisponde a nessun ordine, ESP32 invia `Serial2.println("PIN_ERROR")`.

---

## 5. Collegamenti Elettrici

* **ESP32 ↔ Arduino (Serial2)**

  * ESP32 GPIO16 (RX2) ← Arduino TX (Pin 1)
  * ESP32 GPIO17 (TX2) → Arduino RX (Pin 0)
  * GND Arduino ↔ GND ESP32

* **Arduino ↔ Servomotori**

  * Servo1 segnale → Pin 12 (Arduino)
  * Servo2 segnale → Pin 11 (Arduino)
  * Alimentazione 5 V (pin 5 V di Arduino) per entrambi i servo
  * GND servo → GND Arduino
  * Posizione iniziale: 90° (chiuso)

* **Arduino ↔ Keypad 4×4**

  * Righe → Pin 2, 3, 4, 5
  * Colonne → Pin 6, 7, 8, 9
  * GND e VCC alimentati da Arduino

* **Arduino ↔ LCD I2C**

  * SDA → A4 (Arduino)
  * SCL → A5 (Arduino)
  * VCC → 5 V (Arduino)
  * GND → GND (Arduino)

---

## 6. Problemi Riscontrati e Soluzioni

1. **Parsing errato di `orderId`**

   * Problema: inizialmente si utilizzavano concatenazioni di stringhe per estrarre l’ID, dando errori quando lo stream veniva attivato con nodo “root” o altri campi.
   * Soluzione: si è implementato un parsing più robusto con due chiamate a `indexOf('/')` (o `lastIndexOf('/')`), estraendo esattamente il frammento tra il primo e il secondo slash.

2. **Evento “root” dallo stream**

   * Problema: il primo evento di `readStream()` generava `dataPath() == "/"`, che influiva sul parsing.
   * Soluzione: ignorare esplicitamente i casi in cui `path == "/"` e procedere solo se il percorso termina con `/openRequest` o provare a leggere il campo con `getBool()`.

3. **Timeout SSL in `getRules()`**

   * Problema: il tentativo di inizializzare lo stream utilizzando `getRules()` per forzare il layer SSL causava ritardi e timeout.
   * Soluzione: eliminare il `getRules()` e usare direttamente `beginStream()` dopo `Firebase.begin()`, accettando un breve ritardo nell’avvio.

4. **Valori di angolo del servo non validi**

   * Problema: venivano passati valori negativi come `-90` all’interno di `servo.write()`, che accetta solo 0–180.
   * Soluzione: definire 0° e 180° come angoli di apertura, 90° come chiusura. Ora i servo si muovono correttamente.

5. **Instabilità dei servo alimentati a 9 V**

   * Problema: alimentare i servo direttamente da una batteria da 9 V non forniva corrente stabile, causando movimenti irregolari o mancati.
   * Soluzione: alimentare i servo dal pin 5 V di Arduino (tramite regolatore interno) e assicurarsi che il GND sia comune a ESP32 e Arduino.

6. **Filtro ordini cliente non funzionante**

   * Problema: il client desktop filtrava per `userId` (UID) mentre l’ordine conteneva solo `email_cliente`. Di conseguenza la lista compariva vuota.
   * Soluzione: modificare la query di Pyrebase in:

     ```
     db.child("orders")
       .order_by_child("email_cliente")
       .equal_to(email_cliente)
       .get(token)
     ```

     Inserendo inoltre in Firebase Rules:

     ```json
     "orders": {
       ".indexOn": ["email_cliente", "corriere", "pin", "openRequest"]
     }
     ```

---

## 7. Conclusioni e Miglioramenti Futuri

SmartLocker dimostra come integrare efficacemente:

* **Cloud computing** (Firebase Realtime Database)
* **Programmazione embedded** (ESP32, Arduino)
* **Interfaccia desktop** (PySide6)

per implementare una soluzione di consegna e ritiro automatizzato di pacchi.
Il sistema è:

* **Sicuro**: il PIN viene eliminato da Firebase dopo l’uso, impedendo riutilizzi.
* **Flessibile**: l’utente può aprire il locker da remoto o con un tastierino fisico.
* **Scalabile**: con poche modifiche si possono aggiungere altri locker o gestire più utenti simultaneamente.
* **Affidabile**: l’uso di stream Realtime DB garantisce la sincronizzazione immediata delle modifiche.
