
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd()))

from app.core.security import encrypt_token, decrypt_token
from app.infrastructure.config import settings

def test_encryption():
    print(f"Testing with key: {settings.ENCRYPTION_KEY[:10]}...")
    
    original_token = "secret_access_token_123"
    
    # 1. Test basic helpers
    encrypted = encrypt_token(original_token)
    print(f"Encrypted: {encrypted}")
    
    decrypted = decrypt_token(encrypted)
    print(f"Decrypted: {decrypted}")
    
    assert decrypted == original_token, f"Decryption failed! Expected {original_token}, got {decrypted}"
    print("Base encryption test passed!")

    # 2. Test empty/None
    assert encrypt_token(None) is None
    assert decrypt_token(None) is None
    print("Empty values test passed!")

if __name__ == "__main__":
    try:
        test_encryption()
        print("\nALL ENCRYPTION TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
