# Repository Instructions

## Repository identity

- Repository: `constitutionalmoney/verus_agent`.
- Purpose: executable Python 3.11 Verus Blockchain Specialist Agent with
  local CLI and HTTP JSON-RPC backends, VerusID, DeFi, storage,
  authentication, mobile, MCP, provenance, and optional
  security/marketplace/IP-protection integrations.
- Supporting Markdown files include research, architecture proposals, and
  implementation guidance. They are not proof that a feature is implemented.
- Version: `0.4.0` from `__init__.py`.
- Visibility: PUBLIC repository. Treat all committed content, Git history,
  issues, pull requests, logs, and artifacts as public.
- Never add internal records, unpublished or reconstruction-enabling
  intellectual property, client or participant data, real identity or wallet
  inventories, balances, credentials, wallet material, workstation/VPS
  details, private endpoints, network topology, private notes, or other
  sensitive information. Use synthetic fixtures and placeholders.

## Current status and execution gate

- Status: SOFTWARE REPOSITORY WITH IMPLEMENTED CODE, TESTS, AND
  RESEARCH/REFERENCE DOCUMENTATION.
- Supported source environments include Python 3.11 on Windows and
  Ubuntu/Docker. No generic VPS execution lane is documented.
- Do not treat generic Bitcoin or Ethereum behavior as Verus behavior.
- Retrieve exact Verus references before changing VDXF, VerusID, PBaaS, RPC,
  currency, wallet, or mobile behavior.
- Treat files under `Extras/` and external guides as research/design evidence
  unless behavior is also present in current source and tests.
- Testnet is the source default. A Mainnet code path still exists, so the
  Testnet boundary is not an enforced code guard.
- Never use Mainnet.
- Do not use production infrastructure or production credentials.
- Knowledge and documentation changes must preserve source provenance and
  distinguish source fact, operator policy, inference, and proposal.

## Read before editing

Read whichever of the following files exist before proposing changes:

- `README.md`;
- `AGENTS.md` and `AGENTS.override.md`;
- `pytest.ini`;
- `docker-compose.verus-agent.yml`;
- `verus-agent-smoke.yml`;
- capability allowlists;
- repository manifests and lockfiles, when added;
- `.github/workflows/`, when added;
- architecture, security, mobile, and deployment documentation relevant to
  the requested surface.

Do not invent build, test, deployment, API, blockchain, or repository
behavior. When a command or claim is not verified by current source, stop and
report it as unverified.

## Local operator boundary

When LOCAL_OPERATOR.md exists, read it before local Android, wallet, Verus,
or external-auth testing. LOCAL_OPERATOR.md is ignored, workstation-specific,
and must never be committed.

Do not copy local operator details into source, logs, issues, pull requests,
prompts, test fixtures, or artifacts.

## Architecture and runtime constraints

- The repository currently has no packaging manifest, requirements file,
  dependency lockfile, or Dockerfile. Do not claim that `pip install .`,
  `pip install -e .`, or `pip install -r requirements.txt` is supported.
- `VerusCLI` has two backends:
  - local CLI subprocess, requiring a configured local Verus binary and daemon;
  - HTTP JSON-RPC, used when no valid CLI path is configured.
- Real smoke/runtime operations require a reachable API or daemon and explicit
  authorization for the external Testnet access.
- The source-coded minimum daemon version is `1.2.14-2` when a version is
  detected. Connectivity or version-detection failures currently log a warning
  and allow initialization to continue. This source floor is not evidence that
  it is the current mandatory Verus release; verify the current official
  release and project-specific minimum before any live work.
- Do not perform a blockchain mutation unless the expected network, daemon
  version, connectivity, synchronization state, and relevant identity are
  positively verified.
- UAI integration defaults to enabled in Python but is disabled by the
  standalone Compose configuration. Disable it explicitly when swarm
  registration is not intended.
- MCP is optional and disabled by default. It requires Node.js 18+ and `npx`
  when enabled.
- `updateidentity` is a serialized identity-UTXO operation. The daemon clears
  the current identity UTXO's `contentmultimap` snapshot before applying the
  submitted map, so a submitted map must preserve every current-state entry
  intended to remain. Historical aggregation is separate: entries can
  accumulate across updates, and explicit `contentmultimapremove` actions
  control aggregated removal. Read current state first, update one identity
  serially, wait for confirmation, and verify current and historical reads as
  appropriate.
- `sendcurrency` returns an operation ID, not a completed transaction ID. Poll
  `z_getoperationstatus`; do not claim completion until the operation reports
  success and yields the resulting transaction ID.
- Respect verified on-chain storage, script-element, transaction, and payload
  limits. Do not copy size claims from research material without checking the
  target daemon/version and the exact serialization path.
- The standalone agent health server binds port `9124` and serves `/health`.
- `verus-agent-smoke.yml` is at repository root, not under
  `.github/workflows/`, and is not an active GitHub Actions workflow.

## Blockchain authorization and security

- Require explicit human authorization for every blockchain mutation,
  including identity, currency, transfer, storage, provenance, marketplace,
  trust, mining, staking, signing, or broadcast operations. Capability access,
  an allowlist entry, a test fixture, or prior approval for another operation
  is not authorization.
- Use `run_verus_agent_task.py` for allowlisted automation. Direct
  `agent.process_task`, module handlers, and direct CLI/API calls bypass the
  runner allowlist.
