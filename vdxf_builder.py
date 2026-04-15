"""
VDXF Object Builder — Construct typed contentmultimap entries.

Provides fluent builders for DataDescriptors, ContentMultiMaps, and compact
binary serialization (inspired by paco_message.js VDXFObject pattern).

The Verus ``contentmultimap`` is a VDXF-keyed key→array-of-values store on
every VerusID.  Each value is a typed DataDescriptor with version, flags,
label, mimetype, and objectdata.  This module builds the JSON structures
expected by ``updateidentity`` and ``signdata`` RPCs.

DataDescriptor flags reference:
    0x00 (0)  — plain data
    0x01 (1)  — has salt
    0x02 (2)  — decrypted / contains data
    0x04 (4)  — has epk (encryption public key)
    0x05 (5)  — encrypted (salt + epk)
    0x08 (8)  — has label
    0x0D (13) — encrypted + salted + epk
    0x40 (64) — has mimetype

References:
    - Bitcoin Kali NFT pattern (10 typed DataDescriptors per identity)
    - paco_message.js (custom VDXFObject with compact binary serialization)
    - verus-typescript-primitives DataDescriptor / ContentMultiMap
    - verusidx-mcp tool-specs/data.md (signdata vdxfdata object form)
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# DataDescriptor flags
# ---------------------------------------------------------------------------

DD_FLAG_HAS_SALT = 0x01
DD_FLAG_HAS_DATA = 0x02
DD_FLAG_HAS_EPK = 0x04
DD_FLAG_HAS_LABEL = 0x08
DD_FLAG_ENCRYPTED = 0x05         # salt + epk
DD_FLAG_ENCRYPTED_FULL = 0x0D    # salt + epk + label
DD_FLAG_HAS_MIMETYPE = 0x40

DD_VERSION_CURRENT = 1


# ---------------------------------------------------------------------------
# DataDescriptor Builder
# ---------------------------------------------------------------------------

class DataDescriptorBuilder:
    """
    Fluent builder for a single DataDescriptor object.

    Usage::

        desc = (DataDescriptorBuilder()
            .set_label("iK7a5JNJnbeuYWVHCDRpJosj3irGJ5Qa8c")
            .set_mimetype("text/plain")
            .set_message("Hello, Verus!")
            .build())

    The result can be placed inside a ContentMultiMapBuilder or passed
    directly to ``updateidentity`` / ``signdata``.
    """

    def __init__(self) -> None:
        self._version: int = DD_VERSION_CURRENT
        self._flags: int = 0
        self._label: Optional[str] = None
        self._mimetype: Optional[str] = None
        self._objectdata: Optional[Any] = None
        self._salt: Optional[str] = None
        self._epk: Optional[str] = None

    def set_version(self, version: int) -> "DataDescriptorBuilder":
        self._version = version
        return self

    def set_label(self, label: str) -> "DataDescriptorBuilder":
        """Set the VDXF key label (i-address or URI)."""
        self._label = label
        self._flags |= DD_FLAG_HAS_LABEL
        return self

    def set_mimetype(self, mimetype: str) -> "DataDescriptorBuilder":
        self._mimetype = mimetype
        self._flags |= DD_FLAG_HAS_MIMETYPE
        return self

    def set_message(self, message: str) -> "DataDescriptorBuilder":
        """Set objectdata as a text message (``text/plain``)."""
        self._objectdata = {"message": message}
        self._flags |= DD_FLAG_HAS_DATA
        if not self._mimetype:
            self.set_mimetype("text/plain")
        return self

    def set_objectdata_hex(self, hex_data: str) -> "DataDescriptorBuilder":
        """Set objectdata as raw hex bytes."""
        self._objectdata = hex_data
        self._flags |= DD_FLAG_HAS_DATA
        return self

    def set_objectdata_json(self, data: Any) -> "DataDescriptorBuilder":
        """Set objectdata as a JSON-serializable object (encoded as hex)."""
        json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self._objectdata = json_bytes.hex()
        self._flags |= DD_FLAG_HAS_DATA
        if not self._mimetype:
            self.set_mimetype("application/json")
        return self

    def set_hash(self, hash_hex: str) -> "DataDescriptorBuilder":
        """Set objectdata as a uint256 hash (e.g. SHA-256 of an image)."""
        self._objectdata = hash_hex
        self._flags |= DD_FLAG_HAS_DATA
        return self

    def set_salt(self, salt: str) -> "DataDescriptorBuilder":
        self._salt = salt
        self._flags |= DD_FLAG_HAS_SALT
        return self

    def set_epk(self, epk: str) -> "DataDescriptorBuilder":
        self._epk = epk
        self._flags |= DD_FLAG_HAS_EPK
        return self

    def build(self) -> Dict[str, Any]:
        """Build the DataDescriptor dict for RPC submission."""
        desc: Dict[str, Any] = {
            "version": self._version,
            "flags": self._flags,
        }
        if self._label is not None:
            desc["label"] = self._label
        if self._mimetype is not None:
            desc["mimetype"] = self._mimetype
        if self._objectdata is not None:
            desc["objectdata"] = self._objectdata
        if self._salt is not None:
            desc["salt"] = self._salt
        if self._epk is not None:
            desc["epk"] = self._epk
        return desc


# ---------------------------------------------------------------------------
# ContentMultiMap Builder
# ---------------------------------------------------------------------------

class ContentMultiMapBuilder:
    """
    Build a ``contentmultimap`` JSON structure for ``updateidentity``.

    The contentmultimap maps VDXF key i-addresses to arrays of
    DataDescriptor objects.  Matches the Bitcoin Kali pattern where
    a single series key holds an array of 10+ typed descriptors.

    Usage::

        cmm = (ContentMultiMapBuilder()
            .add_descriptor("i5mntfEpcAWot1dses5qu3hGom3y7r6VHm", name_desc)
            .add_descriptor("i5mntfEpcAWot1dses5qu3hGom3y7r6VHm", attr_desc)
            .build())

        # Use in updateidentity:
        await cli.updateidentity({"name": "MyNFT@", "contentmultimap": cmm})
    """

    def __init__(self) -> None:
        self._entries: Dict[str, List[Dict[str, Any]]] = {}

    def add_descriptor(
        self, vdxf_key: str, descriptor: Dict[str, Any]
    ) -> "ContentMultiMapBuilder":
        """Add a DataDescriptor under a VDXF key."""
        self._entries.setdefault(vdxf_key, []).append(descriptor)
        return self

    def add_raw(self, vdxf_key: str, value: str) -> "ContentMultiMapBuilder":
        """Add a raw string value under a VDXF key (legacy format)."""
        self._entries.setdefault(vdxf_key, []).append({"": value})
        return self

    def add_data_wrapper(
        self,
        vdxf_key: str,
        identity_name: str,
        file_path: str,
        label: str = "",
        mimetype: str = "application/octet-stream",
        createmmr: bool = True,
    ) -> "ContentMultiMapBuilder":
        """
        Add a data wrapper entry that triggers signdata auto-processing.

        This is the recommended Method 1 storage format — the daemon's
        ``updateidentity`` handler sees the ``data`` key and automatically
        runs ``signdata``, ``BreakApart()`` chunking, and encryption.
        """
        self._entries.setdefault(vdxf_key, []).append({
            "data": {
                "address": identity_name,
                "filename": file_path,
                "createmmr": createmmr,
                "label": label or file_path.split("/")[-1].split("\\")[-1],
                "mimetype": mimetype,
            }
        })
        return self

    def build(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return the contentmultimap dictionary."""
        return dict(self._entries)


