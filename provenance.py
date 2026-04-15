"""
Verus Provenance & NFT Workflow Module

Implements the Bitcoin Kali pattern for on-chain provenance — typed
DataDescriptors in contentmultimap, signed MMR roots, encrypted file
delivery via shielded z-addresses, and public verification.

This module is a high-level orchestrator that composes:
  - VerusIDManager   — identity creation
  - VerusCLI         — signdata, verifysignature, sendcurrency, decryptdata
  - VerusStorageManager — file storage helpers
  - VDXFBuilder      — contentmultimap construction

Pattern (from Bitcoin Kali 7-NFT series):
    1.  Register a VerusID for the NFT (``Destroyer of Fiat.bitcoins@``)
    2.  Store 10 typed DataDescriptors in contentmultimap under a series
        VDXF key (name, description, attributes, image-ref, image-hash,
        signature, mmrroot, mmrdescriptor, rights, delivery)
    3.  Build an MMR over data leaves and sign the root with ``signdata``
    4.  Deliver encrypted file via ``sendcurrency`` to a single-purpose
        z-address; publish the Extended Viewing Key (EVK) on-chain for
        public verification
    5.  Verify: getidentitycontent → decryptdata → SHA-256 → compare
        on-chain hash → verifysignature against curator
    6.  List on decentralized marketplace via ``makeoffer`` with optional
        ``for.address`` proceeds routing

References:
    - https://medium.com/@vdappdev/bitcoin-kali-7-nfts-that-live-entirely-on-chain
    - https://bitcoinkali.com/
    - verusidx-mcp tool-specs/data.md (signdata, decryptdata, verifysignature)
    - verusidx-mcp tool-specs/send.md (sendcurrency with data)
    - verusidx-mcp tool-specs/marketplace.md (makeoffer, getoffers)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from verus_agent.cli_wrapper import VerusCLI, VerusError
from verus_agent.vdxf_builder import (
    ContentMultiMapBuilder,
    DataDescriptorBuilder,
    build_updateidentity_payload,
)

logger = logging.getLogger("verus_agent.provenance")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceResult:
    """Result of a provenance operation."""
    operation: str
    success: bool
    txid: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "success": self.success,
            "txid": self.txid,
            "error": self.error,
            "data": self.data,
        }


# ---------------------------------------------------------------------------
# Preset descriptor templates (Bitcoin Kali 10-field schema)
# ---------------------------------------------------------------------------

PROVENANCE_LABELS = [
    "name", "description", "attributes", "image-ref", "image-datahash",
    "signature", "mmrroot", "mmrdescriptor", "rights", "delivery",
]


def build_provenance_descriptor(
    label: str,
    value: Any,
    mimetype: str = "text/plain",
) -> Dict[str, Any]:
    """Build a single DataDescriptor for a provenance field."""
    builder = DataDescriptorBuilder().set_label(label).set_mimetype(mimetype)
    if isinstance(value, str):
        builder.set_message(value)
    elif isinstance(value, dict):
        builder.set_objectdata_json(value)
    else:
        builder.set_objectdata_hex(str(value))
    return builder.build()


# ---------------------------------------------------------------------------
# Provenance Manager
# ---------------------------------------------------------------------------

class VerusProvenanceManager:
    """
    High-level orchestrator for on-chain provenance / NFT workflows.

    Composes identity creation, typed DataDescriptor storage, MMR signing,
    encrypted file delivery, and marketplace listing into a coherent
    pipeline following the Bitcoin Kali pattern.

    Usage::

        provenance = VerusProvenanceManager(cli, id_mgr, storage_mgr)

        # 1. Create the NFT identity
        result = await provenance.create_nft_identity(
            name="MyArtwork",
            primary_addresses=["RAddress..."],
        )

        # 2. Store typed descriptors
        result = await provenance.store_typed_descriptors(
            identity_name="MyArtwork@",
            series_key="i5mntfEpcAWot1...",
            descriptors=[
                {"label": "name",        "value": "My Artwork"},
                {"label": "description", "value": "A digital masterpiece"},
                {"label": "attributes",  "value": {"medium": "digital"}},
                {"label": "image-datahash", "value": sha256_of_image},
                {"label": "rights",      "value": "All rights transferred..."},
            ],
        )

        # 3. Sign provenance MMR
        result = await provenance.sign_provenance_mmr(
            signing_identity="curator@",
            data_leaves=[
                {"message": "My Artwork"},
                {"message": "A digital masterpiece"},
                {"datahash": sha256_of_image},
            ],
        )

        # 4. Deliver encrypted file
        result = await provenance.encrypted_file_delivery(
            from_address="curator@",
            z_address="zs1...",
            file_path="/path/to/artwork.png",
        )

        # 5. List on marketplace
        result = await provenance.list_for_marketplace(
            identity_name="MyArtwork@",
            price=258,
            currency="VRSC",
            for_address="Verus Coin Foundation@",
        )
    """

    def __init__(
        self,
        cli: VerusCLI,
        identity_manager: Any,   # VerusIDManager
        storage_manager: Any,    # VerusStorageManager
    ):
        self.cli = cli
        self.identity_manager = identity_manager
        self.storage_manager = storage_manager

    # ------------------------------------------------------------------
    # 1. Create NFT identity
    # ------------------------------------------------------------------

    async def create_nft_identity(
        self,
        name: str,
        primary_addresses: List[str],
        recovery_authority: Optional[str] = None,
        revocation_authority: Optional[str] = None,
        content_multimap: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register a VerusID to serve as an NFT identity.

        Uses the standard two-step process (commitment → registration).
        The identity can immediately hold contentmultimap data.
        """
        try:
            result = await self.identity_manager.create_identity(
                name=name,
                primary_addresses=primary_addresses,
                recovery_authority=recovery_authority,
                revocation_authority=revocation_authority,
                content_multimap=content_multimap,
            )
            return ProvenanceResult(
                operation="create_nft_identity",
                success=result.success,
                txid=result.txid,
                error=result.error,
                data={"name": name, "commitment": result.data},
            ).to_dict()
        except VerusError as exc:
            return ProvenanceResult(
                operation="create_nft_identity", success=False, error=str(exc),
            ).to_dict()

    # ------------------------------------------------------------------
    # 2. Store typed DataDescriptors
    # ------------------------------------------------------------------

    async def store_typed_descriptors(
        self,
        identity_name: str,
        series_key: str,
        descriptors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Store an array of typed DataDescriptors in a contentmultimap.

        Each descriptor dict should have:
          - ``label``: human-readable label or VDXF i-address
          - ``value``: the content (string, dict, or hex)
          - ``mimetype``: (optional) e.g. ``text/plain``, ``application/json``

        They are stored under ``series_key`` in the identity's
        contentmultimap, matching the Bitcoin Kali pattern.
        """
        try:
            builder = ContentMultiMapBuilder()
            for desc_input in descriptors:
                label = desc_input.get("label", "")
                value = desc_input.get("value", "")
                mimetype = desc_input.get("mimetype", "text/plain")
                desc = build_provenance_descriptor(label, value, mimetype)
                builder.add_descriptor(series_key, desc)

            payload = build_updateidentity_payload(
                name=identity_name,
                content_multimap=builder.build(),
            )
            result = await self.cli.updateidentity(payload)
            txid = result if isinstance(result, str) else result.get("txid")

            return ProvenanceResult(
                operation="store_typed_descriptors",
                success=True,
                txid=txid,
                data={
                    "identity": identity_name,
                    "series_key": series_key,
                    "descriptor_count": len(descriptors),
                },
            ).to_dict()
        except VerusError as exc:
            return ProvenanceResult(
                operation="store_typed_descriptors", success=False, error=str(exc),
            ).to_dict()

    # ------------------------------------------------------------------
    # 3. Sign provenance MMR
    # ------------------------------------------------------------------

    async def sign_provenance_mmr(
        self,
        signing_identity: str,
        data_leaves: List[Dict[str, Any]],
        mmrhashtype: str = "blake2b",
        encrypttoaddress: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a Merkle Mountain Range over data leaves and sign the root.

        Each leaf in ``data_leaves`` is a dict with exactly one of:
        ``message``, ``messagehex``, ``datahash``, ``filename``, ``vdxfdata``.

        Returns the MMR root, signature, and optionally encrypted descriptors.
        """
        try:
            sign_args: Dict[str, Any] = {
                "address": signing_identity,
                "mmrdata": data_leaves,
                "mmrhashtype": mmrhashtype,
                "createmmr": True,
            }
            if encrypttoaddress:
                sign_args["encrypttoaddress"] = encrypttoaddress

            result = await self.cli.call("signdata", [sign_args])
            r = result.result if hasattr(result, "result") else result

            return ProvenanceResult(
                operation="sign_provenance_mmr",
                success=True,
                data={
                    "mmrroot": r.get("mmrroot"),
                    "signature": r.get("signature"),
                    "hashes": r.get("hashes"),
                    "signaturedata": r.get("signaturedata"),
                    "identity": r.get("identity"),
                    "signatureheight": r.get("signatureheight"),
                    # Encrypted variants (present when encrypttoaddress is used)
                    "mmrdescriptor_encrypted": r.get("mmrdescriptor_encrypted"),
                    "signaturedata_encrypted": r.get("signaturedata_encrypted"),
                    "signaturedata_ssk": r.get("signaturedata_ssk"),
                },
            ).to_dict()
        except VerusError as exc:
            return ProvenanceResult(
                operation="sign_provenance_mmr", success=False, error=str(exc),
            ).to_dict()

    # ------------------------------------------------------------------
    # 4. Encrypted file delivery
    # ------------------------------------------------------------------

    async def encrypted_file_delivery(
        self,
        from_address: str,
        z_address: str,
        file_path: Optional[str] = None,
        data: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Encrypt a file and deliver it via ``sendcurrency`` to a z-address.

        The file is included as structured data in the sendcurrency call.
        Sapling encryption is built-in — only the z-address holder (or
        anyone with the EVK) can decrypt it.

        Returns the opid for async tracking via ``z_getoperationstatus``.
        """
        try:
            if file_path:
                with open(file_path, "rb") as f:
                    file_data = f.read()
            elif data:
                file_data = data
            else:
                return ProvenanceResult(
                    operation="encrypted_file_delivery",
                    success=False,
                    error="Either file_path or data must be provided",
                ).to_dict()

            file_hash = hashlib.sha256(file_data).hexdigest()

            # sendcurrency with data payload to z-address
            outputs = [{
                "address": z_address,
                "amount": 0.0001,
                "data": {
                    "messagehex": file_data.hex(),
                },
            }]
            result = await self.cli.call(
                "sendcurrency", [from_address, outputs]
            )
            r = result.result if hasattr(result, "result") else result

            # sendcurrency returns an opid for async operations
            opid = r if isinstance(r, str) else r.get("opid", r)

            return ProvenanceResult(
                operation="encrypted_file_delivery",
                success=True,
                data={
                    "opid": opid,
                    "z_address": z_address,
                    "file_hash": file_hash,
                    "size_bytes": len(file_data),
                },
            ).to_dict()
        except (VerusError, IOError) as exc:
            return ProvenanceResult(
                operation="encrypted_file_delivery", success=False, error=str(exc),
            ).to_dict()

    # ------------------------------------------------------------------
    # 4b. Publish viewing key
    # ------------------------------------------------------------------

    async def publish_viewing_key(
        self,
        identity_name: str,
        z_address: str,
        series_key: str,
        delivery_label: str = "delivery",
    ) -> Dict[str, Any]:
        """
        Export the EVK for a z-address and store it in the NFT identity's
        delivery DataDescriptor for public verification.
        """
        try:
            # Export the viewing key
            evk_result = await self.cli.call(
                "z_exportviewingkey", [z_address]
            )
            evk = evk_result.result if hasattr(evk_result, "result") else evk_result

            # Store in contentmultimap as a delivery descriptor
            builder = ContentMultiMapBuilder()
            desc = (DataDescriptorBuilder()
                    .set_label(delivery_label)
                    .set_mimetype("text/plain")
                    .set_message(evk if isinstance(evk, str) else str(evk))
                    .build())
            builder.add_descriptor(series_key, desc)

            payload = build_updateidentity_payload(
                name=identity_name,
                content_multimap=builder.build(),
            )
            result = await self.cli.updateidentity(payload)
            txid = result if isinstance(result, str) else result.get("txid")

            return ProvenanceResult(
                operation="publish_viewing_key",
                success=True,
                txid=txid,
                data={"evk": evk, "z_address": z_address},
            ).to_dict()
        except VerusError as exc:
            return ProvenanceResult(
                operation="publish_viewing_key", success=False, error=str(exc),
            ).to_dict()

    # ------------------------------------------------------------------
    # 5. Verify provenance
    # ------------------------------------------------------------------

    async def verify_provenance(
        self,
        identity_name: str,
        curator_identity: str,
        series_key: Optional[str] = None,
        evk: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full provenance verification pipeline:

        1. Fetch identity content (contentmultimap)
        2. Extract the image-datahash and mmrroot from descriptors
        3. Verify the curator's signature on the mmrroot via verifysignature
        4. Optionally: decrypt delivered file → SHA-256 → compare hash

        Returns structured verification results.
        """
        try:
            checks: Dict[str, Any] = {
                "identity_exists": False,
                "has_content": False,
                "signature_verified": False,
                "hash_matched": None,
            }

            # Step 1: Fetch identity
            identity_data = await self.cli.getidentity(identity_name)
            checks["identity_exists"] = True

            identity = identity_data.get("identity", identity_data)
            cmm = identity.get("contentmultimap", {})
            checks["has_content"] = bool(cmm)

            # Step 2: Extract fields from contentmultimap
            # Look for mmrroot and signature in the descriptors
            mmrroot = None
            signature = None
            image_hash = None

            # If series_key is provided, look under that key
            descriptors = []
            if series_key and series_key in cmm:
                descriptors = cmm[series_key]
            else:
                # Flatten all descriptors
                for values in cmm.values():
                    if isinstance(values, list):
                        descriptors.extend(values)

            for desc in descriptors:
                if not isinstance(desc, dict):
                    continue
                label = desc.get("label", "")
                objectdata = desc.get("objectdata", "")
                if "mmrroot" in label:
                    mmrroot = objectdata.get("message", objectdata) if isinstance(objectdata, dict) else objectdata
                elif "signature" in label:
                    signature = objectdata.get("message", objectdata) if isinstance(objectdata, dict) else objectdata
                elif "image-datahash" in label or "imagehash" in label:
                    image_hash = objectdata.get("message", objectdata) if isinstance(objectdata, dict) else objectdata

            checks["mmrroot"] = mmrroot
            checks["image_hash"] = image_hash

            # Step 3: Verify signature
            if mmrroot and signature:
                verify_result = await self.cli.call("verifysignature", [{
                    "address": curator_identity,
                    "datahash": mmrroot,
                    "signature": signature,
                    "hashtype": "blake2b",
                }])
                r = verify_result.result if hasattr(verify_result, "result") else verify_result
                checks["signature_verified"] = (
                    r.get("signaturestatus") == "verified"
                )
                checks["signature_details"] = r

            return ProvenanceResult(
                operation="verify_provenance",
                success=checks["signature_verified"],
                data=checks,
            ).to_dict()
        except VerusError as exc:
            return ProvenanceResult(
                operation="verify_provenance", success=False, error=str(exc),
            ).to_dict()

    # ------------------------------------------------------------------
    # 6. List on marketplace
    # ------------------------------------------------------------------

    async def list_for_marketplace(
        self,
        identity_name: str,
        price: float,
        currency: str = "VRSC",
        for_address: Optional[str] = None,
        expiry_height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create an atomic swap offer for a provenance NFT identity.

        Uses ``makeoffer`` to list the identity on the Verus decentralized
        marketplace.  The optional ``for_address`` routes proceeds to a
        third party (e.g. a foundation or charity), matching the Bitcoin
        Kali pattern.
        """
        try:
            offer: Dict[str, Any] = {
                "changeaddress": identity_name,
                "offer": {
                    "identity": identity_name,
                    "amount": 1,
                },
                "for": {
                    "currency": currency,
                    "amount": price,
                },
            }
            if for_address:
                offer["for"]["address"] = for_address
            if expiry_height:
                offer["expiryheight"] = expiry_height

            result = await self.cli.call("makeoffer", [offer])
            r = result.result if hasattr(result, "result") else result
            txid = r if isinstance(r, str) else r.get("txid", r.get("hex"))

            return ProvenanceResult(
                operation="list_for_marketplace",
                success=True,
                txid=txid,
                data={
                    "identity": identity_name,
                    "price": price,
                    "currency": currency,
                    "for_address": for_address,
                    "expiry_height": expiry_height,
                },
            ).to_dict()
        except VerusError as exc:
            return ProvenanceResult(
                operation="list_for_marketplace", success=False, error=str(exc),
            ).to_dict()
