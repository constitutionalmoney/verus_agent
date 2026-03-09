"""
Verus Blockchain Specialist Agent — UAI Neural Swarm Integration

Purpose-built agent for developing on the Verus Blockchain (VRSC),
leveraging protocol-level primitives: currencies, DeFi, VerusID,
VDXF data, storage, and cross-chain bridges.

Modules:
    - cli_wrapper: Low-level Verus daemon/API interaction
    - verusid: VerusID identity management
    - defi: Currency & DeFi operations
    - login: VerusID-based authentication
    - storage: Blockchain file storage
    - bridge: Cross-chain bridge operations
    - market: Market & volume monitoring
    - agent: Main agent class with swarm integration
    - swarm_security: Optional VerusID-backed swarm security layer
    - marketplace: Decentralized agent monetization via VerusID
    - ip_protection: LLM/SLM IP protection via VerusID provenance & encryption
    - reputation: VerusID-backed agent reputation & attestation system
    - mobile: Mobile wallet integration helpers (VerusPay URIs, LoginConsent QR)
"""

from verus_agent.agent import VerusBlockchainAgent, VerusAgentState, VerusSpecialization
from verus_agent.config import VerusConfig
from verus_agent.ip_protection import VerusIPProtection, ModelLicenseType, StorageBackend
from verus_agent.marketplace import VerusAgentMarketplace, PricingModel, LicenseTier
from verus_agent.mobile import VerusMobileHelper, PaymentNetwork
from verus_agent.reputation import VerusReputationSystem, AttestationCategory
from verus_agent.swarm_security import VerusSwarmSecurity, SecurityLevel, AgentPermission

__all__ = [
    "VerusBlockchainAgent",
    "VerusAgentState",
    "VerusSpecialization",
    "VerusConfig",
    # Extension modules
    "VerusSwarmSecurity",
    "SecurityLevel",
    "AgentPermission",
    "VerusAgentMarketplace",
    "PricingModel",
    "LicenseTier",
    "VerusIPProtection",
    "ModelLicenseType",
    "StorageBackend",
    "VerusReputationSystem",
    "AttestationCategory",
    "VerusMobileHelper",
    "PaymentNetwork",
]

__version__ = "0.4.0"
