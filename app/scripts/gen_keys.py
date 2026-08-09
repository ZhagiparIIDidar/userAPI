# app/scripts/generate_keys.py
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pathlib import Path


def generate_rsa_keypair(key_dir: str = "keys", key_size: int = 2048):
    key_path = Path(key_dir)
    key_path.mkdir(exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    (key_path / "private.pem").write_bytes(private_pem)

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    (key_path / "public.pem").write_bytes(public_pem)


if __name__ == "__main__":
    generate_rsa_keypair()
