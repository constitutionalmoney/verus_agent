# Verus Blockchain Specialist Agent

`verus_agent` 0.5.0 is an executable Python 3.11 Verus specialist agent plus
research and reference material. Source modules implement local CLI and HTTP
JSON-RPC backends, VerusID, currency, storage, authentication, mobile, MCP,
provenance, and optional integrations. Markdown proposals and files under
`Extras/` are not proof that a feature is implemented or safe to activate.

This is a public repository. Treat commits, history, issues, pull requests,
logs, and artifacts as public. Never add secrets, wallet material, identities,
balances, real participant/client data, private endpoints, infrastructure
details, or unpublished/reconstruction-enabling intellectual property.

## Safety state

- VRSCTEST is the only accepted network. Mainnet configuration is rejected.
- The built-in activation stage is `read_only`; UAI, MCP, marketplace, IP
  protection, and swarm security default off.
- Initialization fails closed unless `getinfo` positively reports Testnet and
  its revision-bearing daemon version is at least the verified floor
  `1.2.17-6`. The source is the official
  [`v1.2.17-6` release](https://github.com/VerusCoin/VerusCoin/releases/tag/v1.2.17-6),
  checked 2026-08-26. Re-verify it before live work.
- Every new mutation re-checks Testnet, the version floor, peer connectivity,
  and synchronization immediately before dispatch.
- Raw RPC dispatch is limited to reviewed read-only methods. Every other RPC
  requires a scoped mutation context.
- Default runner allowlists contain reads only. Allowlist membership is not
  human approval.
- `verify_only` is observability, not authorization enforcement. MCP safeguards
  apply only while MCP is enabled, connected, and selected for a capability.

Only `verus.identity.update` and `verus.currency.send` currently implement the
complete Testnet write contract. They remain disabled until a project selects
`testnet_write` and supplies an exact local approval and durable outbox. All
other mutations fail closed through task dispatch. See
[`docs/CROSS_PROJECT_ACTIVATION.md`](docs/CROSS_PROJECT_ACTIVATION.md).

## Correct mutation semantics

`updateidentity` replaces the current identity UTXO's `contentmultimap`
snapshot. The manager reads current state and preserves existing keys before
submitting additions, executes identity writes serially, and requires
current-state readback. Historical aggregation and explicit
`contentmultimapremove` actions are separate behavior.

`sendcurrency` returns an operation ID, not a completed transaction ID. The
manager polls `z_getoperationstatus`; success requires a terminal `success`
state and the resulting txid. A timeout, failure, cancellation, or missing txid
is not reported as success.

## Install

Python 3.11 is required. Runtime and test dependencies are resolver-locked with
hashes.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.build.lock
python -m pip install --require-hashes -r requirements.runtime.lock
python -m pip install --no-build-isolation --no-deps .
```

For development tests, use `requirements.test.lock` instead. `pyproject.toml`
is the packaging manifest, `uv.lock` is the complete resolution record, and the
two exported requirements files are the pip/runtime inputs.

## Read-only runner

The smoke command initializes the agent and calls `getinfo` on an external
Testnet API or configured local daemon. Run it only with explicit authorization
for that external access.

```powershell
verus-agent --network testnet smoke
```

Read-only task example:

```powershell
verus-agent --network testnet task `
  --task-id synthetic-read-001 `
  --capability verus.identity.get `
  --params-json '{"name":"Synthetic@"}'
```

Do not place approval records or secrets in `--params-json`. Mutation approval
is supplied only by an untracked local file and must match the task ID,
capability, network, idempotency key, RPC method, and short validity window.

## Verus Mobile v1.1.0-14

The knowledge base now records official Android v1.1.0-14 Gift Cards, VerusPay
V4/burn invoices, experimental User Data, Data Packet, and Identity Update
requests, HTTPS response defaults, encrypted GenericResponses, and expanded
validation. Helpers wrap already encoded Testnet payloads; they do not simulate
wallet review or approval. See
[`docs/VERUS_MOBILE_V1.1.0-14.md`](docs/VERUS_MOBILE_V1.1.0-14.md) and
[`verus-mobile-integration.md`](verus-mobile-integration.md).

## Validation lanes

Mock-based unit and integration tests do not require a daemon:

```powershell
python -m pip install --require-hashes -r requirements.test.lock
python -m pip install --no-deps .
pytest tests/ -m "not upstream_contract"
```

Upstream source-contract tests require a current checkout at
`./verus-typescript-primitives`:

```powershell
pytest -m upstream_contract
```

A zero exit with all three tests skipped is not upstream validation. Active CI
checks out the upstream repository before running this lane. External Testnet
smoke is a separate manual GitHub workflow with an environment approval gate;
it is not a unit test.

## Standalone container and deployment

`Dockerfile` defines a pinned, non-root standalone runtime image.
`docker-compose.verus-agent.yml` remains a local/runtime compose file with no
`build:` section. Neither is an authorized Dokploy deployment contract.

No deployment is performed or authorized by this repository update. Feature
branches and worktrees are never deployed. Dokploy remains blocked because no
reviewed repository-specific deployment compose exists. See `AGENTS.md` for the
complete source/SHA/merge/secrets contract.
