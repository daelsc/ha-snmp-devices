"""Minimal SNMPv2c client using only the Python standard library.

Implements GET and SET for single OIDs over UDP. No external dependencies.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

# BER/ASN.1 tags
_TAG_INTEGER = 0x02
_TAG_OCTET_STRING = 0x04
_TAG_NULL = 0x05
_TAG_OID = 0x06
_TAG_SEQUENCE = 0x30
_TAG_GET_REQUEST = 0xA0
_TAG_GET_RESPONSE = 0xA2
_TAG_SET_REQUEST = 0xA3
# Application-specific (unsigned integer types)
_TAG_COUNTER32 = 0x41
_TAG_GAUGE32 = 0x42
_TAG_TIMETICKS = 0x43
_TAG_COUNTER64 = 0x46
# Exception types
_TAG_NO_SUCH_OBJECT = 0x80
_TAG_NO_SUCH_INSTANCE = 0x81
_TAG_END_OF_MIB_VIEW = 0x82

_SNMP_VERSION_2C = 1


# ---------------------------------------------------------------------------
# BER encoding
# ---------------------------------------------------------------------------

def _encode_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    parts: list[int] = []
    tmp = length
    while tmp:
        parts.insert(0, tmp & 0xFF)
        tmp >>= 8
    return bytes([0x80 | len(parts)] + parts)


def _encode_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def _encode_integer(value: int) -> bytes:
    if value == 0:
        return _encode_tlv(_TAG_INTEGER, b"\x00")
    if value > 0:
        raw: list[int] = []
        tmp = value
        while tmp:
            raw.insert(0, tmp & 0xFF)
            tmp >>= 8
        if raw[0] & 0x80:
            raw.insert(0, 0)
        return _encode_tlv(_TAG_INTEGER, bytes(raw))
    # Negative — two's complement
    byte_len = (value.bit_length() + 8) // 8
    unsigned = value & ((1 << (byte_len * 8)) - 1)
    raw = []
    tmp = unsigned
    while tmp:
        raw.insert(0, tmp & 0xFF)
        tmp >>= 8
    while len(raw) < byte_len:
        raw.insert(0, 0xFF)
    return _encode_tlv(_TAG_INTEGER, bytes(raw))


def _encode_octet_string(value: str | bytes) -> bytes:
    if isinstance(value, str):
        value = value.encode()
    return _encode_tlv(_TAG_OCTET_STRING, value)


def _encode_null() -> bytes:
    return b"\x05\x00"


def _encode_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.strip(".").split(".")]
    if len(parts) < 2:
        raise ValueError(f"OID too short: {oid}")
    encoded = [40 * parts[0] + parts[1]]
    for part in parts[2:]:
        if part < 0x80:
            encoded.append(part)
        else:
            sub: list[int] = []
            tmp = part
            while tmp:
                sub.insert(0, tmp & 0x7F)
                tmp >>= 7
            for i in range(len(sub) - 1):
                sub[i] |= 0x80
            encoded.extend(sub)
    return _encode_tlv(_TAG_OID, bytes(encoded))


def _encode_sequence(contents: bytes) -> bytes:
    return _encode_tlv(_TAG_SEQUENCE, contents)


# ---------------------------------------------------------------------------
# BER decoding
# ---------------------------------------------------------------------------

def _decode_length(data: bytes, offset: int) -> tuple[int, int]:
    if data[offset] < 0x80:
        return data[offset], offset + 1
    num = data[offset] & 0x7F
    length = 0
    for i in range(num):
        length = (length << 8) | data[offset + 1 + i]
    return length, offset + 1 + num


def _decode_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    tag = data[offset]
    length, off = _decode_length(data, offset + 1)
    return tag, data[off : off + length], off + length


def _decode_signed(data: bytes) -> int:
    if not data:
        return 0
    value = 0
    for b in data:
        value = (value << 8) | b
    if data[0] & 0x80:
        value -= 1 << (len(data) * 8)
    return value


def _decode_unsigned(data: bytes) -> int:
    value = 0
    for b in data:
        value = (value << 8) | b
    return value


# ---------------------------------------------------------------------------
# Packet builders
# ---------------------------------------------------------------------------

def _build_request(tag: int, community: str, oid: str, request_id: int, value_tlv: bytes) -> bytes:
    varbind = _encode_sequence(_encode_oid(oid) + value_tlv)
    varbind_list = _encode_sequence(varbind)
    pdu = _encode_tlv(
        tag,
        _encode_integer(request_id)
        + _encode_integer(0)
        + _encode_integer(0)
        + varbind_list,
    )
    return _encode_sequence(
        _encode_integer(_SNMP_VERSION_2C)
        + _encode_octet_string(community)
        + pdu,
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

@dataclass
class SNMPResponse:
    """Parsed SNMP response."""

    value: Any = None
    error: str | None = None
    no_such: bool = False


def _parse_response(data: bytes) -> SNMPResponse:
    try:
        tag, seq_data, _ = _decode_tlv(data, 0)
        if tag != _TAG_SEQUENCE:
            return SNMPResponse(error="Invalid response: not a SEQUENCE")

        off = 0
        # version
        _, _, off = _decode_tlv(seq_data, off)
        # community
        _, _, off = _decode_tlv(seq_data, off)
        # PDU
        tag, pdu_data, _ = _decode_tlv(seq_data, off)
        if tag != _TAG_GET_RESPONSE:
            return SNMPResponse(error=f"Unexpected PDU tag: {tag:#x}")

        poff = 0
        # request-id
        _, _, poff = _decode_tlv(pdu_data, poff)
        # error-status
        _, err_data, poff = _decode_tlv(pdu_data, poff)
        error_status = _decode_signed(err_data)
        if error_status != 0:
            return SNMPResponse(error=f"SNMP error status: {error_status}")
        # error-index
        _, _, poff = _decode_tlv(pdu_data, poff)
        # varbind-list
        _, vbl_data, _ = _decode_tlv(pdu_data, poff)
        # first varbind
        _, vb_data, _ = _decode_tlv(vbl_data, 0)
        voff = 0
        # OID
        _, _, voff = _decode_tlv(vb_data, voff)
        # value
        tag, val_data, _ = _decode_tlv(vb_data, voff)

        if tag in (_TAG_NO_SUCH_OBJECT, _TAG_NO_SUCH_INSTANCE, _TAG_END_OF_MIB_VIEW):
            return SNMPResponse(no_such=True)
        if tag == _TAG_INTEGER:
            return SNMPResponse(value=_decode_signed(val_data))
        if tag in (_TAG_COUNTER32, _TAG_GAUGE32, _TAG_TIMETICKS, _TAG_COUNTER64):
            return SNMPResponse(value=_decode_unsigned(val_data))
        if tag == _TAG_OCTET_STRING:
            return SNMPResponse(value=val_data.decode("utf-8", errors="replace"))
        # Unknown type — return raw
        return SNMPResponse(value=val_data)

    except Exception as err:
        return SNMPResponse(error=f"Parse error: {err}")


# ---------------------------------------------------------------------------
# Async UDP transport
# ---------------------------------------------------------------------------

async def _snmp_request(host: str, port: int, packet: bytes, timeout: float) -> SNMPResponse:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bytes] = loop.create_future()

    class _Protocol(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
            if not future.done():
                future.set_result(data)

        def error_received(self, exc: Exception | None) -> None:
            if not future.done():
                future.set_exception(exc or OSError("UDP error"))

    try:
        transport, _ = await asyncio.wait_for(
            loop.create_datagram_endpoint(lambda: _Protocol(), remote_addr=(host, port)),
            timeout=timeout,
        )
    except Exception as err:
        return SNMPResponse(error=f"Connection error: {err}")

    try:
        transport.sendto(packet)
        data = await asyncio.wait_for(future, timeout=timeout)
        return _parse_response(data)
    except asyncio.TimeoutError:
        return SNMPResponse(error="Timeout")
    except Exception as err:
        return SNMPResponse(error=str(err))
    finally:
        transport.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def snmp_get(
    host: str, community: str, oid: str, *, port: int = 161, timeout: float = 2.0
) -> SNMPResponse:
    """Perform an SNMPv2c GET."""
    request_id = int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF
    packet = _build_request(_TAG_GET_REQUEST, community, oid, request_id, _encode_null())
    return await _snmp_request(host, port, packet, timeout)


async def snmp_set(
    host: str, community: str, oid: str, value: int, *, port: int = 161, timeout: float = 2.0
) -> SNMPResponse:
    """Perform an SNMPv2c SET."""
    request_id = int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF
    packet = _build_request(_TAG_SET_REQUEST, community, oid, request_id, _encode_integer(value))
    return await _snmp_request(host, port, packet, timeout)