# ---------------------------------------------------------------------------
# Identity update payload builder
# ---------------------------------------------------------------------------

def build_updateidentity_payload(
    name: str,
    content_multimap: Optional[Dict[str, Any]] = None,
    primary_addresses: Optional[List[str]] = None,
    recovery_authority: Optional[str] = None,
    revocation_authority: Optional[str] = None,
    private_address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a complete ``updateidentity`` param dict.

    Convenience wrapper that constructs the JSON expected by the
    ``updateidentity`` RPC command.
    """
    payload: Dict[str, Any] = {"name": name}
    if content_multimap:
        payload["contentmultimap"] = content_multimap
    if primary_addresses:
        payload["primaryaddresses"] = primary_addresses
    if recovery_authority:
        payload["recoveryauthority"] = recovery_authority
    if revocation_authority:
        payload["revocationauthority"] = revocation_authority
    if private_address:
        payload["privateaddress"] = private_address
    return payload


# ---------------------------------------------------------------------------
# Compact binary serialization helpers (paco_message.js pattern)
# ---------------------------------------------------------------------------

def write_varint(value: int) -> bytes:
    """Encode an integer as a Bitcoin-style CompactSize varint."""
    if value < 0xFD:
        return struct.pack("<B", value)
    elif value <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", value)
    elif value <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", value)
    else:
        return b"\xff" + struct.pack("<Q", value)


def read_varint(data: bytes, offset: int = 0) -> tuple:
    """Decode a CompactSize varint. Returns (value, new_offset)."""
    first = data[offset]
    if first < 0xFD:
        return first, offset + 1
    elif first == 0xFD:
        return struct.unpack_from("<H", data, offset + 1)[0], offset + 3
    elif first == 0xFE:
        return struct.unpack_from("<I", data, offset + 1)[0], offset + 5
    else:
        return struct.unpack_from("<Q", data, offset + 1)[0], offset + 9


def write_varslice(data: bytes) -> bytes:
    """Write a length-prefixed byte slice (CompactSize + data)."""
    return write_varint(len(data)) + data


def read_varslice(buf: bytes, offset: int = 0) -> tuple:
    """Read a length-prefixed byte slice. Returns (bytes, new_offset)."""
    length, offset = read_varint(buf, offset)
    return buf[offset:offset + length], offset + length


def compact_serialize(fields: Dict[str, Any]) -> bytes:
    """
    Compact binary serialize a dict of named fields.

    Matches the paco_message.js pattern:
      - strings → varslice (CompactSize + UTF-8 bytes)
      - lists of short strings → CompactSize count + fixed 4-byte slices
      - Other values → JSON varslice fallback

    This produces smaller on-chain payloads than raw JSON, reducing
    transaction fees.
    """
    parts: List[bytes] = []
    for key, value in fields.items():
        if isinstance(value, str):
            parts.append(write_varslice(value.encode("utf-8")))
        elif isinstance(value, list) and all(
            isinstance(v, str) and len(v) <= 4 for v in value
        ):
            # Short string list (e.g. chess moves) → CompactSize + 4-byte slices
            parts.append(write_varint(len(value)))
            for item in value:
                padded = item.encode("utf-8").ljust(4, b" ")[:4]
                parts.append(padded)
        elif isinstance(value, (int, float)):
            parts.append(write_varslice(str(value).encode("utf-8")))
        else:
            # Fallback: JSON encode
            parts.append(write_varslice(
                json.dumps(value, separators=(",", ":")).encode("utf-8")
            ))
    return b"".join(parts)


def compact_deserialize(data: bytes, field_names: List[str]) -> Dict[str, str]:
    """
    Deserialize compact binary data given ordered field names.

    Each field is read as a varslice (CompactSize + UTF-8 bytes).
    """
    result: Dict[str, str] = {}
    offset = 0
    for name in field_names:
        value_bytes, offset = read_varslice(data, offset)
        result[name] = value_bytes.decode("utf-8")
    return result


def sha256_hex(data: Union[str, bytes]) -> str:
    """Compute SHA-256 hex digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
