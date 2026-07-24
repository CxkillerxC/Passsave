# Passsave
simple local password save (lokal, Python)

Ein sicherer, komplett lokal laufender Passwort-Manager mit grafischer
Oberfläche. Keine Cloud, kein Server, kein Internetzugriff nötig.

## Funktionen

- Master-Passwort schützt den gesamten Tresor
- Starke Verschlüsselung: PBKDF2-HMAC-SHA256 (480.000 Iterationen) zur
  Schlüsselableitung + Fernet (AES-128 + HMAC, authentifiziert) zur
  Verschlüsselung der Daten
- Master-Passwort wird **nie** gespeichert – nur ein zufälliges Salt
- Einträge anlegen, bearbeiten, löschen, durchsuchen
- Integrierter Passwort-Generator (Länge, Groß-/Kleinschreibung, Zahlen,
  Sonderzeichen)
- Passwort-Stärkeanzeige
- Ein-Klick-Kopieren von Benutzername/Passwort in die Zwischenablage
  (Zwischenablage wird nach 20 Sekunden automatisch geleert)
- **(Auto-Type)**: tippt Benutzername + Tab + Passwort
  automatisch in ein beliebiges Browser- oder App-Fenster – wie bei
  KeePass, ganz ohne Browser-Erweiterung (siehe unten)
- Automatische Sperre nach 5 Minuten Inaktivität
- Master-Passwort jederzeit änderbar (Tresor wird neu verschlüsselt)
- Alle Daten liegen lokal unter `~/.python_password_manager/`

## Installation (VS Code / Terminal)

1. Python 3.9+ muss installiert sein (`python3 --version`).
2. Projektordner in VS Code öffnen.
3. Virtuelle Umgebung erstellen und aktivieren (empfohlen):

   ```bash
   python3 -m venv venv
   # macOS/Linux:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

4. Abhängigkeiten installieren:

   ```bash
   pip install -r requirements.txt
   ```

5. App starten:

   ```bash
   python main.py
   ```

   In VS Code reicht auch: Datei `main.py` öffnen → oben rechts auf
   **▷ Run** klicken (oder `F5`).

## Erste Schritte

- Beim allerersten Start wirst du gebeten, ein **Master-Passwort**
  festzulegen. Merke es dir gut – ohne dieses Passwort können die
  gespeicherten Daten **nicht** wiederhergestellt werden.
- Danach landest du im Tresor und kannst über "+ Neuer Eintrag" deine
  ersten Zugangsdaten speichern.

## Wo liegen meine Daten?

```
~/.python_password_manager/
├── vault.dat   # verschlüsselter Tresor (alle Einträge)
└── salt.bin    # Salt zur Schlüsselableitung (nicht geheim, aber nötig)
```

- Windows: `C:\Users\<DeinName>\.python_password_manager\`
- macOS/Linux: `/home/<DeinName>/.python_password_manager/`

**Backup:** Es reicht, beide Dateien zu kopieren (z. B. auf einen
verschlüsselten USB-Stick). Ohne dein Master-Passwort sind sie wertlos –
bewahre sie trotzdem nicht öffentlich zugänglich auf.

## Automatisches Ausfüllen im Browser/in Apps (Auto-Type)

Es gibt **keine** Browser-Erweiterung – die würde ein komplett eigenes
Projekt sein (Extension + Native-Messaging-Host + Formularerkennung pro
Website). Stattdessen gibt es **Auto-Type**, wie man es von KeePass
kennt:

1. Eintrag in der Liste auswählen
2. Auf **"⌨️ Auto-Ausfüllen"** klicken
3. Der Passwort-Manager minimiert sich, ein kleiner Countdown erscheint
4. **Innerhalb der 3 Sekunden** in das Login-Feld im Browser/in der App
   klicken
5. Der Manager tippt automatisch: `Benutzername` → `Tab` → `Passwort`
   (kein automatisches Absenden/Enter – du prüfst die Daten und
   bestätigst selbst)
6. Mit `ESC` lässt sich der Vorgang jederzeit abbrechen

**Wichtig:** Es findet keine Erkennung von Formularfeldern statt – es
werden blind Tastatureingaben gesendet, dorthin, wo gerade der
Eingabefokus liegt. Du musst also selbst vorher in das richtige Feld
klicken.

**Plattformhinweise:**
- Windows/macOS: funktioniert direkt nach `pip install pyautogui`.
- Linux: benötigt eine **X11**-Sitzung. Unter reinem Wayland (ohne
  XWayland) funktioniert die Tastatursimulation eventuell nicht – nutze
  in dem Fall die "Kopieren"-Buttons als Alternative.
- macOS verlangt zusätzlich, dass du der Python-App unter
  **Systemeinstellungen → Datenschutz & Sicherheit → Bedienungshilfen**
  Zugriff erlaubst (sonst kann nichts simuliert werden).

## Sicherheitshinweise

- Dies ist ein Lernprojekt / persönliches Tool. Es wurde sorgfältig mit
  bewährten, geprüften Bibliotheken (`cryptography`) gebaut, hat aber
  kein professionelles Sicherheitsaudit durchlaufen wie kommerzielle
  Passwort-Manager (Bitwarden, 1Password, KeePass).
- Für sehr sensible/geschäftskritische Nutzung empfiehlt sich weiterhin
  ein etabliertes, auditiertes Produkt.
- Der Tresor wird beim Speichern jedes Mal komplett neu verschlüsselt
  (kein Klartext-Zwischenspeichern auf der Festplatte).
- Bei falschem Master-Passwort wird der Login abgelehnt, ohne
  Rückschlüsse auf den Inhalt zuzulassen (authentifizierte
  Verschlüsselung via Fernet).

## Projektstruktur

```
password_manager/
├── main.py           # GUI (customtkinter)
├── storage.py         # Laden/Speichern des verschlüsselten Tresors
├── crypto_utils.py    # Schlüsselableitung, Ver-/Entschlüsselung, Generator
├── requirements.txt
└── README.md
```

## Mögliche Erweiterungen

- Kategorien/Tags für Einträge
- Import/Export (z. B. verschlüsseltes JSON, CSV-Import aus anderen Managern)
- 2FA-/TOTP-Codes direkt im Manager anzeigen
- Mehrere Tresore/Profile
