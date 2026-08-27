"""Fail-closed activation and mutation controls for :mod:`verus_agent`.

The controls in this module are deliberately independent of the runner
allowlist.  An allowlist says which capability a caller may request; it is not
evidence that a person approved an on-chain mutation.

Approval files are local operator records.  Their presence is evidence used by
the runtime gate, not cryptographic proof that a human created or reviewed
them.  Projects remain responsible for the human workflow that creates those
records and for keeping them outside Git, prompts, and logs.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional


class PolicyViolation(RuntimeError):
    """A request failed a fail-closed runtime policy check."""


class ActivationStage(str, Enum):
    """Cross-project activation stages, ordered by increasing authority."""

    DISABLED = "disabled"
    READ_ONLY = "read_only"
    WALLET_REVIEW = "wallet_review"
    TESTNET_WRITE = "testnet_write"


# RPC methods which this repository treats as non-mutating.  Unknown RPC
# methods fail closed in the low-level wrapper instead of being assumed safe.
READ_ONLY_RPC_METHODS = frozenset(
    {
        "estimateconversion",
        "getblock",
        "getblockcount",
        "getcurrency",
        "getcurrencystate",
        "getidentity",
        "getidentitycontent",
        "getidentitytrust",
        "getcurrencytrust",
        "getinfo",
        "getmininginfo",
        "getoffers",
        "getrawmempool",
        "getvdxfid",
        "verifymessage",
        "verifysignature",
        "z_getoperationstatus",
    }
)


# Known writes and wallet-sensitive RPCs.  The low-level wrapper also treats
# every RPC absent from READ_ONLY_RPC_METHODS as authorization-required.
MUTATING_RPC_METHODS = frozenset(
    {
        "closeoffers",
        "createinvoice",
        "definecurrency",
        "importprivkey",
        "makeoffer",
        "registeridentity",
        "registernamecommitment",
        "sendcurrency",
        "sendrawtransaction",
        "setcurrencytrust",
        "setgenerate",
        "setidentitytrust",
        "signdata",
        "signmessage",
        "signrawtransaction",
        "takeoffer",
        "updateidentity",
        "z_exportviewingkey",
        "z_getnewaddress",
        "z_importviewingkey",
        "z_sendmany",
    }
)


READ_ONLY_CAPABILITIES = frozenset(
    {
        "verus.identity.get",
        "verus.currency.estimate",
        "verus.storage.retrieve",
        "verus.storage.retrieve_data_wrapper",
        "verus.login.authenticate",
        "verus.login.validate",
        "verus.market.monitor",
        "verus.cli.execute",
        "verus.mining.info",
        "verus.staking.status",
        "verus.trust.get_ratings",
        "verus.marketplace.list_open_offers",
        "verus.security.verify",
        "verus.security.status",
        "verus.marketplace.verify_license",
        "verus.marketplace.list_offers",
        "verus.marketplace.discover",
        "verus.marketplace.search",
        "verus.marketplace.verify_license_cross_chain",
        "verus.ip.verify_integrity",
        "verus.ip.get_model_info",
        "verus.reputation.query",
        "verus.reputation.leaderboard",
        "verus.reputation.verify",
        "verus.data.verify",
        "verus.data.getvdxfid",
        "verus.data.build_vdxf",
        "verus.provenance.verify",
        "verus.mobile.capabilities",
    }
)


# The built-in default is deliberately smaller than the full read-only
# inventory. Other reads may expose application or wallet data and therefore
# require an explicit consuming-project profile.
DEFAULT_READ_ONLY_CAPABILITIES = frozenset(
    {
        "verus.cli.execute",
        "verus.identity.get",
        "verus.currency.estimate",
        "verus.storage.retrieve",
        "verus.storage.retrieve_data_wrapper",
        "verus.mobile.capabilities",
        "verus.login.authenticate",
        "verus.login.validate",
        "verus.market.monitor",
    }
)


WALLET_REVIEW_CAPABILITIES = frozenset(
    {
        "verus.mobile.payment_uri",
        "verus.mobile.login_consent",
        "verus.mobile.purchase_link",
        "verus.mobile.generic_request_link",
        "verus.mobile.identity_update_request_link",
        "verus.mobile.user_data_request_link",
        "verus.mobile.data_packet_request_link",
    }
)


# These implemented surfaces do not yet have a sufficient cross-project
# privacy/local-file authorization contract. They remain callable as library
# research surfaces but cannot be activated through process_task.
BLOCKED_CAPABILITIES = frozenset(
    {
        "verus.data.decrypt",
        "verus.data.list_received",
        "verus.messaging.receive_decrypt",
        "verus.mobile.app_encryption_request_link",
        "verus.ip.decrypt_model",
        "verus.ip.encrypt_model",
        "verus.ip.generate_watermark",
        "verus.ip.verify_watermark",
    }
)


# These two handlers now implement the complete verification contract.  Other
# write handlers remain present as research/implementation surfaces but cannot
# be activated through process_task until they implement equivalent checks.
SUPPORTED_TESTNET_MUTATIONS = frozenset(
    {
        "verus.identity.update",
        "verus.currency.send",
    }
)


MUTATING_CAPABILITIES = frozenset(
    {
        "verus.bridge.cross",
        "verus.currency.convert",
        "verus.currency.launch",
        "verus.currency.send",
        "verus.data.export_viewingkey",
        "verus.data.import_viewingkey",
        "verus.data.sign",
        "verus.defi.create_revenue_basket",
        "verus.defi.define_pbaas_chain",
        "verus.defi.distribute_revenue",
        "verus.identity.create",
        "verus.identity.update",
        "verus.identity.vault",
        "verus.ip.full_protect",
        "verus.ip.register_model",
        "verus.ip.register_storage",
        "verus.marketplace.close_offers",
        "verus.marketplace.create_invoice",
        "verus.marketplace.issue_license",
        "verus.marketplace.make_offer",
        "verus.marketplace.register_product",
        "verus.marketplace.take_offer",
        "verus.messaging.send_encrypted",
        "verus.mining.start",
        "verus.provenance.create_nft",
        "verus.provenance.deliver_encrypted",
        "verus.provenance.list_offer",
        "verus.provenance.sign_mmr",
        "verus.provenance.store_descriptors",
        "verus.reputation.attest",
        "verus.security.register",
        "verus.security.revoke",
        "verus.storage.store",
        "verus.storage.store_data_wrapper",
        "verus.storage.store_sendcurrency",
        "verus.trust.set_currency_trust",
        "verus.trust.set_identity_trust",
    }
)


CAPABILITY_RPC_METHODS: Mapping[str, frozenset[str]] = {
    "verus.identity.update": frozenset({"updateidentity"}),
    "verus.currency.send": frozenset({"sendcurrency"}),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PolicyViolation(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PolicyViolation(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ActivationProfile:
    """Public-safe project contract loaded by consuming applications."""

    profile_id: str
    stage: ActivationStage
    network: str
    canonical_store: str
    actor_model: str
    private_data_boundary: str
    non_goals: tuple[str, ...]
    allowed_capabilities: frozenset[str]
    allowed_rpc_methods: frozenset[str]

    @classmethod
    def safe_default(cls) -> "ActivationProfile":
        return cls(
            profile_id="default-read-only",
            stage=ActivationStage.READ_ONLY,
            network="testnet",
            canonical_store="undeclared",
            actor_model="undeclared",
            private_data_boundary="No real participant, wallet, or client data.",
            non_goals=("blockchain mutation", "mainnet", "production deployment"),
            allowed_capabilities=frozenset(DEFAULT_READ_ONLY_CAPABILITIES),
            allowed_rpc_methods=frozenset(
                {
                    "estimateconversion",
                    "getblockcount",
                    "getcurrencystate",
                    "getidentity",
                    "getidentitycontent",
                    "getinfo",
                    "z_getoperationstatus",
                }
            ),
        )

    @classmethod
    def from_path(cls, path: Optional[str]) -> "ActivationProfile":
        if not path:
            return cls.safe_default()
        source = Path(path).expanduser().resolve()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyViolation(f"Cannot load activation profile: {source}") from exc
        if not isinstance(payload, dict):
            raise PolicyViolation("Activation profile must be a JSON object")
        required_text = (
            "profile_id",
            "stage",
            "network",
            "canonical_store",
            "actor_model",
            "private_data_boundary",
        )
        for key in required_text:
            if not isinstance(payload.get(key), str) or not payload[key].strip():
                raise PolicyViolation(f"Activation profile requires non-empty {key}")
        if payload["network"].lower() != "testnet":
            raise PolicyViolation("Activation profiles are Testnet-only")
        try:
            stage = ActivationStage(payload["stage"])
        except ValueError as exc:
            raise PolicyViolation("Unknown activation stage") from exc
        non_goals = payload.get("non_goals")
        allowed = payload.get("allowed_capabilities")
        allowed_rpc_methods = payload.get("allowed_rpc_methods")
        if not isinstance(non_goals, list) or not all(isinstance(v, str) for v in non_goals):
            raise PolicyViolation("non_goals must be a list of strings")
        if not isinstance(allowed, list) or not all(isinstance(v, str) for v in allowed):
            raise PolicyViolation("allowed_capabilities must be a list of strings")
        if not isinstance(allowed_rpc_methods, list) or not all(
            isinstance(v, str) for v in allowed_rpc_methods
        ):
            raise PolicyViolation("allowed_rpc_methods must be a list of strings")
        return cls(
            profile_id=payload["profile_id"],
            stage=stage,
            network="testnet",
            canonical_store=payload["canonical_store"],
            actor_model=payload["actor_model"],
            private_data_boundary=payload["private_data_boundary"],
            non_goals=tuple(non_goals),
            allowed_capabilities=frozenset(allowed),
            allowed_rpc_methods=frozenset(allowed_rpc_methods),
        )

    def ensure_task_allowed(self, capability: str, params: Mapping[str, Any]) -> None:
        if capability not in self.allowed_capabilities:
            raise PolicyViolation(
                f"Capability '{capability}' is not enabled by activation profile "
                f"'{self.profile_id}'"
            )
        classified = (
            READ_ONLY_CAPABILITIES
            | WALLET_REVIEW_CAPABILITIES
            | MUTATING_CAPABILITIES
            | BLOCKED_CAPABILITIES
        )
        if capability not in classified:
            raise PolicyViolation(
                f"Capability '{capability}' has no reviewed activation classification"
            )
        if capability in BLOCKED_CAPABILITIES:
            raise PolicyViolation(
                f"Capability '{capability}' has no complete privacy/authorization contract"
            )
        if capability == "verus.cli.execute":
            method = str(params.get("method", ""))
            if method not in READ_ONLY_RPC_METHODS or method not in self.allowed_rpc_methods:
                raise PolicyViolation(
                    "Raw RPC dispatch is limited to profile-approved read-only methods"
                )
        if self.stage == ActivationStage.DISABLED:
            raise PolicyViolation("Activation profile is disabled")
        if capability in WALLET_REVIEW_CAPABILITIES and self.stage not in {
            ActivationStage.WALLET_REVIEW,
            ActivationStage.TESTNET_WRITE,
        }:
            raise PolicyViolation("Wallet-mediated capability requires wallet_review stage")
        if requires_mutation_authorization(capability, params):
            if self.stage != ActivationStage.TESTNET_WRITE:
                raise PolicyViolation("Mutation requires testnet_write activation stage")
            if capability not in SUPPORTED_TESTNET_MUTATIONS:
                raise PolicyViolation(
                    f"Mutation capability '{capability}' has no complete verification contract"
                )

    def capability_is_activatable(self, capability: str) -> bool:
        """Return whether status output may truthfully advertise a capability."""

        if self.stage == ActivationStage.DISABLED:
            return False
        if capability not in self.allowed_capabilities or capability in BLOCKED_CAPABILITIES:
            return False
        if capability in MUTATING_CAPABILITIES:
            return (
                self.stage == ActivationStage.TESTNET_WRITE
                and capability in SUPPORTED_TESTNET_MUTATIONS
            )
        if capability in WALLET_REVIEW_CAPABILITIES:
            return self.stage in {
                ActivationStage.WALLET_REVIEW,
                ActivationStage.TESTNET_WRITE,
            }
        return capability in READ_ONLY_CAPABILITIES


@dataclass(frozen=True)
class ApprovalGrant:
    approval_id: str
    task_id: str
    capability: str
    network: str
    idempotency_key: str
    rpc_methods: frozenset[str]
    issued_at: datetime
    expires_at: datetime

    @property
    def summary_hash(self) -> str:
        payload = f"{self.approval_id}|{self.task_id}|{self.capability}|{self.idempotency_key}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ApprovalStore:
    """Load and validate exact, short-lived operator approval records."""

    def __init__(self, path: Optional[str]):
        self.path = Path(path).expanduser().resolve() if path else None

    def authorize(
        self,
        *,
        task_id: str,
        capability: str,
        network: str,
        idempotency_key: str,
    ) -> ApprovalGrant:
        if not self.path:
            raise PolicyViolation("No local mutation approval file is configured")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyViolation("Local mutation approval file cannot be loaded") from exc
        grants = payload.get("grants") if isinstance(payload, dict) else None
        if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(grants, list):
            raise PolicyViolation("Mutation approval file must use schema version 1")
        now = _utcnow()
        for item in grants:
            if not isinstance(item, dict):
                continue
            if (
                item.get("task_id") != task_id
                or item.get("capability") != capability
                or item.get("network") != network
                or item.get("idempotency_key") != idempotency_key
            ):
                continue
            approval_id = item.get("approval_id")
            rpc_methods = item.get("rpc_methods")
            if not isinstance(approval_id, str) or len(approval_id) < 8:
                raise PolicyViolation("approval_id must contain at least 8 characters")
            if not isinstance(rpc_methods, list) or not all(
                isinstance(method, str) for method in rpc_methods
            ):
                raise PolicyViolation("rpc_methods must be a list of strings")
            issued_at = _parse_utc(item.get("issued_at", ""), "issued_at")
            expires_at = _parse_utc(item.get("expires_at", ""), "expires_at")
            lifetime = (expires_at - issued_at).total_seconds()
            if lifetime <= 0 or lifetime > 900:
                raise PolicyViolation("Approval lifetime must be between 1 and 900 seconds")
            if now < issued_at or now >= expires_at:
                raise PolicyViolation("Mutation approval is not currently valid")
            required_methods = CAPABILITY_RPC_METHODS.get(capability, frozenset())
            granted_methods = frozenset(rpc_methods)
            if granted_methods != required_methods:
                raise PolicyViolation(
                    "Mutation approval RPC methods must exactly match the capability contract"
                )
            return ApprovalGrant(
                approval_id=approval_id,
                task_id=task_id,
                capability=capability,
                network=network,
                idempotency_key=idempotency_key,
                rpc_methods=granted_methods,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        raise PolicyViolation("No exact approval grant matches this mutation")


_CURRENT_GRANT: ContextVar[Optional[ApprovalGrant]] = ContextVar(
    "verus_mutation_approval", default=None
)


@contextmanager
def mutation_scope(grant: ApprovalGrant) -> Iterator[None]:
    now = _utcnow()
    if now < grant.issued_at or now >= grant.expires_at:
        raise PolicyViolation("Mutation approval expired before dispatch")
    token = _CURRENT_GRANT.set(grant)
    try:
        yield
    finally:
        _CURRENT_GRANT.reset(token)


def require_rpc_authorization(method: str) -> None:
    """Allow reviewed reads and require a scoped grant for every other RPC."""

    if method in READ_ONLY_RPC_METHODS:
        return
    grant = _CURRENT_GRANT.get()
    if grant is None:
        raise PolicyViolation(f"RPC method '{method}' requires mutation authorization")
    if method not in grant.rpc_methods:
        raise PolicyViolation(f"Approval does not authorize RPC method '{method}'")


def requires_mutation_authorization(
    capability: str, params: Optional[Mapping[str, Any]] = None
) -> bool:
    if capability in MUTATING_CAPABILITIES:
        return True
    if capability == "verus.cli.execute":
        method = str((params or {}).get("method", ""))
        return method not in READ_ONLY_RPC_METHODS
    return False


class MutationOutbox:
    """Small durable idempotency journal for approved mutation tasks."""

    def __init__(self, path: Optional[str]):
        self.path = Path(path).expanduser().resolve() if path else None

    def _connect(self) -> sqlite3.Connection:
        if not self.path:
            raise PolicyViolation("No local mutation outbox path is configured")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path), timeout=5)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mutation_outbox (
                idempotency_key TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        return connection

    @staticmethod
    def request_hash(capability: str, params: Mapping[str, Any]) -> str:
        canonical = json.dumps(
            {"capability": capability, "params": params},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def claim(
        self, idempotency_key: str, capability: str, params: Mapping[str, Any]
    ) -> Optional[Dict[str, Any]]:
        request_hash = self.request_hash(capability, params)
        now = _utcnow().isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT request_hash, status, result_json FROM mutation_outbox "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row:
                previous_hash, status, result_json = row
                if previous_hash != request_hash:
                    raise PolicyViolation("Idempotency key was already used for another request")
                if status == "complete" and result_json:
                    result = json.loads(result_json)
                    result["_idempotent_replay"] = True
                    return result
                raise PolicyViolation(f"Idempotent mutation is already {status}")
            connection.execute(
                "INSERT INTO mutation_outbox VALUES (?, ?, 'pending', NULL, ?)",
                (idempotency_key, request_hash, now),
            )
        return None

    def complete(self, idempotency_key: str, result: Mapping[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE mutation_outbox SET status='complete', result_json=?, updated_at=? "
                "WHERE idempotency_key=?",
                (json.dumps(result, sort_keys=True, default=str), _utcnow().isoformat(), idempotency_key),
            )

    def fail(self, idempotency_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE mutation_outbox SET status='failed', updated_at=? "
                "WHERE idempotency_key=?",
                (_utcnow().isoformat(), idempotency_key),
            )


def validate_confirmed_result(capability: str, result: Any) -> None:
    if not isinstance(result, dict) or result.get("success") is not True:
        raise PolicyViolation("Mutation handler did not report success")
    if capability == "verus.currency.send":
        if result.get("confirmed") is not True or not result.get("txid"):
            raise PolicyViolation("Currency send lacks terminal operation confirmation")
    elif capability == "verus.identity.update":
        if result.get("readback_verified") is not True or not result.get("txid"):
            raise PolicyViolation("Identity update lacks confirmed state readback")
