from __future__ import annotations

from binascii import hexlify, unhexlify
import struct

from monero import base58, const, ed25519
from monero.address import Address
from monero.keccak import keccak_256

# Override monero library network constants for Wownero
from monero import const as _mc
_mc.NETS = ('main',)
_mc.MASTERADDR_NETBYTES = (53,)   # Wownero mainnet address prefix
_mc.SUBADDR_NETBYTES = (63,)      # Wownero subaddress prefix
_mc.INTADDRR_NETBYTES = (54,)     # Wownero integrated address prefix


def derive_subaddress(
    *,
    payment_address: str,
    view_key: str,
    account_index: int,
    address_index: int,
) -> str:
    address = Address(payment_address)
    view_key_bytes = unhexlify(view_key)
    spend_pub_bytes = unhexlify(address.spend_key())

    data = (
        b"SubAddr\0"
        + view_key_bytes
        + struct.pack("<II", account_index, address_index)
    )
    m = ed25519.scalar_reduce(keccak_256(data).digest())
    mG = ed25519.scalarmult_B(m)
    D = ed25519.edwards_add(spend_pub_bytes, mG)
    C = ed25519.scalarmult(view_key_bytes, D)
    prefix = const.SUBADDR_NETBYTES[const.NETS.index(address.net)]
    payload = bytearray([prefix]) + D + C
    checksum = keccak_256(payload).digest()[:4]
    return base58.encode(hexlify(payload + checksum))
