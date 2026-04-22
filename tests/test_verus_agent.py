"""
Tests for the Verus Blockchain Specialist Agent

Covers: config, CLI wrapper, VerusID, DeFi, Login, Storage, and main agent.
Uses mocks for all RPC calls (no live daemon required).
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------
from verus_agent.config import (
    AGENT_CAPABILITIES,
    AGENT_ID,
    API_ENDPOINTS,
    REFERENCE_LIBRARIES,
    VerusConfig,
    VerusNetwork,
)
from verus_agent.cli_wrapper import (
    CLIResult,
    VerusAPIError,
    VerusCLI,
)
from verus_agent.verusid import VerusIDManager
from verus_agent.defi import VerusDeFiManager, ConversionEstimate
from verus_agent.login import VerusLoginManager
from verus_agent.storage import VerusStorageManager
from verus_agent.agent import (
    VerusBlockchainAgent,
    VerusAgentState,
    VerusSpecialization,
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


def make_cli_result(method: str, result: Any) -> CLIResult:
    return CLIResult(method=method, params=[], result=result, elapsed_ms=5.0)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestVerusConfig:
    def test_default_is_testnet(self):
        cfg = VerusConfig()
        assert cfg.network == VerusNetwork.TESTNET
        assert cfg.api_url == API_ENDPOINTS[VerusNetwork.TESTNET]
        assert cfg.is_testnet
        assert not cfg.is_mainnet

    def test_mainnet_config(self):
        cfg = VerusConfig(network=VerusNetwork.MAINNET)
        assert cfg.is_mainnet
        assert cfg.api_url == API_ENDPOINTS[VerusNetwork.MAINNET]

    def test_agent_id(self):
        cfg = VerusConfig()
        assert cfg.agent_id == AGENT_ID

    def test_uai_integration_default_enabled(self):
        cfg = VerusConfig()
        assert cfg.uai_integration_enabled is True

    def test_uai_integration_env_override(self, monkeypatch):
        monkeypatch.setenv("VERUS_UAI_INTEGRATION_ENABLED", "false")
        cfg = VerusConfig()
        assert cfg.uai_integration_enabled is False

    def test_capabilities_count(self):
        # there used to be exactly 14 core capabilities; allow new ones to
        # accumulate without breaking the test (only a lower bound is
        # required for validation).
        assert len(AGENT_CAPABILITIES) >= 14

    def test_primitives_reference_uses_canonical_upstream(self):
        assert REFERENCE_LIBRARIES["verus_typescript_primitives"]["github"] == (
            "https://github.com/VerusCoin/verus-typescript-primitives"
        )


# ---------------------------------------------------------------------------
# CLI wrapper tests
# ---------------------------------------------------------------------------

class TestVerusCLI:
    def test_backend_defaults_to_api(self, config):
        cli = VerusCLI(config)
        assert cli._backend == "api"

    @pytest.mark.asyncio
    async def test_call_api_success(self, mock_cli):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps({
            "jsonrpc": "2.0", "id": 1, "result": {"version": 1021400}
        }))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()

        mock_session.post = MagicMock(return_value=mock_response)
        mock_cli._session = mock_session

        result = await mock_cli.call("getinfo")
        assert result.result == {"version": 1021400}
        assert result.method == "getinfo"
        assert result.elapsed_ms >= 0
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_api_error(self, mock_cli):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "error": {"code": -5, "message": "Identity not found"}
        }))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_cli._session = mock_session

        with pytest.raises(VerusAPIError) as exc_info:
            await mock_cli.call("getidentity", ["nonexistent@"])
        assert "Identity not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_daemon_version_accepts_revision(self, config):
        """Daemon string with revision (e.g. '1.2.14-2') should be accepted when
        MIN_DAEMON_VERSION_STR is '1.2.14-2'."""
        cli = VerusCLI(config)
        cli._backend = "api"

        # Mock getinfo to return string version with revision
        cli.getinfo = AsyncMock(return_value={"version": "1.2.14-2"})
        await cli._verify_daemon_version()
        assert cli._daemon_version_str == "1.2.14-2"
        # Numeric encoding remains for major.minor.patch
        assert cli._daemon_version == 1021400
        assert getattr(cli, "_daemon_revision", 0) == 2

    @pytest.mark.asyncio
    async def test_verify_daemon_version_rejects_missing_revision(self, config):
        """Daemon reporting '1.2.14' (no revision) should be rejected when the
        configured minimum requires '1.2.14-2'."""
        cli = VerusCLI(config)
        cli._backend = "api"

        # Mock getinfo to return string version without revision
        cli.getinfo = AsyncMock(return_value={"version": "1.2.14"})
        with pytest.raises(Exception) as exc_info:
            await cli._verify_daemon_version()
        assert "Please upgrade" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_daemon_version_rejects_integer_without_revision(self, config):
        """Integer-encoded version (1021400) should also be rejected when the
        configured minimum requires a revision suffix (1.2.14-2)."""
        cli = VerusCLI(config)
        cli._backend = "api"

        # Mock getinfo to return integer-encoded version (no revision)
        cli.getinfo = AsyncMock(return_value={"version": 1021400})
        with pytest.raises(Exception) as exc_info:
            await cli._verify_daemon_version()
        assert "Please upgrade" in str(exc_info.value)

    def test_avg_latency_zero_when_no_calls(self, mock_cli):
        assert mock_cli.avg_latency_ms == 0.0


# ---------------------------------------------------------------------------
# VerusID tests
# ---------------------------------------------------------------------------

class TestVerusIDManager:
    @pytest.fixture
    def id_mgr(self, mock_cli):
        return VerusIDManager(mock_cli)

    @pytest.mark.asyncio
    async def test_get_identity(self, id_mgr, mock_cli):
        mock_cli.getidentity = AsyncMock(return_value={
            "identity": {
                "name": "TestAgent",
                "identityaddress": "iTestAddr123",
                "parent": "iRootID",
                "version": 3,
                "flags": 0,
                "primaryaddresses": ["RAddr1"],
                "recoveryauthority": "recovery@",
                "revocationauthority": "revoke@",
                "minimumsignatures": 1,
                "contentmap": {},
                "contentmultimap": {},
            }
        })

        identity = await id_mgr.get_identity("TestAgent@")
        assert identity.name == "TestAgent"
        assert identity.full_name == "TestAgent@"
        assert not identity.is_locked
        assert not identity.is_revoked
        assert identity.primary_addresses == ["RAddr1"]

    @pytest.mark.asyncio
    async def test_create_identity(self, id_mgr, mock_cli):
        mock_cli.registernamecommitment = AsyncMock(return_value={
            "txid": "commit_txid_123",
            "namereservation": {"name": "NewAgent", "salt": "abc"},
        })
        mock_cli.registeridentity = AsyncMock(return_value="register_txid_456")

        result = await id_mgr.create_identity(
            name="NewAgent",
            primary_addresses=["RAddr1"],
            recovery_authority="recovery@",
        )
        assert result.success
        assert result.txid == "register_txid_456"
        assert result.operation == "create"

    @pytest.mark.asyncio
    async def test_lock_vault(self, id_mgr, mock_cli):
        mock_cli.getidentity = AsyncMock(return_value={
            "identity": {"name": "Vaulted", "identityaddress": "iVault",
                         "parent": "", "version": 3, "flags": 0,
                         "primaryaddresses": [], "recoveryauthority": "",
                         "revocationauthority": "", "minimumsignatures": 1,
                         "contentmap": {}, "contentmultimap": {}}
        })
        mock_cli.updateidentity = AsyncMock(return_value="lock_txid")

        result = await id_mgr.lock_vault("Vaulted@", timelock_blocks=2880)
        assert result.success
        assert result.data["timelock_blocks"] == 2880

    @pytest.mark.asyncio
    async def test_sign_and_verify(self, id_mgr, mock_cli):
        mock_cli.signmessage = AsyncMock(return_value="base64sig==")
        mock_cli.verifymessage = AsyncMock(return_value=True)

        sig = await id_mgr.sign_message("Agent@", "hello world")
        assert sig == "base64sig=="

        valid = await id_mgr.verify_signature("Agent@", sig, "hello world")
        assert valid is True


# ---------------------------------------------------------------------------
# DeFi tests
# ---------------------------------------------------------------------------

class TestVerusDeFiManager:
    @pytest.fixture
    def defi(self, mock_cli):
        return VerusDeFiManager(mock_cli, destination_address="RTestDest")

    @pytest.mark.asyncio
    async def test_get_currency_state(self, defi, mock_cli):
        mock_cli.getcurrencystate = AsyncMock(return_value=[{
            "height": 100000,
            "currencystate": {
                "currencyid": "iFloralis",
                "supply": 1000000,
                "reservecurrencies": [
                    {"currencyid": "iVRSC", "reserves": 500000, "weight": 0.5},
                    {"currencyid": "iBTC", "reserves": 10, "weight": 0.5},
                ],
            }
        }])

        state = await defi.get_currency_state("Floralis")
        assert state.name == "Floralis"
        assert state.supply == 1000000
        assert "iVRSC" in state.reserves
        assert state.reserves["iVRSC"] == 500000

    @pytest.mark.asyncio
    async def test_estimate_conversion(self, defi, mock_cli):
        mock_cli.estimateconversion = AsyncMock(return_value={
            "estimatedcurrencyout": 0.00123
        })

        est = await defi.estimate_conversion("VRSC", "tBTC.vETH", 10.0, via="Floralis")
        assert est.estimated_output == 0.00123
        assert est.from_currency == "VRSC"
        assert est.via == "Floralis"

    @pytest.mark.asyncio
    async def test_convert(self, defi, mock_cli):
        mock_cli.sendcurrency = AsyncMock(return_value="conv_txid_789")

        result = await defi.convert("VRSC", "tBTC.vETH", 10.0, via="Floralis")
        assert result.success
        assert result.txid == "conv_txid_789"

    @pytest.mark.asyncio
    async def test_convert_no_destination(self, mock_cli):
        defi = VerusDeFiManager(mock_cli, destination_address="")
        result = await defi.convert("VRSC", "tBTC.vETH", 10.0)
        assert not result.success
        assert "destination" in result.error.lower()

    @pytest.mark.asyncio
    async def test_detect_arbitrage_no_opportunity(self, defi, mock_cli):
        mock_cli.estimateconversion = AsyncMock(side_effect=[
            {"estimatedcurrencyout": 0.95},   # Forward
            {"estimatedcurrencyout": 0.90},   # Return (loss)
        ])

        opp = await defi.detect_arbitrage("VRSC", "BTC", "Floralis", "Pure", 1.0)
        assert opp is None  # No profit

    @pytest.mark.asyncio
    async def test_launch_currency_broadcast_pipeline(self, defi, mock_cli):
        """definecurrency returns hex → signrawtransaction → sendrawtransaction."""
        mock_cli.definecurrency = AsyncMock(return_value={"hex": "0100deadbeef"})
        mock_cli.call = AsyncMock(side_effect=[
            make_cli_result("signrawtransaction", {"hex": "0100deadbeefsigned", "complete": True}),
            make_cli_result("sendrawtransaction", "final_txid_999"),
        ])

        result = await defi.launch_currency({"name": "TestToken", "options": 32})
        assert result.success
        assert result.txid == "final_txid_999"
        # Verify sign+send were called
        assert mock_cli.call.call_count == 2
        calls = [c.args[0] for c in mock_cli.call.call_args_list]
        assert calls == ["signrawtransaction", "sendrawtransaction"]

    @pytest.mark.asyncio
    async def test_launch_currency_skips_broadcast_when_txid_present(self, defi, mock_cli):
        """If definecurrency already returns a txid, skip sign+send."""
        mock_cli.definecurrency = AsyncMock(return_value={"txid": "already_broadcast"})

        result = await defi.launch_currency({"name": "TestToken", "options": 32})
        assert result.success
        assert result.txid == "already_broadcast"


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

class TestVerusLoginManager:
    @pytest.fixture
    def login(self, mock_cli):
        return VerusLoginManager(mock_cli)

    def test_create_challenge(self, login):
        challenge = login.create_challenge(signing_identity="User@")
        assert challenge.challenge_id
        assert challenge.signing_identity == "User@"
        assert not challenge.is_expired
        assert "verusid_login" in challenge.message

    @pytest.mark.asyncio
    async def test_full_login_flow(self, login, mock_cli):
        # Create challenge
        challenge = login.create_challenge(signing_identity="User@")

        # Mock verification
        mock_cli.verifymessage = AsyncMock(return_value=True)
        mock_cli.getidentity = AsyncMock(return_value={
            "identity": {
                "name": "User", "identityaddress": "iUserAddr",
                "flags": 0, "primaryaddresses": ["RUser1"], "parent": "",
            }
        })

        # Process login
        result = await login.process_login(
            challenge_id=challenge.challenge_id,
            identity_name="User@",
            signature="fake_sig_base64",
        )

        assert result.success
        assert result.session is not None
        assert result.session.identity_name == "User@"

        # Validate session
        session = login.validate_session(result.session.session_id)
        assert session is not None
        assert session.is_valid

        # Invalidate
        login.invalidate_session(result.session.session_id)
        assert login.validate_session(result.session.session_id) is None

    @pytest.mark.asyncio
    async def test_login_expired_challenge(self, login, mock_cli):
        challenge = login.create_challenge()
        # Force expire
        login._challenges[challenge.challenge_id].expires_at = datetime.now() - timedelta(seconds=1)

        result = await login.process_login(
            challenge_id=challenge.challenge_id,
            identity_name="User@",
            signature="sig",
        )
        assert not result.success
        assert "expired" in result.error.lower()

    @pytest.mark.asyncio
    async def test_login_revoked_identity(self, login, mock_cli):
        challenge = login.create_challenge()
        mock_cli.verifymessage = AsyncMock(return_value=True)
        mock_cli.getidentity = AsyncMock(return_value={
            "identity": {"name": "Revoked", "identityaddress": "iRevoked", "flags": 8, "primaryaddresses": [], "parent": ""}
        })

        result = await login.process_login(
            challenge_id=challenge.challenge_id,
            identity_name="Revoked@",
            signature="sig",
        )
        assert not result.success
        assert "revoked" in result.error.lower()


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------

class TestVerusStorageManager:
    @pytest.fixture
    def storage(self, mock_cli):
        return VerusStorageManager(mock_cli)

    @pytest.mark.asyncio
    async def test_store_data(self, storage, mock_cli):
        mock_cli.updateidentity = AsyncMock(return_value="store_txid_111")

        result = await storage.store_data(
            identity_name="Agent@",
            key="model_config",
            data={"layers": 12, "hidden": 768},
        )
        assert result.success
        assert result.file_id  # SHA-256 hash
        assert result.txid == "store_txid_111"

    @pytest.mark.asyncio
    async def test_store_data_too_large(self, storage, mock_cli):
        big_data = {"key": "x" * 10000}
        result = await storage.store_data(
            identity_name="Agent@",
            key="big",
            data=big_data,
        )
        assert not result.success
        assert "too large" in result.error.lower()


# ---------------------------------------------------------------------------
# Main agent tests
# ---------------------------------------------------------------------------

class TestVerusBlockchainAgent:
    @pytest.fixture
    def agent(self, config):
        return VerusBlockchainAgent(config)

    def test_initial_state(self, agent):
        assert agent.state == VerusAgentState.INITIALIZING
        assert agent.agent_id == AGENT_ID
        assert agent.agent_type == "verus_blockchain_agent"
        assert agent.specialization == VerusSpecialization.FULL_STACK

    @pytest.mark.asyncio
    async def test_initialize(self, agent):
        with patch.object(VerusCLI, "initialize", new_callable=AsyncMock):
            await agent.initialize()
            assert agent.state == VerusAgentState.IDLE
            assert agent.cli is not None
            assert agent.identity_manager is not None
            assert agent.defi_manager is not None
            assert agent.login_manager is not None
            assert agent.storage_manager is not None

    def test_get_status(self, agent):
        agent.state = VerusAgentState.IDLE
        agent.start_time = datetime.now()
        agent.cli = MagicMock()
        agent.cli.daemon_version = "1.2.14-2"
        agent.cli.avg_latency_ms = 5.0
        agent.cli.call_count = 10
        agent.login_manager = MagicMock()
        agent.login_manager.active_session_count = 2

        status = agent.get_status()
        assert status["agent_id"] == AGENT_ID
        assert status["state"] == "idle"
        assert status["network"] == "testnet"
        # number of advertised capabilities can grow over time;
        # we only require the original baseline to be present.
        assert len(status["capabilities"]) >= 14
        assert status["metrics"]["cli_call_count"] == 10

    @pytest.mark.asyncio
    async def test_process_task_unknown_capability(self, agent):
        with patch.object(VerusCLI, "initialize", new_callable=AsyncMock):
            await agent.initialize()

        result = await agent.process_task({
            "task_id": "t1",
            "capability": "verus.nonexistent",
            "params": {},
        })
        assert not result.success
        assert "Unknown capability" in result.error

    @pytest.mark.asyncio
    async def test_process_task_estimate(self, agent):
        with patch.object(VerusCLI, "initialize", new_callable=AsyncMock):
            await agent.initialize()

        agent.defi_manager.estimate_conversion = AsyncMock(
            return_value=ConversionEstimate(
                from_currency="VRSC", to_currency="BTC",
                input_amount=10.0, estimated_output=0.001,
                via="Floralis", price=0.0001,
            )
        )

        result = await agent.process_task({
            "task_id": "t2",
            "capability": "verus.currency.estimate",
            "params": {
                "from_currency": "VRSC",
                "to_currency": "BTC",
                "amount": 10.0,
                "via": "Floralis",
            },
        })
        assert result.success
        assert result.result["estimated_output"] == 0.001
        assert agent.tasks_completed == 1

    def test_adapt_behavior(self, agent):
        # Seed experiences
        for i in range(10):
            agent.experience_history.append({
                "capability": AGENT_CAPABILITIES[0],
                "success": i < 8,  # 80% success
                "elapsed_ms": 10.0,
                "timestamp": datetime.now().isoformat(),
            })
        agent.adapt_behavior()
        assert 0.0 < agent.accuracy_score <= 1.0
