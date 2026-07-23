"""
Kryptographie-Hilfsfunktionen für den Passwort-Manager.

- Der Verschlüsselungsschlüssel wird NIE gespeichert. Er wird bei jedem
  Login frisch aus dem Master-Passwort + einem gespeicherten Salt
  abgeleitet (PBKDF2-HMAC-SHA256, 480.000 Iterationen, OWASP-Empfehlung).
- Die eigentlichen Daten werden mit Fernet (AES-128-CBC + HMAC-SHA256,
  also authentifizierte Verschlüsselung) geschützt.
"""
import base64
import os
import secrets
import string

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_SIZE = 16
KDF_ITERATIONS = 480_000  # OWASP-Empfehlung (Stand 2024/2025) für PBKDF2-SHA256


def generate_salt() -> bytes:
    """Erzeugt ein kryptographisch sicheres, zufälliges Salt."""
    return os.urandom(SALT_SIZE)


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Leitet aus Master-Passwort + Salt einen 256-Bit-Schlüssel für Fernet ab."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def encrypt(data: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(data)


def decrypt(token: bytes, key: bytes) -> bytes:
    # Wirft cryptography.fernet.InvalidToken bei falschem Passwort
    # oder manipulierten/beschädigten Daten.
    return Fernet(key).decrypt(token)


def generate_password(
    length: int = 20,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Erzeugt ein zufälliges, starkes Passwort mit garantierter Zeichenvielfalt."""
    length = max(length, 4)
    pools = [string.ascii_lowercase]
    if use_upper:
        pools.append(string.ascii_uppercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{};:,.<>?")

    alphabet = "".join(pools)

    # Mindestens ein Zeichen aus jedem aktiven Pool, Rest zufällig auffüllen
    password_chars = [secrets.choice(pool) for pool in pools]
    password_chars += [
        secrets.choice(alphabet) for _ in range(length - len(password_chars))
    ]
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def password_strength_label(password: str) -> str:
    """Sehr einfache heuristische Einschätzung für die UI (kein Sicherheitsbeweis)."""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 14:
        score += 1
    if any(c.islower() for c in password) and any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()-_=+[]{};:,.<>?/\\|~`" for c in password):
        score += 1

    if score <= 2:
        return "Schwach"
    if score <= 3:
        return "Okay"
    if score == 4:
        return "Stark"
    return "Sehr stark"
