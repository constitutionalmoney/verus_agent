"""
Mobile Wallet Integration Helpers — VerusPay & Verus Mobile Deep Links

Provides self-contained helper functions for generating VerusPay-compatible
payment URIs, LoginConsentRequest QR data, and marketplace deep links that
work with the Verus Mobile wallet and any wallet implementing VerusPay.

Architecture (from Issue #9 §6 / extends Issue #8):
    - VerusPay URIs follow ``vrsc:`` scheme (BIP-21 style)
    - LoginConsentRequest provides passwordless wallet-based auth
    - Marketplace purchase links embed product + tier + price
    - QR codes = JSON payloads (optionally base64-encoded)

⚠️ IMPORTANT: Offline QR Code Generation & UTXO Library
    This module generates QR **data strings** (JSON payloads). For full
    offline QR code generation and UTXO transaction construction/signing,
    the companion JS/TS layer MUST use the BitGo UTXO library:

        @bitgo/utxo-lib  — https://www.npmjs.com/package/@bitgo/utxo-lib

    Key usage in the QR/mobile flow:
      - ``createUnfundedCurrencyTransfer`` from ``@bitgo/utxo-lib/smarttxs``
      - ``networks.verus`` for Verus-specific network parameters
      - UTXO signing for LoginConsentRequest construction
      - The Python helpers here generate the *data payloads*; the JS/TS
        layer converts them to actual signed QR codes via @bitgo/utxo-lib.

Toggle via config:  ``VERUS_MOBILE_ENABLED=true``

Mobile Wallet UI Routing (from developer discussion):
    The Verus Mobile wallet renders **different UI pages** depending on the
    VDXF key type in the GenericRequest ``details[]`` array:

    | Detail VDXF Key                        | Wallet UI Page        | Status       |
    |:----------------------------------------|:----------------------|:-------------|
    | AUTHENTICATION_REQUEST_VDXF_KEY         | Login / Auth page     | ✅ Supported  |
    | IDENTITY_UPDATE_REQUEST_VDXF_KEY        | ID Update confirm     | ✅ Supported  |
    | VERUSPAY_INVOICE_DETAILS_VDXF_KEY       | Payment / Invoice     | ✅ Supported  |
    | APP_ENCRYPTION_REQUEST_VDXF_KEY         | App Encryption        | ⚠️ Partial   |
    | DATA_PACKET_REQUEST_VDXF_KEY            | Data Packet           | ❓ Unknown   |
    | USER_DATA_REQUEST_VDXF_KEY              | User Data             | ❓ Unknown   |

    There is NO generic catch-all page — each detail type maps to a specific
    wallet page. Login, updateidentity, and invoices all have different UIs.

VDXF Tags (vdxftag) for Payment Tracking:
    Tagged transactions use ``getvdxfid`` + ``indexid`` to create x-addresses
    for tracking payments (e.g., invoice IDs) without separate deposit addresses.

    Example::

        verus getvdxfid "yourns.vrsc::invoiceid" '{"indexid":1002}'
        # → { "indexid": "xTevrzs5W4WyhRiCDnchF4BsdjQEF2dPRH" }

        verus sendcurrency "*" '[{"address":"to@","amount":100,"vdxftag":"xTevrzs5W4WyhRiCDnchF4BsdjQEF2dPRH"}]'

    - No VerusID required to use vdxftags — works with any address
    - Supported in: sendcurrency, currency conversions, VerusPay QR codes
    - Privacy note: tagging LINKS transactions; use separate addresses for privacy
    - Coming soon: vdxftag in next Verus Mobile VerusPay release

References:
    - Issue #9: VerusID as LLM/SLM Container, Security Layer & Monetization Engine
    - Issue #8: Verus Mobile wallet integration
    - VerusPay: https://docs.verus.io/verusid/veruspay/
    - LoginConsentRequest: https://docs.verus.io/verusid/loginconsentrequest/
    - @bitgo/utxo-lib: https://www.npmjs.com/package/@bitgo/utxo-lib (QR generation)
    - Login template: https://github.com/monkins1010/verusid-login-template
    - verusd-rpc-ts-client: https://github.com/VerusCoin/verusd-rpc-ts-client
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

from verus_agent.config import VERUS_MOBILE_WALLET_CAPABILITIES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VDXF / namespace constants
# ---------------------------------------------------------------------------
VDXF_LOGIN_CONSENT = "vrsc::system.identity.loginconsent.request"
VDXF_AGENT_PRODUCT = "vrsc::uai.product.name"

# Verus Mobile deep-link scheme
VRSC_URI_SCHEME = "vrsc"
GENERIC_REQUEST_URI_PREFIX = "verus://1/"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class PaymentNetwork(str, Enum):
    """Verus payment networks."""
    VRSC = "VRSC"
    VRSCTEST = "vrsctest"


@dataclass
class PaymentURI:
    """A VerusPay-compatible payment URI."""
    address: str
    amount: Optional[float] = None
    currency: str = "VRSC"
    label: str = ""
    message: str = ""
    memo: str = ""
    uri: str = ""
    qr_data: str = ""


@dataclass
class LoginConsentData:
    """LoginConsentRequest payload for QR / deep-link auth."""
    challenge_id: str
    agent_identity: str
    redirect_uri: str = ""
    requested_access: List[str] = field(default_factory=list)
    expires_at: int = 0  # Unix timestamp
    payload: Dict[str, Any] = field(default_factory=dict)
    qr_data: str = ""


@dataclass
class MobileLinkResult:
    """Result of a mobile link generation operation."""
    operation: str
    success: bool
    uri: str = ""
    qr_data: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


# ---------------------------------------------------------------------------
# VerusMobileHelper — stateless helper class
# ---------------------------------------------------------------------------

class VerusMobileHelper:
    """
    Generates VerusPay URIs, LoginConsentRequest payloads, and deep links.

    This is a stateless helper — it does not require CLI or daemon access.
    All methods are synchronous and produce URI/QR strings that can be
    rendered or transmitted to mobile wallets.

    Parameters
    ----------
    network : PaymentNetwork
        Target network (VRSC mainnet or vrsctest).
    agent_identity : str
        The agent's VerusID (used as recipient in payment URIs).
    """

    def __init__(
        self,
        network: PaymentNetwork = PaymentNetwork.VRSC,
        agent_identity: str = "",
    ):
        self.network = network
        self.agent_identity = agent_identity
        self.enabled = os.getenv(
            "VERUS_MOBILE_ENABLED", ""
        ).lower() in ("true", "1", "yes")

    # ------------------------------------------------------------------
    # VerusPay URI Generation
    # ------------------------------------------------------------------

    def generate_payment_uri(
        self,
        destination: str = "",
        amount: Optional[float] = None,
        currency: str = "VRSC",
        label: str = "",
        message: str = "",
        memo: str = "",
    ) -> PaymentURI:
        """
        Generate a VerusPay-compatible payment URI.

        Follows the ``vrsc:`` URI scheme (BIP-21 style):
            ``vrsc:<address>?amount=<n>&currency=<c>&label=<l>&message=<m>``

        VerusIDs are valid as destinations (e.g., ``MyAgent@``).

        Parameters
        ----------
        destination : str
            Receiving address or VerusID. Defaults to ``self.agent_identity``.
        amount : float, optional
            Payment amount in the specified currency.
        currency : str
            Currency code (default "VRSC").
        label : str
            Short description shown in wallet.
        message : str
            Longer freeform message for the recipient.
        memo : str
            On-chain memo / OP_RETURN data.
        """
        dest = destination or self.agent_identity
        if not dest:
            return PaymentURI(address="", uri="", qr_data="")

        params: Dict[str, str] = {}
        if amount is not None:
            params["amount"] = f"{amount:.8f}"
        if currency and currency != "VRSC":
            params["currency"] = currency
        if label:
            params["label"] = label
        if message:
            params["message"] = message
        if memo:
            params["memo"] = memo

        uri = f"{VRSC_URI_SCHEME}:{quote(dest)}"
        if params:
            uri += "?" + urlencode(params)

        result = PaymentURI(
            address=dest,
            amount=amount,
            currency=currency,
            label=label,
            message=message,
            memo=memo,
            uri=uri,
            qr_data=uri,
        )

        logger.debug("Generated VerusPay URI: %s", uri)
        return result

    # ------------------------------------------------------------------
    # LoginConsentRequest (Passwordless Wallet Auth)
    # ------------------------------------------------------------------

    def generate_login_consent(
        self,
        agent_identity: str = "",
        redirect_uri: str = "",
        requested_access: Optional[List[str]] = None,
        expires_seconds: int = 300,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> LoginConsentData:
        """
        Generate a VerusID LoginConsentRequest for mobile wallet auth.

        Creates a challenge that the wallet signs with the user's VerusID
        private key, proving identity without passwords.

        The resulting QR data can be displayed to the user; scanning with
        Verus Mobile produces a signed response proving VerusID ownership.

        Parameters
        ----------
        agent_identity : str
            The agent/service VerusID requesting login. Falls back to
            ``self.agent_identity``.
        redirect_uri : str
            Callback URI after wallet signs the consent.
        requested_access : list[str]
            Optional list of access scopes (e.g., ``["identity.read"]``).
        expires_seconds : int
            How long the challenge is valid (default 5 minutes).
        custom_fields : dict
            Additional fields to include in the consent payload.
        """
        agent = agent_identity or self.agent_identity
        challenge_id = secrets.token_hex(16)
        now = int(time.time())

        payload: Dict[str, Any] = {
            "system_id": self.network.value,
            "signing_id": agent,
            "challenge": {
                "challenge_id": challenge_id,
                "created_at": now,
                "expires": now + expires_seconds,
                "requested_access": requested_access or [],
            },
        }

        if redirect_uri:
            payload["redirect_uris"] = [redirect_uri]

        if custom_fields:
            payload["custom"] = custom_fields

        # VDXF-wrapped payload
        vdxf_payload = {
            VDXF_LOGIN_CONSENT: payload,
        }

        qr_data = json.dumps(vdxf_payload, separators=(",", ":"))

        result = LoginConsentData(
            challenge_id=challenge_id,
            agent_identity=agent,
            redirect_uri=redirect_uri,
            requested_access=requested_access or [],
            expires_at=now + expires_seconds,
            payload=vdxf_payload,
            qr_data=qr_data,
        )

        logger.debug(
            "Generated LoginConsentRequest: challenge=%s, agent=%s",
            challenge_id, agent,
        )
        return result

    # ------------------------------------------------------------------
    # Marketplace Purchase Deep Links
    # ------------------------------------------------------------------

    def generate_purchase_link(
        self,
        product_identity: str,
        tier: str = "basic",
        price: Optional[float] = None,
        currency: str = "VRSC",
        buyer_memo: str = "",
    ) -> MobileLinkResult:
        """
        Generate a deep link for purchasing a marketplace product.

        Encodes product identity, tier, and price into a VerusPay URI
        with structured memo data, allowing one-tap purchase from a
        Verus Mobile wallet.

        Parameters
        ----------
        product_identity : str
            The product's VerusID (e.g., ``UAICodeHelper@``).
        tier : str
            License tier (basic / professional / enterprise).
        price : float, optional
            Price in the specified currency.
        currency : str
            Payment currency (default "VRSC").
        buyer_memo : str
            Additional memo from the buyer.
        """
        if not product_identity:
            return MobileLinkResult(
                operation="purchase_link",
                success=False,
                error="product_identity is required",
            )

        # Structured memo embedding product + tier info
        memo_payload = json.dumps({
            "uai_purchase": True,
            "product": product_identity,
            "tier": tier,
            "ts": int(time.time()),
            "buyer_memo": buyer_memo,
        }, separators=(",", ":"))

        payment = self.generate_payment_uri(
            destination=product_identity,
            amount=price,
            currency=currency,
            label=f"UAI Agent: {product_identity}",
            message=f"License purchase — tier: {tier}",
            memo=memo_payload,
        )

        return MobileLinkResult(
            operation="purchase_link",
            success=True,
            uri=payment.uri,
            qr_data=payment.qr_data,
            data={
                "product_identity": product_identity,
                "tier": tier,
                "price": price,
                "currency": currency,
                "memo_payload": memo_payload,
            },
        )

    # ------------------------------------------------------------------
    # License Activation Deep Links
    # ------------------------------------------------------------------

    def generate_license_activation_link(
        self,
        license_identity: str,
        activation_code: str = "",
    ) -> MobileLinkResult:
        """
        Generate a deep link for activating a purchased license.

        After a buyer purchases a license SubID, this link lets the
        mobile wallet claim/activate it.

        Parameters
        ----------
        license_identity : str
            The license SubID (e.g., ``buyer123.UAICodeHelper@``).
        activation_code : str
            Optional one-time activation code. Auto-generated if empty.
        """
        if not license_identity:
            return MobileLinkResult(
                operation="license_activation",
                success=False,
                error="license_identity is required",
            )

        code = activation_code or secrets.token_hex(8)
        payload = {
            "uai_activate": True,
            "license": license_identity,
            "code": code,
            "ts": int(time.time()),
        }

        qr_data = json.dumps(payload, separators=(",", ":"))
        uri = f"{VRSC_URI_SCHEME}:activate?license={quote(license_identity)}&code={code}"

        return MobileLinkResult(
            operation="license_activation",
            success=True,
            uri=uri,
            qr_data=qr_data,
            data={
                "license_identity": license_identity,
                "activation_code": code,
            },
        )

    # ------------------------------------------------------------------
    # Model Access Token Generation
    # ------------------------------------------------------------------

    def generate_model_access_qr(
        self,
        model_identity: str,
        buyer_identity: str,
        access_token: str = "",
        endpoint: str = "",
    ) -> MobileLinkResult:
        """
        Generate a QR payload for model download/access.

        After purchasing and decrypting a model, the buyer's mobile
        wallet can scan this QR to configure their inference endpoint.

        Parameters
        ----------
        model_identity : str
            The model's VerusID.
        buyer_identity : str
            The buyer's VerusID (must match a valid license).
        access_token : str
            Bearer token for API access. Auto-generated if empty.
        endpoint : str
            Inference or download endpoint URL.
        """
        token = access_token or secrets.token_urlsafe(32)

        payload = {
            "uai_model_access": True,
            "model": model_identity,
            "buyer": buyer_identity,
            "token": token,
            "endpoint": endpoint,
            "ts": int(time.time()),
        }

        qr_data = json.dumps(payload, separators=(",", ":"))

        return MobileLinkResult(
            operation="model_access",
            success=True,
            uri=endpoint or "",
            qr_data=qr_data,
            data={
                "model_identity": model_identity,
                "buyer_identity": buyer_identity,
                "access_token": token,
                "endpoint": endpoint,
            },
        )

    # ------------------------------------------------------------------
    # Utility — Batch QR Payload
    # ------------------------------------------------------------------

    def generate_generic_request_link(
        self,
        compact_payload: str,
        detail_types: Optional[List[str]] = None,
        requires_experimental: bool = False,
        legacy_fallback_uri: str = "",
    ) -> MobileLinkResult:
        """
        Generate a compact GenericRequest deeplink.

        Format:
            verus://1/<compact payload>
        """
        payload = (compact_payload or "").strip()
        if not payload:
            return MobileLinkResult(
                operation="generic_request_link",
                success=False,
                error="compact_payload is required",
            )

        uri = f"{GENERIC_REQUEST_URI_PREFIX}{payload}"
        data = {
            "format": "GenericRequest",
            "uri_prefix": GENERIC_REQUEST_URI_PREFIX,
            "detail_types": detail_types or [],
            "requires_experimental_deeplinks": bool(requires_experimental),
            "legacy_formats_still_supported": True,
        }
        if legacy_fallback_uri:
            data["legacy_fallback_uri"] = legacy_fallback_uri

        return MobileLinkResult(
            operation="generic_request_link",
            success=True,
            uri=uri,
            qr_data=uri,
            data=data,
        )

    def generate_identity_update_request_link(
        self,
        compact_payload: str,
        legacy_fallback_uri: str = "",
    ) -> MobileLinkResult:
        """Generate a GenericRequest deeplink for IdentityUpdateRequest."""
        result = self.generate_generic_request_link(
            compact_payload=compact_payload,
            detail_types=["IdentityUpdateRequest"],
            requires_experimental=True,
            legacy_fallback_uri=legacy_fallback_uri,
        )
        if result.success:
            result.operation = "identity_update_request_link"
            result.data["requires_z_seed_for_credential_encryption"] = True
            result.data["credential_key"] = "vrsc::identity.credential"
        return result

    def generate_app_encryption_request_link(
        self,
        compact_payload: str,
        requests_secret_key_material: bool = False,
        legacy_fallback_uri: str = "",
    ) -> MobileLinkResult:
        """Generate a GenericRequest deeplink for AppEncryptionRequest."""
        result = self.generate_generic_request_link(
            compact_payload=compact_payload,
            detail_types=["AppEncryptionRequest"],
            requires_experimental=True,
            legacy_fallback_uri=legacy_fallback_uri,
        )
        if result.success:
            result.operation = "app_encryption_request_link"
            result.data["requires_z_seed"] = True
            result.data["requests_secret_key_material"] = bool(requests_secret_key_material)
            result.data["can_encrypt_response_descriptor"] = True
        return result

    def get_mobile_capabilities(self) -> Dict[str, Any]:
        """
        Return a capability snapshot for Verus Mobile integration guidance.

        This is intended for agent responses when deciding whether mobile can
        execute a workflow that might otherwise be desktop-only.
        """
        snapshot = json.loads(json.dumps(VERUS_MOBILE_WALLET_CAPABILITIES))
        snapshot["runtime"] = {
            "network": self.network.value,
            "helper_enabled": self.enabled,
            "agent_identity": self.agent_identity,
        }
        return snapshot

    def encode_qr_base64(self, data: str) -> str:
        """Base64-encode a QR payload (for compact transmission)."""
        return base64.urlsafe_b64encode(data.encode()).decode()

    def decode_qr_base64(self, encoded: str) -> str:
        """Decode a base64-encoded QR payload."""
        return base64.urlsafe_b64decode(encoded.encode()).decode()
