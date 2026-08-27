# Cross-project activation contract

This repository supplies reusable Verus integration primitives. It does not
decide another application's governance, canonical data model, privacy policy,
or deployment authority.

## Project contract

Before a consuming project activates `verus_agent`, it must create and review a
project-local activation profile based on `activation-profile.example.json`.
The profile must declare:

- the canonical database or source of truth;
- the human and service actor model;
- the private-data boundary;
- explicit non-goals;
- `testnet` as the only network;
- the smallest capability set needed for the current stage.
- the exact reviewed read-only RPC methods, if raw RPC is enabled.

Keep workstation-specific paths and approval records in ignored local files.
Do not add identities, addresses, balances, participant records, private
endpoints, infrastructure details, or unpublished strategy to the profile.

## Activation stages

1. `disabled`: no task capability is accepted.
2. `read_only`: reviewed blockchain reads and local validation only. This is
   the built-in default when no profile is supplied.
3. `wallet_review`: adds offline creation of supported Verus Mobile request
   links. A link or QR code is not wallet authorization. Validate the request
   on the current target device and wallet build.
4. `testnet_write`: may add only a mutation with a complete repository
   verification contract. Version 0.5.0 supports `verus.identity.update` and
   `verus.currency.send`; every other mutation remains blocked.

Promotion is per project and per stage. Success in one project does not
authorize another project, and success for one capability does not authorize a
different capability.

## Mutation contract

Every Testnet mutation requires all of the following:

- an explicit task ID and stable idempotency key;
- an exact, short-lived record in an untracked local operator approval file;
- a `testnet_write` activation profile which names the capability;
- a local SQLite outbox configured by `VERUS_MUTATION_OUTBOX_PATH`;
- single-writer execution through `VerusBlockchainAgent.process_task`;
- a fresh daemon check proving Testnet, the required revision-bearing version,
  peer connectivity, and synchronization immediately before dispatch;
- capability-specific completion evidence;
- operator reconciliation before retrying an unknown or failed outcome.

The approval record is runtime evidence, not cryptographic proof that a human
created it. The organization must keep the human review and approval procedure
separate from the agent which requests the action. Never put approval records,
wallet material, secrets, or production data in prompts or Git.

For `verus.currency.send`, completion means `z_getoperationstatus` reached
`success` and returned the transaction ID. For `verus.identity.update`, the
current identity is read first, the submitted `contentmultimap` is merged with
the current snapshot, and success requires current-state readback of every
submitted field.

## Delegated authentication

An `auth.md` or equivalent delegation layer may be added by a consuming project
only after it defines bounded scopes, expiry, revocation, audit records, and
wallet-mediated human review. Authentication, an allowlist entry, swarm
membership, `verify_only`, and MCP policy are not substitutes for per-mutation
human authorization.

## Deployment boundary

Activation is not deployment. Feature branches and worktrees are never
deployed. This repository has no authorized Dokploy compose file; production
deployment remains prohibited. See `AGENTS.md` for the full deployment
contract.
