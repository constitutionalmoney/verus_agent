"""
Tests for Verus Agent Extension Modules

Covers: swarm_security, marketplace, ip_protection.
Uses mocks for all RPC/VerusID calls (no live daemon required).
"""

from __future__ import annotations

import json
import os
import tempfile
import hashlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from verus_agent.config import VerusConfig, VerusNetwork
from verus_agent.cli_wrapper import CLIResult, VerusCLI
from verus_agent.verusid import VerusIDManager

# Extension modules under test
from verus_agent.swarm_security import (
    VerusSwarmSecurity,
    SecurityLevel,
    AgentPermission,
)
from verus_agent.marketplace import (
    VerusAgentMarketplace,
    PricingModel,
    LicenseTier,
)
from verus_agent.ip_protection import (
    VerusIPProtection,
    ModelLicenseType,
    StorageBackend,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return VerusConfig(network=VerusNetwork.TESTNET)


@pytest.fixture
def mock_cli(config):
    cli = VerusCLI(config)
    cli._backend = "api"
    cli._daemon_version_str = "1.2.14-2"
    cli._daemon_version = 1021400
    return cli


@pytest.fixture
def mock_id_mgr(mock_cli):
    mgr = VerusIDManager(mock_cli)
    return mgr


def _mock_identity_result(success=True, txid="abc123", error=None):
    """Create a mock VerusID operation result."""
    result = MagicMock()
    result.success = success
    result.txid = txid
    result.error = error
    result.operation = "mock_op"
    return result


def _mock_identity(name="TestAgent", active=True, content_multimap=None, primary_addresses=None):
    """Create a mock VerusIdentity."""
    identity = MagicMock()
    identity.name = name
    identity.full_name = f"{name}@"
    identity.identity_address = "iTestAddr123"
    identity.status = "active" if active else "revoked"
    identity.content_multimap = content_multimap or {}
    identity.flags = 0
    identity.recovery_authority = "Controller@"
    identity.revocation_authority = "Controller@"
    identity.primary_addresses = primary_addresses or []
    return identity


# ---------------------------------------------------------------------------
# Swarm Security Tests
# ---------------------------------------------------------------------------

class TestSwarmSecurity:
    """Tests for VerusSwarmSecurity module."""

    def test_disabled_by_default(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(mock_cli, mock_id_mgr)
        assert not sec.enabled
        status = sec.get_security_status()
        assert status["enabled"] is False
        assert status["security_level"] == "disabled"

    def test_enabled_via_param(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(
            mock_cli, mock_id_mgr,
            security_level=SecurityLevel.VERIFY_ONLY,
        )
        assert sec.enabled

    @pytest.mark.asyncio
    async def test_verify_returns_synthetic_when_disabled(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(mock_cli, mock_id_mgr)
        cred = await sec.verify_agent("test_agent_1")
        assert cred is not None
        assert cred.verified is True
        assert cred.agent_id == "test_agent_1"

    @pytest.mark.asyncio
    async def test_register_agent_when_enabled(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(
            mock_cli, mock_id_mgr,
            security_level=SecurityLevel.ENFORCED,
            controller_identity="UAISwarm@",
        )

        mock_id_mgr.create_identity = AsyncMock(return_value=_mock_identity_result())

        result = await sec.register_agent(
            agent_id="worker_1",
            role="worker",
            permissions=["read", "execute"],
        )
        assert result.success is True
        assert result.txid == "abc123"
        mock_id_mgr.create_identity.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_agent_when_enabled(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(
            mock_cli, mock_id_mgr,
            security_level=SecurityLevel.VERIFY_ONLY,
            controller_identity="UAISwarm@",
        )

        mm = {
            "vrsc::uai.agent.role": [{"": "worker"}],
            "vrsc::uai.agent.permissions": [{"": "read,execute"}],
        }
        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("worker_1", active=True, content_multimap=mm)
        )

        cred = await sec.verify_agent("worker_1")
        assert cred is not None
        assert cred.verified is True
        assert cred.role == "worker"
        assert "read" in cred.permissions

    @pytest.mark.asyncio
    async def test_verify_revoked_agent_fails(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(
            mock_cli, mock_id_mgr,
            security_level=SecurityLevel.ENFORCED,
            controller_identity="UAISwarm@",
        )

        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("bad_agent", active=False)
        )

        cred = await sec.verify_agent("bad_agent")
        assert cred is None or cred.verified is False

    @pytest.mark.asyncio
    async def test_revoke_agent(self, mock_cli, mock_id_mgr):
        sec = VerusSwarmSecurity(
            mock_cli, mock_id_mgr,
            security_level=SecurityLevel.ENFORCED,
            controller_identity="UAISwarm@",
        )

        mock_id_mgr.revoke_identity = AsyncMock(return_value=_mock_identity_result())

        result = await sec.revoke_agent("bad_worker")
        assert result.success is True

    def test_permission_enum(self):
        assert AgentPermission.READ == "read"
        assert AgentPermission.ADMIN == "admin"
        assert AgentPermission.DEFI == "defi"

    def test_security_level_enum(self):
        assert SecurityLevel.DISABLED.value == "disabled"
        assert SecurityLevel.VAULT_PROTECTED.value == "vault_protected"


# ---------------------------------------------------------------------------
# Marketplace Tests
# ---------------------------------------------------------------------------

class TestMarketplace:
    """Tests for VerusAgentMarketplace module."""

    def test_disabled_by_default(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr)
        assert not mp.enabled
        status = mp.get_marketplace_status()
        assert status["enabled"] is False

    def test_enabled_via_param(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        assert mp.enabled

    @pytest.mark.asyncio
    async def test_register_product_when_disabled(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr)
        result = await mp.register_product(
            name="TestProduct",
            description="A test product",
        )
        assert result.success is False
        assert "disabled" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_register_product_when_enabled(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        mock_id_mgr.create_identity = AsyncMock(return_value=_mock_identity_result())

        result = await mp.register_product(
            name="UAIAnalytics",
            description="Real-time analytics agent",
            tier="pro",
            price_vrsc=50.0,
            capabilities=["analytics.query", "analytics.dashboard"],
        )
        assert result.success is True
        mock_id_mgr.create_identity.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_license(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        mock_id_mgr.create_identity = AsyncMock(return_value=_mock_identity_result())

        result = await mp.issue_license(
            product_identity="UAIAnalytics@",
            buyer_identity="BuyerCorp@",
            tier="starter",
            duration_days=30,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_verify_license(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)

        mm = {
            "vrsc::uai.license.tier": [{"": "pro"}],
            "vrsc::uai.license.expiry": [{"": (datetime.now() + timedelta(days=30)).isoformat()}],
            "vrsc::uai.license.owner": [{"": "BuyerCorp@"}],
        }
        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("license_abc", active=True, content_multimap=mm)
        )

        result = await mp.verify_license("license_abc@")
        assert result.success is True
        assert result.data.get("valid") is True

    @pytest.mark.asyncio
    async def test_verify_expired_license(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)

        mm = {
            "vrsc::uai.license.tier": [{"": "starter"}],
            "vrsc::uai.license.expiry": [{"": (datetime.now() - timedelta(days=1)).isoformat()}],
            "vrsc::uai.license.owner": [{"": "ExpiredBuyer@"}],
        }
        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("expired_lic", active=True, content_multimap=mm)
        )

        result = await mp.verify_license("expired_lic@")
        # Should report expired
        assert result.data.get("valid") is False or "expired" in (result.error or "").lower()

    def test_pricing_model_enum(self):
        assert PricingModel.SUBSCRIPTION == "subscription"
        assert PricingModel.PAY_PER_USE == "pay_per_use"
        assert PricingModel.STAKING == "staking"

    def test_license_tier_enum(self):
        assert LicenseTier.FREE == "free"
        assert LicenseTier.PRO == "pro"
        assert LicenseTier.ENTERPRISE == "enterprise"


# ---------------------------------------------------------------------------
# IP Protection Tests
# ---------------------------------------------------------------------------

class TestIPProtection:
    """Tests for VerusIPProtection module."""

    def test_disabled_by_default(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr)
        assert not ip.enabled
        status = ip.get_protection_status()
        assert status["enabled"] is False

    def test_enabled_via_param(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)
        assert ip.enabled

    @pytest.mark.asyncio
    async def test_register_model_when_disabled(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr)
        result = await ip.register_model(
            model_name="TestModel",
            model_file_path="/tmp/nonexistent.gguf",
        )
        assert result.success is False
        assert "disabled" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_register_model_when_enabled(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

        # Create a temp file to hash
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"fake model weights " * 100)
            tmp_path = f.name

        try:
            mock_id_mgr.create_identity = AsyncMock(return_value=_mock_identity_result())
            mock_id_mgr.sign_message = AsyncMock(return_value="sig_abc123")
            mock_id_mgr.update_identity = AsyncMock(return_value=_mock_identity_result())

            result = await ip.register_model(
                model_name="UAICode7B",
                model_file_path=tmp_path,
                architecture="llama-7b",
                owner_identity="UAICluster@",
                version="1.0.0",
                quantization="q4_k_m",
            )

            assert result.success is True
            assert result.model_identity == "UAICode7B@"
            assert result.data["model_hash"]  # Non-empty SHA-256
            assert result.data["provenance_signed"] is True
            mock_id_mgr.create_identity.assert_called_once()
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_verify_integrity_match(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

        # Create a temp file
        content = b"deterministic model content for hash test"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(content)
            tmp_path = f.name

        expected_hash = hashlib.sha256(content).hexdigest()

        try:
            mm = {
                "vrsc::uai.model.hash": [{"": expected_hash}],
                "vrsc::uai.model.owner": [{"": "Owner@"}],
                "vrsc::uai.model.name": [{"": "TestModel"}],
            }
            mock_id_mgr.get_identity = AsyncMock(
                return_value=_mock_identity("TestModel", content_multimap=mm)
            )

            check = await ip.verify_integrity("TestModel@", tmp_path)
            assert check.matches is True
            assert check.expected_hash == expected_hash
            assert check.actual_hash == expected_hash
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_verify_integrity_mismatch(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"tampered model content")
            tmp_path = f.name

        try:
            mm = {
                "vrsc::uai.model.hash": [{"": "0000000000000000000000000000000000000000000000000000000000000000"}],
            }
            mock_id_mgr.get_identity = AsyncMock(
                return_value=_mock_identity("Tampered", content_multimap=mm)
            )

            check = await ip.verify_integrity("Tampered@", tmp_path)
            assert check.matches is False
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_register_storage_reference(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)
        mock_id_mgr.update_identity = AsyncMock(return_value=_mock_identity_result())

        result = await ip.register_storage_reference(
            model_identity="UAICode7B@",
            url="ipfs://QmXyz123abc",
            backend=StorageBackend.IPFS,
            data_hash="abc123",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_store_encrypted_key(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)
        mock_id_mgr.update_identity = AsyncMock(return_value=_mock_identity_result())

        result = await ip.store_encrypted_key(
            model_identity="UAICode7B@",
            encrypted_key_b64="base64EncodedEncryptedKey==",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_model_info(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

        mm = {
            "vrsc::uai.model.name": [{"": "UAICode7B"}],
            "vrsc::uai.model.version": [{"": "1.0.0"}],
            "vrsc::uai.model.hash": [{"": "abc123hash"}],
            "vrsc::uai.model.arch": [{"": "llama-7b"}],
            "vrsc::uai.model.license": [{"": "proprietary"}],
            "vrsc::uai.model.owner": [{"": "UAICluster@"}],
            "vrsc::uai.model.size": [{"": "4000000000"}],
            "vrsc::uai.model.quantization": [{"": "q4_k_m"}],
        }
        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("UAICode7B", content_multimap=mm)
        )

        info = await ip.get_model_info("UAICode7B@")
        assert info is not None
        assert info.name == "UAICode7B"
        assert info.architecture == "llama-7b"
        assert info.size_bytes == 4000000000
        assert info.license_type == ModelLicenseType.PROPRIETARY

    @pytest.mark.asyncio
    async def test_register_watermark(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)
        mock_id_mgr.update_identity = AsyncMock(return_value=_mock_identity_result())

        result = await ip.register_watermark(
            model_identity="UAICode7B@",
            buyer_identity="Buyer123@",
            watermark_hash="wm_hash_abc",
        )
        assert result.success is True
        assert result.data["buyer"] == "Buyer123@"

    def test_model_license_type_enum(self):
        assert ModelLicenseType.PROPRIETARY == "proprietary"
        assert ModelLicenseType.OPEN_SOURCE == "open_source"

    def test_storage_backend_enum(self):
        assert StorageBackend.IPFS == "ipfs"
        assert StorageBackend.ARWEAVE == "arweave"
        assert StorageBackend.R2 == "r2"

    def test_human_size(self):
        assert "1.0 KB" == VerusIPProtection._human_size(1024)
        assert "1.0 GB" == VerusIPProtection._human_size(1024 ** 3)


# ==========================================================================
# Phase 4 Tests: AES-256-GCM Encryption
# ==========================================================================

class TestIPProtectionEncryption:
    """Tests for the AES-256-GCM model encryption pipeline."""

    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock(spec=VerusCLI)
        cli.call = AsyncMock(return_value=CLIResult(result="ok", error=None))
        return cli

    @pytest.fixture
    def mock_id_mgr(self):
        mgr = MagicMock(spec=VerusIDManager)
        mgr.create_identity = AsyncMock(return_value=_mock_identity_result())
        mgr.update_identity = AsyncMock(return_value=_mock_identity_result())
        mgr.sign_message = AsyncMock(return_value="sig_test")
        return mgr

    @pytest.mark.asyncio
    async def test_encrypt_disabled(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=False)
        result = await ip.encrypt_model_file("/fake/model.bin")
        assert result.success is False
        assert "disabled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_encrypt_file_not_found(self, mock_cli, mock_id_mgr):
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)
        result = await ip.encrypt_model_file("/nonexistent/model.bin")
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip(self, mock_cli, mock_id_mgr):
        """Full encrypt → decrypt → verify roundtrip."""
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

        original_data = b"test model weights " * 500
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(original_data)
            original_path = f.name

        enc_path = original_path + ".enc"
        dec_path = original_path + ".dec"

        try:
            # Encrypt
            enc_result = await ip.encrypt_model_file(original_path, enc_path)

            # Check if cryptography lib is available
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
            except ImportError:
                pytest.skip("cryptography package not installed")

            assert enc_result.success is True
            assert enc_result.data["aes_key_b64"]
            assert enc_result.data["encrypted_path"] == enc_path
            assert enc_result.data["original_hash"]
            assert os.path.isfile(enc_path)

            # Decrypt
            dec_result = await ip.decrypt_model_file(
                enc_path, dec_path, enc_result.data["aes_key_b64"]
            )
            assert dec_result.success is True

            # Verify content matches
            with open(dec_path, "rb") as f:
                decrypted_data = f.read()
            assert decrypted_data == original_data

            # Verify hash matches
            original_hash = hashlib.sha256(original_data).hexdigest()
            assert dec_result.data["decrypted_hash"] == original_hash

        finally:
            for p in [original_path, enc_path, dec_path]:
                if os.path.isfile(p):
                    os.unlink(p)

    @pytest.mark.asyncio
    async def test_decrypt_wrong_key(self, mock_cli, mock_id_mgr):
        """Decryption with wrong key should fail."""
        ip = VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        except ImportError:
            pytest.skip("cryptography package not installed")

        original_data = b"secret model data"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(original_data)
            original_path = f.name

        enc_path = original_path + ".enc"
        dec_path = original_path + ".dec"

        try:
            enc_result = await ip.encrypt_model_file(original_path, enc_path)
            assert enc_result.success is True

            # Use a different (wrong) key
            import base64
            wrong_key = base64.b64encode(os.urandom(32)).decode()

            dec_result = await ip.decrypt_model_file(enc_path, dec_path, wrong_key)
            assert dec_result.success is False
            assert "wrong key" in dec_result.error.lower() or "tampered" in dec_result.error.lower()

        finally:
            for p in [original_path, enc_path, dec_path]:
                if os.path.isfile(p):
                    os.unlink(p)


# ==========================================================================
# Phase 4 Tests: VerusPay Invoice + Bulk Discovery
# ==========================================================================

class TestMarketplaceInvoiceDiscovery:
    """Tests for VerusPay invoice creation and bulk product discovery."""

    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock(spec=VerusCLI)
        cli.call = AsyncMock(return_value=CLIResult(result="ok", error=None))
        cli.veruspay_createinvoice = AsyncMock(
            return_value={"invoiceid": "inv_123", "txid": "tx_abc"}
        )
        cli.listidentities = AsyncMock(return_value=[])
        return cli

    @pytest.fixture
    def mock_id_mgr(self):
        mgr = MagicMock(spec=VerusIDManager)
        mgr.update_identity = AsyncMock(return_value=_mock_identity_result())
        return mgr

    @pytest.mark.asyncio
    async def test_create_invoice_disabled(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=False)
        result = await mp.create_invoice("Product@", 10.0)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_create_invoice_success(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        result = await mp.create_invoice(
            product_identity="UAITranslator@",
            amount=5.0,
            currency="VRSC",
            buyer_identity="Alice@",
        )
        assert result.success is True
        assert result.data["amount"] == 5.0
        assert result.data["invoice_id"] == "inv_123"

    @pytest.mark.asyncio
    async def test_create_invoice_fallback(self, mock_cli, mock_id_mgr):
        """When createinvoice RPC fails, fallback to on-chain memo."""
        mock_cli.veruspay_createinvoice = AsyncMock(
            side_effect=Exception("RPC unavailable")
        )
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        result = await mp.create_invoice("Product@", 2.5)
        assert result.success is True
        assert result.data.get("fallback") is True

    @pytest.mark.asyncio
    async def test_discover_products_empty(self, mock_cli, mock_id_mgr):
        mock_cli.listidentities = AsyncMock(return_value=[])
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        products = await mp.discover_products()
        assert products == []

    @pytest.mark.asyncio
    async def test_discover_products_filters(self, mock_cli, mock_id_mgr):
        """Products without the VDXF marker key should be filtered out."""
        mock_cli.listidentities = AsyncMock(return_value=[
            {"identity": {"name": "uai.translator", "contentmultimap": {
                "vrsc::uai.product.name": [{"": "UAI Translator"}],
            }}},
            {"identity": {"name": "randomid", "contentmultimap": {}}},
        ])
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        products = await mp.discover_products()
        assert len(products) == 1
        assert products[0].name == "UAI Translator"

    @pytest.mark.asyncio
    async def test_search_products(self, mock_cli, mock_id_mgr):
        mp = VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)
        # Manually populate cache
        from verus_agent.marketplace import AgentProduct, PricingModel
        mp._product_cache["A@"] = AgentProduct(
            product_identity="A@", name="Alpha", description="Translation service",
            version="1.0", capabilities=["translate"], pricing_model=PricingModel.FREE,
            price="0", owner_identity="Owner@",
        )
        mp._product_cache["B@"] = AgentProduct(
            product_identity="B@", name="Beta", description="Code review",
            version="1.0", capabilities=["review"], pricing_model=PricingModel.FREE,
            price="0", owner_identity="Owner@",
        )
        results = await mp.search_products("translate")
        assert len(results) == 1
        assert results[0].name == "Alpha"


# ==========================================================================
# Phase 4 Tests: Reputation System
# ==========================================================================

class TestReputationSystem:
    """Tests for the VerusID-backed reputation/attestation system."""

    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock(spec=VerusCLI)
        cli.call = AsyncMock(return_value=CLIResult(result="ok", error=None))
        cli.z_getbalance = AsyncMock(return_value=100.0)
        return cli

    @pytest.fixture
    def mock_id_mgr(self):
        mgr = MagicMock(spec=VerusIDManager)
        mgr.sign_message = AsyncMock(return_value="sig_rep_123")
        mgr.update_identity = AsyncMock(return_value=_mock_identity_result())
        mgr.get_identity = AsyncMock(return_value=_mock_identity("Agent"))
        mgr.verify_message = AsyncMock(return_value=True)
        return mgr

    @pytest.mark.asyncio
    async def test_attest_disabled(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem
        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=False)
        result = await rep.attest("Alice@", "Agent@", 80)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_attest_success(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem, AttestationCategory
        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=True)

        result = await rep.attest(
            attestor="Alice@",
            target="UAITranslator@",
            rating=85,
            category=AttestationCategory.QUALITY,
            comment="Great output quality",
        )
        assert result.success is True
        assert result.data["rating"] == 85
        assert result.data["category"] == "quality"
        mock_id_mgr.sign_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_reputation(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem, AttestationCategory
        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=True)

        # Issue multiple attestations
        for r in [80, 90, 85]:
            await rep.attest("Reviewer@", "Agent@", r, AttestationCategory.QUALITY)

        score = await rep.get_reputation("Agent@")
        assert score.overall_score > 0
        assert score.total_attestations == 3
        assert "quality" in score.category_scores
        assert score.confidence > 0

    @pytest.mark.asyncio
    async def test_get_reputation_empty(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem
        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=True)

        # No attestations in contentmultimap
        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("Empty", content_multimap={})
        )
        score = await rep.get_reputation("Empty@")
        assert score.overall_score == 0.0
        assert score.total_attestations == 0
        assert score.confidence == 0.0

    @pytest.mark.asyncio
    async def test_leaderboard(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem, AttestationCategory
        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=True)

        # Build some scores
        await rep.attest("R@", "A@", 90, AttestationCategory.OVERALL)
        await rep.attest("R@", "B@", 70, AttestationCategory.OVERALL)
        await rep.attest("R@", "C@", 95, AttestationCategory.OVERALL)

        await rep.get_reputation("A@")
        await rep.get_reputation("B@")
        await rep.get_reputation("C@")

        board = await rep.get_leaderboard(limit=2)
        assert len(board) == 2
        assert board[0].overall_score >= board[1].overall_score

    @pytest.mark.asyncio
    async def test_stake_weight(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem

        mock_id_mgr.get_identity = AsyncMock(
            return_value=_mock_identity("Staker", primary_addresses=["R_addr1"])
        )
        mock_cli.z_getbalance = AsyncMock(return_value=10000.0)

        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=True)
        weight = await rep.update_stake_weight("Staker@")
        assert weight > 1.0  # Should have a bonus from 10K VRSC

    def test_reputation_status(self, mock_cli, mock_id_mgr):
        from verus_agent.reputation import VerusReputationSystem
        rep = VerusReputationSystem(mock_cli, mock_id_mgr, enabled=True)
        status = rep.get_reputation_status()
        assert status["enabled"] is True
        assert status["tracked_agents"] == 0


# ==========================================================================
# Phase 4b Tests — PBaaS, Cross-chain, Watermark, Mobile
# ==========================================================================


class TestPBaaSChain:
    """Tests for define_uai_pbaas_chain in defi.py."""

    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock()
        cli.execute = AsyncMock(return_value={"result": {"txid": "pbaas_txid_001"}})
        return cli

    @pytest.fixture
    def defi(self, mock_cli):
        from verus_agent.defi import VerusDeFiManager
        return VerusDeFiManager(mock_cli)

    @pytest.mark.asyncio
    async def test_define_pbaas_chain_defaults(self, defi, mock_cli):
        result = await defi.define_uai_pbaas_chain(
            chain_name="UAITestChain",
            controller_identity="Controller@",
        )
        assert result.success is True
        # Verify definecurrency was called
        mock_cli.execute.assert_called_once()
        call_args = mock_cli.execute.call_args
        assert call_args[0][0] == "definecurrency"
        defn = json.loads(call_args[0][1])
        assert defn["name"] == "UAITestChain"
        # Options: 256 (PBAAS) + 16384 (ID_ISSUANCE) + 32768 (ID_REFERRALS)
        assert defn["options"] == 256 + 16384 + 32768
        assert defn["idregistrationfees"] == 10.0
        assert defn["idreferrallevels"] == 3

    @pytest.mark.asyncio
    async def test_define_pbaas_chain_custom_fees(self, defi, mock_cli):
        result = await defi.define_uai_pbaas_chain(
            chain_name="CustomChain",
            controller_identity="Admin@",
            id_registration_fees=25.0,
            id_referral_levels=5,
            block_time=30,
            initial_supply=1000000.0,
        )
        assert result.success is True
        defn = json.loads(mock_cli.execute.call_args[0][1])
        assert defn["idregistrationfees"] == 25.0
        assert defn["idreferrallevels"] == 5
        assert defn["blocktime"] == 30

    @pytest.mark.asyncio
    async def test_get_pbaas_chain_info(self, defi, mock_cli):
        mock_cli.execute = AsyncMock(return_value={"result": {"name": "UAITestChain", "currencyid": "iXYZ"}})
        result = await defi.get_pbaas_chain_info("UAITestChain")
        assert result["name"] == "UAITestChain"


class TestCrossChainLicense:
    """Tests for verify_license_cross_chain in marketplace.py."""

    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock()
        return cli

    @pytest.fixture
    def mock_id_mgr(self):
        return MagicMock()

    @pytest.fixture
    def marketplace(self, mock_cli, mock_id_mgr):
        from verus_agent.marketplace import VerusAgentMarketplace
        return VerusAgentMarketplace(mock_cli, mock_id_mgr, enabled=True)

    @pytest.mark.asyncio
    async def test_cross_chain_valid(self, marketplace, mock_cli):
        mock_cli.execute = AsyncMock(return_value={
            "result": {
                "identity": {
                    "name": "buyer.Agent",
                    "flags": 0,
                    "contentmultimap": {
                        "vrsc::uai.license.tier": [{"": "professional"}],
                        "vrsc::uai.license.expiry": [{"": "2099-12-31T00:00:00"}],
                    },
                },
            },
        })

        lic = await marketplace.verify_license_cross_chain(
            "buyer.Agent@", source_chain="UAIChain",
        )
        assert lic is not None
        assert lic.valid is True
        assert lic.tier == "professional"
        assert lic.raw.get("cross_chain") is True

    @pytest.mark.asyncio
    async def test_cross_chain_not_found(self, marketplace, mock_cli):
        mock_cli.execute = AsyncMock(return_value={"result": None})
        lic = await marketplace.verify_license_cross_chain(
            "missing@", source_chain="VRSC",
        )
        assert lic is None

    @pytest.mark.asyncio
    async def test_cross_chain_revoked(self, marketplace, mock_cli):
        mock_cli.execute = AsyncMock(return_value={
            "result": {
                "identity": {
                    "name": "buyer.Agent",
                    "flags": 8,  # IDENTITY_FLAG_REVOKED
                    "contentmultimap": {},
                },
            },
        })

        lic = await marketplace.verify_license_cross_chain(
            "buyer.Agent@", source_chain="VRSC",
        )
        assert lic is None


class TestLoRAWatermark:
    """Tests for generate_buyer_watermark / verify_watermark in ip_protection.py."""

    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock()
        cli.execute = AsyncMock(return_value={"result": {"txid": "wm_txid_001"}})
        return cli

    @pytest.fixture
    def mock_id_mgr(self):
        mgr = MagicMock()
        mgr.update_identity = AsyncMock(return_value=MagicMock(
            success=True, txid="wm_txid_001",
        ))
        return mgr

    @pytest.fixture
    def ip(self, mock_cli, mock_id_mgr):
        from verus_agent.ip_protection import VerusIPProtection
        return VerusIPProtection(mock_cli, mock_id_mgr, enabled=True)

    @pytest.mark.asyncio
    async def test_byte_watermark_creates_file(self, ip):
        """Byte watermark fallback should create a different file hash."""
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(os.urandom(10000))
            model_path = f.name

        try:
            result = await ip.generate_buyer_watermark(
                model_identity="TestModel@",
                buyer_identity="Buyer1@",
                model_file_path=model_path,
            )
            assert result.success is True
            assert result.data["method"] == "byte_perturbation"
            assert result.data["original_hash"] != result.data["watermarked_hash"]
            assert os.path.isfile(result.data["watermarked_path"])

            # Cleanup watermarked file
            os.unlink(result.data["watermarked_path"])
        finally:
            os.unlink(model_path)

    @pytest.mark.asyncio
    async def test_watermark_deterministic(self, ip, mock_id_mgr):
        """Same buyer + model should produce the same watermark seed."""
        mock_id_mgr.update_identity = AsyncMock(return_value=MagicMock(
            success=True, txid="wm_txid_002",
        ))

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\x00" * 10000)
            model_path = f.name

        try:
            r1 = await ip.generate_buyer_watermark(
                "Model@", "BuyerA@", model_path,
                output_path=model_path + ".wm1",
            )
            r2 = await ip.generate_buyer_watermark(
                "Model@", "BuyerA@", model_path,
                output_path=model_path + ".wm2",
            )
            assert r1.data["seed_preview"] == r2.data["seed_preview"]
            assert r1.data["watermarked_hash"] == r2.data["watermarked_hash"]

            os.unlink(model_path + ".wm1")
            os.unlink(model_path + ".wm2")
        finally:
            os.unlink(model_path)

    @pytest.mark.asyncio
    async def test_watermark_different_buyers(self, ip, mock_id_mgr):
        """Different buyers should produce different watermarks."""
        mock_id_mgr.update_identity = AsyncMock(return_value=MagicMock(
            success=True, txid="wm_txid_003",
        ))

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"\xFF" * 10000)
            model_path = f.name

        try:
            r1 = await ip.generate_buyer_watermark(
                "Model@", "Alpha@", model_path,
                output_path=model_path + ".a",
            )
            r2 = await ip.generate_buyer_watermark(
                "Model@", "Beta@", model_path,
                output_path=model_path + ".b",
            )
            assert r1.data["watermarked_hash"] != r2.data["watermarked_hash"]

            os.unlink(model_path + ".a")
            os.unlink(model_path + ".b")
        finally:
            os.unlink(model_path)

    @pytest.mark.asyncio
    async def test_watermark_file_not_found(self, ip):
        result = await ip.generate_buyer_watermark(
            "Model@", "Buyer@", "/nonexistent/model.bin",
        )
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_watermark_disabled(self):
        from verus_agent.ip_protection import VerusIPProtection
        ip = VerusIPProtection(MagicMock(), MagicMock(), enabled=False)
        result = await ip.generate_buyer_watermark(
            "Model@", "Buyer@", "/tmp/fake.bin",
        )
        assert result.success is False
        assert "disabled" in result.error


class TestMobileWallet:
    """Tests for VerusMobileHelper."""

    @pytest.fixture
    def helper(self):
        from verus_agent.mobile import VerusMobileHelper
        return VerusMobileHelper(agent_identity="TestAgent@")

    def test_payment_uri_basic(self, helper):
        pay = helper.generate_payment_uri(
            destination="Recipient@",
            amount=10.5,
            currency="VRSC",
        )
        assert pay.uri.startswith("vrsc:Recipient%40")
        assert "amount=10.50000000" in pay.uri
        assert pay.address == "Recipient@"

    def test_payment_uri_custom_currency(self, helper):
        pay = helper.generate_payment_uri(
            destination="R9abc",
            amount=100.0,
            currency="tBTC.vETH",
            label="Payment for AI service",
        )
        assert "currency=tBTC.vETH" in pay.uri
        assert "label=Payment" in pay.uri

    def test_payment_uri_defaults_to_agent(self, helper):
        pay = helper.generate_payment_uri(amount=1.0)
        assert "TestAgent" in pay.uri

    def test_login_consent(self, helper):
        consent = helper.generate_login_consent(
            redirect_uri="https://myapp.com/callback",
            requested_access=["identity.read"],
            expires_seconds=600,
        )
        assert len(consent.challenge_id) == 32  # 16 bytes hex
        assert consent.agent_identity == "TestAgent@"
        assert "vrsc::system.identity.loginconsent.request" in consent.qr_data
        payload = json.loads(consent.qr_data)
        inner = payload["vrsc::system.identity.loginconsent.request"]
        assert inner["signing_id"] == "TestAgent@"
        assert inner["challenge"]["requested_access"] == ["identity.read"]

    def test_purchase_link(self, helper):
        result = helper.generate_purchase_link(
            product_identity="UAICodeHelper@",
            tier="professional",
            price=50.0,
        )
        assert result.success is True
        assert "UAICodeHelper" in result.uri
        assert result.data["tier"] == "professional"
        assert result.data["price"] == 50.0

    def test_purchase_link_no_product(self, helper):
        result = helper.generate_purchase_link(product_identity="")
        assert result.success is False

    def test_license_activation(self, helper):
        result = helper.generate_license_activation_link(
            license_identity="buyer.UAICode@",
        )
        assert result.success is True
        assert "buyer.UAICode" in result.uri
        assert len(result.data["activation_code"]) == 16  # 8 bytes hex

    def test_model_access_qr(self, helper):
        result = helper.generate_model_access_qr(
            model_identity="MyModel@",
            buyer_identity="Buyer@",
            endpoint="https://api.example.com/v1/infer",
        )
        assert result.success is True
        payload = json.loads(result.qr_data)
        assert payload["uai_model_access"] is True
        assert payload["model"] == "MyModel@"
        assert payload["endpoint"] == "https://api.example.com/v1/infer"

    def test_qr_base64_roundtrip(self, helper):
        original = '{"test": true}'
        encoded = helper.encode_qr_base64(original)
        decoded = helper.decode_qr_base64(encoded)
        assert decoded == original
