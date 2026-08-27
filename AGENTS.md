# Repository Instructions

## Repository identity

- Repository: `constitutionalmoney/verus_agent`.
- Purpose: executable Python 3.11 Verus specialist agent with local CLI and
  HTTP JSON-RPC backends, plus research/reference material.
- Source modules include VerusID, currency/DeFi, storage, authentication,
  mobile, MCP, provenance, and optional security/marketplace/IP-protection
  integrations. Research and proposals are not proof of implementation or
  activation.
- Version: `0.5.0` from `__init__.py` and `pyproject.toml`.
- Visibility: PUBLIC. Treat committed content, history, issues, pull requests,
  logs, CI output, packages, and artifacts as public.
- Never add private or reconstruction-enabling intellectual property, client
  or participant data, identities, addresses, balances, credentials, wallet
  material, workstation/VPS details, private endpoints, topology, operator
  notes, or secrets. Use synthetic fixtures and placeholders.

## Execution gate

- Default activation is read-only and UAI integration defaults off.
- VRSCTEST is the only supported runtime network. Mainnet configuration is
  rejected. Never use Mainnet.
- Do not use production infrastructure, production credentials, or real
  participant/client data.
- Every consuming project must declare its canonical store, actor model,
  privacy boundary, non-goals, network, activation stage, and smallest
  capability/RPC set. Follow `docs/CROSS_PROJECT_ACTIVATION.md`.
- Retrieve exact current Verus references before changing VDXF, VerusID,
  PBaaS, RPC, currency, wallet, or mobile behavior.
- Treat `Extras/` and external guides as research/design evidence unless
  behavior is present in current source and tests.
- Preserve source provenance and distinguish source fact, operator policy,
  inference, and proposal.

## Read before editing

Read the files relevant to the requested surface, including whichever exist:

- `README.md`, `AGENTS.md`, and `AGENTS.override.md`;
- `LOCAL_OPERATOR.md` under the boundary below;
- `pyproject.toml`, `uv.lock`, and exported requirements locks;
- `pytest.ini`, `Dockerfile`, `.dockerignore`, and
  `docker-compose.verus-agent.yml`;
- `.github/workflows/`;
- capability allowlists and activation-profile examples;
- architecture, security, mobile, and deployment documentation.

Do not invent build, test, deployment, API, blockchain, mobile, or repository
behavior. Report unverified claims as unverified.

## Local operator boundary

When LOCAL_OPERATOR.md exists, read it before local Android, wallet, Verus,
or external-auth testing. LOCAL_OPERATOR.md is ignored, workstation-specific,
and must never be committed.

Do not copy local operator details into source, logs, issues, pull requests,
prompts, test fixtures, reports, or artifacts.

## Architecture and runtime facts

- Packaging is defined by `pyproject.toml`; `uv.lock` is the complete resolver
  record. `requirements.build.lock`, `requirements.runtime.lock`, and
  `requirements.test.lock` are pip-compatible, hash-locked inputs.
- `Dockerfile` is a pinned Python 3.11.16, non-root standalone runtime image.
  It is not a Dokploy deployment contract.
- `VerusCLI` selects a configured local CLI binary when valid and otherwise
  uses HTTP JSON-RPC.
- The source-coded daemon floor is the official `1.2.17-6` release verified
  2026-08-26. Initialization requires `getinfo` to prove Testnet and prefers
  its revision-bearing `VRSCversion` over the numeric `version`. Connectivity,
  network, version detection, and floor failures fail closed. Re-verify the
  current official release and any project-specific floor before live work.
- Every new mutation must re-check Testnet, the version floor, peer
  connectivity, and synchronization immediately before dispatch.
- `updateidentity` replaces the current identity UTXO's `contentmultimap`
  snapshot. The manager reads current state, merges submitted keys with every
  current entry intended to remain, writes serially, and requires current-state
  readback. Historical aggregation and `contentmultimapremove` are separate.
- `sendcurrency` returns an operation ID. Success requires polling
  `z_getoperationstatus` to terminal success and extracting the txid.
- UAI, MCP, marketplace, IP protection, and swarm security default off.
- MCP requires Node.js 18+ and `npx` only when explicitly enabled.
- The health server binds port `9124` and serves `/health`.
- `docker-compose.verus-agent.yml` is standalone local/runtime Compose with no
  `build:` section.

## Activation, authorization, and mutation safety

- The built-in activation profile is read-only. Wallet request helpers require
  `wallet_review`. Testnet mutations require `testnet_write`.
- Version 0.5.0 activates only `verus.identity.update` and
  `verus.currency.send` as eligible Testnet mutation contracts. Every other
  write surface remains blocked through `process_task` until it implements
  equivalent confirmation/readback checks.
- Require explicit human authorization for every blockchain mutation,
  including identity, currency, transfer, storage, provenance, marketplace,
  trust, mining, staking, signing, export, or broadcast operations.
- A mutation task requires exact short-lived local approval evidence, a stable
  idempotency key, durable SQLite outbox, single-writer execution, terminal
  confirmation, and capability-specific readback.
- Approval-file evidence is not cryptographic proof that a human approved the
  task. The operator workflow must remain separate from the requesting agent.
- Use `run_verus_agent_task.py` for allowlisted automation. Default allowlists
  are read-only. Allowlist membership is not human approval.
