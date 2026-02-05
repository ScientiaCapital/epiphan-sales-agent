"""Tests for checkpoint encryption.

TDD tests for AESCipher and get_serializer() in checkpointing.py.
Tests cover:
- AESCipher encrypt/decrypt roundtrip
- get_serializer() returns EncryptedSerializer when LANGGRAPH_AES_KEY set
- get_serializer() returns None when key missing
- Invalid key length handling (not 32 bytes)
- Cipher name validation
"""

import base64
import os
from unittest.mock import patch

import pytest

from app.services.langgraph.checkpointing import AESCipher, get_serializer


class TestAESCipher:
    """Tests for AESCipher class."""

    @pytest.fixture
    def valid_key(self) -> bytes:
        """Create a valid 32-byte AES key."""
        return b"0123456789abcdef0123456789abcdef"  # 32 bytes

    @pytest.fixture
    def cipher(self, valid_key: bytes) -> AESCipher:
        """Create an AESCipher instance with valid key."""
        return AESCipher(valid_key)

    def test_cipher_name_is_aes_256_gcm(self) -> None:
        """Test cipher name constant."""
        assert AESCipher.CIPHER_NAME == "aes-256-gcm"

    def test_encrypt_returns_tuple_with_cipher_name(
        self, cipher: AESCipher
    ) -> None:
        """Test encrypt returns (cipher_name, ciphertext)."""
        plaintext = b"Hello, World!"

        result = cipher.encrypt(plaintext)

        assert isinstance(result, tuple)
        assert len(result) == 2
        cipher_name, ciphertext = result
        assert cipher_name == "aes-256-gcm"
        assert isinstance(ciphertext, bytes)

    def test_encrypt_ciphertext_contains_nonce(
        self, cipher: AESCipher
    ) -> None:
        """Test ciphertext has prepended 12-byte nonce."""
        plaintext = b"Test data"

        _, ciphertext = cipher.encrypt(plaintext)

        # Ciphertext should be at least 12 bytes (nonce) + 16 bytes (GCM tag)
        assert len(ciphertext) >= 28

    def test_decrypt_recovers_original_plaintext(
        self, cipher: AESCipher
    ) -> None:
        """Test roundtrip: encrypt then decrypt recovers original."""
        plaintext = b"Sensitive checkpoint data with unicode: \xc3\xa9\xc3\xa0"

        cipher_name, ciphertext = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(cipher_name, ciphertext)

        assert decrypted == plaintext

    def test_decrypt_with_wrong_cipher_name_raises(
        self, cipher: AESCipher
    ) -> None:
        """Test decrypt raises ValueError for wrong cipher name."""
        _, ciphertext = cipher.encrypt(b"data")

        with pytest.raises(ValueError) as exc_info:
            cipher.decrypt("aes-128-cbc", ciphertext)

        assert "Unknown cipher: aes-128-cbc" in str(exc_info.value)
        assert "expected aes-256-gcm" in str(exc_info.value)

    def test_decrypt_with_tampered_ciphertext_raises(
        self, cipher: AESCipher
    ) -> None:
        """Test decrypt raises on tampered ciphertext (GCM auth)."""
        from cryptography.exceptions import InvalidTag

        _, ciphertext = cipher.encrypt(b"original data")

        # Tamper with the ciphertext (after the nonce)
        tampered = bytearray(ciphertext)
        tampered[15] ^= 0xFF  # Flip bits in ciphertext portion
        tampered_bytes = bytes(tampered)

        with pytest.raises(InvalidTag):
            cipher.decrypt("aes-256-gcm", tampered_bytes)

    def test_encrypt_produces_different_ciphertext_each_time(
        self, cipher: AESCipher
    ) -> None:
        """Test each encryption uses unique nonce (different ciphertext)."""
        plaintext = b"Same message"

        _, ciphertext1 = cipher.encrypt(plaintext)
        _, ciphertext2 = cipher.encrypt(plaintext)

        # Nonces should be different, making ciphertexts different
        assert ciphertext1 != ciphertext2

    def test_empty_plaintext_roundtrip(self, cipher: AESCipher) -> None:
        """Test empty plaintext can be encrypted and decrypted."""
        plaintext = b""

        cipher_name, ciphertext = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(cipher_name, ciphertext)

        assert decrypted == plaintext

    def test_large_plaintext_roundtrip(self, cipher: AESCipher) -> None:
        """Test large data roundtrip (1MB)."""
        plaintext = b"x" * (1024 * 1024)  # 1MB

        cipher_name, ciphertext = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(cipher_name, ciphertext)

        assert decrypted == plaintext


