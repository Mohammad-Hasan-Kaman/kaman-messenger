# کد MakeKey.py (فقط یک بار اجرا شود)
from cryptography.fernet import Fernet
import os

key = Fernet.generate_key()

with open("secret.key", "wb") as key_file:
    key_file.write(key)

print("Key generated successfully: secret.key")