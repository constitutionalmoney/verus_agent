"""
MCP Client — VerusIDX MCP Server Integration Layer

Connects the Verus Agent to the verusidx-mcp servers via the Model Context
Protocol (stdio JSON-RPC transport).  Provides automatic routing of agent
capabilities to MCP tools when MCP servers are available, with fallback
to the direct CLI/API path.

Architecture
------------
    VerusBlockchainAgent
        → MCPRouter.call_tool(mcp_server, tool_name, arguments)
            → MCPServerConnection (stdin/stdout JSON-RPC 2.0)
                → @verusidx/*-mcp process
                    → verusd (local daemon)

Safety
------
The MCP servers enforce spending limits, audit logging, and optional
read-only mode.  Write operations are always preferred via MCP when
available for these safety benefits.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("verus_agent.mcp")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class MCPServerName(str, Enum):
    """Known verusidx MCP server package names."""
    CHAIN = "chain"
    IDENTITY = "identity"
    SEND = "send"
    DATA = "data"
    ADDRESS = "address"
    MARKETPLACE = "marketplace"
    DEFINECURRENCY = "definecurrency"


@dataclass
class MCPTool:
    """Descriptor for an MCP tool discovered via tools/list."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server: MCPServerName


@dataclass
class MCPCallResult:
    """Result of an MCP tool invocation."""
    success: bool
    content: Any = None
    error: Optional[str] = None
    is_error: bool = False


@dataclass
class MCPServerStatus:
    """Health status of an MCP server connection."""
    server: MCPServerName
    connected: bool = False
    tools: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# MCP Server Connection (stdio JSON-RPC 2.0)
# ---------------------------------------------------------------------------