class TestGetSerializer:
    """Tests for get_serializer() function."""

    @pytest.fixture
    def valid_base64_key(self) -> str:
        """Create a valid base64-encoded 32-byte key."""
        key_bytes = b"0123456789abcdef0123456789abcdef"
        return base64.b64encode(key_bytes).decode()

    def test_returns_none_when_no_key_set(self) -> None:
        """Test returns None when LANGGRAPH_AES_KEY not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure key is not in environment
            if "LANGGRAPH_AES_KEY" in os.environ:
                del os.environ["LANGGRAPH_AES_KEY"]

            result = get_serializer()

            assert result is None

    def test_returns_encrypted_serializer_when_key_set(
        self, valid_base64_key: str
    ) -> None:
        """Test returns EncryptedSerializer when valid key is set."""
        with patch.dict(os.environ, {"LANGGRAPH_AES_KEY": valid_base64_key}):
            result = get_serializer()

            # Should return an EncryptedSerializer instance
            assert result is not None
            # Check it has the expected interface (LangGraph's SerializerProtocol)
            assert hasattr(result, "dumps_typed")
            assert hasattr(result, "loads_typed")

    def test_returns_none_for_invalid_key_length(self) -> None:
        """Test returns None when key is not 32 bytes after decode."""
        # 16-byte key (too short)
        short_key = base64.b64encode(b"0123456789abcdef").decode()

        with patch.dict(os.environ, {"LANGGRAPH_AES_KEY": short_key}):
            result = get_serializer()

            assert result is None

    def test_returns_none_for_empty_key(self) -> None:
        """Test returns None when key is empty string."""
        with patch.dict(os.environ, {"LANGGRAPH_AES_KEY": ""}):
            result = get_serializer()

            assert result is None

    def test_returns_none_for_invalid_base64(self) -> None:
        """Test returns None when key is invalid base64."""
        with patch.dict(os.environ, {"LANGGRAPH_AES_KEY": "not-valid-base64!!"}):
            result = get_serializer()

            # Should handle gracefully and return None
            assert result is None

    def test_logs_warning_for_wrong_key_length(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning is logged for wrong key length."""
        import logging

        short_key = base64.b64encode(b"tooshort").decode()

        with (
            patch.dict(os.environ, {"LANGGRAPH_AES_KEY": short_key}),
            caplog.at_level(logging.WARNING),
        ):
            get_serializer()

        assert "must be 32 bytes" in caplog.text

    def test_logs_info_when_encryption_enabled(
        self, valid_base64_key: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test info log when encryption is successfully enabled."""
        import logging

        with (
            patch.dict(os.environ, {"LANGGRAPH_AES_KEY": valid_base64_key}),
            caplog.at_level(logging.INFO),
        ):
            result = get_serializer()

        if result is not None:  # Only if EncryptedSerializer available
            assert "encryption enabled" in caplog.text.lower()


class TestAESCipherProtocolCompliance:
    """Tests verifying AESCipher implements CipherProtocol correctly."""

    @pytest.fixture
    def cipher(self) -> AESCipher:
        """Create cipher for protocol tests."""
        return AESCipher(b"0123456789abcdef0123456789abcdef")

    def test_has_encrypt_method(self, cipher: AESCipher) -> None:
        """Test cipher has encrypt(plaintext) -> (name, ciphertext)."""
        assert hasattr(cipher, "encrypt")
        assert callable(cipher.encrypt)

    def test_has_decrypt_method(self, cipher: AESCipher) -> None:
        """Test cipher has decrypt(name, ciphertext) -> plaintext."""
        assert hasattr(cipher, "decrypt")
        assert callable(cipher.decrypt)

    def test_encrypt_signature(self, cipher: AESCipher) -> None:
        """Test encrypt accepts bytes and returns tuple[str, bytes]."""
        result = cipher.encrypt(b"test")
        assert isinstance(result[0], str)
        assert isinstance(result[1], bytes)

    def test_decrypt_signature(self, cipher: AESCipher) -> None:
        """Test decrypt accepts str, bytes and returns bytes."""
        cipher_name, ct = cipher.encrypt(b"test")
        result = cipher.decrypt(cipher_name, ct)
        assert isinstance(result, bytes)
