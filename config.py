"""
Verus Agent Configuration & Constants

Centralizes all configuration for the Verus Blockchain Specialist Agent
including API endpoints, CLI paths, default parameters, and VDXF keys.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
import os


class VerusNetwork(str, Enum):
    """Verus network environments."""
    MAINNET = "mainnet"
    TESTNET = "testnet"


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
API_ENDPOINTS = {
    VerusNetwork.MAINNET: "https://api.verus.services",
    VerusNetwork.TESTNET: "https://api.verustest.net",
}

# ---------------------------------------------------------------------------
# Well-Known Currency IDs
# ---------------------------------------------------------------------------
CURRENCY_IDS = {
    "VRSC": "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV",
    "tBTC.vETH": "iS8TfRPfVpKo5FVfSUzfHBQxo9KuzpnqLU",
    "Bridge.vETH": "i4Xr5TAMrDTidtGnBqVfZmv4dp2CSTe1HY",
    "vETH": "i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X",
    "DAI.vETH": "iGBs4DWztRNvNEJBt4mqHszLxfKTNHTkhU",
    "MKR.vETH": "iCkKJuJScy4Z6NSDK7Mt42ZAB2NEnAE1o4",
}

# ---------------------------------------------------------------------------
# Ethereum Bridge Contract Addresses (updated March 2026)
# WARNING: Previous addresses (0x1Af5b8015C64d39Ab44C60EAd8317f9F5a9B6C4C
#          and 0x0200EbbD26467B866120D84A0d37c82CdE0acAEB) are DEPRECATED.
#          Using old addresses will send funds to deprecated/defunct contracts.
# ---------------------------------------------------------------------------
ETH_BRIDGE_CONTRACTS = {
    "delegator": "0xBc2738BA63882891094C99E59a02141Ca1A1C36a",
    "verus_bridge": "0xE6052Dcc60573561ECef2D9A4C0FEA6d3aC5B9A2",
}

# ---------------------------------------------------------------------------
# Protocol Facts (from Verus Facts and Statistics — Wiki Update March 2026)
# ---------------------------------------------------------------------------
PROTOCOL_FACTS = {
    "block_time_seconds": 60,           # ~60s (not ~62s as previously documented)
    "blocks_per_day": 1440,             # 60s × 1440 = 86400s = 24h
    "mining_algorithm": "VerusHash 2.2",  # NOT 2.0 — version 2.2 is deployed
    "consensus": "Verus Proof of Power (50% PoW / 50% PoS)",
    "max_supply": 83_540_184,           # VRSC
    "block_reward": 24,                 # VRSC per block (as of block ~3.9M)
    "halving_interval": "~2 years",
    "transaction_fee": 0.0001,          # VRSC
    "launch_date": "2018-05-21",
    "launch_type": "Fair launch — no ICO, no premine, no dev tax",
    "license": "MIT",
    "cli_commands": 201,                # across 14 categories
    "root_id_cost_vrsc": 100,           # ~80 with referral
    "subid_min_cost_vrsc": 0.01,
    "conversion_fee": 0.00025,          # 0.025% basket↔reserve
    "pbaas_launch_cost_vrsc": 10_000,
}

# ---------------------------------------------------------------------------
# getinfo Response Fields (13 newly documented — Wiki Update March 2026)
# These fields are returned by the ``getinfo`` RPC call but were previously
# undocumented.  Useful for node diagnostics and chain introspection.
# ---------------------------------------------------------------------------
GETINFO_EXTRA_FIELDS = {
    "tiptime": "Timestamp of the chain tip (epoch seconds)",
    "nextblocktime": "Expected next block timestamp",
    "CCid": "Consensus branch ID",
    "p2pport": "P2P network port",
    "rpcport": "RPC server port",
    "magic": "Network magic bytes (hex string)",
    "premine": "Premine amount",
    "eras": "Number of reward eras",
    "reward": "Current block reward (satoshis)",
    "halving": "Halving interval (blocks)",
    "decay": "Decay parameter",
    "endsubsidy": "Block height where subsidy ends",
    "veruspos": "VerusPoS configuration value",
}

# ---------------------------------------------------------------------------
# definecurrency — PBaaS Notary Parameters (Wiki Update March 2026)
# ---------------------------------------------------------------------------
DEFINECURRENCY_PBAAS_PARAMS = {
    "notaries": "Array of notary identity names for PBaaS chain validation (e.g. [\"notary1@\", \"notary2@\"])",
    "minnotariesconfirm": "Minimum unique notary signatures required for confirmation (integer)",
}

# ---------------------------------------------------------------------------
# Webhook vs Redirect VDXF Key for Login (verus-connect analysis, March 2026)
# ---------------------------------------------------------------------------
# CRITICAL: When constructing a VerusID login challenge ``redirect_uri``,
# the VDXF key determines HOW the wallet sends back the signed response.
#
#   LOGIN_CONSENT_WEBHOOK_VDXF_KEY  → wallet POSTs response to server (server-to-server)
#   LOGIN_CONSENT_REDIRECT_VDXF_KEY → wallet redirects user's browser to callback URL
#
# USE WEBHOOK for all new code. The Redirect key only works with Verus Mobile;
# the Verus Web Wallet extension rejects challenges with the Redirect key,
# returning "No webhook URI found in challenge."  verus-connect uses Webhook
# automatically.
LOGIN_VDXF_KEY_USAGE = {
    "webhook": {
        "key": "LOGIN_CONSENT_WEBHOOK_VDXF_KEY",
        "i_address": "i61GGEtjHTjFKJkz5ykLNATUBsjVi8XVvN",
        "behavior": "Wallet POSTs signed response directly to server (works with ALL wallets)",
    },
    "redirect": {
        "key": "LOGIN_CONSENT_REDIRECT_VDXF_KEY",
        "i_address": "i4VoSEihPNEGbqW8tcrmDs5BF5oLPFRCNp",
        "behavior": "Wallet redirects user's browser (Verus Mobile ONLY — fails on web extension)",
    },
}

# ---------------------------------------------------------------------------
# Verus Web Wallet Extension Provider API (window.verus)
# ---------------------------------------------------------------------------
# The Verus Web Wallet browser extension injects ``window.verus`` and
# dispatches a ``verus#initialized`` event when ready.  This provider
# allows direct login and send operations without QR codes.
#
# Provider interface (TypeScript source from verus-connect):
#   window.verus.isVerusWallet  → true
#   window.verus.version        → string
#   window.verus.requestLogin(uri: string)        → wallet opens approval popup
#   window.verus.sendDeeplink(uri: string)         → wallet processes deep link
#   window.verus.sendTransaction({ to, amount, currency? }) → { txid: string }
#
# Detection: check ``window.verus?.isVerusWallet`` or listen for
#            ``verus#initialized`` event (give ~500ms for injection).
WEB_WALLET_EXTENSION_PROVIDER = {
    "global_var": "window.verus",
    "ready_event": "verus#initialized",
    "methods": ["requestLogin", "sendDeeplink", "sendTransaction"],
    "detection_timeout_ms": 500,
}

# ---------------------------------------------------------------------------
# Deep Link Schemes (from verus-connect deeplink.ts)
# ---------------------------------------------------------------------------
# Only these URI schemes are safe for deep links.  Reject javascript:, data:, etc.
DEEP_LINK_SCHEMES = ["verus:", "vrsc:", "i5jtwbp6zymeay9llnraglgjqgdrffsau4:"]
VERUSPAY_DEEP_LINK_SCHEME = "i5jtwbp6zymeay9llnraglgjqgdrffsau4"

# ---------------------------------------------------------------------------
# Wallet Environment Detection (from verus-connect detect.ts)
# ---------------------------------------------------------------------------
# The verus-connect frontend SDK auto-detects how to present login:
#   extension → window.verus provider present → send challenge directly
#   mobile    → user-agent is mobile browser  → deep link (verus://)
#   desktop   → neither of the above          → QR code for Verus Mobile to scan
WALLET_ENVIRONMENTS = ["extension", "mobile", "desktop"]

# ---------------------------------------------------------------------------
# verus-connect Library Reference
# ---------------------------------------------------------------------------
# Drop-in VerusID login for websites.  Server middleware + frontend SDK.
# Repo: https://github.com/Fried333/verus-connect
# Install: npm install verus-connect express
#          npm install git+https://github.com/VerusCoin/verusid-ts-client.git
VERUS_CONNECT_LIBRARY = {
    "repo": "https://github.com/Fried333/verus-connect",
    "npm_package": "verus-connect",
    "version": "0.1.0",
    "server_import": "verus-connect/server",
    "client_import": "verus-connect",
    "peer_deps": ["express>=4.0.0", "verusid-ts-client (GitHub)"],
    "server_routes": [
        "POST /login            — Create signed login challenge",
        "POST /verusidlogin     — Receives signed response from wallet",
        "GET  /result/:id       — Frontend polls for result",
        "POST /pay-deeplink     — Generate VerusPay invoice deep link",
        "GET  /health           — Health check",
    ],
}

# ---------------------------------------------------------------------------
# Memo Limitation (Wiki Update March 2026)
# ---------------------------------------------------------------------------
# IMPORTANT: ``memo`` field in sendcurrency outputs ONLY works when sending
# to z-addresses (shielded addresses starting with ``zs...``).
# Transparent addresses (``R...``) silently ignore the memo field.
MEMO_REQUIRES_Z_ADDRESS = True

# ---------------------------------------------------------------------------
# Minimum daemon version (v1.2.14-2 mandatory upgrade — Jan 7, 2026)
# ---------------------------------------------------------------------------
MIN_DAEMON_VERSION = 1021400  # 1.2.14 → encoded as int (revision handled separately)
MIN_DAEMON_VERSION_STR = "1.2.14-2"

# ---------------------------------------------------------------------------
# Agent identity
# ---------------------------------------------------------------------------
AGENT_ID = "verus_blockchain_agent"
AGENT_ROLE = "SPECIALIST"
AGENT_DOMAIN = "blockchain_verus"
AGENT_CATEGORY = "neural_swarm_intelligence"

# ---------------------------------------------------------------------------
# Exposed capabilities (matches the spec in verus-blockchain-agent.md)
# ---------------------------------------------------------------------------
AGENT_CAPABILITIES = [
    "verus.identity.create",
    "verus.identity.update",
    "verus.identity.vault",
    "verus.currency.launch",
    "verus.currency.convert",
    "verus.currency.send",
    "verus.currency.estimate",
    "verus.storage.store",
    "verus.storage.retrieve",
    "verus.storage.store_data_wrapper",   # Method 1: updateidentity + data (auto-chunk, encrypt)
    "verus.storage.store_sendcurrency",   # Method 2: sendcurrency to z-address (shielded)
    "verus.storage.retrieve_data_wrapper",# Retrieve + decrypt Method 1 data
    "verus.login.authenticate",
    "verus.login.validate",
    "verus.bridge.cross",
    "verus.market.monitor",
    "verus.cli.execute",
    # Encrypted messaging (z-address based)
    "verus.messaging.send_encrypted",
    "verus.messaging.receive_decrypt",
    # Mining & staking
    "verus.mining.start",
    "verus.mining.info",
    "verus.staking.status",
    # Trust & reputation (setidentitytrust / setcurrencytrust)
    "verus.trust.set_identity_trust",
    "verus.trust.set_currency_trust",
    "verus.trust.get_ratings",
    # Marketplace atomic swaps (makeoffer/takeoffer)
    "verus.marketplace.make_offer",
    "verus.marketplace.take_offer",
    "verus.marketplace.list_open_offers",
    "verus.marketplace.close_offers",
    # Extension capabilities (registered only when enabled)
    "verus.security.register",
    "verus.security.verify",
    "verus.security.revoke",
    "verus.security.status",
    "verus.marketplace.register_product",
    "verus.marketplace.issue_license",
    "verus.marketplace.verify_license",
    "verus.marketplace.list_offers",
    "verus.ip.register_model",
    "verus.ip.verify_integrity",
    "verus.ip.get_model_info",
    "verus.ip.register_storage",
    # Phase 4 capabilities
    "verus.ip.encrypt_model",
    "verus.ip.decrypt_model",
    "verus.ip.full_protect",
    "verus.marketplace.create_invoice",
    "verus.marketplace.discover",
    "verus.marketplace.search",
    "verus.reputation.attest",
    "verus.reputation.query",
    "verus.reputation.leaderboard",
    "verus.reputation.verify",
    "verus.defi.create_revenue_basket",
    "verus.defi.distribute_revenue",
    # Phase 4b capabilities (PBaaS, cross-chain, watermark, mobile)
    "verus.defi.define_pbaas_chain",
    "verus.marketplace.verify_license_cross_chain",
    "verus.ip.generate_watermark",
    "verus.ip.verify_watermark",
    "verus.mobile.payment_uri",
    "verus.mobile.login_consent",
    "verus.mobile.purchase_link",
]

# ---------------------------------------------------------------------------
# VDXF Namespace Keys (common prefixes)
# ---------------------------------------------------------------------------
VDXF_NAMESPACE = {
    "uai_agent": "vrsc::uai.agent",
    "uai_license": "vrsc::uai.license",
    "uai_license_expiry": "vrsc::uai.license.expiry",
    "uai_model_hash": "vrsc::uai.model.hash",
    "uai_model_metadata": "vrsc::uai.model.metadata",
    "uai_agent_config": "vrsc::uai.agent.config",
    # Swarm Security VDXF keys
    "agent_role": "vrsc::uai.agent.role",
    "agent_permissions": "vrsc::uai.agent.permissions",
    "agent_version": "vrsc::uai.agent.version",
    "agent_model_hash": "vrsc::uai.agent.modelhash",
    "agent_config_enc": "vrsc::uai.agent.config.encrypted",
    "agent_endpoint": "vrsc::uai.agent.endpoint",
    "agent_health": "vrsc::uai.agent.health",
    "swarm_membership": "vrsc::uai.swarm.membership",
    # Marketplace VDXF keys
    "product_name": "vrsc::uai.product.name",
    "product_desc": "vrsc::uai.product.desc",
    "product_tier": "vrsc::uai.product.tier",
    "product_price": "vrsc::uai.product.price.vrsc",
    "product_capabilities": "vrsc::uai.product.capabilities",
    "license_owner": "vrsc::uai.license.owner",
    "license_tier": "vrsc::uai.license.tier",
    "license_rate_limit": "vrsc::uai.license.ratelimit",
    # IP Protection VDXF keys
    "model_name": "vrsc::uai.model.name",
    "model_version": "vrsc::uai.model.version",
    "model_arch": "vrsc::uai.model.arch",
    "model_license": "vrsc::uai.model.license",
    "model_owner": "vrsc::uai.model.owner",
    "model_sig": "vrsc::uai.model.sig",
    "model_size": "vrsc::uai.model.size",
    "model_quantization": "vrsc::uai.model.quantization",
    "storage_primary": "vrsc::uai.model.storage.primary",
    "storage_backup": "vrsc::uai.model.storage.backup",
    "storage_key_enc": "vrsc::uai.model.storage.key.encrypted",
    "watermark_buyer": "vrsc::uai.model.watermark.buyer",
    "watermark_hash": "vrsc::uai.model.watermark.hash",
    # Reputation / Attestation VDXF keys
    "attest_attestor": "vrsc::uai.agent.attestation.attestor",
    "attest_rating": "vrsc::uai.agent.attestation.rating",
    "attest_category": "vrsc::uai.agent.attestation.category",
    "attest_comment": "vrsc::uai.agent.attestation.comment",
    "attest_timestamp": "vrsc::uai.agent.attestation.timestamp",
    "attest_signature": "vrsc::uai.agent.attestation.signature",
    "reputation_score": "vrsc::uai.agent.reputation.score",
    "reputation_count": "vrsc::uai.agent.reputation.count",
    # --- NEW: Agent Profile Schema (from Verus Agent Wiki) ---
    # ari::agent.v1.* namespace (testnet)
    "ari_agent_version": "ari::agent.v1.version",       # i6HXzMMD3TTDDPvGB5UbHZVKxk8UhnKiE3
    "ari_agent_type": "ari::agent.v1.type",              # iB5K4HoKTBzJErGscJaQkWrdg6c3tMsU6R
    "ari_agent_name": "ari::agent.v1.name",              # iDdkfGg9wCLk6im1BrKTwh9rhSiUEcrE9d
    "ari_agent_description": "ari::agent.v1.description", # iKdG3eo2DLm19NJWDHiem2WobtYzbmqW6U
    "ari_agent_capabilities": "ari::agent.v1.capabilities", # iRu8CaKpMEkqYiednh7Ff1BT32TNgDXasZ
    "ari_agent_endpoints": "ari::agent.v1.endpoints",    # i9kWQsJkfSATuWdSJs9QG6SA9MfbhbpPKt
    "ari_agent_protocols": "ari::agent.v1.protocols",    # i8BMBVcsX9GDm3yrRNaMeTe1TQ2m1ng1qC
    "ari_agent_owner": "ari::agent.v1.owner",            # iC6oQAC5rufBtks35ctW1YtugXc9QyxF2a
    "ari_agent_status": "ari::agent.v1.status",          # iCwKbumFMBTmBFFQAGzsH4Nz2xpT2yvsyf
    "ari_agent_services": "ari::agent.v1.services",      # iPpTtEbDj79FMMScKyfjSyhjJbSyaeXLHe
    # agentplatform::agent.v1.* namespace
    "ap_agent_version": "agentplatform::agent.v1.version",    # iBShCc1dESnTq25WkxzrKGjHvHwZFSoq6b
    "ap_agent_type": "agentplatform::agent.v1.type",          # i9YN6ovGcotCnFdNyUtNh72Nw11WcBuD8y
    "ap_agent_name": "agentplatform::agent.v1.name",          # i3oa8uNjgZjmC1RS8rg1od8czBP8bsh5A8
    "ap_agent_description": "agentplatform::agent.v1.description", # i9Ww2jR4sFt7nzdc5vRy5MHUCjTWULXCqH
    "ap_agent_status": "agentplatform::agent.v1.status",      # iNCvffXEYWNBt1K5izxKFSFKBR5LPAAfxW
    "ap_agent_capabilities": "agentplatform::agent.v1.capabilities", # i7Aumh6Akeq7SC8VJBzpmJrqKNCvREAWMA
    "ap_agent_protocols": "agentplatform::agent.v1.protocols", # iFQzXU4V6am1M9q6LGBfR4uyNAtjhJiW2d
    "ap_agent_owner": "agentplatform::agent.v1.owner",        # i5uUotnF2LzPci3mkz9QaozBtFjeFtAw45
    "ap_agent_services": "agentplatform::agent.v1.services",  # iGVUNBQSNeGzdwjA4km5z6R9h7T2jao9Lz
    # agentplatform::svc.v1.* namespace (service schema)
    "ap_svc_name": "agentplatform::svc.v1.name",             # iNTrSV1bqDAoaGRcpR51BeoS5wQvQ4P9Qj
    "ap_svc_description": "agentplatform::svc.v1.description", # i7ZUWAqwLu9b4E8oXZq4uX6X5W6BJnkuHz
    "ap_svc_price": "agentplatform::svc.v1.price",           # iLjLxTk1bkEd7SAAWT27VQ7ECFuLtTnuKv
    "ap_svc_currency": "agentplatform::svc.v1.currency",     # iANfkUFM797eunQt4nFV3j7SvK8pUkfsJe
    "ap_svc_category": "agentplatform::svc.v1.category",     # iGiUqVQcdLC3UAj8mHtSyWNsAKdEVXUFVC
    "ap_svc_turnaround": "agentplatform::svc.v1.turnaround", # iNGq3xh28oV2U3VmMtQ3gjMX8jrH1ohKfp
    "ap_svc_status": "agentplatform::svc.v1.status",         # iNbPugdyVSCv54zsZs68vAfvifcf14btX2
    # --- NEW: Storage VDXF keys (from On-Chain File Storage Wiki) ---
    "storage_hash": "vrsc::uai.storage.hash",
    "storage_meta": "vrsc::uai.storage.meta",
    "storage_chunk": "vrsc::uai.storage.chunk",
    "storage_manifest": "vrsc::uai.storage.manifest",
    # --- NEW: Messaging VDXF keys ---
    "msg_type": "vrsc::uai.messaging.type",
    "msg_from": "vrsc::uai.messaging.from",
    "msg_to": "vrsc::uai.messaging.to",
    "msg_body": "vrsc::uai.messaging.body",
    "msg_timestamp": "vrsc::uai.messaging.timestamp",
    # --- System VDXF keys (from VDXF Data Pipeline Wiki) ---
    "vdxf_type_string": "vrsc::data.type.string",               # iK7a5JNJnbeuYWVHCDRpJosj3irGJ5Qa8c
    "vdxf_type_datadescriptor": "vrsc::data.type.object.datadescriptor",  # i4GC1YGEVD21afWudGoFJVdnfjJ5XWnCQv
    "vdxf_mmrdescriptor": "vrsc::data.mmrdescriptor",           # i9dVDb4LgfMYrZD1JBNP2uaso4bNAkT4Jr
    "vdxf_signaturedata": "vrsc::data.signaturedata",           # i7PcVF9wwPtQ6p6jDtCVpohX65pTZuP2ah
    "vdxf_multimap_key": "vrsc::identity.multimapkey",          # i3mbggp3NBR77C5JeFQJTpAxmgMidayLLE
    "vdxf_multimap_remove": "vrsc::identity.multimapremove",    # i5Zkx5Z7tEfh42xtKfwbJ5LgEWE9rEgpFY
    "vdxf_type_url": "vrsc::data.type.url",                    # iJ3WDnpueJTqSCMN8dUWmfPuKbjFhZqQdM
    "vdxf_profile_media": "vrsc::identity.profile.media",       # iF4oGJU53g4ZpeSJ4CxV6EFjPBPgBCznzR
    "vdxf_definedkey": "vrsc::data.type.object.definedkey",     # iD3yzD6KnrSG75d8RzirMD6SyvrAS2HxjH
    # =========================================================================
    #  Official VDXF Keys from verus-typescript-primitives/src/vdxf/keys.ts
    #  These are the canonical keys used by the TypeScript SDK for login,
    #  provisioning, attestation, and session management.
    # =========================================================================
    # --- Generic Envelope (NEW login API) ---
    "GENERIC_ENVELOPE_DEEPLINK":  "iHybTbGDvBQsxGKzBkjCBqS2RmEYQWMqaW",
    "GENERIC_REQUEST_DEEPLINK":   "iML2i1HBEPb5CfMXjpz5A14LGWMQC4pKdp",
    "GENERIC_RESPONSE_DEEPLINK":  "iL5aWfjGFPJEpYgPmSEvLfUzFi8sR41c5E",
    # --- Identity Update ---
    "IDENTITY_UPDATE_REQUEST":    "i9YLAS79BjndxK98qYL6WFiJjXiMbvuHAX",
    "IDENTITY_UPDATE_RESPONSE":   "iU7kDLEyPSTpMK1raQh8sib8hNSCp96JvK",
    # --- Identity Auth Signature ---
    "IDENTITY_AUTH_SIG":          "i6qAAxsGMiasFj84c3GrUCKnAQFbMxRvBx",
    # --- Login Consent Flow (deprecated but still used in legacy) ---
    "LOGIN_CONSENT_REQUEST":      "iKNufnRrJiQXnBMDHbvHBFjBRKMLKSEsvk",
    "LOGIN_CONSENT_RESPONSE":     "iRQZGW36EPMBJhJFhf6fQHTzRCJtni4cYU",
    "LOGIN_CONSENT_CHALLENGE":    "iKJ465xQKaEz3PFYcLEEMqjqPB4kCpNquf",
    "LOGIN_CONSENT_DECISION":     "i5SYcDuXZVWqfeaYZPQYHami6LS36ZWEET",
    "LOGIN_CONSENT_REDIRECT":     "i4VoSEihPNEGbqW8tcrmDs5BF5oLPFRCNp",
    "LOGIN_CONSENT_WEBHOOK":      "i61GGEtjHTjFKJkz5ykLNATUBsjVi8XVvN",
    "LOGIN_CONSENT_CONTEXT":      "i92PaETCi27UVEPcSibkXdaMPANdRaZhAy",
    # --- Provisioning Flow ---
    "IDENTITY_PROVISIONING_REQUEST":    "i8kWr3VKy4EBiYUm1sG5kXmFKcXKHQHqin",
    "IDENTITY_PROVISIONING_RESPONSE":   "iLSa6CZCyKkQFGCi3BxVnnGsHb4q8Mr7bp",
    "IDENTITY_PROVISIONING_CHALLENGE":  "i7Rk6bshMdAhBTtriQFXPCemcwMXydZm5F",
    "IDENTITY_PROVISIONING_DECISION":   "iCwEvrTQvTuaY6KUQX7SB3ENkgMeGTu7xi",
    "IDENTITY_PROVISIONING_RESULT":     "iCBqZEPsfBxJRH2jkNuFsNvEvMfJBtiJe6",
    "IDENTITY_PROVISIONING_URL":        "i9YtP87JtRK6ozMFr3djbgEvNwpGq6uS2z",
    # --- Attestation ---
    "ATTESTATION_ID":       "i4T29e1LBcFYw1LBDXCRdGrJJvq9qFNbWr",
    "ATTESTATION_NAME":     "iR22E2v53G6K6R3FWJuq7jB1Y8hFVBwpGv",
    "ATTESTATION_TYPE":     "iCg3VyF3mwELryq59b7ALdWWN4LXxgrKaK",
    "ATTESTATION_WEBHOOK":  "i9PgBFw1kF54VNjTXMHt2evQ7CJGm3W5cD",
    # --- Session Objects ---
    "SESSION_OBJECT_DATA":  "iC2R2amfCULGBav2PuqBQQeKQGmPT1bt7S",
    "SESSION_OBJECT":       "iDuACGp5FkCRsAHPMxvPvnSQ4fGTnBHCR4",
    # --- Identity Data Fields (from identitydatakeys.ts) ---
    "ID_ADDRESS":           "iBjeKhnzjJJx4Qv6KnmceYdNSjCkjLWccX",
    "ID_SYSTEMID":          "i7DUGH2akhNaX2Cig6TYJqRRsDTzrmQ1q5",
    "ID_FULLYQUALIFIEDNAME":"iS3d6CLRSmmHNpcbbrXDozStakWMiY4LUd",
    "ID_PARENT":            "i7ur4rh2RjJGPQ7ZQzJQp22bXm28vrxEGc",
    # --- Permission Scopes (from scopes.ts) ---
    "SCOPE_IDENTITY_VIEW":          "iLUrDR3gfNVicoM5nsT78RDjdqWtUahFXQ",
    "SCOPE_IDENTITY_AGREEMENT":     "iRmBDkNsBPiCmfQDxS5kTFoJmhEH7JqPmb",
    "SCOPE_ATTESTATION_READ_REQ":   "iQXF1LS389JUBm1xPfg7PDqTa1MmJHE9Xz",
    "SCOPE_PROFILE_DATA_READ_REQ":  "iDJUWYmj2FLJbBZboTjpjR7554E1nSYhEi",
    # --- Mobile Wallet Detail Types (from Verus Mobile source) ---
    # These VDXF keys determine which UI page the mobile wallet renders
    # when processing a GenericRequest QR code / deep link.
    #   AUTH                → login/authentication page
    #   IDENTITY_UPDATE     → identity update confirmation page
    #   VERUSPAY_INVOICE    → payment/invoice page
    #   APP_ENCRYPTION      → app encryption seed page (status: not fully known)
    #   DATA_PACKET         → data packet page (status: not fully known)
    #   USER_DATA           → user data page (status: not fully known)
    "AUTHENTICATION_REQUEST":       "AUTHENTICATION_REQUEST_VDXF_KEY",
    "VERUSPAY_INVOICE_DETAILS":     "VERUSPAY_INVOICE_DETAILS_VDXF_KEY",
    "APP_ENCRYPTION_REQUEST":       "APP_ENCRYPTION_REQUEST_VDXF_KEY",
    "DATA_PACKET_REQUEST":          "DATA_PACKET_REQUEST_VDXF_KEY",
    "USER_DATA_REQUEST":            "USER_DATA_REQUEST_VDXF_KEY",
}

# ---------------------------------------------------------------------------
# VDXF Tags & x-Addresses — Tagged Transaction Payment Tracking
# ---------------------------------------------------------------------------
# vdxftags allow tagging any sendcurrency transaction (payment, conversion,
# cross-chain) with a VDXF-derived x-address for tracking (e.g., invoice IDs).
# The x-address is the "indexid" from getvdxfid, NOT the vdxfid itself.
#
# Workflow:
#   1. getvdxfid "yournamespace.vrsc::invoiceid" '{"indexid": <invoice_number>}'
#      → returns { vdxfid: "iXXX...", indexid: "xYYY..." }
#   2. sendcurrency from@ '[{"address":"to@","amount":100,"vdxftag":"xYYY..."}]'
#   3. The tagged tx can be identified via getaddressdeltas / getaddressutxos
#
# Key facts:
#   - Does NOT require a VerusID — any address can tag transactions
#   - Supported in: sendcurrency, currency conversions, VerusPay QR codes
#   - The x-address (indexid) is derived from namespace + key + bound data
#   - Privacy note: tagging links transactions; use separate addresses for privacy
#   - Coming soon: vdxftag support in next Verus Mobile VerusPay release
VDXF_TAG_EXAMPLE = {
    "command": 'verus getvdxfid "namespace.vrsc::invoiceid" \'{"indexid":1002}\'',
    "result_key": "indexid",  # use the x-address (indexid), not vdxfid
    "sendcurrency_field": "vdxftag",
}

# ---------------------------------------------------------------------------
# Default operational parameters
# ---------------------------------------------------------------------------
DEFAULT_TRADE_THRESHOLD = 1.0003  # 0.03% profit threshold for arbitrage
DEFAULT_SLEEP_SECONDS = 80        # Polling interval for market monitoring
DEFAULT_HEALTH_INTERVAL = 30      # Seconds between health checks
DEFAULT_API_TIMEOUT = 30          # Seconds for API call timeout

# ---------------------------------------------------------------------------
# Reference Libraries (JS/TS companion layer)
# ---------------------------------------------------------------------------
# The Python agent handles server-side logic; these JS/TS libraries are
# required for the client-side wallet / QR / mobile integration layer.
REFERENCE_LIBRARIES = {
    "bitgo_utxo_lib": {
        "package": "@bitgo/utxo-lib",
        "npm": "https://www.npmjs.com/package/@bitgo/utxo-lib",
        "purpose": "UTXO transaction construction, signing, offline QR code generation for VerusID login",
        "key_imports": [
            "IdentitySignature     — offline sign/verify VerusID signatures",
            "ECPair                — key pair from WIF (ECPair.fromWIF(wif, networks.verus))",
            "networks              — networks.verus for chain parameters",
            "address               — fromBase58Check / toBase58Check",
            "smarttxs              — createUnfundedIdentityUpdate, validateFundedCurrencyTransfer, completeFundedIdentityUpdate, getFundedTxBuilder",
            "Transaction           — SIGHASH_ALL, fromHex, toHex",
        ],
    },
    "verusid_ts_client": {
        "package": "verusid-ts-client",
        "github": "https://github.com/VerusCoin/verusid-ts-client",
        "purpose": "VerusID authentication SDK — signing, verification, login, identity updates",
        "key_class": "VerusIdInterface",
        "constructor": "new VerusIdInterface(chainId, baseURL, axiosConfig?)",
        "methods_new_api": [
            "createGenericRequest(params, wif?, identity?, height?, chainIAddr?)",
            "createGenericResponse(params, wif?, identity?, height?, chainIAddr?)",
            "signGenericRequest(request, wif, identity?, height?)",
            "signGenericResponse(response, wif, identity?, height?)",
            "verifyGenericRequest(request, identity?, chainIAddr?, sigBlockTime?)",
            "verifyGenericResponse(response, identity?, chainIAddr?, sigBlockTime?)",
        ],
        "methods_signatures": [
            "signMessage(iAddrOrIdentity, message, wif, ...)",
            "verifyMessage(iAddrOrIdentity, base64Sig, message, ...)",
            "signHash(iAddrOrIdentity, hash, wif, ...)",
            "verifyHash(iAddrOrIdentity, base64Sig, hash, ...)",
            "getSignatureInfo(iAddrOrIdentity, base64Sig, chainIAddr?)",
        ],
        "methods_identity": [
            "createUpdateIdentityTransaction(identity, changeAddr, rawTx, height, utxos?, ...)",
            "createRevokeIdentityTransaction(identity, changeAddr, rawTx, height, utxos?, ...)",
            "createRecoverIdentityTransaction(identity, changeAddr, rawTx, height, utxos?, ...)",
            "signUpdateIdentityTransaction(hex, inputs, keys)",
        ],
        "methods_deprecated_login": [
            "createLoginConsentRequest   — @deprecated, use GenericRequest",
            "verifyLoginConsentRequest   — @deprecated, use verifyGenericRequest",
            "createLoginConsentResponse  — @deprecated, use GenericResponse",
            "verifyLoginConsentResponse  — @deprecated, use verifyGenericResponse",
        ],
        "methods_verus_pay": [
            "createVerusPayInvoice(details, signingId?, wif?, ...)",
            "signVerusPayInvoice(invoice, signingId, systemId, wif, ...)",
            "verifySignedVerusPayInvoice(invoice, identity?, chainIAddr?)",
        ],
        "methods_provisioning": [
            "signVerusIdProvisioningResponse(response, wif, identity?, height?)",
            "createVerusIdProvisioningResponse(signingId, decision, wif?, ...)",
            "verifyVerusIdProvisioningResponse(response, identity?, chainIAddr?)",
            "static createVerusIdProvisioningRequest(signingAddr, challenge, wif?)",
            "static verifyVerusIdProvisioningRequest(request, address)",
        ],
    },
    "verus_typescript_primitives": {
        "package": "verus-typescript-primitives",
        "github": "https://github.com/AuraSoldique/verus-typescript-primitives",
        "purpose": "Core data types: GenericRequest/Response, VDXF, Identity, PBaaS, Offers",
        "key_classes_new_login": [
            "GenericRequest / GenericResponse — new envelope-based request/response",
            "GenericEnvelope — base class (version, flags, signature, details[])",
            "OrdinalVDXFObject — details item with type + key + data",
            "AuthenticationRequestOrdinalVDXFObject — login auth ordinal",
            "AuthenticationRequestDetails — requestID, recipientConstraints, expiryTime",
            "AuthenticationResponseDetails — flags, requestID",
            "RecipientConstraint — REQUIRED_ID(1), REQUIRED_SYSTEM(2), REQUIRED_PARENT(3)",
            "VerifiableSignatureData — systemID, identityID, signatureAsVch (replaces VerusIDSignature)",
            "ResponseURI — TYPE_POST(1), TYPE_REDIRECT(2)",
            "RequestURI — POST-only URI for response delivery",
        ],
        "key_classes_identity": [
            "Identity — extends Principal; version, parent, system_id, name, content_multimap",
            "PartialIdentity — partial update serialization",
            "IdentityUpdateRequestDetails — client-side identity update with signDataMap",
            "ContentMultiMap — key-value multimap for identity data storage",
        ],
        "key_classes_provisioning": [
            "ProvisionIdentityDetails — systemID, parentID, identityID, uri",
            "ProvisioningChallenge / ProvisioningDecision / ProvisioningRequest / ProvisioningResponse",
        ],
        "key_classes_payment": [
            "VerusPayInvoiceDetails — flags, amount, destination, currency, expiry (V3/V4)",
            "VerusPayInvoice — signed invoice wrapper",
        ],
        "key_classes_encryption": [
            "AppEncryptionRequestDetails — encrypted derived seed from master seed",
            "SaltedData — salted VDXF data wrapper",
        ],
        "key_classes_pbaas": [
            "DataDescriptor — type, label, salt, epk, ivk, ssk, objectdata[]",
            "SignatureData — signed data with MMR proofs",
            "VdxfUniValue — universal VDXF data value",
            "TransferDestination — address + flags for transfers",
        ],
    },
    "verusd_rpc_ts_client": {
        "package": "verusd-rpc-ts-client",
        "version": "0.1.0",
        "github": "https://github.com/VerusCoin/verusd-rpc-ts-client",
        "author": "Michael Filip Toutonghi",
        "purpose": "TypeScript RPC client for verusd daemon communication. "
                   "Used by verusid-ts-client internally for ALL RPC calls. "
                   "VerusID login MUST reference this client for server-side verification.",
        "key_class": "VerusdRpcInterface",
        "constructor": "new VerusdRpcInterface(chain, baseURL, config?, rpcRequestOverride?)",
        "constructor_notes": [
            "chain — chain i-address (VRSC: i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV, VRSCTEST: iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq)",
            "baseURL — RPC endpoint URL (e.g. http://localhost:27486 or https://api.verus.services)",
            "config — optional AxiosRequestConfig (auth: {username, password})",
            "rpcRequestOverride — optional custom transport (bypasses Axios entirely; used in React Native bridges)",
        ],
        "rpc_methods_identity": [
            "getIdentity(nameOrAddress, height?, includeTxid?, includeHistory?) → {identity, status, canspendfor, cansignfor, blockheight, txid, vout}",
            "getIdentityContent(nameOrAddress, fromHeight?, toHeight?) → same as getIdentity return",
            "updateIdentity(identityJSON) → txid string",
        ],
        "rpc_methods_blockchain": [
            "getInfo() → {version, blocks, longestchain, connections, testnet, ...}",
            "getBlock(hashOrHeight, verbosity?) → string | BlockInfo",
            "getBlockCount() → number",
            "getRawTransaction(txid, verbose?) → string | RawTransaction",
        ],
        "rpc_methods_address": [
            "getAddressBalance(addresses) → {balance, received, currencybalance, currencyreceived}",
            "getAddressDeltas(addresses, start?, end?, fromHeight?) → Array<{satoshis, txid, index, ...}>",
            "getAddressMempool(addresses) → Array<{satoshis, txid, ...}>",
            "getAddressUtxos(addresses) → Array<{address, txid, outputIndex, script, satoshis, height, ...}>",
        ],
        "rpc_methods_defi": [
            "getCurrency(name) → CurrencyDefinition",
            "getCurrencyConverters(currencies) → Array<{[key]: CurrencyDefinition}>",
            "listCurrencies(query?) → Array<{currencydefinition, bestheight?, ...}>",
            "estimateConversion(amount, convertTo, via?, preConvert?, sendTo?) → {estimatedcurrencyout, ...}",
            "sendCurrency(fromAddr, outputs) → txid string or {outputtotals, feeamount, hextx}",
        ],
        "rpc_methods_tx": [
            "sendRawTransaction(hex) → txid",
            "fundRawTransaction(hex, changeAddr?) → {hex, changepos, fee}",
            "signRawTransaction(hex) → {hex, complete, errors?}",
        ],
        "rpc_methods_marketplace": [
            "makeOffer(offer) → {txid?, hex?}",
            "getOffers(currencyOrId, isCurrency?, withTx?) → OfferList",
        ],
        "rpc_methods_vdxf_sig": [
            "getVdxfId(vdxfuri) → {vdxfid, hash160result, qualifiedname, bounddata?}",
            "signData(sigParams) → {signature?, signaturedata?, mmrdescriptor?, ...}",
        ],
        "rpc_methods_misc": [
            "zGetOperationStatus(opids?) → z_operation[]",
        ],
        "helper_methods": [
            "getCurrencyConversionPaths(src, dest?, includeVia?, ignoreCurrencies?, via?, root?) → Convertables",
            "  ↳ Complex composite method: pre-caches currencies, discovers all conversion paths recursively",
            "  ↳ Handles gateway, fractional, and PBaaS currency routing with automatic cache cleanup",
            "static extractRpcResult(res) → result or throws Error(res.error.message)",
        ],
        "currency_flags": {
            "IS_TOKEN_FLAG": "0x20 (32)",
            "IS_FRACTIONAL_FLAG": "0x01 (1)",
            "IS_PBAAS_FLAG": "0x100 (256)",
            "IS_GATEWAY_FLAG": "0x80 (128)",
            "IS_GATEWAY_CONVERTER_FLAG": "0x200 (512)",
        },
        "constants": {
            "VERUS_I_ADDRESS": "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV",
            "VERUSTEST_I_ADDRESS": "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq",
        },
        "dependencies": ["axios 1.11.0", "verus-typescript-primitives (git)"],
        "imports_from_primitives": "56+ symbols (26 Request classes, 24 Response types, 2 core types, re-exports all as Primitives)",
        "re_exports": "import * as Primitives from 'verus-typescript-primitives'; export { Primitives }",
    },
}

# ---------------------------------------------------------------------------
# On-Chain Storage Limits (from C++ source analysis)
# ---------------------------------------------------------------------------
STORAGE_LIMITS = {
    "max_script_element_bytes": 6000,       # MAX_SCRIPT_ELEMENT_SIZE_PBAAS
    "max_signdata_input_bytes": 1_000_000,  # signdata hard limit
    "max_block_bytes": 2_000_000,           # MAX_BLOCK_SIZE
    "max_raw_multimap_bytes": 5000,         # Above this: silent truncation
    "recommended_chunk_bytes": 999_000,     # Leaves headroom for metadata
}


@dataclass
class VerusConfig:
    """Runtime configuration for the Verus agent."""

    network: VerusNetwork = VerusNetwork.TESTNET
    api_url: Optional[str] = None
    verus_cli_path: Optional[str] = None
    destination_address: str = ""
    trade_threshold: float = DEFAULT_TRADE_THRESHOLD
    sleep_seconds: int = DEFAULT_SLEEP_SECONDS
    api_timeout: int = DEFAULT_API_TIMEOUT

    # RPC authentication (for direct daemon or rust_verusd_rpc_server connections)
    rpc_user: Optional[str] = None
    rpc_password: Optional[str] = None

    # Agent registration
    agent_id: str = AGENT_ID
    agent_priority: int = 5

    # UAI core endpoint for agent registration
    uai_core_url: str = "http://uai-core:8001"

    # Swarm coordinator
    swarm_ws_url: str = "ws://uai-core:8001/ws/swarm"

    # Extension toggles
    security_enabled: bool = False
    security_level: str = "disabled"  # disabled | verify_only | enforced | vault_protected
    swarm_controller: str = ""  # Controller VerusID for swarm security
    marketplace_enabled: bool = False
    ip_protection_enabled: bool = False

    # Extra CLI flags
    cli_extra_flags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.api_url is None:
            self.api_url = API_ENDPOINTS[self.network]
        # Environment overrides
        self.api_url = os.getenv("VERUS_API_URL", self.api_url)
        # Also accept VERUS_RPC_URL as an alias for VERUS_API_URL
        if "VERUS_RPC_URL" in os.environ and "VERUS_API_URL" not in os.environ:
            self.api_url = os.environ["VERUS_RPC_URL"]
        self.verus_cli_path = os.getenv("VERUS_CLI_PATH", self.verus_cli_path)
        self.destination_address = os.getenv("VERUS_DESTINATION_ADDRESS", self.destination_address)
        self.uai_core_url = os.getenv("UAI_CORE_URL", self.uai_core_url)
        self.swarm_ws_url = os.getenv("UAI_SWARM_WS_URL", self.swarm_ws_url)

        # RPC auth from environment
        self.rpc_user = os.getenv("VERUS_RPC_USER", self.rpc_user)
        self.rpc_password = os.getenv("VERUS_RPC_PASSWORD", self.rpc_password)

        # Extension env overrides
        self.security_level = os.getenv("VERUS_SECURITY_LEVEL", self.security_level)
        self.security_enabled = self.security_level != "disabled"
        self.swarm_controller = os.getenv("VERUS_SWARM_CONTROLLER", self.swarm_controller)
        self.marketplace_enabled = os.getenv(
            "VERUS_MARKETPLACE_ENABLED", ""
        ).lower() in ("true", "1", "yes")
        self.ip_protection_enabled = os.getenv(
            "VERUS_IP_PROTECTION_ENABLED", ""
        ).lower() in ("true", "1", "yes")

        net = os.getenv("VERUS_NETWORK", "").lower()
        if net in ("mainnet", "testnet"):
            self.network = VerusNetwork(net)
            if "VERUS_API_URL" not in os.environ:
                self.api_url = API_ENDPOINTS[self.network]

    @property
    def is_mainnet(self) -> bool:
        return self.network == VerusNetwork.MAINNET

    @property
    def is_testnet(self) -> bool:
        return self.network == VerusNetwork.TESTNET
