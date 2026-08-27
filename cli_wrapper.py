"""
Verus CLI Wrapper — Low-level Verus Daemon & API Interaction

Provides two execution backends:
  1. Local CLI (subprocess) — for nodes running verusd locally
  2. HTTP JSON-RPC API — for remote interaction via api.verus.services / api.verustest.net

All Verus CLI commands are executed through this wrapper with full error
handling, version enforcement, and structured JSON responses.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import aiohttp

from verus_agent.config import (
    MIN_DAEMON_VERSION,
    MIN_DAEMON_VERSION_STR,
    VerusConfig,
)
from verus_agent.runtime_policy import require_rpc_authorization

logger = logging.getLogger("verus_agent.cli")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class VerusError(Exception):
    """Base exception for Verus operations."""


class VerusCLIError(VerusError):
    """Error executing a Verus CLI command."""

    def __init__(self, command: str, stderr: str, returncode: int):
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(f"CLI error (rc={returncode}) for '{command}': {stderr}")


class VerusAPIError(VerusError):
    """Error calling the Verus JSON-RPC API."""

    def __init__(self, method: str, message: str, code: int = -1):
        self.method = method
        self.code = code
        super().__init__(f"API error ({code}) for '{method}': {message}")


class VerusVersionError(VerusError):
    """Daemon version does not meet the minimum requirement."""


class VerusNetworkError(VerusError):
    """The connected daemon is not positively identified as Testnet."""


class VerusReadinessError(VerusError):
    """The connected Testnet daemon is not ready for a mutation."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CLIResult:
    """Structured result from a CLI / API call.

    Historically some tests constructed this object with an ``error``
    keyword (see verus_agent/tests/test_extensions.py).  The dataclass
    signature previously did not include that field which caused
    ``TypeError: __init__() got an unexpected keyword argument 'error'``.

    To keep the tests happy we now give every field a default value so
    cheap instances can be constructed with only keyword args.
    """
    method: str = ""
    params: List[Any] = field(default_factory=list)
    result: Any = None
    elapsed_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    raw: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# CLI Wrapper
# ---------------------------------------------------------------------------

