from __future__ import annotations

from binascii import hexlify, unhexlify
import struct

from monero import base58, ed25519
from monero.keccak import keccak_256

# Wownero network prefix bytes (first byte of varint-encoded base58 prefix).
# Primary: base58 prefix 4146 -> varint [0xb2, 0x20]  -> "Wo"
# Subaddr: base58 prefix 12208 -> varint [0xb0, 0x5f] -> "Ww"
_WOW_PRIMARY_VARINT = bytes([0xb2, 0x20])
_WOW_SUBADDR_VARINT = bytes([0xb0, 0x5f])


def _decode_wow_address(payment_address: str) -> tuple[bytes, bytes]:
    """Decode a Wownero primary address and return (pub_spend, pub_view) as raw bytes."""
    decoded = bytearray(unhexlify(base58.decode(payment_address)))
    # Verify checksum
    if decoded[-4:] != keccak_256(decoded[:-4]).digest()[:4]:
        raise ValueError("Invalid checksum")
    if decoded[0] != _WOW_PRIMARY_VARINT[0]:
        raise ValueError(f"Not a Wownero primary address (netbyte {decoded[0]})")
    # 2-byte varint prefix, then 32-byte spend key, 32-byte view key, 4-byte checksum
    pub_spend = bytes(decoded[2:34])
    pub_view = bytes(decoded[34:66])
    return pub_spend, pub_view


def derive_subaddress(
    *,
    payment_address: str,
    view_key: str,
    account_index: int,
    address_index: int,
) -> str:
    """Derive a Wownero subaddress from a primary address and secret view key."""
    pub_spend, _pub_view = _decode_wow_address(payment_address)
    view_key_bytes = unhexlify(view_key)

    data = (
        b"SubAddr\0"
        + view_key_bytes
        + struct.pack("<II", account_index, address_index)
    )
    m = ed25519.scalar_reduce(keccak_256(data).digest())
    mG = ed25519.scalarmult_B(m)
    D = ed25519.edwards_add(pub_spend, mG)
    C = ed25519.scalarmult(view_key_bytes, D)
    # Wownero subaddress uses 2-byte varint prefix
    payload = bytearray(_WOW_SUBADDR_VARINT) + D + C
    checksum = keccak_256(payload).digest()[:4]
    return base58.encode(hexlify(payload + checksum))
