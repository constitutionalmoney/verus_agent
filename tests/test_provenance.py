"""
Tests for provenance.py and vdxf_builder.py

Covers: DataDescriptorBuilder, ContentMultiMapBuilder, compact binary
serialization, VerusProvenanceManager orchestration.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from verus_agent.vdxf_builder import (
    ContentMultiMapBuilder,
    DataDescriptorBuilder,
    build_updateidentity_payload,
    compact_serialize,
    compact_deserialize,
    write_varint,
    read_varint,
    write_varslice,
    read_varslice,
    sha256_hex,
)
from verus_agent.provenance import (
    ProvenanceResult,
    VerusProvenanceManager,
    build_provenance_descriptor,
    PROVENANCE_LABELS,
)


# ---------------------------------------------------------------------------
# VDXF Builder unit tests
# ---------------------------------------------------------------------------

class TestDataDescriptorBuilder:
    def test_basic_message(self):
        desc = (DataDescriptorBuilder()
                .set_label("name")
                .set_message("My Artwork")
                .build())
        assert desc["label"] == "name"
        assert desc["objectdata"]["message"] == "My Artwork"
        assert desc["version"] == 1

    def test_json_objectdata(self):
        payload = {"medium": "digital", "year": 2024}
        desc = (DataDescriptorBuilder()
                .set_label("attributes")
                .set_mimetype("application/json")
                .set_objectdata_json(payload)
                .build())
        assert desc["mimetype"] == "application/json"
        # objectdata is hex-encoded JSON bytes
        import json
        decoded = bytes.fromhex(desc["objectdata"]).decode("utf-8")
        assert json.loads(decoded) == payload
        assert desc["flags"] & 0x40  # HAS_MIMETYPE

    def test_hex_objectdata(self):
        desc = (DataDescriptorBuilder()
                .set_objectdata_hex("deadbeef")
                .build())
        # objectdata stored as raw hex string
        assert desc["objectdata"] == "deadbeef"

    def test_hash_and_salt(self):
        desc = (DataDescriptorBuilder()
                .set_hash("abc123")
                .set_salt("salt456")
                .build())
        # set_hash stores the hash as the objectdata string
        assert desc["objectdata"] == "abc123"
        assert desc["salt"] == "salt456"
        assert desc["flags"] & 0x01  # HAS_SALT

    def test_epk_sets_flag(self):
        desc = (DataDescriptorBuilder()
                .set_epk("ephemeral_public_key")
                .build())
        assert desc["epk"] == "ephemeral_public_key"
        assert desc["flags"] & 0x04  # HAS_EPK

    def test_chaining(self):
        """Builder supports method chaining."""
        desc = (DataDescriptorBuilder()
                .set_label("test")
                .set_mimetype("text/plain")
                .set_message("hello")
                .set_salt("s")
                .set_epk("e")
                .build())
        assert desc["label"] == "test"
        assert desc["mimetype"] == "text/plain"
        # set_message stores {"message": ...} dict as objectdata
        assert desc["objectdata"] == {"message": "hello"}


class TestContentMultiMapBuilder:
    def test_single_descriptor(self):
        desc = DataDescriptorBuilder().set_message("test").build()
        cmm = ContentMultiMapBuilder().add_descriptor("iKey123", desc).build()
        assert "iKey123" in cmm
        assert len(cmm["iKey123"]) == 1

    def test_multiple_descriptors_same_key(self):
        d1 = DataDescriptorBuilder().set_message("first").build()
        d2 = DataDescriptorBuilder().set_message("second").build()
        cmm = (ContentMultiMapBuilder()
               .add_descriptor("iKey", d1)
               .add_descriptor("iKey", d2)
               .build())
        assert len(cmm["iKey"]) == 2

    def test_raw_entry(self):
        # add_raw wraps the value in {"":  value}
        cmm = (ContentMultiMapBuilder()
               .add_raw("iOther", "raw_hex_data")
               .build())
        assert cmm["iOther"] == [{"": "raw_hex_data"}]

    def test_data_wrapper(self):
        cmm = (ContentMultiMapBuilder()
               .add_data_wrapper("iKey", "Agent@", "/tmp/file.bin")
               .build())
        entry = cmm["iKey"][0]
        assert "data" in entry
        assert entry["data"]["filename"] == "/tmp/file.bin"


class TestBuildUpdateIdentityPayload:
    def test_basic_payload(self):
        cmm = {"iKey": [{"": "data"}]}
        payload = build_updateidentity_payload("TestID@", content_multimap=cmm)
        assert payload["name"] == "TestID@"
        assert payload["contentmultimap"] == cmm

    def test_with_primary_addresses(self):
        payload = build_updateidentity_payload(
            "TestID@",
            primary_addresses=["RAddr1"],
        )
        assert payload["primaryaddresses"] == ["RAddr1"]

    def test_empty_multimap(self):
        payload = build_updateidentity_payload("TestID@")
        assert "contentmultimap" not in payload


# ---------------------------------------------------------------------------
# Compact binary serialization tests
# ---------------------------------------------------------------------------

class TestCompactSerialization:
    def test_varint_small(self):
        buf = write_varint(42)
        val, offset = read_varint(buf, 0)
        assert val == 42
        assert offset == 1

    def test_varint_medium(self):
        buf = write_varint(300)
        val, offset = read_varint(buf, 0)
        assert val == 300

    def test_varint_large(self):
        buf = write_varint(70000)
        val, offset = read_varint(buf, 0)
        assert val == 70000

    def test_varslice_roundtrip(self):
        data = b"hello world"
        encoded = write_varslice(data)
        decoded, offset = read_varslice(encoded, 0)
        assert decoded == data

    def test_compact_serialize_roundtrip(self):
        fields = {"a": "first", "b": "second", "c": "third"}
        serialized = compact_serialize(fields)
        deserialized = compact_deserialize(serialized, ["a", "b", "c"])
        assert deserialized == {"a": "first", "b": "second", "c": "third"}

    def test_sha256_hex(self):
        h = sha256_hex(b"test")
        assert len(h) == 64
        assert h == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------

class TestProvenanceHelpers:
    def test_provenance_labels(self):
        assert "name" in PROVENANCE_LABELS
        assert "mmrroot" in PROVENANCE_LABELS
        assert "delivery" in PROVENANCE_LABELS
        assert len(PROVENANCE_LABELS) == 10

    def test_build_provenance_descriptor_string(self):
        desc = build_provenance_descriptor("name", "My NFT")
        assert desc["label"] == "name"
        assert desc["objectdata"]["message"] == "My NFT"

    def test_build_provenance_descriptor_dict(self):
        import json as _json
        desc = build_provenance_descriptor(
            "attributes", {"medium": "digital"}, mimetype="application/json"
        )
        # Dict values are hex-encoded JSON
        decoded = bytes.fromhex(desc["objectdata"]).decode("utf-8")
        assert _json.loads(decoded) == {"medium": "digital"}

    def test_provenance_result_to_dict(self):
        r = ProvenanceResult(operation="test", success=True, txid="abc")
        d = r.to_dict()
        assert d["operation"] == "test"
        assert d["success"] is True
        assert d["txid"] == "abc"


# ---------------------------------------------------------------------------
# VerusProvenanceManager tests (mocked)
# ---------------------------------------------------------------------------

class TestVerusProvenanceManager:
    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock()
        cli.call = AsyncMock()
        cli.updateidentity = AsyncMock(return_value="tx_abc")
        cli.getidentity = AsyncMock(return_value={
            "identity": {
                "name": "TestNFT",
                "contentmultimap": {},
            }
        })
        return cli

    @pytest.fixture
    def mock_id_mgr(self):
        mgr = MagicMock()
        result = MagicMock()
        result.success = True
        result.txid = "commit_tx_123"
        result.error = None
        result.data = {"name": "TestNFT"}
        mgr.create_identity = AsyncMock(return_value=result)
        return mgr

    @pytest.fixture
    def mock_storage(self):
        return MagicMock()

    @pytest.fixture
    def provenance(self, mock_cli, mock_id_mgr, mock_storage):
        return VerusProvenanceManager(mock_cli, mock_id_mgr, mock_storage)

    @pytest.mark.asyncio
    async def test_create_nft_identity(self, provenance):
        result = await provenance.create_nft_identity(
            name="TestNFT",
            primary_addresses=["RAddr1"],
        )
        assert result["success"] is True
        assert result["operation"] == "create_nft_identity"

    @pytest.mark.asyncio
    async def test_store_typed_descriptors(self, provenance, mock_cli):
        result = await provenance.store_typed_descriptors(
            identity_name="TestNFT@",
            series_key="iSeriesKey123",
            descriptors=[
                {"label": "name", "value": "My Artwork"},
                {"label": "description", "value": "A digital masterpiece"},
            ],
        )
        assert result["success"] is True
        assert result["data"]["descriptor_count"] == 2
        mock_cli.updateidentity.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_provenance_mmr(self, provenance, mock_cli):
        mock_cli.call.return_value = MagicMock(result={
            "mmrroot": "root_hash_123",
            "signature": "sig_base64",
            "hashes": ["h1", "h2"],
            "identity": "curator@",
            "signatureheight": 50000,
        })

        result = await provenance.sign_provenance_mmr(
            signing_identity="curator@",
            data_leaves=[
                {"message": "My Artwork"},
                {"datahash": "abc123"},
            ],
        )
        assert result["success"] is True
        assert result["data"]["mmrroot"] == "root_hash_123"
        assert result["data"]["signature"] == "sig_base64"

    @pytest.mark.asyncio
    async def test_verify_provenance_no_content(self, provenance, mock_cli):
        mock_cli.getidentity = AsyncMock(return_value={
            "identity": {
                "name": "TestNFT",
                "contentmultimap": {},
            }
        })

        result = await provenance.verify_provenance(
            identity_name="TestNFT@",
            curator_identity="curator@",
        )
        # No content → signature not verified
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_list_for_marketplace(self, provenance, mock_cli):
        mock_cli.call.return_value = MagicMock(result="offer_tx_789")

        result = await provenance.list_for_marketplace(
            identity_name="TestNFT@",
            price=258,
            currency="VRSC",
            for_address="Verus Coin Foundation@",
        )
        assert result["success"] is True
        assert result["data"]["price"] == 258
        assert result["data"]["for_address"] == "Verus Coin Foundation@"

    @pytest.mark.asyncio
    async def test_encrypted_file_delivery_no_input(self, provenance):
        result = await provenance.encrypted_file_delivery(
            from_address="curator@",
            z_address="zs1test...",
        )
        assert result["success"] is False
        assert "file_path or data" in result["error"]

    @pytest.mark.asyncio
    async def test_encrypted_file_delivery_with_data(self, provenance, mock_cli):
        mock_cli.call.return_value = MagicMock(result="opid-123")

        result = await provenance.encrypted_file_delivery(
            from_address="curator@",
            z_address="zs1test...",
            data=b"image data bytes",
        )
        assert result["success"] is True
        assert result["data"]["opid"] == "opid-123"
        assert result["data"]["size_bytes"] == 16

    @pytest.mark.asyncio
    async def test_publish_viewing_key(self, provenance, mock_cli):
        mock_cli.call.return_value = MagicMock(result="zxviews1testevk...")

        result = await provenance.publish_viewing_key(
            identity_name="TestNFT@",
            z_address="zs1test...",
            series_key="iSeriesKey",
        )
        assert result["success"] is True
        assert "evk" in result["data"]