class MCPServerConnection:
    """
    Manages a single MCP server subprocess and communicates via
    JSON-RPC 2.0 over stdin/stdout (MCP stdio transport).
    """

    def __init__(self, server_name: MCPServerName, env: Optional[Dict[str, str]] = None):
        self.server_name = server_name
        self.package = f"@verusidx/{server_name.value}-mcp"
        self._env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._process is not None and self._process.returncode is None

    @property
    def tools(self) -> Dict[str, MCPTool]:
        return dict(self._tools)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Spawn the MCP server process and complete the MCP handshake."""
        if self.connected:
            return

        npx = shutil.which("npx")
        if not npx:
            raise RuntimeError(
                "npx not found on PATH. Install Node.js >= 18 to use MCP servers."
            )

        env = {**os.environ, **self._env}
        try:
            self._process = await asyncio.create_subprocess_exec(
                npx, "-y", self.package,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to spawn MCP server {self.package}: {exc}") from exc

        # Start the stdout reader coroutine
        self._reader_task = asyncio.create_task(self._read_loop())

        # MCP handshake: initialize → initialized → tools/list
        await self._handshake()
        logger.info(
            "MCP server %s started (pid=%d, tools=%d)",
            self.package, self._process.pid, len(self._tools),
        )

    async def stop(self) -> None:
        """Terminate the MCP server process."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
        self._process = None
        self._initialized = False
        self._tools.clear()
        # Cancel pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(ConnectionError("MCP server stopped"))
        self._pending.clear()

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPCallResult:
        """Call an MCP tool and return the result."""
        if not self.connected or not self._initialized:
            return MCPCallResult(success=False, error="MCP server not connected")

        if tool_name not in self._tools:
            return MCPCallResult(
                success=False,
                error=f"Tool '{tool_name}' not found in {self.package}",
            )

        resp = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if "error" in resp:
            return MCPCallResult(
                success=False,
                error=resp["error"].get("message", str(resp["error"])),
                is_error=True,
            )

        result = resp.get("result", {})
        content = result.get("content", [])
        is_error = result.get("isError", False)

        # Extract text content from MCP content blocks
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        combined = "\n".join(text_parts) if text_parts else str(content)

        # Try parsing as JSON
        parsed = combined
        if isinstance(combined, str):
            try:
                parsed = json.loads(combined)
            except (json.JSONDecodeError, ValueError):
                pass

        return MCPCallResult(
            success=not is_error,
            content=parsed,
            is_error=is_error,
            error=combined if is_error else None,
        )

    # ------------------------------------------------------------------
    # Internal: MCP protocol
    # ------------------------------------------------------------------

    async def _handshake(self) -> None:
        """Perform the MCP initialize / initialized / tools-list sequence."""
        # 1. initialize
        resp = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "verus-agent",
                "version": "1.0.0",
            },
        })
        if "error" in resp:
            raise RuntimeError(f"MCP initialize failed: {resp['error']}")

        # 2. initialized notification (no id)
        await self._send_notification("notifications/initialized", {})

        # 3. Discover tools
        tools_resp = await self._send_request("tools/list", {})
        if "error" in tools_resp:
            raise RuntimeError(f"MCP tools/list failed: {tools_resp['error']}")

        for tool_def in tools_resp.get("result", {}).get("tools", []):
            tool = MCPTool(
                name=tool_def["name"],
                description=tool_def.get("description", ""),
                input_schema=tool_def.get("inputSchema", {}),
                server=self.server_name,
            )
            self._tools[tool.name] = tool

        self._initialized = True

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for the response."""
        async with self._lock:
            self._request_id += 1
            rid = self._request_id

        message = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params,
        }

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = fut

        await self._write(message)

        try:
            return await asyncio.wait_for(fut, timeout=60)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            return {"error": {"code": -1, "message": f"Timeout waiting for {method}"}}

    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        await self._write(message)

    async def _write(self, message: Dict[str, Any]) -> None:
        """Write a JSON-RPC message to the process stdin."""
        if not self._process or not self._process.stdin:
            raise ConnectionError("MCP server process not running")
        data = json.dumps(message)
        # MCP stdio uses newline-delimited JSON
        self._process.stdin.write((data + "\n").encode("utf-8"))
        await self._process.stdin.drain()

    async def _read_loop(self) -> None:
        """Continuously read JSON-RPC responses from stdout."""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break  # EOF — process exited

                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue

                try:
                    msg = json.loads(line_str)
                except json.JSONDecodeError:
                    logger.debug("MCP %s non-JSON output: %s", self.server_name.value, line_str[:200])
                    continue

                # Match response to pending request
                rid = msg.get("id")
                if rid is not None and rid in self._pending:
                    fut = self._pending.pop(rid)
                    if not fut.done():
                        fut.set_result(msg)
                elif msg.get("method"):
                    # Server-initiated notification — log and ignore
                    logger.debug("MCP %s notification: %s", self.server_name.value, msg.get("method"))

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("MCP %s reader error: %s", self.server_name.value, exc)


# ---------------------------------------------------------------------------
# MCP Router — Capability → MCP Tool Mapping & Automatic Routing
# ---------------------------------------------------------------------------

# Maps agent capabilities to (MCPServerName, mcp_tool_name, param_transform_fn).
# param_transform_fn converts agent capability params → MCP tool arguments.

def _identity_param(chain: str):
    """Return a closure that injects the chain param."""
    def _inject(params: Dict[str, Any]) -> Dict[str, Any]:
        return {"chain": chain, **params}
    return _inject


# Write operations that MUST go through MCP for safety (spending limits + audit)
WRITE_CAPABILITIES: set = {
    "verus.currency.send",
    "verus.currency.convert",
    "verus.currency.launch",
    "verus.bridge.cross",
    "verus.identity.create",
    "verus.identity.update",
    "verus.identity.vault",
    "verus.marketplace.make_offer",
    "verus.marketplace.take_offer",
    "verus.marketplace.close_offers",
    "verus.storage.store",
    "verus.storage.store_data_wrapper",
    "verus.storage.store_sendcurrency",
    # Phase 5: Data pipeline write operations
    "verus.data.import_viewingkey",
    "verus.provenance.deliver_encrypted",
    "verus.provenance.list_offer",
    "verus.provenance.create_nft",
    "verus.provenance.store_descriptors",
}

# Capability → (server, tool, is_write)
# Each entry maps an agent capability string to
# the MCP server and tool that handles it.
CAPABILITY_TO_MCP: Dict[str, Tuple[MCPServerName, str]] = {
    # --- Chain / Foundation ---
    "verus.cli.execute":                    (MCPServerName.CHAIN, "help"),
    "verus.mining.info":                    (MCPServerName.CHAIN, "getinfo"),
    "verus.staking.status":                 (MCPServerName.CHAIN, "getinfo"),

    # --- Identity ---
    "verus.identity.create":                (MCPServerName.IDENTITY, "registeridentity"),
    "verus.identity.update":                (MCPServerName.IDENTITY, "updateidentity"),
    "verus.identity.vault":                 (MCPServerName.IDENTITY, "setidentitytimelock"),

    # --- Currency / DeFi ---
    "verus.currency.launch":                (MCPServerName.DEFINECURRENCY, "definecurrency"),
    "verus.currency.convert":               (MCPServerName.SEND, "sendcurrency"),
    "verus.currency.send":                  (MCPServerName.SEND, "sendcurrency"),
    "verus.currency.estimate":              (MCPServerName.SEND, "estimateconversion"),
    "verus.bridge.cross":                   (MCPServerName.SEND, "sendcurrency"),
    "verus.market.monitor":                 (MCPServerName.CHAIN, "getcurrency"),

    # --- Storage (identity-based) ---
    "verus.storage.store":                  (MCPServerName.IDENTITY, "updateidentity"),
    "verus.storage.store_data_wrapper":     (MCPServerName.IDENTITY, "updateidentity"),
    "verus.storage.store_sendcurrency":     (MCPServerName.SEND, "sendcurrency"),
    "verus.storage.retrieve":               (MCPServerName.IDENTITY, "getidentitycontent"),
    "verus.storage.retrieve_data_wrapper":  (MCPServerName.IDENTITY, "getidentitycontent"),

    # --- Data / Messaging ---
    "verus.messaging.send_encrypted":       (MCPServerName.DATA, "signdata"),
    "verus.messaging.receive_decrypt":      (MCPServerName.DATA, "decryptdata"),
    "verus.login.authenticate":             (MCPServerName.DATA, "signdata"),
    "verus.login.validate":                 (MCPServerName.DATA, "verifysignature"),
    # --- VDXF Data Pipeline (Phase 5) ---
    "verus.data.sign":                      (MCPServerName.DATA, "signdata"),
    "verus.data.verify":                    (MCPServerName.DATA, "verifysignature"),
    "verus.data.decrypt":                   (MCPServerName.DATA, "decryptdata"),
    "verus.data.getvdxfid":                 (MCPServerName.IDENTITY, "getvdxfid"),
    "verus.data.list_received":             (MCPServerName.DATA, "z_listreceivedbyaddress"),
    "verus.data.export_viewingkey":         (MCPServerName.DATA, "z_exportviewingkey"),
    "verus.data.import_viewingkey":         (MCPServerName.DATA, "z_importviewingkey"),

    # --- Provenance (Phase 5) ---
    "verus.provenance.create_nft":          (MCPServerName.IDENTITY, "registeridentity"),
    "verus.provenance.store_descriptors":   (MCPServerName.IDENTITY, "updateidentity"),
    "verus.provenance.sign_mmr":            (MCPServerName.DATA, "signdata"),
    "verus.provenance.deliver_encrypted":   (MCPServerName.SEND, "sendcurrency"),
    "verus.provenance.verify":              (MCPServerName.DATA, "verifysignature"),
    "verus.provenance.list_offer":          (MCPServerName.MARKETPLACE, "makeoffer"),
    # --- Marketplace ---
    "verus.marketplace.make_offer":         (MCPServerName.MARKETPLACE, "makeoffer"),
    "verus.marketplace.take_offer":         (MCPServerName.MARKETPLACE, "takeoffer"),
    "verus.marketplace.list_open_offers":   (MCPServerName.MARKETPLACE, "getoffers"),
    "verus.marketplace.close_offers":       (MCPServerName.MARKETPLACE, "closeoffers"),

    # --- Address ---
    "verus.trust.get_ratings":              (MCPServerName.CHAIN, "getinfo"),
}

# MCP-only capabilities (no direct CLI handler in agent)
MCP_EXCLUSIVE_TOOLS: Dict[str, Tuple[MCPServerName, str]] = {
    "mcp.chain.getwalletinfo":              (MCPServerName.CHAIN, "getwalletinfo"),
    "mcp.chain.help":                       (MCPServerName.CHAIN, "help"),
    "mcp.chain.getblockcount":              (MCPServerName.CHAIN, "getblockcount"),
    "mcp.chain.status":                     (MCPServerName.CHAIN, "status"),
    "mcp.chain.refresh_chains":             (MCPServerName.CHAIN, "refresh_chains"),
    "mcp.chain.sendrawtransaction":         (MCPServerName.CHAIN, "sendrawtransaction"),
    "mcp.chain.signrawtransaction":         (MCPServerName.CHAIN, "signrawtransaction"),
    "mcp.chain.verusd":                     (MCPServerName.CHAIN, "verusd"),
    "mcp.chain.stop":                       (MCPServerName.CHAIN, "stop"),
    "mcp.identity.getidentityhistory":      (MCPServerName.IDENTITY, "getidentityhistory"),
    "mcp.identity.listidentities":          (MCPServerName.IDENTITY, "listidentities"),
    "mcp.identity.revokeidentity":          (MCPServerName.IDENTITY, "revokeidentity"),
    "mcp.identity.recoveridentity":         (MCPServerName.IDENTITY, "recoveridentity"),
    "mcp.identity.getvdxfid":              (MCPServerName.IDENTITY, "getvdxfid"),
    "mcp.send.getcurrencybalance":          (MCPServerName.SEND, "getcurrencybalance"),
    "mcp.send.getcurrencyconverters":       (MCPServerName.SEND, "getcurrencyconverters"),
    "mcp.send.listcurrencies":              (MCPServerName.SEND, "listcurrencies"),
    "mcp.send.gettransaction":              (MCPServerName.SEND, "gettransaction"),
    "mcp.send.listtransactions":            (MCPServerName.SEND, "listtransactions"),
    "mcp.send.z_getoperationstatus":        (MCPServerName.SEND, "z_getoperationstatus"),
    "mcp.data.z_listreceivedbyaddress":     (MCPServerName.DATA, "z_listreceivedbyaddress"),
    "mcp.data.z_exportviewingkey":          (MCPServerName.DATA, "z_exportviewingkey"),
    "mcp.data.z_viewtransaction":           (MCPServerName.DATA, "z_viewtransaction"),
    "mcp.data.z_importviewingkey":          (MCPServerName.DATA, "z_importviewingkey"),
    "mcp.data.signdata":                    (MCPServerName.DATA, "signdata"),
    "mcp.data.verifysignature":             (MCPServerName.DATA, "verifysignature"),
    "mcp.address.validateaddress":          (MCPServerName.ADDRESS, "validateaddress"),
    "mcp.address.z_validateaddress":        (MCPServerName.ADDRESS, "z_validateaddress"),
    "mcp.address.getaddressesbyaccount":    (MCPServerName.ADDRESS, "getaddressesbyaccount"),
    "mcp.address.getnewaddress":            (MCPServerName.ADDRESS, "getnewaddress"),
    "mcp.address.z_getnewaddress":          (MCPServerName.ADDRESS, "z_getnewaddress"),
    "mcp.address.z_listaddresses":          (MCPServerName.ADDRESS, "z_listaddresses"),
    "mcp.marketplace.listopenoffers":       (MCPServerName.MARKETPLACE, "listopenoffers"),
}


class MCPRouter:
    """
    Routes agent capability requests to MCP servers or falls back to
    direct CLI.  Manages lifecycle of all MCP server connections.

    Routing logic
    -------------
    1. If MCP is disabled → always use direct CLI.
    2. If the capability is a write operation and MCP is available → MCP
       (for spending limits + audit logging).
    3. If the capability is MCP-exclusive → MCP only.
    4. For read operations → prefer MCP, fallback to CLI.
    """

    def __init__(
        self,
        chain: str = "VRSC",
        enabled: bool = True,
        read_only: bool = False,
        servers: Optional[List[MCPServerName]] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ):
        self.chain = chain
        self.enabled = enabled
        self.read_only = read_only
        self._env_overrides = env_overrides or {}

        # Which servers to start — default is all 7
        self._server_list = servers or list(MCPServerName)

        # Server connections
        self._connections: Dict[MCPServerName, MCPServerConnection] = {}

        # All discovered tools across all servers
        self._all_tools: Dict[str, MCPTool] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> Dict[MCPServerName, MCPServerStatus]:
        """Start all configured MCP servers and discover their tools."""
        if not self.enabled:
            logger.info("MCP routing disabled.")
            return {}

        statuses: Dict[MCPServerName, MCPServerStatus] = {}

        for server_name in self._server_list:
            env = dict(self._env_overrides)
            if self.read_only:
                env["VERUSIDX_READ_ONLY"] = "true"

            conn = MCPServerConnection(server_name, env=env)
            status = MCPServerStatus(server=server_name)

            try:
                await conn.start()
                self._connections[server_name] = conn
                self._all_tools.update(conn.tools)
                status.connected = True
                status.tools = list(conn.tools.keys())
            except Exception as exc:
                logger.warning(
                    "MCP server %s failed to start: %s", server_name.value, exc
                )
                status.error = str(exc)

            statuses[server_name] = status

        logger.info(
            "MCP router initialized: %d/%d servers, %d tools",
            sum(1 for s in statuses.values() if s.connected),
            len(self._server_list),
            len(self._all_tools),
        )
        return statuses

    async def shutdown(self) -> None:
        """Stop all MCP server processes."""
        for conn in self._connections.values():
            try:
                await conn.stop()
            except Exception as exc:
                logger.warning("Error stopping MCP server %s: %s", conn.server_name.value, exc)
        self._connections.clear()
        self._all_tools.clear()
        logger.info("MCP router shut down.")

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def should_route_to_mcp(self, capability: str) -> bool:
        """
        Determine whether a capability request should be routed to MCP.

        Returns True when:
        - MCP is enabled AND the relevant server is connected AND either:
          a) The capability is a write operation (safety: spending limits + audit)
          b) The capability is MCP-exclusive (no CLI handler)
          c) The capability has a mapping and the server is healthy
        """
        if not self.enabled:
            return False

        # MCP-exclusive — always route if available
        if capability in MCP_EXCLUSIVE_TOOLS:
            server_name, _ = MCP_EXCLUSIVE_TOOLS[capability]
            return server_name in self._connections

        # Mapped capability — prefer MCP for writes, allow for reads
        if capability in CAPABILITY_TO_MCP:
            server_name, _ = CAPABILITY_TO_MCP[capability]
            return server_name in self._connections

        return False

    def get_mcp_target(self, capability: str) -> Optional[Tuple[MCPServerName, str]]:
        """Get the MCP server and tool name for a capability."""
        if capability in MCP_EXCLUSIVE_TOOLS:
            return MCP_EXCLUSIVE_TOOLS[capability]
        if capability in CAPABILITY_TO_MCP:
            return CAPABILITY_TO_MCP[capability]
        return None

    async def call_tool(
        self,
        server_name: MCPServerName,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPCallResult:
        """
        Call an MCP tool directly on a specific server.
        Injects the ``chain`` parameter automatically.
        """
        conn = self._connections.get(server_name)
        if not conn or not conn.connected:
            return MCPCallResult(
                success=False,
                error=f"MCP server {server_name.value} not connected",
            )

        # Inject chain parameter (required by all verusidx tools)
        if "chain" not in arguments:
            arguments["chain"] = self.chain

        return await conn.call_tool(tool_name, arguments)

    async def route_capability(
        self, capability: str, params: Dict[str, Any]
    ) -> Optional[MCPCallResult]:
        """
        Attempt to route a capability to an MCP server.

        Returns MCPCallResult if routed, None if the capability should
        be handled by the direct CLI fallback.
        """
        target = self.get_mcp_target(capability)
        if not target:
            return None

        server_name, tool_name = target
        if server_name not in self._connections:
            return None

        # Build MCP arguments from agent params
        mcp_args = self._transform_params(capability, tool_name, params)

        result = await self.call_tool(server_name, tool_name, mcp_args)

        if not result.success:
            # For write operations, do NOT fall back to CLI —
            # better to fail safely than bypass spending limits
            if capability in WRITE_CAPABILITIES:
                logger.error(
                    "MCP write operation failed (no CLI fallback): %s → %s: %s",
                    capability, tool_name, result.error,
                )
                return result
            # For reads, return None to signal fallback
            logger.warning(
                "MCP read failed, falling back to CLI: %s → %s: %s",
                capability, tool_name, result.error,
            )
            return None

        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return MCP router status for health reporting."""
        server_statuses = {}
        for name, conn in self._connections.items():
            server_statuses[name.value] = {
                "connected": conn.connected,
                "tools": list(conn.tools.keys()),
            }
        return {
            "enabled": self.enabled,
            "chain": self.chain,
            "read_only": self.read_only,
            "servers_connected": sum(1 for c in self._connections.values() if c.connected),
            "servers_total": len(self._server_list),
            "total_tools": len(self._all_tools),
            "servers": server_statuses,
        }

    def list_all_capabilities(self) -> List[str]:
        """Return all capabilities available via MCP (mapped + exclusive)."""
        caps = list(CAPABILITY_TO_MCP.keys())
        caps.extend(MCP_EXCLUSIVE_TOOLS.keys())
        return caps

    # ------------------------------------------------------------------
    # Parameter transformation
    # ------------------------------------------------------------------

    def _transform_params(
        self, capability: str, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform agent capability params into MCP tool arguments.

        The agent's internal parameter names don't always match the MCP tool
        input schemas.  This method handles the translation.
        """
        chain = params.pop("chain", self.chain)
        args: Dict[str, Any] = {"chain": chain}

        # --- Identity creation (two-step in MCP) ---
        if capability == "verus.identity.create":
            args.update({
                "name": params.get("name", ""),
                "primaryaddresses": params.get("primary_addresses", []),
                "minimumsignatures": params.get("minimumsignatures", 1),
            })
            if params.get("recovery_authority"):
                args["recoveryauthority"] = params["recovery_authority"]
            if params.get("revocation_authority"):
                args["revocationauthority"] = params["revocation_authority"]
            if params.get("private_address"):
                args["privateaddress"] = params["private_address"]
            if params.get("content_multimap"):
                args["contentmultimap"] = params["content_multimap"]
            return args

        # --- Identity update ---
        if capability == "verus.identity.update":
            args["name"] = params.get("name", "")
            updates = params.get("updates", {})
            args.update(updates)
            return args

        # --- Identity vault (timelock) ---
        if capability == "verus.identity.vault":
            args["identity"] = params.get("name", "")
            action = params.get("action", "lock")
            if action == "lock":
                args["lockblocks"] = params.get("timelock_blocks", 1440)
            else:
                args["unlock"] = True
            return args

        # --- Currency send ---
        if capability == "verus.currency.send":
            args["fromaddress"] = params.get("from_address", "*")
            args["outputs"] = [{
                "currency": params.get("currency", "VRSC"),
                "address": params.get("to_address", ""),
                "amount": params.get("amount", 0),
            }]
            return args

        # --- Currency convert ---
        if capability == "verus.currency.convert":
            output: Dict[str, Any] = {
                "currency": params.get("from_currency", "VRSC"),
                "convertto": params.get("to_currency", ""),
                "amount": params.get("amount", 0),
                "address": params.get("destination", params.get("from_address", "*")),
            }
            if params.get("via"):
                output["via"] = params["via"]
            args["fromaddress"] = params.get("from_address", "*")
            args["outputs"] = [output]
            return args

        # --- Bridge cross ---
        if capability == "verus.bridge.cross":
            output = {
                "currency": params.get("currency", "VRSC"),
                "address": params.get("destination", ""),
                "amount": params.get("amount", 0),
            }
            if params.get("convertto"):
                output["convertto"] = params["convertto"]
            if params.get("via"):
                output["via"] = params["via"]
            if params.get("exportto"):
                output["exportto"] = params["exportto"]
            args["fromaddress"] = params.get("from_address", "*")
            args["outputs"] = [output]
            return args

        # --- Estimate conversion ---
        if capability == "verus.currency.estimate":
            args.update({
                "currency": params.get("from_currency", "VRSC"),
                "convertto": params.get("to_currency", ""),
                "amount": params.get("amount", 0),
            })
            if params.get("via"):
                args["via"] = params["via"]
            return args

        # --- Currency launch ---
        if capability == "verus.currency.launch":
            args.update(params.get("definition", {}))
            return args

        # --- Marketplace offers ---
        if capability == "verus.marketplace.make_offer":
            args.update({
                "fromaddress": params.get("change_address", "*"),
                "offer": params.get("offer", {}),
                "for": params.get("for_item", {}),
            })
            if params.get("expiry"):
                args["expiry"] = params["expiry"]
            return args

        if capability == "verus.marketplace.take_offer":
            args.update({
                "txid": params.get("offer_txid", ""),
                "fromaddress": params.get("change_address", "*"),
                "deliver": params.get("deliver", {}),
                "accept": params.get("accept", {}),
            })
            return args

        if capability == "verus.marketplace.list_open_offers":
            args.update({
                "currencyorid": params.get("currency", "VRSC"),
                "iscurrency": params.get("is_buy", True),
            })
            return args

        if capability == "verus.marketplace.close_offers":
            args["txids"] = params.get("offer_txids", [])
            return args

        # --- Messaging / signdata ---
        if capability == "verus.messaging.send_encrypted":
            import json as _json
            message_payload = _json.dumps({
                "type": params.get("msg_type", "message"),
                "from": params.get("sender_identity", ""),
                "body": params.get("body", ""),
            }, separators=(",", ":"))
            args.update({
                "address": params.get("sender_identity", ""),
                "message": message_payload,
                "encrypttoaddress": params.get("recipient_z_address", ""),
            })
            return args

        if capability == "verus.messaging.receive_decrypt":
            args.update({
                "datadescriptor": {
                    "version": 1,
                    "flags": 5,
                    "objectdata": params.get("objectdata_hex", ""),
                    "epk": params.get("epk", ""),
                },
                "ivk": params.get("ivk", ""),
            })
            return args

        # --- Storage retrieve ---
        if capability in ("verus.storage.retrieve", "verus.storage.retrieve_data_wrapper"):
            args.update({
                "name": params.get("identity_name", ""),
            })
            if params.get("key"):
                args["vdxfkey"] = params["key"]
            if params.get("height_start"):
                args["fromblock"] = params["height_start"]
            if params.get("height_end"):
                args["toblock"] = params["height_end"]
            return args

        # --- Market monitor ---
        if capability == "verus.market.monitor":
            args["currencyname"] = params.get("basket_name", "VRSC")
            return args

        # --- Default: pass through all params ---
        args.update(params)
        return args