- Allowlist membership is not human approval. The default allowlist contains
  blockchain-write capabilities.
- Swarm security defaults to `disabled`. `verify_only` is observability, not
  enforcement: it does not reject unauthorized requests, and task dispatch
  does not automatically authenticate or authorize every request.
- MCP spending limits, audit logging, read-only mode, and fail-closed write
  behavior apply only when MCP is enabled, connected, and selected for that
  capability. Direct CLI/API writes remain possible when MCP is disabled or no
  connected mapping is used.
- When MCP handles a write and the MCP write fails, never fall back to a direct
  CLI/API write.
- Safety-critical writes should use an available, verified MCP route with
  read/write policy, spending limits, and audit logging, but MCP does not
  replace per-mutation human authorization.
- Never expose RPC credentials, WIFs, private keys, seed phrases, wallet files,
  z-seeds, spending or viewing keys, secret-bearing MCP chain specifications,
  environment values, or signing material in logs, command output, commits,
  prompts, reports, tests, or artifacts.
- Wallet-sensitive mobile operations require explicit, wallet-mediated user
  review and approval. Do not simulate approval or treat a generated QR code or
  deeplink as authorization.
- Testnet smoke checks contact an external blockchain endpoint. They are not
  unit tests and must not be run casually or reported as local-only evidence.

## Git and scope rules

- Never work directly on `main`.
- Handle one bounded GitHub issue or explicitly authorized documentation task
  per implementation run.
- Use an isolated Codex-managed worktree or isolated Git worktree.
- Do not modify unrelated repositories or files.
- Do not stage unrelated changes.
- Use a DCO sign-off for commits.
- Open a draft pull request for changes unless the task explicitly prohibits
  it.
- Do not merge, deploy, or force-push.
- Do not rewrite published history.

## Deployment contract

- This documentation patch does not deploy anything.
- Feature branches and worktrees are never deployed.
- Any future Dokploy deployment must use the exact
  `constitutionalmoney/verus_agent` GitHub repository.
- Dokploy must track branch `main`.
- Deployment may occur only after the pull request is reviewed and merged.
- The deployed commit must equal the intended `origin/main` SHA.
- Only the repository-controlled compose file explicitly identified in the
  then-current repository-specific instructions may be used.
- `docker-compose.verus-agent.yml` is a standalone local/runtime compose file.
  It has no `build:` section and is not an authorized Dokploy deployment
  contract.
- Dokploy deployment status is BLOCKED. No verified Dokploy compose file
  exists. Deployment is prohibited until a separate deployment compose and a
  reviewed image build, dependency manifest, pinned runtime, secrets boundary,
  health contract, and exact-repository-main source contract are reviewed,
  committed, and validated.
- Never replace a repository-controlled compose file with undocumented inline
  Dokploy configuration.
- Local or VPS pre-deployment tests must run against the exact prospective
  commit content before `git commit` and again against the merged `main` SHA
  before any production deployment.
- Production secrets must never be printed, committed, placed in prompts, or
  passed through unsafe command arguments.

## Validation and completion

- Record exact validation commands and exit results.
- Run the checks required by the changed surface; do not substitute unrelated
  checks.
- For documentation-only changes, run documentation, path, syntax, and diff
  validation. Do not claim application tests passed unless they were actually
  run and are relevant.
- Before committing:
  1. inspect `git status`;
  2. verify only authorized files changed;
  3. run `git diff --check`;
  4. verify every named repository file/path exists;
  5. validate changed YAML or JSON without installing dependencies;
  6. review the complete diff;
  7. identify limitations and unresolved implementation defects.
- Before reporting completion, provide the worktree, base branch, task branch,
  files changed, validation commands and exit results, commit SHA, draft pull
  request URL, and deliberate out-of-scope defects.

## Repository commands

### Build

No build command is currently supported. Add packaging metadata or a
Dockerfile through a reviewed change before documenting a build command.

### Unit tests

```powershell
pytest tests/
```

The suite is mock-based and does not require a live daemon. It requires Python
3.11, `pytest`, `pytest-asyncio`, `aiohttp`, and `numpy`. Some optional
IP-protection tests require `cryptography`; PyTorch and `safetensors` are
optional watermarking accelerators. No supported dependency-install command
currently exists.

### Upstream contract tests

```powershell
pytest -m upstream_contract
```

These three source-contract tests skip unless
`./verus-typescript-primitives` exists inside this repository. A zero exit with
all three skipped is not upstream-contract validation.

### Testnet smoke checks

Run only when external Testnet access is explicitly authorized:

```powershell
python run_verus_agent_task.py --network testnet smoke
python run_verus_agent_task.py --network testnet --allowlist-path capability_allowlist.constitutional_money.json smoke
```

These initialize the agent and contact a configured Verus API or daemon. They
are not unit tests. Never change `--network testnet` to Mainnet.

### Standalone Compose validation and launch

Configuration validation only:

```powershell
docker compose -f docker-compose.verus-agent.yml config
```

The following is a standalone runtime launch, not a build, test, Dokploy, or
production deployment command. Run it only when explicitly authorized:

```powershell
docker compose -f docker-compose.verus-agent.yml up -d
docker compose -f docker-compose.verus-agent.yml ps
```