class VerusCLI:
    """
    Unified interface to the Verus daemon.

    Supports two backends:
      - **cli**: runs ``verus`` / ``verus-cli`` via subprocess  (requires local daemon)
      - **api**: JSON-RPC over HTTP to a remote endpoint

    The backend is selected automatically:
      - If ``config.verus_cli_path`` is set and the binary exists → cli
      - Otherwise → api (using ``config.api_url``)
    """

    def __init__(self, config: VerusConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._daemon_version: Optional[int] = None
        self._daemon_version_str: Optional[str] = None
        self._call_count = 0
        self._total_latency_ms = 0.0

        # Determine backend
        if config.verus_cli_path and os.path.isfile(config.verus_cli_path):
            self._backend = "cli"
            logger.info("Using local CLI backend: %s", config.verus_cli_path)
        else:
            self._backend = "api"
            logger.info("Using remote API backend: %s", config.api_url)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Open HTTP session (for API backend) and verify daemon version."""
        if self._backend == "api":
            auth = None
            if self.config.rpc_user and self.config.rpc_password:
                auth = aiohttp.BasicAuth(self.config.rpc_user, self.config.rpc_password)
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.api_timeout),
                auth=auth,
            )
        try:
            await self._verify_daemon_version()
        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Public: execute any Verus RPC method
    # ------------------------------------------------------------------

    async def call(self, method: str, params: Optional[List[Any]] = None) -> CLIResult:
        """
        Execute a Verus RPC method.

        Parameters
        ----------
        method : str
            The RPC method name (e.g. ``getinfo``, ``getidentity``, ``sendcurrency``).
        params : list, optional
            Positional parameters for the RPC call.

        Returns
        -------
        CLIResult
            Structured result with parsed JSON.
        """
        require_rpc_authorization(method)
        params = params or []
        start = time.monotonic()

        if self._backend == "cli":
            result = await self._call_cli(method, params)
        else:
            result = await self._call_api(method, params)

        elapsed = (time.monotonic() - start) * 1000
        self._call_count += 1
        self._total_latency_ms += elapsed

        # Preserve non-zero latency for successful calls even when execution is
        # faster than the current reporting precision.
        elapsed_ms = max(0.01, round(elapsed, 2))

        return CLIResult(
            method=method,
            params=params,
            result=result["parsed"],
            elapsed_ms=elapsed_ms,
            raw=result.get("raw", ""),
        )

    # ------------------------------------------------------------------
    # Convenience wrappers for common commands
    # ------------------------------------------------------------------

    async def getinfo(self) -> Dict[str, Any]:
        r = await self.call("getinfo")
        return r.result

    async def getidentity(self, name_or_id: str) -> Dict[str, Any]:
        r = await self.call("getidentity", [name_or_id])
        return r.result

    async def getidentitycontent(self, name_or_id: str, vdxf_key: Optional[str] = None) -> Dict[str, Any]:
        params = [name_or_id]
        if vdxf_key:
            params.append(vdxf_key)
        r = await self.call("getidentitycontent", params)
        return r.result

    async def registernamecommitment(
        self,
        name: str,
        controlling_address: str,
        referral_id: str = "",
        parent: str = "",
    ) -> Dict[str, Any]:
        params = [name, controlling_address]
        if referral_id:
            params.append(referral_id)
        if parent:
            params.append(parent)
        r = await self.call("registernamecommitment", params)
        return r.result

    async def registeridentity(self, identity_json: Dict[str, Any]) -> Dict[str, Any]:
        r = await self.call("registeridentity", [json.dumps(identity_json)])
        return r.result

    async def prepare_updateidentity(
        self, identity_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the full current-state identity snapshot for submission."""

        submitted = dict(identity_json)
        if "contentmultimap" in submitted:
            identity_name = submitted.get("name") or submitted.get("identityaddress")
            if not identity_name:
                raise VerusError(
                    "updateidentity with contentmultimap requires name or identityaddress"
                )
            current_rpc = await self.getidentity(str(identity_name))
            current_identity = current_rpc.get("identity", current_rpc)
            current_map = current_identity.get("contentmultimap", {})
            submitted_map = submitted["contentmultimap"]
            if not isinstance(current_map, dict) or not isinstance(submitted_map, dict):
                raise VerusError("contentmultimap must be an object")
            submitted["contentmultimap"] = {**current_map, **submitted_map}
        return submitted

    async def updateidentity_with_snapshot(
        self, identity_json: Dict[str, Any]
    ) -> tuple[Any, Dict[str, Any]]:
        """Submit an update and return both the daemon result and exact payload."""

        submitted = await self.prepare_updateidentity(identity_json)
        r = await self.call("updateidentity", [json.dumps(submitted)])
        return r.result, submitted

    async def updateidentity(self, identity_json: Dict[str, Any]) -> Any:
        result, _submitted = await self.updateidentity_with_snapshot(identity_json)
        return result

    async def getcurrencystate(self, currency_name: str) -> Any:
        r = await self.call("getcurrencystate", [currency_name])
        return r.result

    async def estimateconversion(self, conversion: Dict[str, Any]) -> Dict[str, Any]:
        r = await self.call("estimateconversion", [json.dumps(conversion)])
        return r.result

    async def sendcurrency(
        self,
        from_address: str,
        outputs: List[Dict[str, Any]],
    ) -> str:
        """Send currency (payment, conversion, or cross-chain export).

        IMPORTANT: Returns an **opid** (operation ID), NOT a txid.
        To get the actual txid, poll ``z_getoperationstatus(['opid'])``
        until status is 'success', then read result.txid.

        Parameters
        ----------
        from_address : str
            Source address or ``"*"`` for wildcard (any available funds).
        outputs : list[dict]
            Array of output descriptors: ``{address, amount, currency, ...}``.
            Optional keys: ``convertto``, ``via``, ``exportto``, ``memo``
            (memo only works when sending to z-addresses), ``vdxftag``.

        Returns
        -------
        str
            An opid string (e.g. ``"opid-abcd-1234-..."``).  Poll
            ``z_getoperationstatus`` to track completion and retrieve txid.
        """
        r = await self.call("sendcurrency", [from_address, json.dumps(outputs)])
        return r.result  # opid — poll z_getoperationstatus for txid

    async def getcurrency(self, currency_name: str) -> Dict[str, Any]:
        r = await self.call("getcurrency", [currency_name])
        return r.result

    async def definecurrency(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        r = await self.call("definecurrency", [json.dumps(definition)])
        return r.result

    async def getrawmempool(self, verbose: bool = False, filter_type: Optional[str] = None) -> Any:
        params: List[Any] = [verbose]
        if filter_type:
            params.append(filter_type)
        r = await self.call("getrawmempool", params)
        return r.result

    async def getvdxfid(self, vdxf_uri: str) -> Dict[str, Any]:
        r = await self.call("getvdxfid", [vdxf_uri])
        return r.result

    async def signmessage(self, identity: str, message: str) -> Dict[str, str]:
        """Sign a message with a VerusID.

        Returns
        -------
        dict
            JSON object ``{"hash": "<hexhash>", "signature": "<base64sig>"}``.
            NOTE: This is NOT a plain base64 string — it's a JSON object
            with both the hash of the signed message and the signature.
        """
        r = await self.call("signmessage", [identity, message])
        return r.result  # {"hash": "...", "signature": "..."}

    async def verifymessage(self, identity: str, signature: str, message: str) -> bool:
        r = await self.call("verifymessage", [identity, signature, message])
        return r.result

    async def z_getbalance(self, address: str) -> float:
        r = await self.call("z_getbalance", [address])
        return float(r.result)

    async def z_sendmany(
        self, from_address: str, amounts: List[Dict[str, Any]], minconf: int = 1
    ) -> str:
        """Send from a z-address or t-address to multiple recipients."""
        r = await self.call("z_sendmany", [from_address, json.dumps(amounts), minconf])
        return r.result  # opid

    async def z_getoperationstatus(self, opids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Check the status of z_sendmany / z_shieldcoinbase operations."""
        params = [json.dumps(opids)] if opids else []
        r = await self.call("z_getoperationstatus", params)
        return r.result

    async def await_operation(
        self,
        opid: str,
        *,
        poll_interval: float = 5.0,
        max_polls: int = 120,
    ) -> Dict[str, Any]:
        """Poll an async wallet operation to terminal status."""

        for poll_number in range(max_polls):
            statuses = await self.z_getoperationstatus([opid])
            if statuses:
                status = statuses[0]
                if status.get("status") in {"success", "failed", "cancelled"}:
                    return status
            if poll_number + 1 < max_polls:
                await asyncio.sleep(poll_interval)
        return {"id": opid, "status": "timeout"}

    async def z_getnewaddress(self, address_type: str = "sapling") -> str:
        """Generate a new shielded (z) address."""
        r = await self.call("z_getnewaddress", [address_type])
        return r.result

    async def z_listaddresses(self) -> List[str]:
        """List all z-addresses in the wallet."""
        r = await self.call("z_listaddresses")
        return r.result

    async def makeoffer(
        self, fromaddress: str, offer_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a marketplace offer (VerusID Marketplace).

        Parameters
        ----------
        fromaddress : str
            Address or VerusID funding the offer (e.g. ``"youragent@"``).
        offer_json : dict
            Offer specification: ``{"changeaddress", "offer": {...}, "for": {...}}``.
        """
        r = await self.call("makeoffer", [fromaddress, json.dumps(offer_json)])
        return r.result

    async def takeoffer(
        self, fromaddress: str, offer_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Accept a marketplace offer.

        Parameters
        ----------
        fromaddress : str
            Address or VerusID accepting the offer.
        offer_json : dict
            Acceptance spec — the offer txid goes INSIDE this JSON:
            ``{"txid": "OFFER_TXID", "changeaddress": "...",
               "deliver": {...}, "accept": {...}}``.

        Note
        ----
        The offer txid is NOT a separate parameter — it is a field
        inside ``offer_json``.  This differs from some older documentation.
        """
        r = await self.call("takeoffer", [fromaddress, json.dumps(offer_json)])
        return r.result

    async def getoffers(
        self, currency_or_id: str, is_currency: bool = False, with_tx: bool = False
    ) -> Dict[str, Any]:
        """Get all open offers for an identity or currency."""
        r = await self.call("getoffers", [currency_or_id, is_currency, with_tx])
        return r.result

    async def closeoffers(self, txid_list: List[str]) -> Dict[str, Any]:
        """Close/cancel open offers."""
        r = await self.call("closeoffers", [json.dumps(txid_list)])
        return r.result

    async def veruspay_createinvoice(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a VerusPay invoice for programmatic billing.

        Parameters
        ----------
        invoice : dict
            Must contain: ``amount`` (float), ``currency`` (str),
            ``destination`` (str), ``memo`` (str, optional).
        """
        r = await self.call("createinvoice", [json.dumps(invoice)])
        return r.result

    async def listidentities(
        self,
        include_watch_only: bool = False,
        from_height: int = 0,
        to_height: int = 0,
    ) -> List[Dict[str, Any]]:
        """List identities in the wallet. Useful for discovery."""
        params: List[Any] = [include_watch_only]
        if from_height or to_height:
            params.extend([from_height, to_height])
        r = await self.call("listidentities", params)
        return r.result if isinstance(r.result, list) else []

    async def getblock(self, hash_or_height: Union[str, int], verbosity: int = 1) -> Dict[str, Any]:
        r = await self.call("getblock", [hash_or_height, verbosity])
        return r.result

    async def getblockcount(self) -> int:
        r = await self.call("getblockcount")
        return int(r.result)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def avg_latency_ms(self) -> float:
        if self._call_count == 0:
            return 0.0
        return round(self._total_latency_ms / self._call_count, 2)

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def daemon_version(self) -> Optional[str]:
        return self._daemon_version_str

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _call_cli(self, method: str, params: List[Any]) -> Dict[str, Any]:
        """Execute via local ``verus`` binary."""
        cli = self.config.verus_cli_path
        cmd_parts = [cli, method]
        for p in params:
            if isinstance(p, (dict, list)):
                cmd_parts.append(json.dumps(p))
            else:
                cmd_parts.append(str(p))

        # Never log serialized RPC parameters. They may contain credentials,
        # wallet material, participant data, memos, or unpublished content.
        command_label = f"{os.path.basename(cli) if cli else 'verus'} {method}"
        logger.debug("CLI exec: method=%s param_count=%d", method, len(params))

        proc = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(cli) if cli else None,
        )
        stdout, stderr = await proc.communicate()
        raw = stdout.decode().strip()

        if proc.returncode != 0:
            raise VerusCLIError(command_label, "RPC command failed", proc.returncode or -1)

        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw

        return {"parsed": parsed, "raw": raw}

    async def _call_api(self, method: str, params: List[Any]) -> Dict[str, Any]:
        """Execute via JSON-RPC HTTP API.

        Supports optional Basic Auth for direct daemon / rust_verusd_rpc_server
        connections.  When ``config.rpc_user`` and ``config.rpc_password`` are
        set, requests include an Authorization header.
        """
        if not self._session:
            auth = None
            if self.config.rpc_user and self.config.rpc_password:
                auth = aiohttp.BasicAuth(self.config.rpc_user, self.config.rpc_password)
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.api_timeout),
                auth=auth,
            )

        payload = {
            "jsonrpc": "2.0",
            "id": self._call_count + 1,
            "method": method,
            "params": params,
        }

        # Parameters are intentionally omitted because RPC payloads can contain
        # secrets, wallet data, private records, or unpublished content.
        logger.debug("API call: method=%s param_count=%d", method, len(params))

        async with self._session.post(self.config.api_url, json=payload) as resp:
            raw_text = await resp.text()
            if resp.status != 200:
                raise VerusAPIError(method, f"HTTP {resp.status}")

            data = json.loads(raw_text)
            if "error" in data and data["error"] is not None:
                err = data["error"]
                raise VerusAPIError(
                    method,
                    "RPC endpoint returned an error",
                    err.get("code", -1),
                )

            return {"parsed": data.get("result"), "raw": raw_text}

    @staticmethod
    def _parse_version_str(value: str) -> tuple[int, int]:
        """Parse ``major.minor.patch[-revision]`` into comparable numbers."""

        import re

        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-(\d+))?", value.strip())
        if not match:
            raise VerusVersionError("Daemon returned an unrecognized version string")
        major, minor, patch, revision = match.groups()
        encoded = int(major) * 1_000_000 + int(minor) * 10_000 + int(patch) * 100
        return encoded, int(revision or 0)

    def _validate_daemon_contract(self, info: Dict[str, Any]) -> None:
        """Validate the exact network and current source-coded version floor."""

        if info.get("testnet") is not True:
            raise VerusNetworkError(
                "Daemon did not positively identify itself as Testnet; refusing access"
            )

        # Current Verus getinfo returns both numeric ``version`` and the
        # revision-bearing ``VRSCversion``. Prefer VRSCversion so the release
        # suffix is not silently discarded.
        version = info.get("VRSCversion") or info.get("version")
        if isinstance(version, int) and not isinstance(version, bool):
            self._daemon_version = version
            major = version // 1_000_000
            minor = (version % 1_000_000) // 10_000
            patch = (version % 10_000) // 100
            self._daemon_version_str = f"{major}.{minor}.{patch}"
            self._daemon_revision = 0
        elif isinstance(version, str):
            encoded, revision = self._parse_version_str(version)
            self._daemon_version = encoded
            self._daemon_version_str = version
            self._daemon_revision = revision
        else:
            raise VerusVersionError(
                "Could not determine daemon version from getinfo; refusing to initialize"
            )

        _, minimum_revision = self._parse_version_str(MIN_DAEMON_VERSION_STR)
        if self._daemon_version < MIN_DAEMON_VERSION or (
            self._daemon_version == MIN_DAEMON_VERSION
            and self._daemon_revision < minimum_revision
        ):
            raise VerusVersionError(
                f"Daemon version {self._daemon_version_str} < minimum "
                f"{MIN_DAEMON_VERSION_STR}. Please upgrade."
            )

    async def _verify_daemon_version(self) -> None:
        """Fail closed unless getinfo proves Testnet and the daemon floor."""

        try:
            info = await self.getinfo()
            if not isinstance(info, dict):
                raise VerusVersionError("getinfo did not return an object")
            self._validate_daemon_contract(info)
            logger.info(
                "Verified Testnet daemon version: %s", self._daemon_version_str
            )
        except (VerusAPIError, VerusCLIError) as exc:
            raise VerusVersionError(
                "Could not verify daemon version; refusing to initialize"
            ) from exc

    async def verify_mutation_readiness(self) -> Dict[str, Any]:
        """Re-check Testnet, version, peer connectivity, and sync before a write."""

        try:
            info = await self.getinfo()
        except (VerusAPIError, VerusCLIError) as exc:
            raise VerusReadinessError(
                "Could not reach the daemon for the pre-mutation readiness check"
            ) from exc
        if not isinstance(info, dict):
            raise VerusReadinessError("getinfo did not return an object")
        self._validate_daemon_contract(info)

        values: Dict[str, int] = {}
        for field_name in ("blocks", "longestchain", "connections"):
            value = info.get(field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise VerusReadinessError(
                    f"Daemon readiness is missing integer field '{field_name}'"
                )
            values[field_name] = value

        if values["connections"] <= 0:
            raise VerusReadinessError("Daemon has no verified peer connectivity")
        if (
            values["blocks"] <= 0
            or values["longestchain"] <= 0
            or values["blocks"] < values["longestchain"]
        ):
            raise VerusReadinessError("Daemon is not synchronized to its longest chain")

        return {
            "network": "testnet",
            "version": self._daemon_version_str,
            "blocks": values["blocks"],
            "longestchain": values["longestchain"],
            "connections": values["connections"],
        }
