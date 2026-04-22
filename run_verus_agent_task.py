"""Lightweight task runner for verus_agent workflows.

Provides:
1. Startup smoke check (initialize + getinfo capability call)
2. Consistent one-command task execution with allowlist enforcement
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Set

# Ensure `verus_agent` imports resolve when this script is run from
# the repository root (`.../verus_agent`) instead of its parent.
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_PARENT = SCRIPT_DIR.parent
if str(SCRIPT_PARENT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PARENT))

from verus_agent.agent import VerusBlockchainAgent
from verus_agent.config import VerusConfig, VerusNetwork


DEFAULT_ALLOWLIST_PATH = SCRIPT_DIR / "capability_allowlist.json"


def _load_allowlist(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Allowlist file not found: {path}. Create it or pass --allowlist-path."
        )
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    capabilities = payload.get("allowed_capabilities", [])
    cli_methods = payload.get("allowed_cli_methods", [])
    if not isinstance(capabilities, list) or not all(isinstance(c, str) for c in capabilities):
        raise ValueError("allowed_capabilities must be a list of strings")
    if not isinstance(cli_methods, list) or not all(isinstance(c, str) for c in cli_methods):
        raise ValueError("allowed_cli_methods must be a list of strings")

    return {
        "allowed_capabilities": set(capabilities),
        "allowed_cli_methods": set(cli_methods),
        "raw": payload,
    }


def _parse_network(value: str) -> VerusNetwork:
    value = value.lower().strip()
    if value not in {"testnet", "mainnet"}:
        raise argparse.ArgumentTypeError("--network must be one of: testnet, mainnet")
    return VerusNetwork(value)


def _parse_params_json(value: str | None) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON for --params-json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--params-json must decode to an object")
    return parsed


def _enforce_allowlist(
    capability: str,
    params: Dict[str, Any],
    allowed_capabilities: Set[str],
    allowed_cli_methods: Set[str],
) -> None:
    if capability not in allowed_capabilities:
        raise PermissionError(
            f"Capability '{capability}' is not in allowlist. "
            "Update verus_agent/capability_allowlist.json if intentionally needed."
        )

    if capability == "verus.cli.execute":
        method = params.get("method", "")
        if method not in allowed_cli_methods:
            raise PermissionError(
                f"RPC method '{method}' is not allowed for verus.cli.execute. "
                "Update allowed_cli_methods if required."
            )


async def _run_smoke(
    network: VerusNetwork,
    allowlist: Dict[str, Any],
) -> int:
    agent = VerusBlockchainAgent(VerusConfig(network=network))
    try:
        await agent.initialize()
        params = {"method": "getinfo", "params": []}
        _enforce_allowlist(
            "verus.cli.execute",
            params,
            allowlist["allowed_capabilities"],
            allowlist["allowed_cli_methods"],
        )

        result = await agent.process_task(
            {
                "task_id": "smoke-getinfo",
                "capability": "verus.cli.execute",
                "params": params,
            }
        )
        payload = {
            "ok": result.success,
            "task_id": result.task_id,
            "capability": result.capability,
            "processing_time_ms": result.processing_time_ms,
            "result": result.result,
            "error": result.error,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if result.success else 1
    finally:
        await agent.shutdown()


async def _run_capability(
    network: VerusNetwork,
    capability: str,
    params: Dict[str, Any],
    allowlist: Dict[str, Any],
) -> int:
    _enforce_allowlist(
        capability,
        params,
        allowlist["allowed_capabilities"],
        allowlist["allowed_cli_methods"],
    )

    agent = VerusBlockchainAgent(VerusConfig(network=network))
    try:
        await agent.initialize()
        result = await agent.process_task(
            {
                "capability": capability,
                "params": params,
            }
        )
        payload = {
            "ok": result.success,
            "task_id": result.task_id,
            "capability": result.capability,
            "processing_time_ms": result.processing_time_ms,
            "result": result.result,
            "error": result.error,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if result.success else 1
    finally:
        await agent.shutdown()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run verus_agent tasks with allowlist enforcement.")
    parser.add_argument(
        "--network",
        type=_parse_network,
        default=VerusNetwork.TESTNET,
        help="Verus network profile to use: testnet|mainnet (default: testnet)",
    )
    parser.add_argument(
        "--allowlist-path",
        default=os.getenv("VERUS_AGENT_ALLOWLIST_PATH", str(DEFAULT_ALLOWLIST_PATH)),
        help="Path to capability allowlist JSON",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke", help="Run startup smoke check (initialize + getinfo)")

    task_parser = sub.add_parser("task", help="Execute one allowlisted capability")
    task_parser.add_argument("--capability", required=True, help="Capability string")
    task_parser.add_argument(
        "--params-json",
        default="{}",
        help="Capability params as JSON object",
    )

    sub.add_parser("show-allowlist", help="Print loaded allowlist")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    allowlist_path = Path(args.allowlist_path)
    allowlist = _load_allowlist(allowlist_path)

    if args.command == "show-allowlist":
        print(json.dumps(allowlist["raw"], indent=2, sort_keys=True))
        return 0

    if args.command == "smoke":
        return asyncio.run(_run_smoke(args.network, allowlist))

    if args.command == "task":
        params = _parse_params_json(args.params_json)
        return asyncio.run(_run_capability(args.network, args.capability, params, allowlist))

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
