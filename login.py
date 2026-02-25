"""
VerusID Login Authentication Module

Implements decentralized authentication using the VerusID Login protocol.
Supports server-side login challenge generation, response processing,
and session validation — entirely on-chain, no passwords.

QR Code Generation & UTXO Transaction Construction:
    The VerusID login flow generates QR codes for wallet scanning. For
    **offline QR code generation** and UTXO transaction construction/signing,
    the companion JS/TS layer MUST use the BitGo UTXO library:

        @bitgo/utxo-lib  — https://www.npmjs.com/package/@bitgo/utxo-lib

    Key imports from @bitgo/utxo-lib (used by verusid-ts-client internally)::

        import {
            IdentitySignature,  // Offline sign/verify
            ECPair,             // Key pair from WIF
            networks,           // networks.verus
            address,            // fromBase58Check
            smarttxs,           // createUnfundedIdentityUpdate,
                                //   validateFundedCurrencyTransfer,
                                //   completeFundedIdentityUpdate
            Transaction         // SIGHASH_ALL, fromHex, toHex
        } from "@bitgo/utxo-lib";

    The Python agent handles server-side challenge/verify logic; the
    JS/TS client (Verus Mobile, web apps) handles QR generation via
    @bitgo/utxo-lib. See verus_agent.mobile for QR data string helpers.

⚠️  DEPRECATED vs. NEW LOGIN API (from verusid-ts-client source analysis):
    The old LoginConsent* classes are **@deprecated**. The current API uses:

    **NEW (current)**::

        GenericRequest / GenericResponse  (extend GenericEnvelope)
        ├── details: Array<OrdinalVDXFObject>  (content items)
        │   ├── AuthenticationRequestOrdinalVDXFObject  (MUST be index 0)
        │   ├── ProvisionIdentityDetailsOrdinalVDXFObject
        │   ├── AppEncryptionRequestOrdinalVDXFObject
        │   ├── IdentityUpdateRequestOrdinalVDXFObject  (MUST be last)
        │   └── VerusPayInvoiceDetailsOrdinalVDXFObject (MUST be last)
        ├── signature: VerifiableSignatureData  (replaces VerusIDSignature)
        │   ├── systemID: CompactIAddressObject  (e.g. VRSC)
        │   ├── identityID: CompactIAddressObject (signing identity)
        │   ├── signatureVersion (default 2)
        │   └── signatureAsVch: Buffer
        ├── responseURIs: Array<ResponseURI>  (TYPE_POST=1, TYPE_REDIRECT=2)
        ├── encryptResponseToAddress: SaplingPaymentAddress  (optional)
        ├── requestID, createdAt, salt, appOrDelegatedID
        └── flags: SIGNED | HAS_REQUEST_ID | HAS_CREATED_AT | MULTI_DETAILS
                   | IS_TESTNET | HAS_SALT | HAS_APP_OR_DELEGATED_ID
                   | HAS_RESPONSE_URIS | HAS_ENCRYPT_RESPONSE_TO_ADDRESS

    **OLD (@deprecated — still functional but should migrate)**::

        LoginConsentRequest / LoginConsentResponse
        LoginConsentChallenge / LoginConsentDecision
        LoginConsentProvisioningRequest / LoginConsentProvisioningResponse

    New API methods on VerusIdInterface::

        createGenericRequest(params, wif?, identity?, height?, chainIAddr?)
        createGenericResponse(params, wif?, identity?, height?, chainIAddr?)
        signGenericRequest(request, wif, identity?, height?)
        signGenericResponse(response, wif, identity?, height?)
        verifyGenericRequest(request, identity?, chainIAddr?, sigBlockTime?)
        verifyGenericResponse(response, identity?, chainIAddr?, sigBlockTime?)

    Login-specific details class::

        AuthenticationRequestDetails {
            flags, requestID, expiryTime,
            recipientConstraints: Array<RecipientConstraint>
        }
        RecipientConstraint {
            type: REQUIRED_ID (1) | REQUIRED_SYSTEM (2) | REQUIRED_PARENT (3)
            identity: CompactIAddressObject
        }

    Additional capabilities in GenericRequest::

        AppEncryptionRequestDetails  — Request encrypted derived seed from wallet
        ProvisionIdentityDetails     — Provision new VerusID (system/parent/identity)
        IdentityUpdateRequestDetails — Client-side identity update with signData
        VerusPayInvoiceDetails       — Payment invoice (V3/V4)

Server-Side RPC (via verusd-rpc-ts-client):
    The VerusID login flow requires the TypeScript RPC client for server-side
    verification. VerusIdInterface (verusid-ts-client) wraps VerusdRpcInterface
    (verusd-rpc-ts-client) internally — all RPC calls go through it.

    Key RPC methods used during login::

        // Create VerusdRpcInterface (used internally by VerusIdInterface)
        const rpc = new VerusdRpcInterface(
            "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV",  // VRSC chain ID
            "http://127.0.0.1:27486",               // RPC endpoint
            { auth: { username: 'rpcuser', password: 'rpcpass' } }
        );

        // Methods used during login verification:
        rpc.getIdentity("signingID@")     // Resolve signer's identity
        rpc.getInfo()                      // Get current block height
        rpc.signData(sigParams)            // Server-side signdata (MMR)
        rpc.getVdxfId(vdxfuri)             // Resolve VDXF keys

        // VerusdRpcInterface also provides:
        //   rpcRequestOverride — custom transport for React Native bridges
        //   extractRpcResult() — static helper to unwrap RPC results
        //   getCurrencyConversionPaths() — composite DeFi path discovery

References:
    - https://monkins1010.github.io/veruslogin/
    - https://monkins1010.github.io/veruslogin/getting-started/
    - https://monkins1010.github.io/veruslogin/server-login/
    - https://monkins1010.github.io/veruslogin/process-login/
    - https://monkins1010.github.io/veruslogin/validate-login/
    - https://www.npmjs.com/package/@bitgo/utxo-lib (QR code + UTXO signing)
    - https://github.com/monkins1010/verusid-login-template (reference impl)
    - https://github.com/VerusCoin/verusid-ts-client (TS client source)
    - https://github.com/VerusCoin/verus-typescript-primitives (core types)
    - https://github.com/VerusCoin/verusd-rpc-ts-client (RPC client — REQUIRED for login)
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from verus_agent.cli_wrapper import VerusCLI, VerusError

logger = logging.getLogger("verus_agent.login")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LoginChallenge:
    """Server-generated login challenge for VerusID authentication."""
    challenge_id: str
    message: str
    created_at: datetime
    expires_at: datetime
    signing_identity: Optional[str] = None  # Requested signer
    redirect_uri: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


@dataclass
class LoginSession:
    """Authenticated VerusID login session."""
    session_id: str
    identity_name: str
    identity_address: str
    authenticated_at: datetime
    expires_at: datetime
    challenge_id: str
    signature: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at


@dataclass
class LoginResult:
    """Result of a login attempt."""
    success: bool
    session: Optional[LoginSession] = None
    error: Optional[str] = None
    identity_name: Optional[str] = None


# ---------------------------------------------------------------------------
# VerusID Login Manager
# ---------------------------------------------------------------------------

class VerusLoginManager:
    """
    Manages VerusID-based decentralized authentication.

    Flow:
        1. Server generates a challenge (random message + nonce)
        2. Client signs the challenge with their VerusID private key
        3. Server verifies the signature against the on-chain VerusID
        4. If valid → session created; identity cryptographically proven

    No passwords, no email, no central authority — just math and consensus.

    Usage::

        cli = VerusCLI(config)
        login_mgr = VerusLoginManager(cli)

        # Step 1: Generate challenge
        challenge = login_mgr.create_challenge(signing_identity="UserName@")

        # Step 2: Client signs (handled client-side via wallet)
        # signature = wallet.sign(challenge.message, "UserName@")

        # Step 3: Verify and create session
        result = await login_mgr.process_login(
            challenge_id=challenge.challenge_id,
            identity_name="UserName@",
            signature=signature,
        )
    """

    def __init__(
        self,
        cli: VerusCLI,
        session_duration_hours: int = 24,
        challenge_ttl_seconds: int = 300,
    ):
        self.cli = cli
        self.session_duration = timedelta(hours=session_duration_hours)
        self.challenge_ttl = timedelta(seconds=challenge_ttl_seconds)
        self._challenges: Dict[str, LoginChallenge] = {}
        self._sessions: Dict[str, LoginSession] = {}

    # ------------------------------------------------------------------
    # Challenge management
    # ------------------------------------------------------------------

    def create_challenge(
        self,
        signing_identity: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> LoginChallenge:
        """
        Generate a login challenge for a client to sign.

        Parameters
        ----------
        signing_identity : str, optional
            Restrict which VerusID must sign (e.g. ``UserName@``).
        redirect_uri : str, optional
            Where to redirect after successful login.
        """
        now = datetime.now()
        nonce = secrets.token_hex(32)
        challenge_id = hashlib.sha256(nonce.encode()).hexdigest()[:24]
        timestamp = int(time.time())

        message = json.dumps({
            "type": "verusid_login",
            "challenge": nonce,
            "timestamp": timestamp,
            "signer": signing_identity or "*",
        }, separators=(",", ":"))

        challenge = LoginChallenge(
            challenge_id=challenge_id,
            message=message,
            created_at=now,
            expires_at=now + self.challenge_ttl,
            signing_identity=signing_identity,
            redirect_uri=redirect_uri,
            extra_data=extra_data or {},
        )

        self._challenges[challenge_id] = challenge
        self._cleanup_expired_challenges()

        logger.info("Login challenge created: %s (signer=%s)", challenge_id, signing_identity)
        return challenge

    # ------------------------------------------------------------------
    # Login processing
    # ------------------------------------------------------------------

    async def process_login(
        self,
        challenge_id: str,
        identity_name: str,
        signature: str,
    ) -> LoginResult:
        """
        Process a login response (signed challenge).

        Parameters
        ----------
        challenge_id : str
            The challenge ID from ``create_challenge``.
        identity_name : str
            The VerusID that signed the challenge (e.g. ``UserName@``).
        signature : str
            The base64-encoded signature.
        """
        # Validate challenge exists and is not expired
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            return LoginResult(success=False, error="Unknown challenge ID")
        if challenge.is_expired:
            self._challenges.pop(challenge_id, None)
            return LoginResult(success=False, error="Challenge expired")

        # Check signer restriction
        if challenge.signing_identity and challenge.signing_identity != identity_name:
            return LoginResult(
                success=False,
                error=f"Challenge requires signer '{challenge.signing_identity}', got '{identity_name}'",
            )

        # Verify signature on-chain
        try:
            valid = await self.cli.verifymessage(identity_name, signature, challenge.message)
        except VerusError as exc:
            logger.error("Signature verification RPC error: %s", exc)
            return LoginResult(success=False, error=f"Verification failed: {exc}")

        if not valid:
            logger.warning("Invalid signature for '%s' on challenge %s", identity_name, challenge_id)
            return LoginResult(
                success=False,
                error="Invalid signature",
                identity_name=identity_name,
            )

        # Fetch identity details
        try:
            identity_data = await self.cli.getidentity(identity_name)
        except VerusError:
            identity_data = {}

        identity = identity_data.get("identity", {})

        # Check identity is not revoked
        flags = identity.get("flags", 0)
        if flags & 8:  # REVOKED flag
            return LoginResult(
                success=False,
                error="Identity is revoked",
                identity_name=identity_name,
            )

        # Consume challenge (one-time use)
        self._challenges.pop(challenge_id, None)

        # Create session
        now = datetime.now()
        session_id = secrets.token_hex(32)
        session = LoginSession(
            session_id=session_id,
            identity_name=identity_name,
            identity_address=identity.get("identityaddress", ""),
            authenticated_at=now,
            expires_at=now + self.session_duration,
            challenge_id=challenge_id,
            signature=signature,
            metadata={
                "primary_addresses": identity.get("primaryaddresses", []),
                "parent": identity.get("parent", ""),
            },
        )
        self._sessions[session_id] = session

        logger.info("Login successful: %s (session=%s)", identity_name, session_id[:12])
        return LoginResult(success=True, session=session, identity_name=identity_name)

    # ------------------------------------------------------------------
    # Session validation
    # ------------------------------------------------------------------

    def validate_session(self, session_id: str) -> Optional[LoginSession]:
        """
        Validate an active session.

        Returns the session if valid, None if expired or unknown.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        if not session.is_valid:
            self._sessions.pop(session_id, None)
            return None
        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Explicitly end a session (logout)."""
        if session_id in self._sessions:
            self._sessions.pop(session_id)
            logger.info("Session invalidated: %s", session_id[:12])
            return True
        return False

    # ------------------------------------------------------------------
    # UAI Agent authentication
    # ------------------------------------------------------------------

    async def authenticate_agent(
        self,
        agent_identity: str,
        signature: str,
        message: str,
    ) -> LoginResult:
        """
        Authenticate a UAI swarm agent via its VerusID.

        Simplified flow for agent-to-agent auth (no challenge needed,
        just verify the signature on an agreed message).
        """
        try:
            valid = await self.cli.verifymessage(agent_identity, signature, message)
            if not valid:
                return LoginResult(success=False, error="Invalid agent signature")

            # Create agent session
            now = datetime.now()
            session = LoginSession(
                session_id=secrets.token_hex(32),
                identity_name=agent_identity,
                identity_address="",
                authenticated_at=now,
                expires_at=now + self.session_duration,
                challenge_id="agent_auth",
                signature=signature,
                metadata={"auth_type": "agent"},
            )
            self._sessions[session.session_id] = session

            return LoginResult(success=True, session=session, identity_name=agent_identity)

        except VerusError as exc:
            return LoginResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cleanup_expired_challenges(self) -> None:
        """Remove expired challenges."""
        expired = [
            cid for cid, c in self._challenges.items()
            if c.is_expired
        ]
        for cid in expired:
            self._challenges.pop(cid, None)

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        expired = [
            sid for sid, s in self._sessions.items()
            if not s.is_valid
        ]
        for sid in expired:
            self._sessions.pop(sid, None)

    @property
    def active_session_count(self) -> int:
        self._cleanup_expired_sessions()
        return len(self._sessions)
