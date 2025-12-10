#!/usr/bin/env python3
import secrets

def generate_secret_key():
    """Generates a strong, random 32-byte hex secret key."""
    return secrets.token_hex(32)

if __name__ == "__main__":
    print("Here is a strong, random SECRET_KEY for your production environment:\n")
    print(generate_secret_key())
    print("\nCopy this key and set it in your environment variables.")
