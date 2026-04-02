"""
Tests for the MCP Client Integration Layer

Covers: MCPServerConnection protocol, MCPRouter routing logic,
capability-to-MCP mapping, parameter transformation, and agent
integration with MCP-first routing.

Uses mocks — no live MCP servers or daemon required.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from verus_agent.mcp_client import (
    MCPCallResult,
    MCPRouter,
    MCPServerConnection,
    MCPServerName,
    MCPServerStatus,
    MCPTool,
    CAPABILITY_TO_MCP,
    MCP_EXCLUSIVE_TOOLS,
    WRITE_CAPABILITIES,
)
from verus_agent.config import VerusConfig, VerusNetwork


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp_router():
    """A disabled MCPRouter for unit-testing routing logic without subprocesses."""
    return MCPRouter(chain="vrsctest", enabled=False)


@pytest.fixture
def enabled_router():
    """An MCPRouter with mock connections injected."""
    router = MCPRouter(chain="vrsctest", enabled=True)
    # Inject mock connections for all servers
    for name in MCPServerName:
        mock_conn = MagicMock(spec=MCPServerConnection)
        mock_conn.connected = True
        mock_conn.server_name = name
        mock_conn.tools = {
            f"mock_tool_{name.value}": MCPTool(
                name=f"mock_tool_{name.value}",
                description="mock",
                input_schema={},
                server=name,
            )
        }
        router._connections[name] = mock_conn
    return router


# ---------------------------------------------------------------------------
# MCPRouter: routing logic
# ---------------------------------------------------------------------------

class TestMCPRouterRoutingLogic:
    """Test the should_route_to_mcp decision logic."""

    def test_disabled_router_never_routes(self, mcp_router):
        """When MCP is disabled, nothing should route to MCP."""
        assert not mcp_router.should_route_to_mcp("verus.currency.send")
        assert not mcp_router.should_route_to_mcp("mcp.chain.getwalletinfo")

    def test_enabled_router_routes_write_operations(self, enabled_router):
        """Write operations should route to MCP when available."""
        for cap in WRITE_CAPABILITIES:
            if cap in CAPABILITY_TO_MCP:
                assert enabled_router.should_route_to_mcp(cap), f"{cap} should route to MCP"

    def test_enabled_router_routes_mcp_exclusive(self, enabled_router):
        """MCP-exclusive capabilities should always route to MCP."""
        for cap in MCP_EXCLUSIVE_TOOLS:
            assert enabled_router.should_route_to_mcp(cap), f"{cap} should route to MCP"

    def test_enabled_router_routes_mapped_capabilities(self, enabled_router):
        """All mapped capabilities should route when server is connected."""
        for cap in CAPABILITY_TO_MCP:
            assert enabled_router.should_route_to_mcp(cap), f"{cap} should route to MCP"

    def test_unknown_capability_does_not_route(self, enabled_router):
        """Unknown capabilities should not route to MCP."""
        assert not enabled_router.should_route_to_mcp("verus.unknown.capability")
        assert not enabled_router.should_route_to_mcp("totally.made.up")

    def test_mcp_target_returns_correct_mapping(self, enabled_router):
        """get_mcp_target should return the right (server, tool) tuple."""
        target = enabled_router.get_mcp_target("verus.currency.send")
        assert target == (MCPServerName.SEND, "sendcurrency")

        target = enabled_router.get_mcp_target("verus.identity.create")
        assert target == (MCPServerName.IDENTITY, "registeridentity")

        target = enabled_router.get_mcp_target("mcp.chain.getwalletinfo")
        assert target == (MCPServerName.CHAIN, "getwalletinfo")

    def test_mcp_target_returns_none_for_unknown(self, enabled_router):
        assert enabled_router.get_mcp_target("verus.unknown") is None


# ---------------------------------------------------------------------------
# MCPRouter: parameter transformation
# ---------------------------------------------------------------------------

class TestMCPRouterParamTransform:
    """Test _transform_params for various capabilities."""

    def test_currency_send_transform(self, enabled_router):
        params = {
            "from_address": "RAddress123",
            "to_address": "RAddress456",
            "amount": 10.0,
            "currency": "VRSC",
        }
        args = enabled_router._transform_params(
            "verus.currency.send", "sendcurrency", dict(params)
        )
        assert args["chain"] == "vrsctest"
        assert args["fromaddress"] == "RAddress123"
        assert len(args["outputs"]) == 1
        assert args["outputs"][0]["amount"] == 10.0
        assert args["outputs"][0]["address"] == "RAddress456"

    def test_currency_convert_transform(self, enabled_router):
        params = {
            "from_currency": "VRSC",
            "to_currency": "Bridge.vETH",
            "amount": 5.0,
            "via": "Bridge.vETH",
            "from_address": "RAddr",
        }
        args = enabled_router._transform_params(
            "verus.currency.convert", "sendcurrency", dict(params)
        )
        assert args["outputs"][0]["convertto"] == "Bridge.vETH"
        assert args["outputs"][0]["via"] == "Bridge.vETH"
        assert args["fromaddress"] == "RAddr"

    def test_identity_create_transform(self, enabled_router):
        params = {
            "name": "testid",
            "primary_addresses": ["RAddr1"],
            "recovery_authority": "recovery@",
            "minimumsignatures": 1,
        }
        args = enabled_router._transform_params(
            "verus.identity.create", "registeridentity", dict(params)
        )
        assert args["name"] == "testid"
        assert args["primaryaddresses"] == ["RAddr1"]
        assert args["recoveryauthority"] == "recovery@"

    def test_chain_injected_automatically(self, enabled_router):
        """All transforms should inject the chain parameter."""
        args = enabled_router._transform_params(
            "verus.market.monitor", "getcurrency", {"basket_name": "Bridge.vETH"}
        )
        assert args["chain"] == "vrsctest"

    def test_marketplace_make_offer_transform(self, enabled_router):
        params = {
            "change_address": "RAddr",
            "offer": {"currency": "VRSC", "amount": 10},
            "for_item": {"currency": "tBTC.vETH", "amount": 0.001},
        }
        args = enabled_router._transform_params(
            "verus.marketplace.make_offer", "makeoffer", dict(params)
        )
        assert args["fromaddress"] == "RAddr"
        assert args["offer"]["currency"] == "VRSC"


# ---------------------------------------------------------------------------
# MCPRouter: status
# ---------------------------------------------------------------------------

class TestMCPRouterStatus:
    """Test get_status and list_all_capabilities."""

    def test_status_disabled(self, mcp_router):
        status = mcp_router.get_status()
        assert status["enabled"] is False
        assert status["servers_connected"] == 0

    def test_status_enabled_with_connections(self, enabled_router):
        status = enabled_router.get_status()
        assert status["enabled"] is True
        assert status["servers_connected"] == len(MCPServerName)
        assert "chain" in status["servers"]
        assert "identity" in status["servers"]

    def test_list_all_capabilities(self, enabled_router):
        caps = enabled_router.list_all_capabilities()
        # Should include both mapped and exclusive
        assert "verus.currency.send" in caps
        assert "mcp.chain.getwalletinfo" in caps
        assert len(caps) == len(CAPABILITY_TO_MCP) + len(MCP_EXCLUSIVE_TOOLS)


# ---------------------------------------------------------------------------
# MCPCallResult
# ---------------------------------------------------------------------------

class TestMCPCallResult:
    def test_success_result(self):
        r = MCPCallResult(success=True, content={"txid": "abc123"})
        assert r.success
        assert r.content["txid"] == "abc123"
        assert r.error is None

    def test_error_result(self):
        r = MCPCallResult(success=False, error="Spending limit exceeded", is_error=True)
        assert not r.success
        assert "Spending limit" in r.error


# ---------------------------------------------------------------------------
# MCPRouter: route_capability with mocked call_tool
# ---------------------------------------------------------------------------

class TestMCPRouterRouteCapability:

    @pytest.mark.asyncio
    async def test_route_write_succeeds(self, enabled_router):
        """Successful MCP write should return the result."""
        mock_result = MCPCallResult(success=True, content={"txid": "abc"})
        enabled_router.call_tool = AsyncMock(return_value=mock_result)

        result = await enabled_router.route_capability(
            "verus.currency.send",
            {"from_address": "R1", "to_address": "R2", "amount": 1.0, "currency": "VRSC"},
        )
        assert result is not None
        assert result.success
        assert result.content["txid"] == "abc"

    @pytest.mark.asyncio
    async def test_route_write_fails_no_fallback(self, enabled_router):
        """Failed MCP write should NOT fall back to CLI."""
        mock_result = MCPCallResult(success=False, error="Spending limit exceeded", is_error=True)
        enabled_router.call_tool = AsyncMock(return_value=mock_result)

        result = await enabled_router.route_capability(
            "verus.currency.send",
            {"from_address": "R1", "to_address": "R2", "amount": 1000.0, "currency": "VRSC"},
        )
        # Should return the error result, not None (which would mean fallback)
        assert result is not None
        assert not result.success
        assert "Spending limit" in result.error

    @pytest.mark.asyncio
    async def test_route_read_fails_falls_back(self, enabled_router):
        """Failed MCP read should return None to signal CLI fallback."""
        mock_result = MCPCallResult(success=False, error="timeout")
        enabled_router.call_tool = AsyncMock(return_value=mock_result)

        result = await enabled_router.route_capability(
            "verus.currency.estimate",
            {"from_currency": "VRSC", "to_currency": "tBTC", "amount": 1.0},
        )
        # None means "fall back to CLI"
        assert result is None

    @pytest.mark.asyncio
    async def test_route_unknown_capability_returns_none(self, enabled_router):
        """Unknown capabilities should return None immediately."""
        result = await enabled_router.route_capability(
            "verus.unknown.thing", {}
        )
        assert result is None


# ---------------------------------------------------------------------------
# Capability mapping completeness
# ---------------------------------------------------------------------------

class TestCapabilityMappingCompleteness:
    """Verify the mapping tables are internally consistent."""

    def test_write_capabilities_all_have_mappings(self):
        """Every write capability should have an MCP mapping."""
        for cap in WRITE_CAPABILITIES:
            assert cap in CAPABILITY_TO_MCP, (
                f"Write capability {cap} has no MCP mapping"
            )

    def test_no_overlap_between_mapped_and_exclusive(self):
        """Mapped and exclusive capabilities should not overlap."""
        overlap = set(CAPABILITY_TO_MCP.keys()) & set(MCP_EXCLUSIVE_TOOLS.keys())
        assert not overlap, f"Overlap between mapped and exclusive: {overlap}"

    def test_all_mcp_servers_referenced(self):
        """All 7 MCP server types should appear in at least one mapping."""
        referenced = set()
        for server, _ in CAPABILITY_TO_MCP.values():
            referenced.add(server)
        for server, _ in MCP_EXCLUSIVE_TOOLS.values():
            referenced.add(server)
        for name in MCPServerName:
            assert name in referenced, f"Server {name.value} not referenced in any mapping"

    def test_mcp_exclusive_tools_count(self):
        """Verify we expose a reasonable number of MCP-exclusive tools."""
        assert len(MCP_EXCLUSIVE_TOOLS) >= 25, (
            f"Expected at least 25 MCP-exclusive tools, got {len(MCP_EXCLUSIVE_TOOLS)}"
        )


# ---------------------------------------------------------------------------
# Config: MCP fields
# ---------------------------------------------------------------------------

class TestMCPConfig:

    def test_default_mcp_disabled(self):
        config = VerusConfig()
        assert config.mcp_enabled is False

    def test_mcp_chain_defaults_from_network(self):
        config = VerusConfig(network=VerusNetwork.TESTNET)
        assert config.mcp_chain == "vrsctest"

        config2 = VerusConfig(network=VerusNetwork.MAINNET)
        assert config2.mcp_chain == "VRSC"

    @patch.dict("os.environ", {"VERUS_MCP_ENABLED": "true", "VERUS_MCP_CHAIN": "vrsctest"})
    def test_mcp_env_override(self):
        config = VerusConfig()
        assert config.mcp_enabled is True
        assert config.mcp_chain == "vrsctest"

    @patch.dict("os.environ", {"VERUS_MCP_READ_ONLY": "true"})
    def test_mcp_read_only_env(self):
        config = VerusConfig()
        assert config.mcp_read_only is True
