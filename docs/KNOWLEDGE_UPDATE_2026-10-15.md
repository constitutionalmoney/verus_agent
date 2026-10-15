# Knowledge update validation, 2026-10-15

Base: `origin/main`, `c0bed6f0176e21d8cbbaa8ac68f6f5c12832cfa4`.
Task branch: `codex/verus-ecosystem-knowledge-20261015`.
Work was performed in an isolated Codex worktree. Commit and draft PR are
reported in the delivery message; this report does not merge or deploy.

## Changed surface

- `knowledge.py`, `agent.py`, `runtime_policy.py`, and the two capability
  allowlists add named, offline public-reference retrieval as a read-only task.
- `config.py` and `mobile.py` record store version **v1.1.0-21**, separate
  Android APK/source and Apple marketing versions, current SDK pins, supported
  subsets and callback rules. No new wallet execution route is activated.
- Six `knowledge/*.md` references cover the release, SDK/primitives,
  DREAM structure, bootstrap/treasury resources and all 20 requested community
  discussions. README, AGENTS, integration and historical-guide pointers are updated.
- `pyproject.toml` packages those references and excludes local operator and
  approval files. `scripts/check_knowledge.py` validates local links and builds
  an isolated public-source wheel with synthetic exclusion fixtures.
- `tests/test_knowledge.py` covers retrieval, rejected paths/topics, release
  distinctions, read-only dispatch and disabled activation.
  `tests/test_extensions.py` updates the release-snapshot expectation.

## Commands and results

Test setup used the existing Python 3.11 environment, with this worktree's
parent on `PYTHONPATH`; no dependencies were installed. The mock suite ran on
Python 3.11.9, pytest 8.3.5, pytest-asyncio 1.3.0, aiohttp 3.13.3 and numpy
2.4.4. These differ from repository locks, so this is not validation of the
exact locked installation. The default Python used for stdlib/content/wheel
checks was 3.11.16, existing setuptools 80.10.2 (also not the pinned backend).

| Command | Exit / result |
|---|---|
| `pytest tests/test_knowledge.py -q` (initial work-in-progress run) | 1: 13 passed, one missing community document. Resolved by completing the catalog; final suite below includes all 14 knowledge cases. |
| `pytest tests/ -m 'not upstream_contract'` | 0: **208 passed**, 3 deselected. Mocks; no live daemon. |
| `pytest -m upstream_contract` before selecting an upstream checkout | 0: 3 skipped, not validation. |
| `git clone --depth 1 https://github.com/VerusCoin/verus-typescript-primitives.git $taskUpstreamDir` | 0: public source checkout in a temporary directory, no install or JS execution. |
| `git -C $taskUpstreamDir rev-parse HEAD` | 0: `3ffa9d77a3dd98c23fe4f66cf4368946906de780`. |
| `pytest -m upstream_contract` with `VERUS_TYPESCRIPT_PRIMITIVES_ROOT` selecting that checkout | 0: **3 passed**, 208 deselected. Source strings only. |
| `python scripts/check_knowledge.py --wheel` | 0: 8 documents' local links valid; all six topics readable from the zipped wheel; synthetic local operator/approval files absent. No dependencies installed. |
| `python scripts/check_public_content.py` | 0: passed. |
| `python -m json.tool capability_allowlist.json` | 0. |
| `python -m json.tool capability_allowlist.constitutional_money.json` | 0. |
| `git diff --check` | 0. |

Python AST and `tomllib` syntax validation also exited 0 using:

```powershell
python -c 'import ast,pathlib,tomllib; [ast.parse(pathlib.Path(p).read_text(encoding="utf-8-sig")) for p in ["knowledge.py","config.py","mobile.py","agent.py","runtime_policy.py","tests/test_knowledge.py"]]; tomllib.loads(pathlib.Path("pyproject.toml").read_text()); print("Python syntax, JSON and TOML validation passed")'
```

No YAML was changed. The full implementation diff and all new reference files
were reviewed before commit. Source/release/resource links were inspected
separately from local Markdown link validation; inaccessible links and
contradictions are recorded in the catalog.

## Evidence and deliberate limits

- Google Play live HTML confirms `1.1.0-21`; Apple metadata exposes `1.1.0`;
  the announcement names store build `-21`. Available `-20` source has not been
  proven identical to store binaries.
- All 20 supplied Discord discussions were reviewed through their available
  histories and linked resources. One Make message could not be loaded.
  Media received metadata/presence review only, without transcription. No raw
  transcripts, personal account data or signed CDN URLs were retained in Git.
- The three upstream checks are narrow source contracts, not JS regression,
  binary, cryptographic or daemon 1.2.18 interoperability tests. The upstream
  MMR fixture provenance names 1.2.17-6. Runtime minimum remains 1.2.17-6.
- Legacy payment/login/marketplace helper scaffolds are not newly certified
  protocol implementations. Python link helpers still do not parse the
  encoded request, verify its embedded callback or sign it.
- App Encryption remains blocked from agent task activation. Gift-card
  funding/claims, NFC writing, response-decryption services and a full DREAM
  app are not implemented by this knowledge update.
- No wallet/device test, Testnet smoke, community-code execution, container
  build/launch, production validation, trade, blockchain mutation, merge or
  deployment occurred.

## PR 5 review follow-up

Review found that the new wheel/privacy checker was not a CI gate and used
assertions which optimized Python could disable. Integrity checks now raise
explicit errors, including the zipped-package origin check. CI runs
`python scripts/check_knowledge.py --wheel` using its locked build environment.
Three subprocess regressions prove missing knowledge and operator/approval
file leaks remain failures under `python -O`.

Local review validation, all exit 0:

- `pytest tests/` with `VERUS_TYPESCRIPT_PRIMITIVES_ROOT` selecting the
  inspected `3ffa9d77a3dd98c23fe4f66cf4368946906de780` checkout: **214 passed**.
- `pytest tests/test_knowledge_validation.py tests/test_knowledge.py -q`:
  **17 passed**.
- `python -O scripts/check_knowledge.py --wheel`: all six wheel topics,
  local links and private-file exclusion fixtures passed.
- `python scripts/check_public_content.py` and `git diff --check`: passed.
- CI YAML parsed with existing PyYAML; the knowledge-wheel step was confirmed.

The local dependency-version and live-interoperability limits above remain.
The reviewed head must pass GitHub CI before the separately authorized merge;
the merge does not authorize deployment.
