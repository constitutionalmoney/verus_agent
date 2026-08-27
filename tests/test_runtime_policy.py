"""Tests for staged activation and per-mutation runtime controls."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from verus_agent.agent import VerusBlockchainAgent
from verus_agent.cli_wrapper import VerusCLI
from verus_agent.config import AGENT_CAPABILITIES, VerusConfig
from verus_agent.defi import DeFiOperationResult
from verus_agent.run_verus_agent_task import _parse_network
from verus_agent.runtime_policy import (
    ActivationProfile,
    ApprovalStore,
    BLOCKED_CAPABILITIES,
    MutationOutbox,
    MUTATING_CAPABILITIES,
    PolicyViolation,
    READ_ONLY_CAPABILITIES,
    SUPPORTED_TESTNET_MUTATIONS,
    WALLET_REVIEW_CAPABILITIES,
)


def _write_json(path, payload) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _write_profile(path, *, stage: str, capabilities: list[str]) -> str:
    return _write_json(
        path,
        {
            "profile_id": "synthetic-project",
            "stage": stage,
            "network": "testnet",
            "canonical_store": "synthetic database",
            "actor_model": "human operator and bounded service actor",
            "private_data_boundary": "synthetic data only",
            "non_goals": ["Mainnet", "production"],
            "allowed_capabilities": capabilities,
            "allowed_rpc_methods": [],
        },
    )


def _write_approval(path, *, task_id: str, capability: str, key: str) -> str:
    now = datetime.now(timezone.utc)
    rpc_method = {
        "verus.currency.send": "sendcurrency",
        "verus.identity.update": "updateidentity",
    }[capability]
    return _write_json(
        path,
        {
            "version": 1,
            "grants": [
                {
                    "approval_id": "synthetic-approval",
                    "task_id": task_id,
                    "capability": capability,
                    "network": "testnet",
                    "idempotency_key": key,
                    "rpc_methods": [rpc_method],
                    "issued_at": (now - timedelta(seconds=5)).isoformat(),
                    "expires_at": (now + timedelta(minutes=5)).isoformat(),
                }
            ],
        },
    )


def test_mainnet_parser_is_unavailable() -> None:
    with pytest.raises(Exception, match="Mainnet is disabled"):
        _parse_network("mainnet")


def test_every_advertised_capability_has_one_activation_classification() -> None:
    categories = (
        READ_ONLY_CAPABILITIES,
        WALLET_REVIEW_CAPABILITIES,
        MUTATING_CAPABILITIES,
        BLOCKED_CAPABILITIES,
    )
    inventory = set(AGENT_CAPABILITIES)
    assert set().union(*categories) == inventory
    for capability in inventory:
        assert sum(capability in category for category in categories) == 1
    assert SUPPORTED_TESTNET_MUTATIONS <= MUTATING_CAPABILITIES


def test_safe_default_blocks_mutations() -> None:
    profile = ActivationProfile.safe_default()
    with pytest.raises(PolicyViolation, match="not enabled"):
        profile.ensure_task_allowed("verus.currency.send", {})


def test_safe_default_raw_rpc_is_exactly_scoped() -> None:
    profile = ActivationProfile.safe_default()
    profile.ensure_task_allowed("verus.cli.execute", {"method": "getinfo"})
    with pytest.raises(PolicyViolation, match="profile-approved"):
        profile.ensure_task_allowed("verus.cli.execute", {"method": "listidentities"})


def test_safe_default_excludes_wallet_decryption() -> None:
    profile = ActivationProfile.safe_default()
    assert "verus.messaging.receive_decrypt" not in profile.allowed_capabilities


def test_uncontracted_local_capability_cannot_be_activated(tmp_path) -> None:
    profile_path = _write_profile(
        tmp_path / "profile.json",
        stage="read_only",
        capabilities=["verus.ip.encrypt_model"],
    )
    profile = ActivationProfile.from_path(profile_path)
    with pytest.raises(PolicyViolation, match="privacy/authorization"):
        profile.ensure_task_allowed("verus.ip.encrypt_model", {})


def test_approval_requires_exact_task_scope(tmp_path) -> None:
    path = _write_approval(
        tmp_path / "approval.json",
        task_id="task-exact",
        capability="verus.currency.send",
        key="idempotency-key-0001",
    )
    store = ApprovalStore(path)
    grant = store.authorize(
        task_id="task-exact",
        capability="verus.currency.send",
        network="testnet",
        idempotency_key="idempotency-key-0001",
    )
    assert grant.rpc_methods == frozenset({"sendcurrency"})

    payload = json.loads((tmp_path / "approval.json").read_text(encoding="utf-8"))
    payload["grants"][0]["rpc_methods"].append("importprivkey")
    (tmp_path / "approval.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PolicyViolation, match="exactly match"):
        store.authorize(
            task_id="task-exact",
            capability="verus.currency.send",
            network="testnet",
            idempotency_key="idempotency-key-0001",
        )

    with pytest.raises(PolicyViolation, match="No exact approval"):
        store.authorize(
            task_id="different-task",
            capability="verus.currency.send",
            network="testnet",
            idempotency_key="idempotency-key-0001",
        )


def test_outbox_replays_only_identical_completed_request(tmp_path) -> None:
    outbox = MutationOutbox(str(tmp_path / "outbox.sqlite"))
    params = {"currency": "VRSCTEST", "amount": 1}
    assert outbox.claim("idempotency-key-0002", "verus.currency.send", params) is None
    outbox.complete("idempotency-key-0002", {"success": True, "txid": "txid"})
    replay = outbox.claim("idempotency-key-0002", "verus.currency.send", params)
    assert replay == {"success": True, "txid": "txid", "_idempotent_replay": True}
    with pytest.raises(PolicyViolation, match="another request"):
        outbox.claim(
            "idempotency-key-0002",
            "verus.currency.send",
            {"currency": "VRSCTEST", "amount": 2},
        )


@pytest.mark.asyncio
async def test_agent_write_requires_approval_and_replays_from_outbox(tmp_path) -> None:
    task_id = "approved-test-task"
    key = "idempotency-key-0003"
    profile_path = _write_profile(
        tmp_path / "profile.json",
        stage="testnet_write",
        capabilities=["verus.currency.send"],
    )
    approval_path = _write_approval(
        tmp_path / "approval.json",
        task_id=task_id,
        capability="verus.currency.send",
        key=key,
    )
    config = VerusConfig(
        activation_profile_path=profile_path,
        mutation_approval_path=approval_path,
        mutation_outbox_path=str(tmp_path / "outbox.sqlite"),
    )
    agent = VerusBlockchainAgent(config)
    with patch.object(VerusCLI, "initialize", new_callable=AsyncMock):
        await agent.initialize()

    agent.defi_manager.send_currency = AsyncMock(
        return_value=DeFiOperationResult(
            operation="send",
            success=True,
            txid="confirmed-txid",
            opid="opid-1",
            confirmed=True,
        )
    )
    agent.cli.verify_mutation_readiness = AsyncMock(return_value={
        "network": "testnet",
        "version": "1.2.17-6",
        "blocks": 100,
        "longestchain": 100,
        "connections": 4,
    })
    task = {
        "task_id": task_id,
        "idempotency_key": key,
        "capability": "verus.currency.send",
        "params": {
            "currency": "VRSCTEST",
            "to_address": "RTestOnly",
            "amount": 1,
            "poll_interval": 0,
            "max_polls": 1,
        },
    }
    try:
        first = await agent.process_task(task)
        second = await agent.process_task(task)
    finally:
        await agent.shutdown()

    assert first.success is True
    assert first.result["confirmed"] is True
    assert second.success is True
    assert second.result["_idempotent_replay"] is True
    agent.defi_manager.send_currency.assert_awaited_once()
    agent.cli.verify_mutation_readiness.assert_awaited_once()


def test_default_allowlists_contain_no_mutating_rpc_or_capability() -> None:
    for name in ("capability_allowlist.json", "capability_allowlist.constitutional_money.json"):
        payload = json.loads((__import__("pathlib").Path(__file__).parents[1] / name).read_text())
        assert "verus.currency.send" not in payload["allowed_capabilities"]
        assert "verus.identity.update" not in payload["allowed_capabilities"]
        assert "sendcurrency" not in payload["allowed_cli_methods"]
        assert "updateidentity" not in payload["allowed_cli_methods"]
