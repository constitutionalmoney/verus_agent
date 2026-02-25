"""
Agent Reputation System — VerusID-backed Trust Scoring & Attestations

Implements decentralized, tamper-proof agent reputation via VerusID:
  - Attestation issuance (identity → identity, on-chain signed reviews)
  - Reputation score computation (weighted rolling average)
  - Cross-chain reputation query (for multi-chain agents)
  - Staking-backed reputation (higher stake → higher trust weight)

Architecture (from Issue #9 §5.5 — Phase 4):

    Attestor VerusID  ──signdata──►  vrsc::uai.agent.attestation.*
         │                                    │
         └─ signature + rating stored in ────►│
            target agent's contentmultimap    │
                                              ▼
                                      Reputation Score
                                      (composite from all
                                       on-chain attestations)

Each attestation is a VDXF record on the **target** agent's VerusID
containing: attestor, rating (0-100), category, comment, timestamp,
and the attestor's VerusID signature over the payload.

Toggle via config:  ``VERUS_REPUTATION_ENABLED=true``

References:
    - Issue #9 §5.5: Agent Reputation System as VerusID Attestations
    - VerusID signdata / verifysigneddata RPCs
    - https://docs.verus.io/verusid/#attestations
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from verus_agent.cli_wrapper import VerusCLI, VerusError
from verus_agent.verusid import VerusIDManager

logger = logging.getLogger("verus_agent.reputation")


# ---------------------------------------------------------------------------
# VDXF keys for reputation (vrsc::uai.agent.attestation.*)
# ---------------------------------------------------------------------------

VDXF_ATTEST_ATTESTOR = "vrsc::uai.agent.attestation.attestor"
VDXF_ATTEST_RATING = "vrsc::uai.agent.attestation.rating"
VDXF_ATTEST_CATEGORY = "vrsc::uai.agent.attestation.category"
VDXF_ATTEST_COMMENT = "vrsc::uai.agent.attestation.comment"
VDXF_ATTEST_TIMESTAMP = "vrsc::uai.agent.attestation.timestamp"
VDXF_ATTEST_SIGNATURE = "vrsc::uai.agent.attestation.signature"

# Aggregated reputation score stored on the agent's own identity
VDXF_REPUTATION_SCORE = "vrsc::uai.agent.reputation.score"
VDXF_REPUTATION_COUNT = "vrsc::uai.agent.reputation.count"
VDXF_REPUTATION_CATEGORIES = "vrsc::uai.agent.reputation.categories"


class AttestationCategory(str, Enum):
    """Standard categories for agent ratings."""
    QUALITY = "quality"           # Output quality / correctness
    RELIABILITY = "reliability"   # Uptime, consistency
    SPEED = "speed"               # Response latency
    SECURITY = "security"         # Security posture
    VALUE = "value"               # Cost-effectiveness
    OVERALL = "overall"           # General rating


@dataclass
class Attestation:
    """A single on-chain reputation attestation."""
    attestor_identity: str         # Who rated
    target_identity: str           # Who was rated
    rating: int                    # 0-100
    category: AttestationCategory
    comment: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    signature: str = ""            # VerusID signature of the attestor
    txid: str = ""                 # On-chain transaction ID
    verified: bool = False         # Signature verified?


@dataclass
class ReputationScore:
    """Aggregated reputation for an agent identity."""
    agent_identity: str
    overall_score: float           # 0-100 weighted average
    total_attestations: int
    category_scores: Dict[str, float] = field(default_factory=dict)
    recent_attestations: List[Attestation] = field(default_factory=list)
    stake_weight: float = 1.0      # Multiplier from staking amount
    confidence: float = 0.0        # 0-1, based on attestation count & diversity


@dataclass
class ReputationResult:
    """Result of a reputation operation."""
    operation: str
    success: bool
    agent_identity: Optional[str] = None
    txid: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reputation Manager
# ---------------------------------------------------------------------------

class VerusReputationSystem:
    """
    Decentralized agent reputation via VerusID attestations.

    Usage::

        rep = VerusReputationSystem(cli, id_mgr)

        # Leave a rating
        await rep.attest(
            attestor="Alice@",
            target="UAITranslator@",
            rating=85,
            category=AttestationCategory.QUALITY,
            comment="Excellent translation accuracy",
        )

        # Get reputation
        score = await rep.get_reputation("UAITranslator@")
        print(score.overall_score)  # 85.0

        # Get leaderboard
        top = await rep.get_leaderboard(limit=10)
    """

    # How many recent attestations to keep in memory per agent
    MAX_CACHE_PER_AGENT = 200

    # Minimum attestations before confidence > 0.5
    MIN_ATTESTATIONS_CONFIDENT = 5

    def __init__(
        self,
        cli: VerusCLI,
        identity_manager: VerusIDManager,
        enabled: bool = False,
    ):
        self.cli = cli
        self.identity_manager = identity_manager
        self.enabled = enabled or os.getenv(
            "VERUS_REPUTATION_ENABLED", ""
        ).lower() in ("true", "1", "yes")

        # In-memory attestation store (identity → list[Attestation])
        self._attestations: Dict[str, List[Attestation]] = {}
        # Cached scores
        self._scores: Dict[str, ReputationScore] = {}

        logger.info("Reputation system initialized: enabled=%s", self.enabled)

    # ------------------------------------------------------------------
    # Attestation Issuance
    # ------------------------------------------------------------------

    async def attest(
        self,
        attestor: str,
        target: str,
        rating: int,
        category: AttestationCategory = AttestationCategory.OVERALL,
        comment: str = "",
    ) -> ReputationResult:
        """
        Issue an on-chain attestation (rating) from one VerusID to another.

        The attestation is:
          1. Signed by the attestor's VerusID
          2. Stored in the target's contentmultimap
          3. Cached locally for fast aggregation
        """
        if not self.enabled:
            return ReputationResult(
                operation="attest", success=False,
                error="Reputation system disabled. Set VERUS_REPUTATION_ENABLED=true",
            )

        rating = max(0, min(100, rating))

        # Build the attestation payload
        payload = {
            "attestor": attestor,
            "target": target,
            "rating": rating,
            "category": category.value,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        }
        payload_json = json.dumps(payload, sort_keys=True)

        # Sign the payload with the attestor's identity
        try:
            signature = await self.identity_manager.sign_message(
                attestor, payload_json
            ) or ""
        except VerusError:
            signature = ""

        # Store on-chain in the target's contentmultimap
        attest_record = json.dumps({
            **payload,
            "signature": signature,
        })

        try:
            result = await self.identity_manager.update_identity(
                target,
                content_multimap={
                    VDXF_ATTEST_ATTESTOR: [{"": attestor}],
                    VDXF_ATTEST_RATING: [{"": str(rating)}],
                    VDXF_ATTEST_CATEGORY: [{"": category.value}],
                    VDXF_ATTEST_COMMENT: [{"": comment}],
                    VDXF_ATTEST_TIMESTAMP: [{"": payload["timestamp"]}],
                    VDXF_ATTEST_SIGNATURE: [{"": signature}],
                },
            )

            if not result.success:
                return ReputationResult(
                    operation="attest", success=False,
                    agent_identity=target, error=result.error,
                )

            # Cache the attestation
            att = Attestation(
                attestor_identity=attestor,
                target_identity=target,
                rating=rating,
                category=category,
                comment=comment,
                signature=signature,
                txid=result.txid or "",
                verified=bool(signature),
            )
            self._cache_attestation(att)

            logger.info(
                "Attestation: %s → %s rating=%d category=%s",
                attestor, target, rating, category.value,
            )

            return ReputationResult(
                operation="attest",
                success=True,
                agent_identity=target,
                txid=result.txid,
                data={"rating": rating, "category": category.value},
            )

        except VerusError as exc:
            return ReputationResult(
                operation="attest", success=False,
                agent_identity=target, error=str(exc),
            )

    # ------------------------------------------------------------------
    # Reputation Query
    # ------------------------------------------------------------------

    async def get_reputation(self, agent_identity: str) -> ReputationScore:
        """
        Compute the aggregated reputation score for an agent.

        Pulls attestations from:
          1. Local cache
          2. On-chain contentmultimap (if not cached)

        Returns a :class:`ReputationScore` with overall + per-category scores.
        """
        # Try to fetch on-chain attestations if not cached
        if agent_identity not in self._attestations:
            await self._load_attestations(agent_identity)

        attestations = self._attestations.get(agent_identity, [])

        if not attestations:
            return ReputationScore(
                agent_identity=agent_identity,
                overall_score=0.0,
                total_attestations=0,
                confidence=0.0,
            )

        # Group by category
        by_category: Dict[str, List[int]] = {}
        for att in attestations:
            cat = att.category.value
            by_category.setdefault(cat, []).append(att.rating)

        # Compute per-category averages
        category_scores: Dict[str, float] = {}
        for cat, ratings in by_category.items():
            category_scores[cat] = sum(ratings) / len(ratings)

        # Weight categories equally for overall (can be customized)
        overall = (
            sum(category_scores.values()) / len(category_scores)
            if category_scores else 0.0
        )

        # Confidence: sigmoid-like curve based on attestation count
        n = len(attestations)
        confidence = min(1.0, n / (n + self.MIN_ATTESTATIONS_CONFIDENT))

        # Unique attestors boost confidence
        unique_attestors = len({a.attestor_identity for a in attestations})
        diversity_bonus = min(0.2, unique_attestors * 0.04)
        confidence = min(1.0, confidence + diversity_bonus)

        score = ReputationScore(
            agent_identity=agent_identity,
            overall_score=round(overall, 2),
            total_attestations=n,
            category_scores=category_scores,
            recent_attestations=attestations[-10:],
            confidence=round(confidence, 3),
        )

        self._scores[agent_identity] = score
        return score

    async def get_leaderboard(
        self,
        limit: int = 10,
        category: Optional[AttestationCategory] = None,
    ) -> List[ReputationScore]:
        """
        Return the top-rated agents from the local cache.

        Call :meth:`get_reputation` for each known agent first to refresh.
        """
        scores = list(self._scores.values())

        if category:
            # Sort by specific category score
            scores.sort(
                key=lambda s: s.category_scores.get(category.value, 0),
                reverse=True,
            )
        else:
            scores.sort(key=lambda s: s.overall_score, reverse=True)

        return scores[:limit]

    # ------------------------------------------------------------------
    # Attestation Verification
    # ------------------------------------------------------------------

    async def verify_attestation(self, attestation: Attestation) -> bool:
        """
        Verify the VerusID signature on an attestation.

        Returns True if the signature is valid for the claimed attestor.
        """
        if not attestation.signature:
            return False

        payload = json.dumps({
            "attestor": attestation.attestor_identity,
            "target": attestation.target_identity,
            "rating": attestation.rating,
            "category": attestation.category.value,
            "comment": attestation.comment,
            "timestamp": attestation.timestamp.isoformat(),
        }, sort_keys=True)

        try:
            valid = await self.identity_manager.verify_message(
                attestation.attestor_identity,
                payload,
                attestation.signature,
            )
            attestation.verified = valid
            return valid
        except VerusError:
            return False

    # ------------------------------------------------------------------
    # Staking Weight
    # ------------------------------------------------------------------

    async def update_stake_weight(self, agent_identity: str) -> float:
        """
        Compute reputation weight bonus from VRSC staking amount.

        Agents that stake more VRSC get a higher trust multiplier
        (logarithmic scale to prevent plutocratic domination).
        """
        import math

        try:
            # Get the balance associated with the agent's identity
            identity = await self.identity_manager.get_identity(agent_identity)
            # Check balance of primary address
            addrs = identity.primary_addresses or []
            total_staked = 0.0
            for addr in addrs:
                try:
                    bal = await self.cli.z_getbalance(addr)
                    total_staked += bal
                except VerusError:
                    pass

            # Log-scale weight: 1.0 at 0 VRSC, ~1.5 at 100 VRSC, ~2.0 at 10K VRSC
            weight = 1.0 + 0.15 * math.log10(max(1, total_staked))
            weight = min(3.0, weight)  # Cap at 3x

            if agent_identity in self._scores:
                self._scores[agent_identity].stake_weight = round(weight, 3)

            return round(weight, 3)
        except VerusError:
            return 1.0

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_reputation_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "tracked_agents": len(self._attestations),
            "total_attestations": sum(
                len(v) for v in self._attestations.values()
            ),
            "cached_scores": len(self._scores),
            "top_agents": [
                {"agent": s.agent_identity, "score": s.overall_score}
                for s in sorted(
                    self._scores.values(),
                    key=lambda s: s.overall_score,
                    reverse=True,
                )[:5]
            ],
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cache_attestation(self, att: Attestation) -> None:
        target = att.target_identity
        if target not in self._attestations:
            self._attestations[target] = []
        self._attestations[target].append(att)
        # Trim to max cache size
        if len(self._attestations[target]) > self.MAX_CACHE_PER_AGENT:
            self._attestations[target] = self._attestations[target][
                -self.MAX_CACHE_PER_AGENT:
            ]

    async def _load_attestations(self, agent_identity: str) -> None:
        """Load attestations from the agent's on-chain contentmultimap."""
        try:
            identity = await self.identity_manager.get_identity(agent_identity)
            mm = identity.content_multimap or {}

            attestor = self._mm_str(mm, VDXF_ATTEST_ATTESTOR)
            rating_str = self._mm_str(mm, VDXF_ATTEST_RATING, "0")
            category_str = self._mm_str(mm, VDXF_ATTEST_CATEGORY, "overall")
            comment = self._mm_str(mm, VDXF_ATTEST_COMMENT)
            sig = self._mm_str(mm, VDXF_ATTEST_SIGNATURE)
            ts_str = self._mm_str(mm, VDXF_ATTEST_TIMESTAMP)

            if attestor and rating_str:
                try:
                    rating = int(rating_str)
                except ValueError:
                    rating = 0

                try:
                    ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
                except ValueError:
                    ts = datetime.now()

                att = Attestation(
                    attestor_identity=attestor,
                    target_identity=agent_identity,
                    rating=rating,
                    category=AttestationCategory(category_str),
                    comment=comment,
                    timestamp=ts,
                    signature=sig,
                    verified=False,
                )
                self._cache_attestation(att)

        except VerusError as exc:
            logger.debug("Could not load attestations for %s: %s", agent_identity, exc)

    @staticmethod
    def _mm_str(mm: Dict[str, Any], key: str, default: str = "") -> str:
        if key not in mm:
            return default
        val = mm[key]
        if isinstance(val, list) and val:
            entry = val[0]
            if isinstance(entry, dict) and "" in entry:
                return str(entry[""])
            return str(entry)
        return str(val) if val else default
