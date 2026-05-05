"""
Verus Blockchain Specialist Agent — Main Agent Class

Integrates all Verus modules (CLI, VerusID, DeFi, Login, Storage) into
a single autonomous agent that registers with the UAI Neural Swarm
Coordinator and exposes Verus capabilities to the swarm task queue.

Follows the canonical AutonomousAgent pattern from neural_swarm_intelligence.py
and the LegalRAGAgent pattern for health monitoring, messaging, and learning.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import numpy as np

from verus_agent.cli_wrapper import VerusCLI, VerusError
from verus_agent.config import (
    AGENT_CAPABILITIES,
    AGENT_CATEGORY,
    AGENT_DOMAIN,
    AGENT_ROLE,
    VerusConfig,
)
from verus_agent.defi import VerusDeFiManager
from verus_agent.ip_protection import VerusIPProtection
from verus_agent.login import VerusLoginManager
from verus_agent.marketplace import VerusAgentMarketplace
from verus_agent.mcp_client import (
    MCPRouter,
    MCPServerName,
    MCP_EXCLUSIVE_TOOLS,
    WRITE_CAPABILITIES,
)
from verus_agent.mobile import VerusMobileHelper
from verus_agent.provenance import VerusProvenanceManager
from verus_agent.reputation import VerusReputationSystem
from verus_agent.storage import VerusStorageManager
from verus_agent.swarm_security import VerusSwarmSecurity
from verus_agent.vdxf_builder import ContentMultiMapBuilder, DataDescriptorBuilder
from verus_agent.verusid import VerusIDManager

logger = logging.getLogger("verus_agent")


# ---------------------------------------------------------------------------
# State & Specialization enums
# ---------------------------------------------------------------------------

class VerusAgentState(str, Enum):
    """Agent operational states (matching Neural Swarm pattern)."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    PROCESSING_TASK = "processing_task"
    EXECUTING_CLI = "executing_cli"
    MANAGING_IDENTITY = "managing_identity"
    EXECUTING_DEFI = "executing_defi"
    AUTHENTICATING = "authenticating"
    STORING_DATA = "storing_data"
    MONITORING_MARKET = "monitoring_market"
    COLLABORATING = "collaborating"
    LEARNING = "learning"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class VerusSpecialization(str, Enum):
    """Verus agent sub-specializations."""
    IDENTITY_MANAGER = "identity_manager"
    DEFI_OPERATOR = "defi_operator"
    MARKET_MONITOR = "market_monitor"
    STORAGE_MANAGER = "storage_manager"
    AUTH_PROVIDER = "auth_provider"
    BRIDGE_OPERATOR = "bridge_operator"
    FULL_STACK = "full_stack"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AgentMessage:
    """Inter-agent communication message (matching Neural Swarm pattern)."""
    sender_id: str
    receiver_id: str
    message_type: str  # "task", "result", "collaboration_request", "health"
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class TaskResult:
    """Result of a swarm task processed by this agent."""
    task_id: str
    capability: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Main Agent
# ---------------------------------------------------------------------------

