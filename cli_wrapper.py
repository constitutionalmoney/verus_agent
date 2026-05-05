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
        await self._verify_daemon_version()

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

    async def updateidentity(self, identity_json: Dict[str, Any]) -> Dict[str, Any]:
        r = await self.call("updateidentity", [json.dumps(identity_json)])
        return r.result

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

        cmd_str = " ".join(cmd_parts)
        logger.debug("CLI exec: %s", cmd_str)

        proc = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(cli) if cli else None,
        )
        stdout, stderr = await proc.communicate()
        raw = stdout.decode().strip()

        if proc.returncode != 0:
            raise VerusCLIError(cmd_str, stderr.decode().strip(), proc.returncode or -1)

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

        logger.debug("API call: %s %s", method, params)

        async with self._session.post(self.config.api_url, json=payload) as resp:
            raw_text = await resp.text()
            if resp.status != 200:
                raise VerusAPIError(method, f"HTTP {resp.status}: {raw_text}")

            data = json.loads(raw_text)
            if "error" in data and data["error"] is not None:
                err = data["error"]
                raise VerusAPIError(
                    method,
                    err.get("message", str(err)),
                    err.get("code", -1),
                )

            return {"parsed": data.get("result"), "raw": raw_text}

    async def _verify_daemon_version(self) -> None:
        """Enforce minimum daemon version (supports `major.minor.patch` and
        optional `-<revision>` suffixs, e.g. `1.2.14-2`).

        Numeric encoding (used historically) still applies for major/minor/patch
        (encoded as `major*1_000_000 + minor*10_000 + patch*100`). A revision
        suffix (e.g. `-2`) is compared separately so `1.2.14-2` > `1.2.14`.
        """
        def _parse_version_str(s: str) -> tuple[int, int]:
            """Parse a version string and return (encoded_int, revision).

            Examples:
              - "1.2.14"     -> (1021400, 0)
              - "1.2.14-2"   -> (1021400, 2)
            """
            import re

            # Match: major.minor.patch[-revision]
            m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-?(\d+))?", s)
            if not m:
                # Fallback: extract leading numbers where possible
                parts = s.split(".")
                major = int(parts[0]) if parts and parts[0].isdigit() else 0
                minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                patch_part = parts[2] if len(parts) > 2 else "0"
                patch_match = re.match(r"(\d+)", patch_part)
                patch = int(patch_match.group(1)) if patch_match else 0
                rev_match = re.search(r"-(\d+)", s)
                rev = int(rev_match.group(1)) if rev_match else 0
                return (major * 1000000 + minor * 10000 + patch * 100, rev)

            major_s, minor_s, patch_s, rev_s = m.groups()
            major_i = int(major_s)
            minor_i = int(minor_s)
            patch_i = int(patch_s)
            rev_i = int(rev_s) if rev_s else 0
            return (major_i * 1000000 + minor_i * 10000 + patch_i * 100, rev_i)

        try:
            info = await self.getinfo()
            version = info.get("version") or info.get("VRSCversion")

            # Default revision==0 for integer versions (no suffix possible).
            if isinstance(version, int):
                self._daemon_version = version
                major = version // 1000000
                minor = (version % 1000000) // 10000
                patch = (version % 10000) // 100
                self._daemon_version_str = f"{major}.{minor}.{patch}"
                self._daemon_revision = 0

            elif isinstance(version, str):
                # Accept strings like "1.2.14" or "1.2.14-2"
                self._daemon_version_str = version
                encoded, rev = _parse_version_str(version)
                self._daemon_version = encoded
                self._daemon_revision = rev
            else:
                logger.warning("Could not determine daemon version from getinfo")
                return

            # Determine minimum required revision (if any) from the configured
            # string (e.g. MIN_DAEMON_VERSION_STR == "1.2.14-2").
            _, min_required_rev = _parse_version_str(MIN_DAEMON_VERSION_STR)

            # Numeric (major/minor/patch) check first.
            if self._daemon_version < MIN_DAEMON_VERSION:
                raise VerusVersionError(
                    f"Daemon version {self._daemon_version_str} < minimum "
                    f"{MIN_DAEMON_VERSION_STR}. Please upgrade."
                )

            # If numeric versions are equal, compare revision suffix (if required).
            if self._daemon_version == MIN_DAEMON_VERSION and getattr(self, "_daemon_revision", 0) < min_required_rev:
                raise VerusVersionError(
                    f"Daemon version {self._daemon_version_str} < minimum "
                    f"{MIN_DAEMON_VERSION_STR}. Please upgrade."
                )

            logger.info("Verus daemon version: %s ✓", self._daemon_version_str)
        except (VerusAPIError, VerusCLIError) as exc:
            logger.warning("Could not verify daemon version: %s", exc)
