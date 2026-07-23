"""
Verwaltung des lokalen, verschlüsselten Passwort-Tresors.

Der komplette Tresor (alle Einträge) wird als JSON serialisiert,
als Ganzes mit Fernet verschlüsselt und atomar auf die Festplatte
geschrieben. Es gibt zwei Dateien:

  - salt.bin  : zufälliges Salt (NICHT geheim, wird zur Schlüsselableitung
                gebraucht, ohne Master-Passwort aber nutzlos)
  - vault.dat : verschlüsselter Inhalt (JSON-Liste aller Einträge)

Beide liegen standardmäßig unter ~/.python_password_manager/
"""
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List

from cryptography.fernet import InvalidToken

import crypto_utils

APP_DIR = os.path.join(os.path.expanduser("~"), ".python_password_manager")
VAULT_FILE = os.path.join(APP_DIR, "vault.dat")
SALT_FILE = os.path.join(APP_DIR, "salt.bin")


class WrongPasswordError(Exception):
    """Wird ausgelöst, wenn das Master-Passwort falsch ist oder der Tresor beschädigt ist."""


@dataclass
class Entry:
    service: str
    username: str
    password: str
    url: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def vault_exists() -> bool:
    return os.path.exists(VAULT_FILE) and os.path.exists(SALT_FILE)


def _ensure_app_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def create_vault(master_password: str) -> bytes:
    """Legt einen neuen, leeren Tresor an. Gibt den abgeleiteten Schlüssel zurück."""
    _ensure_app_dir()
    salt = crypto_utils.generate_salt()
    with open(SALT_FILE, "wb") as f:
        f.write(salt)

    key = crypto_utils.derive_key(master_password, salt)
    save_entries([], key)
    return key


def _load_salt() -> bytes:
    with open(SALT_FILE, "rb") as f:
        return f.read()


def derive_key_for_login(master_password: str) -> bytes:
    return crypto_utils.derive_key(master_password, _load_salt())


def load_entries(master_password: str) -> tuple[List[Entry], bytes]:
    """
    Versucht, den Tresor mit dem angegebenen Master-Passwort zu entschlüsseln.
    Gibt (Einträge, Schlüssel) zurück oder wirft WrongPasswordError.
    """
    key = derive_key_for_login(master_password)
    with open(VAULT_FILE, "rb") as f:
        token = f.read()
    try:
        raw = crypto_utils.decrypt(token, key)
    except InvalidToken:
        raise WrongPasswordError("Falsches Master-Passwort oder beschädigter Tresor.")
    data = json.loads(raw.decode("utf-8"))
    entries = [Entry(**item) for item in data]
    return entries, key


def save_entries(entries: List[Entry], key: bytes):
    """Verschlüsselt und schreibt alle Einträge atomar auf die Festplatte."""
    _ensure_app_dir()
    raw = json.dumps([asdict(e) for e in entries]).encode("utf-8")
    token = crypto_utils.encrypt(raw, key)
    tmp_path = VAULT_FILE + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(token)
    os.replace(tmp_path, VAULT_FILE)  # atomar: kein halb-geschriebener Tresor möglich


def change_master_password(entries: List[Entry], new_master_password: str) -> bytes:
    """Erzeugt ein neues Salt + neuen Schlüssel und schreibt den Tresor damit neu."""
    _ensure_app_dir()
    new_salt = crypto_utils.generate_salt()
    new_key = crypto_utils.derive_key(new_master_password, new_salt)

    with open(SALT_FILE, "wb") as f:
        f.write(new_salt)

    save_entries(entries, new_key)
    return new_key


def export_backup_path() -> str:
    return VAULT_FILE