- `agent.process_task` enforces activation independently of the runner
  allowlist. The low-level CLI allows reviewed reads and rejects every other RPC
  outside a scoped mutation grant, so direct module/CLI dispatch cannot
  silently skip the mutation gate.
- Swarm `verify_only` is observability, not enforcement. Swarm membership does
  not authenticate or authorize each task.
- MCP spending limits, audit logging, read-only mode, and fail-closed write
  behavior apply only while MCP is enabled, connected, and selected. Never
  fall back to direct CLI/API after an MCP write failure.
- MCP does not replace per-mutation human authorization.
- Wallet-mediated operations require visible wallet review and approval. A QR
  code, deep link, decode result, or generated request is not authorization.
- Never log RPC parameters or expose credentials, WIFs, keys, seed phrases,
  wallet files, z-seeds, MCP chain secrets, environment values, response
  plaintext, signing material, or private data.

## Verus Mobile

- The current public snapshot is official Android `v1.1.0-14`, published
  2026-08-25. The release page does not establish iOS parity.
- Published capabilities include Gift Cards, VerusPay V4/burn invoices,
  experimental User Data/Data Packet/Identity Update requests, encrypted
  GenericResponses, HTTPS-default response endpoints, signer selection and
  verification, and expanded validation.
- Keep experimental request types behind a project feature flag and validate
  on the exact wallet build and target device.
- Mobile helpers are Testnet-only offline wrappers for already encoded
  payloads; they do not sign, hold keys, submit writes, or simulate approval.

## Public-content boundary

- Run `python scripts/check_public_content.py` before committing.
- The scanner is a high-confidence backstop, not a substitute for human review.
- Never publish literal external IP addresses, private hostnames, VPS paths,
  endpoint inventories, wallet/identity inventories, credentials, or strategy
  whose publication would disclose or reconstruct protected work.
- Removing a value from the current tree does not remove it from Git history;
  any history-remediation decision requires separate explicit authorization.

## Git and scope

- Never work directly on `main`; use an isolated Codex-managed worktree.
- Handle one bounded issue or explicitly authorized task per run.
- Do not modify unrelated repositories/files or stage unrelated changes.
- Use DCO sign-off. Open a draft pull request unless explicitly prohibited.
- Never merge, deploy, force-push, or rewrite published history.

## Deployment contract

- Documentation or implementation patches do not deploy anything.
- Feature branches and worktrees are never deployed.
- Any future Dokploy deployment must use the exact
  `constitutionalmoney/verus_agent` GitHub repository and track `main`.
- Deployment may occur only after pull-request review and merge.
- The deployed commit must equal the intended `origin/main` SHA.
- Only the repository-controlled compose file explicitly identified in the
  then-current repository instructions may be used.
- `docker-compose.verus-agent.yml` is a standalone local/runtime compose file,
  has no `build:` section, and is not an authorized Dokploy compose file.
- Dokploy status is BLOCKED. No verified Dokploy deployment compose exists.
  Deployment is prohibited until a separate deployment compose, reviewed image
  build, dependency manifest, pinned runtime, secrets boundary, health
  contract, exact-main source contract, and production validation procedure
  are reviewed, committed, and validated.
- Never replace repository Compose with undocumented inline Dokploy config.
- Pre-deployment tests must run against the exact prospective commit before
  commit and again against the merged `main` SHA before production deployment.
- Never print, commit, prompt, or pass production secrets through unsafe command
  arguments.

## Validation and completion

Before committing:

1. inspect `git status`;
2. verify only in-scope files changed;
3. run `git diff --check`;
4. verify every named repository path exists;
5. validate changed YAML, JSON, and TOML without installing new tools;
6. run the public-content scanner;
7. review the complete diff;
8. identify limitations and unresolved implementation defects.

Record exact commands and exit results. Distinguish mock unit/integration tests,
upstream source-contract tests, external Testnet smoke, container build,
deployment, merge, and production validation.

## Repository commands

### Install and build

```powershell
python -m pip install --require-hashes -r requirements.build.lock
python -m pip install --require-hashes -r requirements.runtime.lock
python -m pip install --no-build-isolation --no-deps .
python -m pip wheel --no-build-isolation --no-deps --wheel-dir dist .
docker build --tag verus-agent:test .
```

The Docker build does not run the agent or contact Testnet.

### Mock-based unit and integration tests

```powershell
python -m pip install --require-hashes -r requirements.build.lock
python -m pip install --require-hashes -r requirements.test.lock
python -m pip install --no-build-isolation --no-deps .
pytest tests/ -m "not upstream_contract"
```

These tests use mocks and do not require a live daemon.

### Upstream source-contract tests

```powershell
pytest -m upstream_contract
```

The three tests require `./verus-typescript-primitives`. All skipped is not
validation. Active CI checks out the upstream repository first.

### Testnet smoke

Run only with explicit authorization for external Testnet access:

```powershell
verus-agent --network testnet smoke
```

This is not a unit test. Never change the network to Mainnet.

### Standalone Compose

Configuration validation only:

```powershell
docker compose -f docker-compose.verus-agent.yml config
```

Launch only when explicitly authorized; it initializes against Testnet and is
not a build, test, Dokploy, or production deployment command:

```powershell
docker compose -f docker-compose.verus-agent.yml up -d
docker compose -f docker-compose.verus-agent.yml ps
```
