"""
VerusID Management Module

Handles creation, update, vault operations, revocation, and recovery of
VerusID self-sovereign identities on the Verus blockchain.

References:
    - https://docs.verus.io/verusid/
    - https://docs.verus.io/verusid/verusid-create.html
    - https://docs.verus.io/verusid/#verus-vault
    - https://docs.verus.io/verusid/#revoke-recover
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from verus_agent.cli_wrapper import VerusCLI, VerusError

logger = logging.getLogger("verus_agent.verusid")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class IdentityFlag(int, Enum):
    """VerusID identity flags."""
    ACTIVECURRENCY = 1
    TOKENIZED_CONTROL = 2
    LOCKED = 4          # Vault-locked
    REVOKED = 8
    # Extended flags from v1.2.14-2
    NFT_TOKEN = 0x20


@dataclass
class VerusIdentity:
    """Represents a parsed VerusID."""
    name: str
    identity_address: str
    i_address: str  # The i-address (iXXX...)
    parent: str
    version: int
    flags: int
    primary_addresses: List[str] = field(default_factory=list)
    recovery_authority: str = ""
    revocation_authority: str = ""
    private_address: str = ""
    timelock: int = 0
    minimumsignatures: int = 1
    content_map: Dict[str, Any] = field(default_factory=dict)
    content_multimap: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_rpc(cls, data: Dict[str, Any]) -> "VerusIdentity":
        """Parse from ``getidentity`` RPC result."""
        identity = data.get("identity", data)
        return cls(
            name=identity.get("name", ""),
            identity_address=identity.get("identityaddress", ""),
            i_address=data.get("identity", {}).get("identityaddress", "")
                       or identity.get("identityaddress", ""),
            parent=identity.get("parent", ""),
            version=identity.get("version", 0),
            flags=identity.get("flags", 0),
            primary_addresses=identity.get("primaryaddresses", []),
            recovery_authority=identity.get("recoveryauthority", ""),
            revocation_authority=identity.get("revocationauthority", ""),
            private_address=identity.get("privateaddress", ""),
            timelock=identity.get("timelock", 0),
            minimumsignatures=identity.get("minimumsignatures", 1),
            content_map=identity.get("contentmap", {}),
            content_multimap=identity.get("contentmultimap", {}),
            raw=data,
        )

    @property
    def is_locked(self) -> bool:
        return bool(self.flags & IdentityFlag.LOCKED)

    @property
    def is_revoked(self) -> bool:
        return bool(self.flags & IdentityFlag.REVOKED)

    @property
    def full_name(self) -> str:
        return f"{self.name}@" if self.parent else self.name


@dataclass
class VerusIDOperationResult:
    """Result of a VerusID management operation."""
    operation: str
    identity_name: str
    success: bool
    txid: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# VerusID Manager
# ---------------------------------------------------------------------------

class VerusIDManager:
    """
    Manages VerusID lifecycle: create, update, vault, revoke, recover.

    Usage::

        cli = VerusCLI(config)
        await cli.initialize()
        id_mgr = VerusIDManager(cli)

        # Create a new identity
        result = await id_mgr.create_identity(
            name="MyAgent",
            primary_addresses=["RAddress..."],
            recovery_authority="recovery@",
            revocation_authority="revoke@",
        )

        # Get identity info
        identity = await id_mgr.get_identity("MyAgent@")

        # Lock vault
        await id_mgr.lock_vault("MyAgent@", timelock_blocks=1440)
    """

    def __init__(self, cli: VerusCLI):
        self.cli = cli
        self._cache: Dict[str, VerusIdentity] = {}

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_identity(self, name_or_id: str, use_cache: bool = False) -> VerusIdentity:
        """Fetch a VerusID by name or i-address."""
        if use_cache and name_or_id in self._cache:
            return self._cache[name_or_id]

        data = await self.cli.getidentity(name_or_id)
        identity = VerusIdentity.from_rpc(data)
        self._cache[name_or_id] = identity
        logger.info("Fetched identity: %s", identity.full_name)
        return identity

    async def get_identity_content(
        self, name_or_id: str, vdxf_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve content stored in a VerusID's contentmultimap."""
        return await self.cli.getidentitycontent(name_or_id, vdxf_key)

    async def identity_exists(self, name: str) -> bool:
        """Check if a VerusID name is already registered."""
        try:
            await self.get_identity(name)
            return True
        except VerusError:
            return False

    # ------------------------------------------------------------------
    # Create operations
    # ------------------------------------------------------------------

    async def create_identity(
        self,
        name: str,
        primary_addresses: List[str],
        recovery_authority: Optional[str] = None,
        revocation_authority: Optional[str] = None,
        private_address: Optional[str] = None,
        content_multimap: Optional[Dict[str, Any]] = None,
        referral_id: str = "",
        parent: str = "",
        minimumsignatures: int = 1,
    ) -> VerusIDOperationResult:
        """
        Create a new VerusID (two-step: name commitment + registration).

        Parameters
        ----------
        name : str
            The identity name (without @).
        primary_addresses : list
            R-addresses that control this identity.
        recovery_authority : str, optional
            VerusID name that can recover this identity.
        revocation_authority : str, optional
            VerusID name that can revoke this identity.
        """
        try:
            # Step 1: Name commitment
            commitment = await self.cli.registernamecommitment(
                name, primary_addresses[0], referral_id, parent
            )
            logger.info("Name commitment created: %s", commitment)

            # Step 2: Register identity
            identity_def: Dict[str, Any] = {
                "txid": commitment.get("txid", ""),
                "namereservation": commitment.get("namereservation", {}),
                "identity": {
                    "name": name,
                    "primaryaddresses": primary_addresses,
                    "minimumsignatures": minimumsignatures,
                },
            }

            if recovery_authority:
                identity_def["identity"]["recoveryauthority"] = recovery_authority
            if revocation_authority:
                identity_def["identity"]["revocationauthority"] = revocation_authority
            if private_address:
                identity_def["identity"]["privateaddress"] = private_address
            if content_multimap:
                identity_def["identity"]["contentmultimap"] = content_multimap

            result = await self.cli.registeridentity(identity_def)

            return VerusIDOperationResult(
                operation="create",
                identity_name=name,
                success=True,
                txid=result if isinstance(result, str) else result.get("txid"),
                data={"commitment": commitment, "registration": result},
            )

        except VerusError as exc:
            logger.error("Failed to create identity '%s': %s", name, exc)
            return VerusIDOperationResult(
                operation="create",
                identity_name=name,
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Update operations
    # ------------------------------------------------------------------

    async def update_identity(
        self,
        name: str,
        updates: Dict[str, Any],
    ) -> VerusIDOperationResult:
        """
        Update fields on an existing VerusID.

        Parameters
        ----------
        name : str
            The identity name (e.g. ``MyAgent@``).
        updates : dict
            Fields to update (``primaryaddresses``, ``contentmultimap``, etc.).
        """
        try:
            identity_def = {"name": name}
            identity_def.update(updates)
            result = await self.cli.updateidentity(identity_def)

            # Invalidate cache
            self._cache.pop(name, None)

            return VerusIDOperationResult(
                operation="update",
                identity_name=name,
                success=True,
                txid=result if isinstance(result, str) else result.get("txid"),
                data={"updates": updates},
            )
        except VerusError as exc:
            logger.error("Failed to update identity '%s': %s", name, exc)
            return VerusIDOperationResult(
                operation="update",
                identity_name=name,
                success=False,
                error=str(exc),
            )

    async def set_content(
        self,
        name: str,
        vdxf_key: str,
        value: Any,
    ) -> VerusIDOperationResult:
        """Store a VDXF key-value pair in a VerusID's contentmultimap."""
        content_multimap = {vdxf_key: [{"" : value} if isinstance(value, str) else value]}
        return await self.update_identity(name, {"contentmultimap": content_multimap})

    # ------------------------------------------------------------------
    # Vault operations (Timelock)
    # ------------------------------------------------------------------

    async def lock_vault(
        self, name: str, timelock_blocks: int = 1440
    ) -> VerusIDOperationResult:
        """
        Lock a VerusID with a time-delayed unlock (Verus Vault).

        Parameters
        ----------
        timelock_blocks : int
            Number of blocks before funds can be spent (default ~24h at 1 min/block).
        """
        try:
            identity = await self.get_identity(name)
            new_flags = identity.flags | IdentityFlag.LOCKED

            result = await self.cli.updateidentity({
                "name": name,
                "flags": new_flags,
                "timelock": timelock_blocks,
            })
            self._cache.pop(name, None)

            return VerusIDOperationResult(
                operation="lock_vault",
                identity_name=name,
                success=True,
                txid=result if isinstance(result, str) else result.get("txid"),
                data={"timelock_blocks": timelock_blocks},
            )
        except VerusError as exc:
            logger.error("Failed to lock vault for '%s': %s", name, exc)
            return VerusIDOperationResult(
                operation="lock_vault",
                identity_name=name,
                success=False,
                error=str(exc),
            )

    async def unlock_vault(self, name: str) -> VerusIDOperationResult:
        """Begin the unlock delay for a vaulted VerusID."""
        try:
            identity = await self.get_identity(name)
            new_flags = identity.flags & ~IdentityFlag.LOCKED

            result = await self.cli.updateidentity({
                "name": name,
                "flags": new_flags,
                "timelock": 0,
            })
            self._cache.pop(name, None)

            return VerusIDOperationResult(
                operation="unlock_vault",
                identity_name=name,
                success=True,
                txid=result if isinstance(result, str) else result.get("txid"),
            )
        except VerusError as exc:
            logger.error("Failed to unlock vault for '%s': %s", name, exc)
            return VerusIDOperationResult(
                operation="unlock_vault",
                identity_name=name,
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Revoke / Recover
    # ------------------------------------------------------------------

    async def revoke_identity(self, name: str) -> VerusIDOperationResult:
        """Revoke a VerusID (must be called by the revocation authority)."""
        try:
            identity = await self.get_identity(name)
            new_flags = identity.flags | IdentityFlag.REVOKED

            result = await self.cli.updateidentity({
                "name": name,
                "flags": new_flags,
            })
            self._cache.pop(name, None)

            return VerusIDOperationResult(
                operation="revoke",
                identity_name=name,
                success=True,
                txid=result if isinstance(result, str) else result.get("txid"),
            )
        except VerusError as exc:
            logger.error("Failed to revoke identity '%s': %s", name, exc)
            return VerusIDOperationResult(
                operation="revoke",
                identity_name=name,
                success=False,
                error=str(exc),
            )

    async def recover_identity(
        self, name: str, new_primary_addresses: List[str]
    ) -> VerusIDOperationResult:
        """Recover a VerusID to new keys (must be called by recovery authority)."""
        try:
            identity = await self.get_identity(name)
            new_flags = identity.flags & ~IdentityFlag.REVOKED

            result = await self.cli.updateidentity({
                "name": name,
                "flags": new_flags,
                "primaryaddresses": new_primary_addresses,
            })
            self._cache.pop(name, None)

            return VerusIDOperationResult(
                operation="recover",
                identity_name=name,
                success=True,
                txid=result if isinstance(result, str) else result.get("txid"),
                data={"new_addresses": new_primary_addresses},
            )
        except VerusError as exc:
            logger.error("Failed to recover identity '%s': %s", name, exc)
            return VerusIDOperationResult(
                operation="recover",
                identity_name=name,
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Signature operations
    # ------------------------------------------------------------------

    async def sign_message(self, identity_name: str, message: str) -> Optional[str]:
        """Sign a message with a VerusID (creates an unforgeable attestation)."""
        try:
            return await self.cli.signmessage(identity_name, message)
        except VerusError as exc:
            logger.error("Failed to sign message for '%s': %s", identity_name, exc)
            return None

    async def verify_signature(
        self, identity_name: str, signature: str, message: str
    ) -> bool:
        """Verify a VerusID signature."""
        try:
            return await self.cli.verifymessage(identity_name, signature, message)
        except VerusError as exc:
            logger.error("Signature verification failed: %s", exc)
            return False
