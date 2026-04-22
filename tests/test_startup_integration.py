"""Integration tests for verus_agent startup wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from verus_agent.agent import VerusBlockchainAgent, VerusAgentState
from verus_agent.cli_wrapper import VerusCLI
from verus_agent.config import VerusConfig


@pytest.mark.asyncio
@pytest.mark.integration
async def test_initialize_registers_extension_capabilities_from_env(monkeypatch):
    """Startup should honor env toggles and register extension handlers."""
    monkeypatch.setenv("VERUS_SECURITY_LEVEL", "enforced")
    monkeypatch.setenv("VERUS_MARKETPLACE_ENABLED", "true")
    monkeypatch.setenv("VERUS_IP_PROTECTION_ENABLED", "true")

    # Avoid live daemon calls for this integration wiring test.
    monkeypatch.setattr(VerusCLI, "initialize", AsyncMock(return_value=None))

    agent = VerusBlockchainAgent(VerusConfig())
    await agent.initialize()

    try:
        assert agent.state == VerusAgentState.IDLE

        assert agent.swarm_security is not None
        assert agent.swarm_security.is_enabled is True

        assert agent.marketplace is not None
        assert agent.marketplace.enabled is True

        assert agent.ip_protection is not None
        assert agent.ip_protection.enabled is True

        # Security extension capability handlers
        assert "verus.security.register" in agent._capability_handlers
        assert "verus.security.verify" in agent._capability_handlers

        # Marketplace extension capability handlers
        assert "verus.marketplace.register_product" in agent._capability_handlers
        assert "verus.marketplace.issue_license" in agent._capability_handlers

        # IP protection extension capability handlers
        assert "verus.ip.register_model" in agent._capability_handlers
        assert "verus.ip.verify_integrity" in agent._capability_handlers
    finally:
        await agent.shutdown()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_start_skips_swarm_registration_when_uai_disabled(monkeypatch):
    """When UAI is disabled, startup should not attempt swarm registration."""
    monkeypatch.setenv("VERUS_UAI_INTEGRATION_ENABLED", "false")
    monkeypatch.setattr(VerusCLI, "initialize", AsyncMock(return_value=None))

    agent = VerusBlockchainAgent(VerusConfig())
    await agent.initialize()
    agent._register_with_swarm = AsyncMock(return_value=None)  # type: ignore[method-assign]

    try:
        await agent.start()
        agent._register_with_swarm.assert_not_called()  # type: ignore[attr-defined]
    finally:
        await agent.shutdown()