class VerusBlockchainAgent:
    """
    Verus Blockchain Specialist Agent for the UAI Neural Swarm.

    Capabilities:
        verus.identity.create   — Create a new VerusID
        verus.identity.update   — Update VerusID data/permissions
        verus.identity.vault    — Lock/unlock VerusID vault
        verus.currency.launch   — Launch a new currency on Verus
        verus.currency.convert  — Execute a DeFi conversion
        verus.currency.send     — Send currency with optional conversion
        verus.currency.estimate — Estimate conversion output
        verus.storage.store     — Store encrypted file on-chain
        verus.storage.retrieve  — Retrieve stored file
        verus.login.authenticate — VerusID-based authentication
        verus.login.validate    — Validate a VerusID login session
        verus.bridge.cross      — Execute Ethereum bridge crossing
        verus.market.monitor    — Monitor basket reserves and pricing
        verus.cli.execute       — Execute arbitrary Verus CLI command

    Usage::

        config = VerusConfig(network=VerusNetwork.TESTNET)
        agent = VerusBlockchainAgent(config)
        await agent.initialize()
        await agent.start()
    """

    def __init__(
        self,
        config: Optional[VerusConfig] = None,
        specialization: VerusSpecialization = VerusSpecialization.FULL_STACK,
        intelligence_level: float = 0.85,
    ):
        self.config = config or VerusConfig()
        self.agent_id = self.config.agent_id
        self.agent_type = "verus_blockchain_agent"
        self.category = AGENT_CATEGORY
        self.role = AGENT_ROLE
        self.domain = AGENT_DOMAIN
        self.specialization = specialization
        self.intelligence_level = intelligence_level

        # State
        self.state = VerusAgentState.INITIALIZING
        self._running = False

        # Modules (initialized in initialize())
        # Using Any initially; set to proper types in initialize()
        self.cli: VerusCLI = None  # type: ignore[assignment]
        self.identity_manager: VerusIDManager = None  # type: ignore[assignment]
        self.defi_manager: VerusDeFiManager = None  # type: ignore[assignment]
        self.login_manager: VerusLoginManager = None  # type: ignore[assignment]
        self.storage_manager: VerusStorageManager = None  # type: ignore[assignment]

        # Optional extension modules (Issue #9: VerusID security/monetization/IP)
        self.swarm_security: Optional[VerusSwarmSecurity] = None
        self.marketplace: Optional[VerusAgentMarketplace] = None
        self.ip_protection: Optional[VerusIPProtection] = None
        self.mobile_helper: Optional[VerusMobileHelper] = None
        self.provenance: Optional[VerusProvenanceManager] = None

        # MCP router (initialized in initialize() when enabled)
        self.mcp_router: Optional[MCPRouter] = None

        # Learning & adaptation (matching Neural Swarm pattern)
        self.experience_history: List[Dict[str, Any]] = []
        self.learning_rate = 0.1
        self.decision_weights = np.random.dirichlet(np.ones(len(AGENT_CAPABILITIES)))
        self.collaboration_history: List[Dict[str, Any]] = []

        # Communication
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}

        # Performance metrics
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.accuracy_score = 1.0
        self.collaboration_effectiveness = 0.0
        self.last_activity = datetime.now()
        self.start_time: Optional[datetime] = None
        self._total_processing_ms = 0.0

        # Autonomous parameters
        self.curiosity_factor = 0.3
        self.cooperation_tendency = 0.8
        self.innovation_capability = 0.5

        # Capability dispatch table
        self._capability_handlers: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize all sub-modules and connect to the Verus daemon."""
        logger.info("Initializing Verus Blockchain Specialist Agent...")
        self.state = VerusAgentState.INITIALIZING

        try:
            # 1. CLI wrapper
            self.cli = VerusCLI(self.config)
            await self.cli.initialize()

            # 2. Sub-modules
            self.identity_manager = VerusIDManager(self.cli)
            self.defi_manager = VerusDeFiManager(
                self.cli,
                destination_address=self.config.destination_address,
                trade_threshold=self.config.trade_threshold,
            )
            self.login_manager = VerusLoginManager(self.cli)
            self.storage_manager = VerusStorageManager(self.cli)

            # 3. Optional extension modules (enabled via env vars)
            self.swarm_security = VerusSwarmSecurity(
                self.cli, self.identity_manager
            )
            self.marketplace = VerusAgentMarketplace(
                self.cli, self.identity_manager
            )
            self.ip_protection = VerusIPProtection(
                self.cli, self.identity_manager
            )
            self.reputation = VerusReputationSystem(
                self.cli, self.identity_manager
            )
            self.mobile_helper = VerusMobileHelper(
                agent_identity=self.config.agent_id,
            )

            # 3b. Provenance module (uses cli + identity + storage)
            self.provenance = VerusProvenanceManager(
                self.cli, self.identity_manager, self.storage_manager
            )

            # 4. Build capability dispatch table
            self._build_capability_handlers()

            # 5. MCP router (optional — adds spending limits, audit, new tools)
            if self.config.mcp_enabled:
                await self._initialize_mcp()

            ext_status = []
            if self.swarm_security.is_enabled:
                ext_status.append("swarm_security")
            if self.marketplace.enabled:
                ext_status.append("marketplace")
            if self.ip_protection.enabled:
                ext_status.append("ip_protection")
            if self.reputation.enabled:
                ext_status.append("reputation")
            if self.mcp_router and self.mcp_router.enabled:
                ext_status.append("mcp")

            self.state = VerusAgentState.IDLE
            self.start_time = datetime.now()
            logger.info(
                "Verus agent initialized. Network=%s, Daemon=%s, Capabilities=%d, Extensions=%s",
                self.config.network.value,
                self.cli.daemon_version or "unknown",
                len(self._capability_handlers),
                ext_status or "none",
            )

        except Exception as exc:
            self.state = VerusAgentState.ERROR
            logger.error("Agent initialization failed: %s", exc)
            raise

    async def start(self) -> None:
        """Start the agent: register with swarm and begin processing tasks."""
        if self.state != VerusAgentState.IDLE:
            raise RuntimeError(f"Cannot start agent in state {self.state}")

        self._running = True

        # Register with UAI swarm unless explicitly disabled.
        if self.config.uai_integration_enabled:
            await self._register_with_swarm()
        else:
            logger.info("UAI integration disabled; skipping swarm registration.")

        # Start background loops
        asyncio.create_task(self._task_processing_loop())
        asyncio.create_task(self._health_reporting_loop())
        asyncio.create_task(self._message_processing_loop())

        logger.info("Verus agent started and listening for tasks.")

    async def shutdown(self) -> None:
        """Gracefully shut down the agent."""
        logger.info("Shutting down Verus agent...")
        self._running = False
        self.state = VerusAgentState.SHUTDOWN
        if self.mcp_router:
            await self.mcp_router.shutdown()
        if self.cli:
            await self.cli.close()
        logger.info("Verus agent shut down.")

    # ------------------------------------------------------------------
    # Task processing (swarm interface)
    # ------------------------------------------------------------------

    async def process_task(self, task: Dict[str, Any]) -> TaskResult:
        """
        Process a task from the swarm task queue.

        Parameters
        ----------
        task : dict
            Must contain ``capability`` (str) and ``params`` (dict).
        """
        task_id = task.get("task_id", str(uuid.uuid4()))
        capability = task.get("capability", "")
        params = task.get("params", {})

        start = time.monotonic()
        self.state = VerusAgentState.PROCESSING_TASK
        self.last_activity = datetime.now()

        logger.info("Processing task %s: %s", task_id, capability)

        try:
            # --- MCP routing: prefer MCP for safety-critical operations ---
            mcp_result = None
            if self.mcp_router and self.mcp_router.should_route_to_mcp(capability):
                mcp_result = await self.mcp_router.route_capability(capability, dict(params))

            if mcp_result is not None and mcp_result.success:
                # MCP handled it successfully
                result = mcp_result.content
                if isinstance(result, str):
                    result = {"result": result}
                elif not isinstance(result, dict):
                    result = {"result": result}
                result["_routed_via"] = "mcp"
            elif mcp_result is not None and not mcp_result.success and capability in WRITE_CAPABILITIES:
                # Write operation failed via MCP — do NOT fall back (safety)
                raise RuntimeError(
                    f"MCP write operation failed (no CLI fallback for safety): {mcp_result.error}"
                )
            else:
                # Direct CLI path (fallback or MCP not available)
                handler = self._capability_handlers.get(capability)
                if not handler:
                    raise ValueError(f"Unknown capability: {capability}")
                result = await handler(**params)
            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed
            self.tasks_completed += 1

            # Log experience for learning
            await self._log_experience(capability, True, elapsed)

            self.state = VerusAgentState.IDLE
            return TaskResult(
                task_id=task_id,
                capability=capability,
                success=True,
                result=result,
                processing_time_ms=round(elapsed, 2),
            )

        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            self.tasks_failed += 1
            await self._log_experience(capability, False, elapsed)

            self.state = VerusAgentState.IDLE
            logger.error("Task %s failed: %s", task_id, exc)
            return TaskResult(
                task_id=task_id,
                capability=capability,
                success=False,
                error=str(exc),
                processing_time_ms=round(elapsed, 2),
            )

    # ------------------------------------------------------------------
    # Status / Health (matching existing agent patterns)
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return full agent status (for health monitoring integration)."""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        total_tasks = self.tasks_completed + self.tasks_failed
        success_rate = self.tasks_completed / total_tasks if total_tasks > 0 else 1.0
        avg_latency = self._total_processing_ms / self.tasks_completed if self.tasks_completed > 0 else 0

        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "category": self.category,
            "role": self.role,
            "domain": self.domain,
            "specialization": self.specialization.value,
            "state": self.state.value,
            "intelligence_level": self.intelligence_level,
            "network": self.config.network.value,
            "daemon_version": self.cli.daemon_version if self.cli else None,
            "capabilities": AGENT_CAPABILITIES,
            "metrics": {
                "tasks_completed": self.tasks_completed,
                "tasks_failed": self.tasks_failed,
                "success_rate": round(success_rate, 4),
                "accuracy_score": round(self.accuracy_score, 4),
                "avg_latency_ms": round(avg_latency, 2),
                "cli_avg_latency_ms": self.cli.avg_latency_ms if self.cli else 0,
                "cli_call_count": self.cli.call_count if self.cli else 0,
                "collaboration_effectiveness": round(self.collaboration_effectiveness, 4),
                "uptime_seconds": round(uptime, 1),
                "active_sessions": self.login_manager.active_session_count if self.login_manager else 0,
            },
            "learning": {
                "experience_count": len(self.experience_history),
                "learning_rate": self.learning_rate,
                "curiosity_factor": self.curiosity_factor,
                "cooperation_tendency": self.cooperation_tendency,
            },
            "last_activity": self.last_activity.isoformat(),
            "extensions": {
                "swarm_security": self.swarm_security.get_security_status() if self.swarm_security else {"enabled": False},
                "marketplace": self.marketplace.get_marketplace_status() if self.marketplace else {"enabled": False},
                "ip_protection": self.ip_protection.get_protection_status() if self.ip_protection else {"enabled": False},
                "mcp": self.mcp_router.get_status() if self.mcp_router else {"enabled": False},
            },
        }

    # ------------------------------------------------------------------
    # Inter-agent messaging
    # ------------------------------------------------------------------

    async def send_message(self, message: AgentMessage) -> None:
        """Send a message to another agent via the swarm."""
        logger.debug("Sending message to %s: %s", message.receiver_id, message.message_type)
        # In production, this would go through the swarm communication channel
        # For now, log it for the swarm coordinator to pick up
        self.last_activity = datetime.now()

    async def receive_message(self, message: AgentMessage) -> None:
        """Receive and queue a message from another agent."""
        await self.message_queue.put(message)

    # ------------------------------------------------------------------
    # Learning & adaptation
    # ------------------------------------------------------------------

    def adapt_behavior(self) -> None:
        """Adjust decision weights based on experience history."""
        if len(self.experience_history) < 5:
            return

        recent = self.experience_history[-20:]
        successes = [e for e in recent if e["success"]]
        success_rate = len(successes) / len(recent)

        # Reinforce weights for successful capabilities
        for exp in successes:
            cap = exp["capability"]
            if cap in AGENT_CAPABILITIES:
                idx = AGENT_CAPABILITIES.index(cap)
                self.decision_weights[idx] *= (1 + self.learning_rate)

        # Normalize
        total = self.decision_weights.sum()
        if total > 0:
            self.decision_weights /= total

        # Adjust learning rate
        if success_rate > 0.8:
            self.learning_rate = max(0.01, self.learning_rate * 0.95)
        else:
            self.learning_rate = min(0.5, self.learning_rate * 1.1)

        self.accuracy_score = success_rate
        logger.debug("Adapted behavior: accuracy=%.3f, lr=%.4f", success_rate, self.learning_rate)

    # ------------------------------------------------------------------
    # Internal: MCP initialization
    # ------------------------------------------------------------------

    async def _initialize_mcp(self) -> None:
        """Initialize the MCP router and register MCP-exclusive capabilities."""
        # Parse server list from config
        servers = None
        if self.config.mcp_servers:
            try:
                servers = [
                    MCPServerName(s.strip())
                    for s in self.config.mcp_servers.split(",")
                    if s.strip()
                ]
            except ValueError as exc:
                logger.warning("Invalid MCP server name in config: %s", exc)
                servers = None

        # Build env overrides for MCP processes
        env_overrides: Dict[str, str] = {}
        if self.config.mcp_audit_dir:
            env_overrides["VERUSIDX_AUDIT_DIR"] = self.config.mcp_audit_dir
        if self.config.mcp_spending_limits_path:
            env_overrides["VERUSIDX_SPENDING_LIMITS_PATH"] = self.config.mcp_spending_limits_path
        if self.config.mcp_data_dir:
            env_overrides["VERUSIDX_DATA_DIR"] = self.config.mcp_data_dir
        if self.config.mcp_extra_chains:
            env_overrides["VERUSIDX_EXTRA_CHAINS"] = self.config.mcp_extra_chains
        if self.config.mcp_bin_path:
            env_overrides["VERUSIDX_BIN_PATH"] = self.config.mcp_bin_path

        self.mcp_router = MCPRouter(
            chain=self.config.mcp_chain,
            enabled=True,
            read_only=self.config.mcp_read_only,
            servers=servers,
            env_overrides=env_overrides if env_overrides else None,
        )

        statuses = await self.mcp_router.initialize()

        connected = sum(1 for s in statuses.values() if s.connected)
        total = len(statuses)
        logger.info("MCP router: %d/%d servers connected", connected, total)

        # Register MCP-exclusive capabilities as agent handlers
        for cap_name, (server_name, tool_name) in MCP_EXCLUSIVE_TOOLS.items():
            if server_name in {s.server for s in statuses.values() if s.connected}:
                self._capability_handlers[cap_name] = self._make_mcp_handler(
                    server_name, tool_name
                )

        if connected > 0:
            logger.info(
                "MCP-exclusive capabilities registered: %d",
                sum(
                    1 for cap in MCP_EXCLUSIVE_TOOLS
                    if cap in self._capability_handlers
                ),
            )

    def _make_mcp_handler(self, server_name: MCPServerName, tool_name: str):
        """Create a capability handler that delegates to an MCP tool."""
        async def _handler(**params) -> Dict[str, Any]:
            result = await self.mcp_router.call_tool(server_name, tool_name, params)
            if result.success:
                content = result.content
                if isinstance(content, dict):
                    return content
                return {"result": content, "_routed_via": "mcp"}
            return {"success": False, "error": result.error, "_routed_via": "mcp"}
        return _handler

    # ------------------------------------------------------------------
    # Internal: capability dispatch
    # ------------------------------------------------------------------

    def _build_capability_handlers(self) -> None:
        """Build the mapping from capability strings to handler methods."""
        self._capability_handlers = {
            "verus.identity.get": self._handle_identity_get,
            "verus.identity.create": self._handle_identity_create,
            "verus.identity.update": self._handle_identity_update,
            "verus.identity.vault": self._handle_identity_vault,
            "verus.currency.launch": self._handle_currency_launch,
            "verus.currency.convert": self._handle_currency_convert,
            "verus.currency.send": self._handle_currency_send,
            "verus.currency.estimate": self._handle_currency_estimate,
            "verus.storage.store": self._handle_storage_store,
            "verus.storage.retrieve": self._handle_storage_retrieve,
            "verus.storage.store_data_wrapper": self._handle_storage_store_data_wrapper,
            "verus.storage.store_sendcurrency": self._handle_storage_store_sendcurrency,
            "verus.storage.retrieve_data_wrapper": self._handle_storage_retrieve_data_wrapper,
            "verus.login.authenticate": self._handle_login_authenticate,
            "verus.login.validate": self._handle_login_validate,
            "verus.bridge.cross": self._handle_bridge_cross,
            "verus.market.monitor": self._handle_market_monitor,
            "verus.cli.execute": self._handle_cli_execute,
            # Encrypted messaging (z-address based)
            "verus.messaging.send_encrypted": self._handle_messaging_send_encrypted,
            "verus.messaging.receive_decrypt": self._handle_messaging_receive_decrypt,
            # Trust / reputation (setidentitytrust / setcurrencytrust)
            "verus.trust.set_identity_trust": self._handle_trust_set_identity,
            "verus.trust.set_currency_trust": self._handle_trust_set_currency,
            "verus.trust.get_ratings": self._handle_trust_get_ratings,
            # Marketplace atomic swaps (makeoffer/takeoffer)
            "verus.marketplace.make_offer": self._handle_marketplace_make_offer,
            "verus.marketplace.take_offer": self._handle_marketplace_take_offer,
            "verus.marketplace.list_open_offers": self._handle_marketplace_list_open_offers,
            "verus.marketplace.close_offers": self._handle_marketplace_close_offers,
            # Mining & staking
            "verus.mining.start": self._handle_mining_start,
            "verus.mining.info": self._handle_mining_info,
            "verus.staking.status": self._handle_staking_status,
            # VDXF Data Pipeline (Phase 5)
            "verus.data.sign": self._handle_data_sign,
            "verus.data.verify": self._handle_data_verify,
            "verus.data.decrypt": self._handle_data_decrypt,
            "verus.data.getvdxfid": self._handle_data_getvdxfid,
            "verus.data.list_received": self._handle_data_list_received,
            "verus.data.export_viewingkey": self._handle_data_export_viewingkey,
            "verus.data.import_viewingkey": self._handle_data_import_viewingkey,
            # VDXF Object Builder (Phase 5)
            "verus.data.build_vdxf": self._handle_data_build_vdxf,
        }

        # --- Extension handlers (registered when modules are enabled) ---

        if self.swarm_security and self.swarm_security.is_enabled:
            self._capability_handlers.update({
                "verus.security.register": self._handle_security_register,
                "verus.security.verify": self._handle_security_verify,
                "verus.security.revoke": self._handle_security_revoke,
                "verus.security.status": self._handle_security_status,
            })

        if self.marketplace and self.marketplace.enabled:
            self._capability_handlers.update({
                "verus.marketplace.register_product": self._handle_mp_register_product,
                "verus.marketplace.issue_license": self._handle_mp_issue_license,
                "verus.marketplace.verify_license": self._handle_mp_verify_license,
                "verus.marketplace.list_offers": self._handle_mp_list_offers,
                "verus.marketplace.create_invoice": self._handle_mp_create_invoice,
                "verus.marketplace.discover": self._handle_mp_discover,
                "verus.marketplace.search": self._handle_mp_search,
            })

        if self.ip_protection and self.ip_protection.enabled:
            self._capability_handlers.update({
                "verus.ip.register_model": self._handle_ip_register_model,
                "verus.ip.verify_integrity": self._handle_ip_verify_integrity,
                "verus.ip.get_model_info": self._handle_ip_get_model_info,
                "verus.ip.register_storage": self._handle_ip_register_storage,
                "verus.ip.encrypt_model": self._handle_ip_encrypt_model,
                "verus.ip.decrypt_model": self._handle_ip_decrypt_model,
                "verus.ip.full_protect": self._handle_ip_full_protect,
            })

        if hasattr(self, "reputation") and self.reputation and self.reputation.enabled:
            self._capability_handlers.update({
                "verus.reputation.attest": self._handle_rep_attest,
                "verus.reputation.query": self._handle_rep_query,
                "verus.reputation.leaderboard": self._handle_rep_leaderboard,
                "verus.reputation.verify": self._handle_rep_verify_attestation,
            })

        if self.defi_manager:
            self._capability_handlers.update({
                "verus.defi.create_revenue_basket": self._handle_defi_revenue_basket,
                "verus.defi.distribute_revenue": self._handle_defi_distribute_revenue,
                "verus.defi.define_pbaas_chain": self._handle_defi_pbaas_chain,
            })

        if self.marketplace and self.marketplace.enabled:
            self._capability_handlers["verus.marketplace.verify_license_cross_chain"] = (
                self._handle_mp_verify_license_cross_chain
            )

        if self.ip_protection and self.ip_protection.enabled:
            self._capability_handlers.update({
                "verus.ip.generate_watermark": self._handle_ip_generate_watermark,
                "verus.ip.verify_watermark": self._handle_ip_verify_watermark,
            })

        if self.mobile_helper:
            self._capability_handlers.update({
                "verus.mobile.payment_uri": self._handle_mobile_payment_uri,
                "verus.mobile.login_consent": self._handle_mobile_login_consent,
                "verus.mobile.purchase_link": self._handle_mobile_purchase_link,
                "verus.mobile.generic_request_link": self._handle_mobile_generic_request_link,
                "verus.mobile.identity_update_request_link": self._handle_mobile_identity_update_request_link,
                "verus.mobile.app_encryption_request_link": self._handle_mobile_app_encryption_request_link,
                "verus.mobile.capabilities": self._handle_mobile_capabilities,
            })

        # --- Provenance handlers (Phase 5) ---
        if self.provenance:
            self._capability_handlers.update({
                "verus.provenance.create_nft": self._handle_provenance_create_nft,
                "verus.provenance.store_descriptors": self._handle_provenance_store_descriptors,
                "verus.provenance.sign_mmr": self._handle_provenance_sign_mmr,
                "verus.provenance.deliver_encrypted": self._handle_provenance_deliver_encrypted,
                "verus.provenance.verify": self._handle_provenance_verify,
                "verus.provenance.list_offer": self._handle_provenance_list_offer,
            })

    # --- Identity handlers ---

    async def _handle_identity_get(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.MANAGING_IDENTITY
        name_or_id = (
            params.get("name_or_id")
            or params.get("iaddress")
            or params.get("identity")
            or params.get("name")
        )
        if not name_or_id:
            raise ValueError(
                "verus.identity.get requires one of: name_or_id, iaddress, identity, name"
            )

        identity = await self.identity_manager.get_identity(
            name_or_id,
            use_cache=params.get("use_cache", False),
        )
        return {
            "name": identity.name,
            "full_name": identity.full_name,
            "identity_address": identity.identity_address,
            "i_address": identity.i_address,
            "parent": identity.parent,
            "version": identity.version,
            "flags": identity.flags,
            "primary_addresses": identity.primary_addresses,
            "recovery_authority": identity.recovery_authority,
            "revocation_authority": identity.revocation_authority,
            "private_address": identity.private_address,
            "timelock": identity.timelock,
            "minimumsignatures": identity.minimumsignatures,
            "content_map": identity.content_map,
            "content_multimap": identity.content_multimap,
        }

    async def _handle_identity_create(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.MANAGING_IDENTITY
        result = await self.identity_manager.create_identity(
            name=params["name"],
            primary_addresses=params["primary_addresses"],
            recovery_authority=params.get("recovery_authority"),
            revocation_authority=params.get("revocation_authority"),
            private_address=params.get("private_address"),
            content_multimap=params.get("content_multimap"),
            minimumsignatures=params.get("minimumsignatures", 1),
        )
        return {"operation": result.operation, "success": result.success,
                "txid": result.txid, "error": result.error}

    async def _handle_identity_update(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.MANAGING_IDENTITY
        result = await self.identity_manager.update_identity(
            name=params["name"],
            updates=params["updates"],
        )
        return {"operation": result.operation, "success": result.success,
                "txid": result.txid, "error": result.error}

    async def _handle_identity_vault(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.MANAGING_IDENTITY
        action = params.get("action", "lock")
        if action == "lock":
            result = await self.identity_manager.lock_vault(
                params["name"], params.get("timelock_blocks", 1440)
            )
        else:
            result = await self.identity_manager.unlock_vault(params["name"])
        return {"operation": result.operation, "success": result.success,
                "txid": result.txid, "error": result.error}

    # --- Currency / DeFi handlers ---

    async def _handle_currency_launch(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.EXECUTING_DEFI
        result = await self.defi_manager.launch_currency(params["definition"])
        return {"operation": result.operation, "success": result.success,
                "txid": result.txid, "error": result.error}

    async def _handle_currency_convert(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.EXECUTING_DEFI
        result = await self.defi_manager.convert(
            from_currency=params["from_currency"],
            to_currency=params["to_currency"],
            amount=params["amount"],
            via=params.get("via", ""),
            destination=params.get("destination"),
            vdxf_tag=params.get("vdxf_tag"),
        )
        return {"operation": result.operation, "success": result.success,
                "txid": result.txid, "error": result.error}

    async def _handle_currency_send(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.EXECUTING_DEFI
        result = await self.defi_manager.send_currency(
            currency=params["currency"],
            to_address=params["to_address"],
            amount=params["amount"],
            from_address=params.get("from_address"),
            vdxf_tag=params.get("vdxf_tag"),
        )
        return {"operation": result.operation, "success": result.success,
                "txid": result.txid, "error": result.error}

    async def _handle_currency_estimate(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.EXECUTING_DEFI
        est = await self.defi_manager.estimate_conversion(
            from_currency=params["from_currency"],
            to_currency=params["to_currency"],
            amount=params["amount"],
            via=params.get("via", ""),
        )
        return {
            "from": est.from_currency, "to": est.to_currency,
            "input": est.input_amount, "estimated_output": est.estimated_output,
            "price": est.price, "via": est.via,
        }

    # --- Storage handlers ---

    async def _handle_storage_store(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.STORING_DATA
        if "file_path" in params:
            result = await self.storage_manager.store_file(
                identity_name=params["identity_name"],
                file_path=params["file_path"],
                mime_type=params.get("mime_type", "application/octet-stream"),
                encrypt=params.get("encrypt", False),
            )
        else:
            result = await self.storage_manager.store_data(
                identity_name=params["identity_name"],
                key=params["key"],
                data=params["data"],
                encrypt=params.get("encrypt", False),
            )
        return {"operation": result.operation, "success": result.success,
                "file_id": result.file_id, "txid": result.txid, "error": result.error}

    async def _handle_storage_retrieve(self, **params) -> Any:
        self.state = VerusAgentState.STORING_DATA
        return await self.storage_manager.retrieve_data(
            identity_name=params["identity_name"],
            key=params["key"],
        )

    async def _handle_storage_store_data_wrapper(self, **params) -> Dict[str, Any]:
        """Handle Method 1 storage: updateidentity + data wrapper (auto-chunk, encrypt)."""
        self.state = VerusAgentState.STORING_DATA
        result = await self.storage_manager.store_file_data_wrapper(
            identity_name=params["identity_name"],
            file_path=params["file_path"],
            vdxf_key=params.get("vdxf_key", "vrsc::uai.storage.chunk"),
            label=params.get("label"),
            mime_type=params.get("mime_type", "application/octet-stream"),
            create_mmr=params.get("create_mmr", True),
        )
        return {"operation": result.operation, "success": result.success,
                "file_id": result.file_id, "txid": result.txid,
                "error": result.error, "data": result.data}

    async def _handle_storage_store_sendcurrency(self, **params) -> Dict[str, Any]:
        """Handle Method 2 storage: sendcurrency to z-address (shielded)."""
        self.state = VerusAgentState.STORING_DATA
        result = await self.storage_manager.store_file_sendcurrency(
            identity_name=params["identity_name"],
            file_path=params["file_path"],
            z_address=params["z_address"],
            vdxf_key=params.get("vdxf_key", "vrsc::uai.storage.chunk"),
        )
        return {"operation": result.operation, "success": result.success,
                "file_id": result.file_id, "txid": result.txid,
                "error": result.error, "data": result.data}

    async def _handle_storage_retrieve_data_wrapper(self, **params) -> Any:
        """Handle Method 1 retrieval via getidentitycontent."""
        self.state = VerusAgentState.STORING_DATA
        return await self.storage_manager.retrieve_data_wrapper(
            identity_name=params["identity_name"],
            height_start=params.get("height_start", 0),
            height_end=params.get("height_end", 0),
        )

    # --- Messaging handlers (encrypted z-address based) ---

    async def _handle_messaging_send_encrypted(self, **params) -> Dict[str, Any]:
        """Send encrypted message to another agent via z-address."""
        self.state = VerusAgentState.COLLABORATING
        try:
            import json as _json
            message_payload = _json.dumps({
                "type": params.get("msg_type", "message"),
                "from": params["sender_identity"],
                "body": params["body"],
            }, separators=(",", ":"))

            r = await self.cli.call("signdata", [{
                "address": params["sender_identity"],
                "message": message_payload,
                "encrypttoaddress": params["recipient_z_address"],
            }])
            result = r.result
            return {"success": True, "signed_data": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_messaging_receive_decrypt(self, **params) -> Dict[str, Any]:
        """Decrypt an encrypted message received via z-address."""
        self.state = VerusAgentState.COLLABORATING
        try:
            r = await self.cli.call("decryptdata", [{
                "datadescriptor": {
                    "version": 1,
                    "flags": 5,
                    "objectdata": params["objectdata_hex"],
                    "epk": params["epk"],
                },
                "ivk": params["ivk"],
            }])
            result = r.result
            return {"success": True, "decrypted_data": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --- Trust/Reputation handlers (setidentitytrust / setcurrencytrust) ---

    async def _handle_trust_set_identity(self, **params) -> Dict[str, Any]:
        """Set identity trust rating (allow/block list for sync)."""
        try:
            r = await self.cli.call(
                "setidentitytrust",
                [params.get("trust_config", {})]
            )
            return {"success": True, "result": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_trust_set_currency(self, **params) -> Dict[str, Any]:
        """Set currency trust rating."""
        try:
            r = await self.cli.call(
                "setcurrencytrust",
                [params.get("trust_config", {})]
            )
            return {"success": True, "result": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_trust_get_ratings(self, **params) -> Dict[str, Any]:
        """Get current trust ratings."""
        try:
            id_r = await self.cli.call("getidentitytrust", [])
            curr_r = await self.cli.call("getcurrencytrust", [])
            id_trust = id_r.result
            curr_trust = curr_r.result
            return {"success": True, "identity_trust": id_trust, "currency_trust": curr_trust}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --- Marketplace atomic swap handlers (makeoffer/takeoffer) ---

    async def _handle_marketplace_make_offer(self, **params) -> Dict[str, Any]:
        """Create an atomic swap offer via makeoffer."""
        try:
            offer_params = {
                "changeaddress": params["change_address"],
                "offer": params["offer"],
                "for": params["for_item"],
            }
            if "expiry" in params:
                offer_params["expiry"] = params["expiry"]
            r = await self.cli.call("makeoffer", [offer_params])
            return {"success": True, "result": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_marketplace_take_offer(self, **params) -> Dict[str, Any]:
        """Accept an atomic swap offer via takeoffer."""
        try:
            take_params = {
                "changeaddress": params["change_address"],
                "deliver": params["deliver"],
                "accept": params["accept"],
            }
            r = await self.cli.call(
                "takeoffer",
                [params["offer_txid"], take_params]
            )
            return {"success": True, "result": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_marketplace_list_open_offers(self, **params) -> Dict[str, Any]:
        """List open offers for a currency."""
        try:
            r = await self.cli.call(
                "getoffers",
                [params.get("currency", "VRSC"), params.get("is_buy", True)]
            )
            return {"success": True, "offers": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_marketplace_close_offers(self, **params) -> Dict[str, Any]:
        """Close one or more open offers."""
        try:
            r = await self.cli.call(
                "closeoffers",
                [params["offer_txids"]]
            )
            return {"success": True, "result": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --- Mining/Staking handlers ---

    async def _handle_mining_start(self, **params) -> Dict[str, Any]:
        """Start mining with setgenerate."""
        try:
            threads = params.get("threads", 1)
            r = await self.cli.call("setgenerate", [True, threads])
            return {"success": True, "result": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_mining_info(self, **params) -> Dict[str, Any]:
        """Get mining information."""
        try:
            r = await self.cli.call("getmininginfo", [])
            return {"success": True, "mining_info": r.result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_staking_status(self, **params) -> Dict[str, Any]:
        """Get staking status."""
        try:
            r = await self.cli.call("getmininginfo", [])
            info = r.result or {}
            return {
                "success": True,
                "staking": info.get("staking", False) if isinstance(info, dict) else False,
                "generate": info.get("generate", False) if isinstance(info, dict) else False,
                "numthreads": info.get("numthreads", 0) if isinstance(info, dict) else 0,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # --- Login handlers ---

    async def _handle_login_authenticate(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.AUTHENTICATING
        if "challenge_id" in params:
            # Process a signed challenge
            result = await self.login_manager.process_login(
                challenge_id=params["challenge_id"],
                identity_name=params["identity_name"],
                signature=params["signature"],
            )
        else:
            # Create a new challenge
            challenge = self.login_manager.create_challenge(
                signing_identity=params.get("signing_identity"),
                redirect_uri=params.get("redirect_uri"),
            )
            return {
                "challenge_id": challenge.challenge_id,
                "message": challenge.message,
                "expires_at": challenge.expires_at.isoformat(),
            }

        return {
            "success": result.success,
            "session_id": result.session.session_id if result.session else None,
            "identity": result.identity_name,
            "error": result.error,
        }

    async def _handle_login_validate(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.AUTHENTICATING
        session = self.login_manager.validate_session(params["session_id"])
        if session:
            return {
                "valid": True,
                "identity": session.identity_name,
                "expires_at": session.expires_at.isoformat(),
            }
        return {"valid": False}

    # --- Bridge handler ---

    async def _handle_bridge_cross(self, **params) -> Dict[str, Any]:
        """
        Execute an Ethereum bridge crossing.

        Uses sendcurrency with bridge destination.
        Upgraded contracts as of Jan 9, 2026 — reduced fees (~$8-10 minimum).
        """
        self.state = VerusAgentState.EXECUTING_DEFI
        output = {
            "currency": params["currency"],
            "address": params["destination"],
            "amount": params["amount"],
        }
        if "convertto" in params:
            output["convertto"] = params["convertto"]
        if "via" in params:
            output["via"] = params["via"]
        if "exportto" in params:
            output["exportto"] = params["exportto"]

        try:
            txid = await self.cli.sendcurrency(
                params.get("from_address", self.config.destination_address),
                [output],
            )
            return {"success": True, "txid": txid}
        except VerusError as exc:
            return {"success": False, "error": str(exc)}

    # --- Market monitor handler ---

    async def _handle_market_monitor(self, **params) -> Dict[str, Any]:
        self.state = VerusAgentState.MONITORING_MARKET
        basket_name = params.get("basket_name", "")

        if basket_name:
            state = await self.defi_manager.get_currency_state(basket_name)
            return {
                "name": state.name,
                "supply": state.supply,
                "reserves": state.reserves,
                "weights": state.weights,
                "prices": state.prices,
                "block_height": state.block_height,
            }

        # Check for arbitrage if two baskets specified
        if "basket_1" in params and "basket_2" in params:
            opp = await self.defi_manager.detect_arbitrage(
                currency_a=params["currency_a"],
                currency_b=params["currency_b"],
                basket_1=params["basket_1"],
                basket_2=params["basket_2"],
                amount=params.get("amount", 1.0),
            )
            if opp:
                return {
                    "arbitrage_found": True,
                    "path": opp.path,
                    "profit_ratio": opp.profit_ratio,
                    "estimated_profit": opp.estimated_profit,
                }
            return {"arbitrage_found": False}

        return {"error": "Specify basket_name or arbitrage parameters"}

    # --- Raw CLI handler ---

    async def _handle_cli_execute(self, **params) -> Any:
        self.state = VerusAgentState.EXECUTING_CLI
        method = params["method"]
        rpc_params = params.get("params", [])
        result = await self.cli.call(method, rpc_params)
        return result.result

    # ------------------------------------------------------------------
    # Extension handlers: Swarm Security
    # ------------------------------------------------------------------

    async def _handle_security_register(self, **params) -> Dict[str, Any]:
        """Register an agent with VerusID-backed swarm security."""
        result = await self.swarm_security.register_agent(
            agent_id=params["agent_id"],
            role=params.get("role", "worker"),
            permissions=params.get("permissions"),
            primary_addresses=params.get("primary_addresses"),
            controller_identity=params.get("controller_identity", ""),
        )
        return {"success": result.success, "identity": result.agent_identity,
                "txid": result.txid, "error": result.error}

    async def _handle_security_verify(self, **params) -> Dict[str, Any]:
        """Verify an agent's identity and permissions."""
        cred = await self.swarm_security.verify_agent(params["agent_id"])
        if cred:
            return {"verified": cred.verified, "agent_id": cred.agent_id,
                    "role": cred.role, "permissions": cred.permissions}
        return {"verified": False, "error": "Agent not found"}

    async def _handle_security_revoke(self, **params) -> Dict[str, Any]:
        """Revoke an agent's VerusID credentials."""
        result = await self.swarm_security.revoke_agent(params["agent_id"])
        return {"success": result.success, "txid": result.txid, "error": result.error}

    async def _handle_security_status(self, **params) -> Dict[str, Any]:
        """Return swarm security status."""
        return self.swarm_security.get_security_status()

    # ------------------------------------------------------------------
    # Extension handlers: Agent Marketplace
    # ------------------------------------------------------------------

    async def _handle_mp_register_product(self, **params) -> Dict[str, Any]:
        """Register an agent product in the VerusID marketplace."""
        result = await self.marketplace.register_product(
            name=params["name"],
            description=params.get("description", ""),
            tier=params.get("tier", "free"),
            price_vrsc=params.get("price_vrsc", 0.0),
            capabilities=params.get("capabilities", []),
            primary_addresses=params.get("primary_addresses"),
            controller_identity=params.get("controller_identity", ""),
        )
        return {"success": result.success, "product_identity": result.data.get("product_identity"),
                "txid": result.txid, "error": result.error}

    async def _handle_mp_issue_license(self, **params) -> Dict[str, Any]:
        """Issue a license for an agent product."""
        result = await self.marketplace.issue_license(
            product_identity=params["product_identity"],
            buyer_identity=params["buyer_identity"],
            tier=params.get("tier", "starter"),
            duration_days=params.get("duration_days", 30),
        )
        return {"success": result.success, "license_identity": result.data.get("license_identity"),
                "txid": result.txid, "error": result.error}

    async def _handle_mp_verify_license(self, **params) -> Dict[str, Any]:
        """Verify a marketplace license."""
        result = await self.marketplace.verify_license(params["license_identity"])
        return result.__dict__ if hasattr(result, '__dict__') else {"valid": False}

    async def _handle_mp_list_offers(self, **params) -> Dict[str, Any]:
        """List marketplace offers for a product."""
        result = await self.marketplace.list_offers(params["product_identity"])
        return {"success": result.success, "offers": result.data.get("offers", []),
                "error": result.error}

    # ------------------------------------------------------------------
    # Extension handlers: IP Protection
    # ------------------------------------------------------------------

    async def _handle_ip_register_model(self, **params) -> Dict[str, Any]:
        """Register a model's IP on-chain via VerusID."""
        result = await self.ip_protection.register_model(
            model_name=params["model_name"],
            model_file_path=params["model_file_path"],
            architecture=params.get("architecture", ""),
            owner_identity=params.get("owner_identity", ""),
            version=params.get("version", "1.0.0"),
            quantization=params.get("quantization", "unknown"),
            storage_url=params.get("storage_url", ""),
        )
        return {"success": result.success, "model_identity": result.model_identity,
                "txid": result.txid, "data": result.data, "error": result.error}

    async def _handle_ip_verify_integrity(self, **params) -> Dict[str, Any]:
        """Verify model file integrity against on-chain hash."""
        check = await self.ip_protection.verify_integrity(
            model_identity=params["model_identity"],
            model_file_path=params["model_file_path"],
        )
        return {
            "matches": check.matches, "expected_hash": check.expected_hash,
            "actual_hash": check.actual_hash, "provenance_valid": check.provenance_valid,
            "signature_valid": check.signature_valid,
        }

    async def _handle_ip_get_model_info(self, **params) -> Dict[str, Any]:
        """Get model registration info from on-chain."""
        info = await self.ip_protection.get_model_info(params["model_identity"])
        if info:
            return {
                "name": info.name, "version": info.version,
                "model_hash": info.model_hash, "architecture": info.architecture,
                "license_type": info.license_type.value, "owner": info.owner_identity,
                "size_bytes": info.size_bytes, "quantization": info.quantization,
            }
        return {"error": "Model not found"}

    async def _handle_ip_register_storage(self, **params) -> Dict[str, Any]:
        """Register off-chain storage reference for a model."""
        result = await self.ip_protection.register_storage_reference(
            model_identity=params["model_identity"],
            url=params["url"],
            backend=params.get("backend", "ipfs"),
            is_backup=params.get("is_backup", False),
        )
        return {"success": result.success, "txid": result.txid, "error": result.error}

    async def _handle_ip_encrypt_model(self, **params) -> Dict[str, Any]:
        """Encrypt a model file with AES-256-GCM."""
        result = await self.ip_protection.encrypt_model_file(
            file_path=params["file_path"],
            output_path=params.get("output_path"),
        )
        return {"success": result.success, "data": result.data, "error": result.error}

    async def _handle_ip_decrypt_model(self, **params) -> Dict[str, Any]:
        """Decrypt an AES-256-GCM encrypted model file."""
        result = await self.ip_protection.decrypt_model_file(
            encrypted_path=params["encrypted_path"],
            output_path=params["output_path"],
            aes_key_b64=params["aes_key_b64"],
        )
        return {"success": result.success, "data": result.data, "error": result.error}

    async def _handle_ip_full_protect(self, **params) -> Dict[str, Any]:
        """End-to-end model protection: encrypt → register → deliver key."""
        result = await self.ip_protection.full_protect_model(
            model_name=params["model_name"],
            model_file_path=params["model_file_path"],
            owner_identity=params["owner_identity"],
            z_address=params["z_address"],
            architecture=params.get("architecture", ""),
            version=params.get("version", "1.0.0"),
            quantization=params.get("quantization", "unknown"),
            storage_url=params.get("storage_url", ""),
        )
        return {"success": result.success, "model_identity": result.model_identity,
                "txid": result.txid, "data": result.data, "error": result.error}

    # ------------------------------------------------------------------
    # Extension handlers: Marketplace (new)
    # ------------------------------------------------------------------

    async def _handle_mp_create_invoice(self, **params) -> Dict[str, Any]:
        """Create a VerusPay invoice for agent billing."""
        result = await self.marketplace.create_invoice(
            product_identity=params["product_identity"],
            amount=params["amount"],
            currency=params.get("currency", "VRSC"),
            buyer_identity=params.get("buyer_identity", ""),
            memo=params.get("memo", ""),
            destination=params.get("destination", ""),
        )
        return {"success": result.success, "data": result.data,
                "txid": result.txid, "error": result.error}

    async def _handle_mp_discover(self, **params) -> Dict[str, Any]:
        """Discover agent products registered on-chain."""
        products = await self.marketplace.discover_products(
            prefix=params.get("prefix", "uai."),
            limit=params.get("limit", 50),
        )
        return {
            "success": True,
            "count": len(products),
            "products": [
                {"name": p.name, "identity": p.product_identity,
                 "description": p.description, "price": p.price}
                for p in products
            ],
        }

    async def _handle_mp_search(self, **params) -> Dict[str, Any]:
        """Search cached marketplace products by keyword."""
        products = await self.marketplace.search_products(
            query=params["query"],
            limit=params.get("limit", 20),
        )
        return {
            "success": True,
            "count": len(products),
            "products": [
                {"name": p.name, "identity": p.product_identity,
                 "description": p.description}
                for p in products
            ],
        }

    # ------------------------------------------------------------------
    # Extension handlers: Reputation System (Phase 4)
    # ------------------------------------------------------------------

    async def _handle_rep_attest(self, **params) -> Dict[str, Any]:
        """Issue a reputation attestation from one agent to another."""
        from verus_agent.reputation import AttestationCategory
        result = await self.reputation.attest(
            attestor=params["attestor"],
            target=params["target"],
            rating=params["rating"],
            category=AttestationCategory(params.get("category", "overall")),
            comment=params.get("comment", ""),
        )
        return {"success": result.success, "agent": result.agent_identity,
                "txid": result.txid, "data": result.data, "error": result.error}

    async def _handle_rep_query(self, **params) -> Dict[str, Any]:
        """Query reputation score for an agent."""
        score = await self.reputation.get_reputation(params["agent_identity"])
        return {
            "agent": score.agent_identity,
            "overall_score": score.overall_score,
            "total_attestations": score.total_attestations,
            "category_scores": score.category_scores,
            "confidence": score.confidence,
            "stake_weight": score.stake_weight,
        }

    async def _handle_rep_leaderboard(self, **params) -> Dict[str, Any]:
        """Get reputation leaderboard."""
        scores = await self.reputation.get_leaderboard(
            limit=params.get("limit", 10),
        )
        return {
            "leaderboard": [
                {"agent": s.agent_identity, "score": s.overall_score,
                 "attestations": s.total_attestations}
                for s in scores
            ],
        }

    async def _handle_rep_verify_attestation(self, **params) -> Dict[str, Any]:
        """Verify an attestation signature."""
        from verus_agent.reputation import Attestation, AttestationCategory
        att = Attestation(
            attestor_identity=params["attestor"],
            target_identity=params["target"],
            rating=params["rating"],
            category=AttestationCategory(params.get("category", "overall")),
            comment=params.get("comment", ""),
            signature=params["signature"],
        )
        valid = await self.reputation.verify_attestation(att)
        return {"valid": valid, "attestor": att.attestor_identity}

    # ------------------------------------------------------------------
    # Extension handlers: DeFi Revenue Sharing (Phase 4)
    # ------------------------------------------------------------------

    async def _handle_defi_revenue_basket(self, **params) -> Dict[str, Any]:
        """Create a revenue-sharing basket currency."""
        result = await self.defi_manager.create_revenue_basket(
            basket_name=params["basket_name"],
            controller_identity=params["controller_identity"],
            reserve_currencies=params.get("reserve_currencies"),
            reserve_weights=params.get("reserve_weights"),
            initial_supply=params.get("initial_supply", 1000.0),
        )
        return {"success": result.success, "txid": result.txid, "error": result.error}

    async def _handle_defi_distribute_revenue(self, **params) -> Dict[str, Any]:
        """Send revenue into a basket for distribution to token holders."""
        result = await self.defi_manager.distribute_revenue(
            basket_name=params["basket_name"],
            amount=params["amount"],
            from_address=params["from_address"],
            currency=params.get("currency", "VRSC"),
        )
        return {"success": result.success, "txid": result.txid, "error": result.error}

    async def _handle_defi_pbaas_chain(self, **params) -> Dict[str, Any]:
        """Define and launch a UAI PBaaS sidechain."""
        result = await self.defi_manager.define_uai_pbaas_chain(
            chain_name=params["chain_name"],
            controller_identity=params["controller_identity"],
            id_registration_fees=params.get("id_registration_fees", 10.0),
            id_referral_levels=params.get("id_referral_levels", 3),
            block_time=params.get("block_time", 60),
            initial_supply=params.get("initial_supply", 0.0),
            reserve_currencies=params.get("reserve_currencies"),
            reserve_weights=params.get("reserve_weights"),
            era_options=params.get("era_options"),
        )
        return {"success": result.success, "txid": result.txid, "error": result.error}

    # ------------------------------------------------------------------
    # Extension handlers: Cross-chain License (Phase 4)
    # ------------------------------------------------------------------

    async def _handle_mp_verify_license_cross_chain(self, **params) -> Dict[str, Any]:
        """Verify a license across PBaaS chains."""
        lic = await self.marketplace.verify_license_cross_chain(
            license_identity=params["license_identity"],
            source_chain=params.get("source_chain", "VRSC"),
        )
        if lic is None:
            return {"valid": False, "error": "License not found or invalid"}
        return {
            "valid": lic.valid,
            "tier": lic.tier,
            "identity": lic.identity,
            "cross_chain": True,
            "source_chain": params.get("source_chain", "VRSC"),
        }

    # ------------------------------------------------------------------
    # Extension handlers: LoRA Watermark (Phase 4)
    # ------------------------------------------------------------------

    async def _handle_ip_generate_watermark(self, **params) -> Dict[str, Any]:
        """Generate a per-buyer watermarked model."""
        result = await self.ip_protection.generate_buyer_watermark(
            model_identity=params["model_identity"],
            buyer_identity=params["buyer_identity"],
            model_file_path=params["model_file_path"],
            output_path=params.get("output_path"),
            watermark_strength=params.get("watermark_strength", 0.001),
        )
        return {
            "success": result.success,
            "txid": result.txid,
            "data": result.data,
            "error": result.error,
        }

    async def _handle_ip_verify_watermark(self, **params) -> Dict[str, Any]:
        """Check if a suspect model matches a buyer's watermark."""
        result = await self.ip_protection.verify_watermark(
            model_identity=params["model_identity"],
            buyer_identity=params["buyer_identity"],
            suspect_file_path=params["suspect_file_path"],
        )
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }

    # ------------------------------------------------------------------
    # Extension handlers: Mobile Wallet (Phase 4)
    # ------------------------------------------------------------------

    async def _handle_mobile_payment_uri(self, **params) -> Dict[str, Any]:
        """Generate a VerusPay payment URI."""
        pay = self.mobile_helper.generate_payment_uri(
            destination=params.get("destination", ""),
            amount=params.get("amount"),
            currency=params.get("currency", "VRSC"),
            label=params.get("label", ""),
            message=params.get("message", ""),
        )
        return {"uri": pay.uri, "qr_data": pay.qr_data, "address": pay.address}

    async def _handle_mobile_login_consent(self, **params) -> Dict[str, Any]:
        """Generate a LoginConsentRequest for wallet-based auth."""
        consent = self.mobile_helper.generate_login_consent(
            agent_identity=params.get("agent_identity", ""),
            redirect_uri=params.get("redirect_uri", ""),
            requested_access=params.get("requested_access"),
            expires_seconds=params.get("expires_seconds", 300),
        )
        return {
            "challenge_id": consent.challenge_id,
            "qr_data": consent.qr_data,
            "expires_at": consent.expires_at,
        }

    async def _handle_mobile_purchase_link(self, **params) -> Dict[str, Any]:
        """Generate a marketplace purchase deep link."""
        result = self.mobile_helper.generate_purchase_link(
            product_identity=params["product_identity"],
            tier=params.get("tier", "basic"),
            price=params.get("price"),
            currency=params.get("currency", "VRSC"),
        )
        return {
            "success": result.success,
            "uri": result.uri,
            "qr_data": result.qr_data,
            "data": result.data,
            "error": result.error,
        }

    async def _handle_mobile_generic_request_link(self, **params) -> Dict[str, Any]:
        """Generate a compact GenericRequest deeplink (verus://1/<payload>)."""
        result = self.mobile_helper.generate_generic_request_link(
            compact_payload=params["compact_payload"],
            detail_types=params.get("detail_types"),
            requires_experimental=params.get("requires_experimental", False),
            legacy_fallback_uri=params.get("legacy_fallback_uri", ""),
        )
        return {
            "success": result.success,
            "uri": result.uri,
            "qr_data": result.qr_data,
            "data": result.data,
            "error": result.error,
        }

    async def _handle_mobile_identity_update_request_link(self, **params) -> Dict[str, Any]:
        """Generate a GenericRequest deeplink for IdentityUpdateRequest flows."""
        result = self.mobile_helper.generate_identity_update_request_link(
            compact_payload=params["compact_payload"],
            legacy_fallback_uri=params.get("legacy_fallback_uri", ""),
        )
        return {
            "success": result.success,
            "uri": result.uri,
            "qr_data": result.qr_data,
            "data": result.data,
            "error": result.error,
        }

    async def _handle_mobile_app_encryption_request_link(self, **params) -> Dict[str, Any]:
        """Generate a GenericRequest deeplink for AppEncryptionRequest flows."""
        result = self.mobile_helper.generate_app_encryption_request_link(
            compact_payload=params["compact_payload"],
            requests_secret_key_material=params.get("requests_secret_key_material", False),
            legacy_fallback_uri=params.get("legacy_fallback_uri", ""),
        )
        return {
            "success": result.success,
            "uri": result.uri,
            "qr_data": result.qr_data,
            "data": result.data,
            "error": result.error,
        }

    async def _handle_mobile_capabilities(self, **_params) -> Dict[str, Any]:
        """Return the mobile capability snapshot used for developer guidance."""
        return self.mobile_helper.get_mobile_capabilities()

    # ------------------------------------------------------------------
    # VDXF Data Pipeline handlers (Phase 5)
    # ------------------------------------------------------------------

    async def _handle_data_sign(self, **params) -> Dict[str, Any]:
        """Sign data with a VerusID using signdata (supports message, hex,
        file, vdxfdata, MMR multi-item, and encrypttoaddress)."""
        sign_args: Dict[str, Any] = {"address": params["address"]}
        # Accept exactly one data input mode
        for key in ("message", "filename", "messagehex", "messagebase64",
                     "datahash", "vdxfdata", "mmrdata"):
            if key in params:
                sign_args[key] = params[key]
        # Optional parameters
        for key in ("encrypttoaddress", "createmmr", "hashtype",
                     "mmrhashtype", "mmrsalt", "vdxfkeys", "vdxfkeynames",
                     "boundhashes", "prefixstring", "signature"):
            if key in params:
                sign_args[key] = params[key]
        result = await self.cli.call("signdata", [sign_args])
        return result.result if hasattr(result, "result") else result

    async def _handle_data_verify(self, **params) -> Dict[str, Any]:
        """Verify a signature with verifysignature."""
        verify_args: Dict[str, Any] = {
            "address": params["address"],
            "signature": params["signature"],
        }
        for key in ("message", "filename", "messagehex", "messagebase64",
                     "datahash", "prefixstring", "vdxfkeys", "vdxfkeynames",
                     "boundhashes", "hashtype", "checklatest"):
            if key in params:
                verify_args[key] = params[key]
        result = await self.cli.call("verifysignature", [verify_args])
        return result.result if hasattr(result, "result") else result

    async def _handle_data_decrypt(self, **params) -> Dict[str, Any]:
        """Decrypt on-chain data using decryptdata."""
        decrypt_args: Dict[str, Any] = {}
        for key in ("datadescriptor", "iddata", "evk", "ivk", "txid", "retrieve"):
            if key in params:
                decrypt_args[key] = params[key]
        result = await self.cli.call("decryptdata", [decrypt_args])
        return result.result if hasattr(result, "result") else result

    async def _handle_data_getvdxfid(self, **params) -> Dict[str, Any]:
        """Resolve a human-readable VDXF URI to its on-chain i-address."""
        args = [params["vdxfuri"]]
        if "bounddata" in params:
            args.append(params["bounddata"])
        result = await self.cli.call("getvdxfid", args)
        return result.result if hasattr(result, "result") else result

    async def _handle_data_list_received(self, **params) -> Dict[str, Any]:
        """List data/transactions received at a shielded z-address."""
        args = [params["address"]]
        if "minconf" in params:
            args.append(params["minconf"])
        result = await self.cli.call("z_listreceivedbyaddress", args)
        return result.result if hasattr(result, "result") else result

    async def _handle_data_export_viewingkey(self, **params) -> Dict[str, Any]:
        """Export the extended viewing key for a z-address."""
        result = await self.cli.call("z_exportviewingkey", [params["address"]])
        r = result.result if hasattr(result, "result") else result
        return {"evk": r} if isinstance(r, str) else r

    async def _handle_data_import_viewingkey(self, **params) -> Dict[str, Any]:
        """Import a viewing key to enable decryption of data at a z-address."""
        args = [params["vkey"]]
        if "rescan" in params:
            args.append(params["rescan"])
        if "startHeight" in params:
            args.append(params["startHeight"])
        result = await self.cli.call("z_importviewingkey", args)
        return result.result if hasattr(result, "result") else result

    async def _handle_data_build_vdxf(self, **params) -> Dict[str, Any]:
        """Build a structured contentmultimap payload using the VDXF builder."""
        builder = ContentMultiMapBuilder()
        for entry in params.get("entries", []):
            vdxf_key = entry["vdxf_key"]
            desc = DataDescriptorBuilder()
            if "label" in entry:
                desc.set_label(entry["label"])
            if "mimetype" in entry:
                desc.set_mimetype(entry["mimetype"])
            if "message" in entry:
                desc.set_message(entry["message"])
            elif "objectdata" in entry:
                desc.set_objectdata_hex(entry["objectdata"])
            builder.add_descriptor(vdxf_key, desc.build())
        return {"contentmultimap": builder.build()}

    # ------------------------------------------------------------------
    # Provenance & NFT handlers (Phase 5 — Bitcoin Kali pattern)
    # ------------------------------------------------------------------

    async def _handle_provenance_create_nft(self, **params) -> Dict[str, Any]:
        """Create a VerusID to hold NFT data with optional initial descriptors."""
        return await self.provenance.create_nft_identity(
            name=params["name"],
            primary_addresses=params["primary_addresses"],
            recovery_authority=params.get("recovery_authority"),
            revocation_authority=params.get("revocation_authority"),
            content_multimap=params.get("content_multimap"),
        )

    async def _handle_provenance_store_descriptors(self, **params) -> Dict[str, Any]:
        """Store an array of typed DataDescriptors in a contentmultimap."""
        return await self.provenance.store_typed_descriptors(
            identity_name=params["identity_name"],
            series_key=params["series_key"],
            descriptors=params["descriptors"],
        )

    async def _handle_provenance_sign_mmr(self, **params) -> Dict[str, Any]:
        """Build MMR over data leaves and sign the root with a curator identity."""
        return await self.provenance.sign_provenance_mmr(
            signing_identity=params["signing_identity"],
            data_leaves=params["data_leaves"],
            mmrhashtype=params.get("mmrhashtype", "blake2b"),
            encrypttoaddress=params.get("encrypttoaddress"),
        )

    async def _handle_provenance_deliver_encrypted(self, **params) -> Dict[str, Any]:
        """Encrypt file and deliver via sendcurrency to a z-address."""
        return await self.provenance.encrypted_file_delivery(
            from_address=params["from_address"],
            z_address=params["z_address"],
            file_path=params.get("file_path"),
            data=params.get("data"),
        )

    async def _handle_provenance_verify(self, **params) -> Dict[str, Any]:
        """Full verification: get content → decrypt → hash compare → verify signature."""
        return await self.provenance.verify_provenance(
            identity_name=params["identity_name"],
            curator_identity=params["curator_identity"],
            series_key=params.get("series_key"),
            evk=params.get("evk"),
        )

    async def _handle_provenance_list_offer(self, **params) -> Dict[str, Any]:
        """Create an atomic swap marketplace offer for a provenance NFT."""
        return await self.provenance.list_for_marketplace(
            identity_name=params["identity_name"],
            price=params["price"],
            currency=params.get("currency", "VRSC"),
            for_address=params.get("for_address"),
            expiry_height=params.get("expiry_height"),
        )

    # ------------------------------------------------------------------
    # Internal: swarm registration
    # ------------------------------------------------------------------

    async def _register_with_swarm(self) -> None:
        """Register this agent with the UAI swarm coordinator."""
        registration = {
            "agent_id": self.agent_id,
            "capabilities": AGENT_CAPABILITIES,
            "priority": self.config.agent_priority,
            "agent_type": self.agent_type,
            "domain": self.domain,
            "role": self.role,
            "network": self.config.network.value,
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.uai_core_url}/orchestration/agent/register"
                async with session.post(url, json=registration, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info("Registered with swarm: %s", data)
                    else:
                        text = await resp.text()
                        logger.warning("Swarm registration returned %d: %s", resp.status, text)
        except Exception as exc:
            logger.warning("Could not register with swarm (will retry): %s", exc)

    # ------------------------------------------------------------------
    # Internal: background loops
    # ------------------------------------------------------------------

    async def _task_processing_loop(self) -> None:
        """Poll for tasks from the swarm queue."""
        while self._running:
            try:
                # In production: poll swarm task queue or listen on WebSocket
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Task loop error: %s", exc)
                await asyncio.sleep(10)

    async def _health_reporting_loop(self) -> None:
        """Periodically report health to the swarm."""
        while self._running:
            try:
                status = self.get_status()
                # In production: POST to health endpoint
                logger.debug("Health: state=%s, tasks=%d, accuracy=%.3f",
                             self.state.value, self.tasks_completed, self.accuracy_score)
                self.adapt_behavior()
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Health loop error: %s", exc)
                await asyncio.sleep(30)

    async def _message_processing_loop(self) -> None:
        """Process incoming inter-agent messages."""
        while self._running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=5.0)
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Message loop error: %s", exc)

    async def _handle_message(self, message: AgentMessage) -> None:
        """Handle an incoming message from another agent."""
        if message.message_type == "task":
            result = await self.process_task(message.content)
            reply = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                message_type="result",
                content={"task_id": result.task_id, "result": result.result,
                         "success": result.success, "error": result.error},
            )
            await self.send_message(reply)

        elif message.message_type == "collaboration_request":
            self.state = VerusAgentState.COLLABORATING
            self.active_collaborations[message.message_id] = {
                "partner": message.sender_id,
                "started": datetime.now().isoformat(),
                "content": message.content,
            }
            logger.info("Collaboration started with %s", message.sender_id)

    # ------------------------------------------------------------------
    # Internal: learning
    # ------------------------------------------------------------------

    async def _log_experience(self, capability: str, success: bool, elapsed_ms: float) -> None:
        """Record experience for agent learning."""
        self.experience_history.append({
            "capability": capability,
            "success": success,
            "elapsed_ms": elapsed_ms,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep last 1000 experiences
        if len(self.experience_history) > 1000:
            self.experience_history = self.experience_history[-1000:]


# ---------------------------------------------------------------------------
# Lightweight health HTTP server (for Docker HEALTHCHECK on port 9124)
# ---------------------------------------------------------------------------

_health_agent: Optional[VerusBlockchainAgent] = None


async def _health_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Minimal HTTP handler that responds to GET /health."""
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5)
        # Drain remaining headers
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=2)
            if line in (b"\r\n", b"\n", b""):
                break
    except Exception:
        writer.close()
        return

    path = request_line.decode(errors="replace").split(" ")[1] if b" " in request_line else "/"

    if path == "/health":
        import json as _json
        status = _health_agent.get_status() if _health_agent else {}
        body = _json.dumps({"status": "healthy", "agent_state": status.get("state", "unknown")})
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n{body}"
        )
    else:
        body = '{"detail":"Not Found"}'
        response = (
            f"HTTP/1.1 404 Not Found\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n{body}"
        )

    writer.write(response.encode())
    await writer.drain()
    writer.close()


async def _start_health_server(port: int = 9124) -> asyncio.AbstractServer:
    """Start a tiny TCP server for Docker health checks."""
    server = await asyncio.start_server(_health_handler, "0.0.0.0", port)
    logger.info("Health server listening on port %d", port)
    return server


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main():
    """Standalone entrypoint for the Verus agent."""
    global _health_agent

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = VerusConfig()
    agent = VerusBlockchainAgent(config)
    _health_agent = agent

    health_server: Optional[asyncio.AbstractServer] = None

    try:
        await agent.initialize()
        await agent.start()

        # Start health endpoint for Docker HEALTHCHECK
        health_server = await _start_health_server(9124)

        # Keep running
        logger.info("Verus Blockchain Agent running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted.")
    finally:
        if health_server:
            health_server.close()
            await health_server.wait_closed()
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
