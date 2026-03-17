"""
Contract checks for local verus-typescript-primitives updates.

These tests are intentionally lightweight string-level assertions against the
upstream TypeScript source tree cloned next to this repository.

They protect assumptions used by verus_agent docs/integration guidance:
- FQN-aware ContentMultiMap support for PartialIdentity workflows.
- ContentMultiMapRemove action support for action types 3 and 4.
- Optional requestID serialization in AuthenticationRequestDetails.

If the upstream repository is not present in the workspace, tests are skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PRIMITIVES_ROOT = ROOT / "verus-typescript-primitives"


pytestmark = [
    pytest.mark.upstream_contract,
    pytest.mark.skipif(
        not PRIMITIVES_ROOT.exists(),
        reason="Local verus-typescript-primitives clone not found",
    ),
]


def _read(relpath: str) -> str:
    return (PRIMITIVES_ROOT / relpath).read_text(encoding="utf-8")


def test_contentmultimap_supports_fqn_and_partial_identity_flow() -> None:
    content = _read("src/pbaas/ContentMultiMap.ts")

    assert "export class KvContent" in content
    assert "KvContent key collision" in content
    assert "export class FqnContentMultiMap extends ContentMultiMap" in content
    assert "static fromJson(obj: { [key: string]: ContentMultiMapJsonValue }): FqnContentMultiMap" in content


def test_contentmultimapremove_supports_actions_3_and_4() -> None:
    content = _read("src/pbaas/ContentMultiMapRemove.ts")

    assert "static ACTION_REMOVE_ALL_KEY = new BN(3);" in content
    assert "static ACTION_CLEAR_MAP = new BN(4);" in content
    assert "entrykey?: string;" in content
    assert "valuehash?: string;" in content
    assert "if (!this.action.eq(ContentMultiMapRemove.ACTION_CLEAR_MAP))" in content


def test_auth_request_details_requestid_is_optional_in_json() -> None:
    content = _read("src/vdxf/classes/login/AuthenticationRequestDetails.ts")

    assert "hasRequestID()" in content
    assert "requestid: this.hasRequestID() ? this.requestID.toJson() : undefined" in content
