# crypto_utils.py —— 加密 / 解密模块（含HMAC消息签名）
import os
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import config

# HMAC密钥：从预共享密钥派生（与加密密钥不同）
HMAC_KEY = hashlib.sha256(config.PRE_SHARED_KEY + b"_hmac_salt").digest()


# ============================================================
#  加密+签名：明文 bytes → 密文+HMAC bytes
#  步骤：1. 随机IV  2. PKCS7填充  3. AES-CBC加密  4. HMAC-SHA256签名
#  返回：IV(16B) + 密文 + HMAC(32B)
# ============================================================
def encrypt(plaintext: bytes, key: bytes = None) -> bytes:
    if key is None:
        key = config.PRE_SHARED_KEY

    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    body = iv + ciphertext
    sig = hmac.new(HMAC_KEY, body, hashlib.sha256).digest()
    return body + sig


# ============================================================
#  验证+解密：密文+HMAC bytes → 明文 bytes
#  格式：IV(16B) + 密文 + HMAC(32B)
#  验证失败抛出 ValueError
# ============================================================
def decrypt(data: bytes, key: bytes = None) -> bytes:
    if key is None:
        key = config.PRE_SHARED_KEY

    if len(data) < 48:
        raise ValueError("Data too short")

    sig = data[-32:]
    body = data[:-32]

    # 验证HMAC
    expected = hmac.new(HMAC_KEY, body, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("HMAC verification failed - message may be tampered!")

    iv = body[:16]
    ciphertext = body[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_data) + unpadder.finalize()

    return plaintext